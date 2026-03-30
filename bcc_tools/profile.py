#!/usr/bin/python
# @lint-avoid-python-3-compatibility-imports
#
# profile    Profile CPU usage by sampling stack traces at timed intervals.
#            For Linux, uses BCC, eBPF.
#
# USAGE: profile [-h] [-p PID | -t TID] [-U | -K] [-f] [-d] [-F FREQUENCY]
#                [--stack-storage-size SIZE] [duration]
#
# This uses BPF to sample the running process on all CPUs at a specified
# frequency, and capture kernel and user stack traces. The output is a
# folded stack trace suitable for flame graph generation.
#
# Copyright 2016 Netflix, Inc.
# Licensed under the Apache License, Version 2.0

from __future__ import print_function
from bcc import BPF, PerfType, PerfSWConfig
from time import sleep, strftime
import argparse
import signal
import os
import sys

examples = """examples:
    ./profile              # profile stack traces at 49 Hertz until Ctrl-C
    ./profile -F 99       # profile stack traces at 99 Hertz
    ./profile 5            # profile at 49 Hertz for 5 seconds only
    ./profile -f 5         # 5 seconds, and output in folded format
    ./profile -p 185       # only profile PID 185
    ./profile -t 188       # only profile thread 188
    ./profile -U           # only show user space stacks (no kernel)
    ./profile -K           # only show kernel space stacks (no user)
    ./profile -d           # include delimiter between kernel/user stacks
"""
parser = argparse.ArgumentParser(
    description="Profile CPU usage by sampling stack traces",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)
parser.add_argument("-p", "--pid", type=int, help="profile this PID only")
parser.add_argument("-t", "--tid", type=int, help="profile this TID only")
parser.add_argument("-U", "--userstacks", action="store_true",
                    help="show only user space stacks (no kernel)")
parser.add_argument("-K", "--kernelstacks", action="store_true",
                    help="show only kernel space stacks (no user)")
parser.add_argument("-f", "--folded", action="store_true",
                    help="output folded format, one line per stack (for flame graph)")
parser.add_argument("-d", "--delimited", action="store_true",
                    help="insert delimiter between kernel/user stacks")
parser.add_argument("-F", "--frequency", type=int, default=49,
                    help="sample frequency, Hertz (default 49)")
parser.add_argument("--stack-storage-size", type=int, default=1024,
                    help="the number of unique stack traces that can be stored and displayed")
parser.add_argument("-D", "--duration", type=int, default=0,
                    help="total duration of trace, in seconds")
parser.add_argument("--ebpf", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
if args.duration == 0:
    args.duration = 99999999

frequency = args.frequency
if frequency <= 0:
    print("ERROR: frequency must be > 0")
    exit(1)

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct key_t {
    u32 pid;
    u32 tgid;
    int user_stack_id;
    int kernel_stack_id;
};

BPF_HASH(counts, struct key_t, u64);
BPF_STACK_TRACE(stack_traces, STACK_STORAGE_SIZE);

int do_perf_event(struct bpf_perf_event_data *ctx)
{
    u64 id = bpf_get_current_pid_tgid();
    u32 tgid = id >> 32;
    u32 pid = id;

    FILTER_PID
    FILTER_TID

    struct key_t key = {};
    key.pid = pid;
    key.tgid = tgid;

    if (GET_USER_STACK)
        key.user_stack_id = stack_traces.get_stackid(&ctx->regs, BPF_F_USER_STACK);
    else
        key.user_stack_id = -1;

    if (GET_KERNEL_STACK)
        key.kernel_stack_id = stack_traces.get_stackid(&ctx->regs, 0);
    else
        key.kernel_stack_id = -1;

    counts.atomic_increment(key);
    return 0;
}
"""

if args.pid:
    bpf_text = bpf_text.replace('FILTER_PID',
                                'if (tgid != %d) { return 0; }' % args.pid)
else:
    bpf_text = bpf_text.replace('FILTER_PID', '')

if args.tid:
    bpf_text = bpf_text.replace('FILTER_TID',
                                'if (pid != %d) { return 0; }' % args.tid)
else:
    bpf_text = bpf_text.replace('FILTER_TID', '')

if args.kernelstacks:
    bpf_text = bpf_text.replace('GET_USER_STACK', '0')
    bpf_text = bpf_text.replace('GET_KERNEL_STACK', '1')
elif args.userstacks:
    bpf_text = bpf_text.replace('GET_USER_STACK', '1')
    bpf_text = bpf_text.replace('GET_KERNEL_STACK', '0')
else:
    bpf_text = bpf_text.replace('GET_USER_STACK', '1')
    bpf_text = bpf_text.replace('GET_KERNEL_STACK', '1')

bpf_text = bpf_text.replace('STACK_STORAGE_SIZE', str(args.stack_storage_size))

if args.ebpf:
    print(bpf_text)
    exit()

b = BPF(text=bpf_text)
b.attach_perf_event(ev_type=PerfType.SOFTWARE,
                    ev_config=PerfSWConfig.CPU_CLOCK,
                    fn_name="do_perf_event",
                    sample_period=0, sample_freq=frequency)

print("Sampling at %d Hertz of" % frequency, end="")
if args.pid:
    print(" PID %d" % args.pid, end="")
elif args.tid:
    print(" TID %d" % args.tid, end="")
else:
    print(" all threads", end="")
print(" by %s stack for %d secs." % (
    "user + kernel" if not (args.userstacks or args.kernelstacks)
    else ("user" if args.userstacks else "kernel"),
    args.duration))


def signal_ignore(signal, frame):
    print("get kill signal...")
    raise Exception('receive interrupt sig')


signal.signal(signal.SIGINT, signal_ignore)

try:
    sleep(args.duration)
except Exception:
    pass

print()

missing_stacks = 0
counts = b.get_table("counts")
stack_traces = b.get_table("stack_traces")

if args.folded:
    for k, v in sorted(counts.items(), key=lambda counts: counts[1].value):
        # user stack
        user_stack = []
        if k.user_stack_id >= 0:
            user_stack = list(stack_traces.walk(k.user_stack_id))

        # kernel stack
        kernel_stack = []
        if k.kernel_stack_id >= 0:
            kernel_stack = list(stack_traces.walk(k.kernel_stack_id))

        if not user_stack and not kernel_stack:
            missing_stacks += 1
            continue

        line = []
        if kernel_stack:
            line.extend([BPF.ksym(addr) for addr in reversed(kernel_stack)])
        if args.delimited and user_stack and kernel_stack:
            line.append("--")
        if user_stack:
            line.extend([BPF.sym(addr, k.tgid) for addr in reversed(user_stack)])

        print("%s %d" % (";".join(line), v.value))
else:
    for k, v in sorted(counts.items(), key=lambda counts: counts[1].value):
        has_stack = False

        # kernel stack
        if k.kernel_stack_id >= 0:
            print("    %-16s %s" % ("samples", str(v.value)))
            for addr in stack_traces.walk(k.kernel_stack_id):
                print("    %-16x %s" % (addr, BPF.ksym(addr)))
            has_stack = True

        # user stack
        if k.user_stack_id >= 0:
            if not has_stack:
                print("    %-16s %s" % ("samples", str(v.value)))
            for addr in stack_traces.walk(k.user_stack_id):
                print("    %-16x %s" % (addr, BPF.sym(addr, k.tgid)))
            has_stack = True

        if not has_stack:
            missing_stacks += 1
            continue

        print()

if missing_stacks > 0:
    print("WARNING: %d stack traces could not be displayed." % missing_stacks)

print("Detaching...")
