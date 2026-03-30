#!/usr/bin/python
# @lint-avoid-python-3-compatibility-imports
#
# offcputime    Summarize off-CPU time by stack trace and task state.
#               For Linux, uses BCC, eBPF.
#
# USAGE: offcputime [-h] [-p PID | -t TID] [-u | -m] [-f] [--state STATE]
#                   [--stack-storage-size SIZE] [duration]
#
# This captures stack traces and task state when a thread leaves the CPU,
# and summarizes them as a folded stack output or an annotated stack trace.
# This helps identify why threads are blocking: I/O wait, lock contention,
# voluntary sleep, etc.
#
# Copyright 2016 Netflix, Inc.
# Licensed under the Apache License, Version 2.0

from __future__ import print_function
from bcc import BPF
from time import sleep, strftime
import argparse
import signal

examples = """examples:
    ./offcputime             # trace off-CPU stack time until Ctrl-C
    ./offcputime 5           # trace for 5 seconds only
    ./offcputime -f 5        # 5 seconds, and output in folded format
    ./offcputime -m 5        # 5 seconds, output in milliseconds
    ./offcputime -p 185      # only trace threads for PID 185
    ./offcputime -t 188      # only trace thread 188
    ./offcputime -u          # show stacks in microseconds (default: ms)
    ./offcputime --state 1   # only trace TASK_INTERRUPTIBLE (D state)
    ./offcputime --state 128 # only trace TASK_WAKEKILL
"""
parser = argparse.ArgumentParser(
    description="Summarize off-CPU time by kernel stack trace",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)
parser.add_argument("-p", "--pid", type=int, help="trace this PID only")
parser.add_argument("-t", "--tid", type=int, help="trace this TID only")
parser.add_argument("-u", "--microseconds", action="store_true",
                    help="microsecond granularity output")
parser.add_argument("-m", "--milliseconds", action="store_true",
                    help="millisecond granularity output")
parser.add_argument("-f", "--folded", action="store_true",
                    help="output folded format, one line per stack (flame graph)")
parser.add_argument("-d", "--duration", type=int, default=0,
                    help="total duration of trace, in seconds")
parser.add_argument("--state", type=int, default=0,
                    help="filter on task state bitmask (e.g. 1=TASK_INTERRUPTIBLE)")
parser.add_argument("--stack-storage-size", type=int, default=1024,
                    help="the number of unique stack traces that can be stored and displayed")
parser.add_argument("--ebpf", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
if args.duration == 0:
    args.duration = 99999999

TASK_INTERRUPTIBLE = 1
TASK_UNINTERRUPTIBLE = 2
TASK_WAKEKILL = 128

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

#define MINBLOCK_US    MINBLOCK_US_VALUE
#define MAXBLOCK_US    MAXBLOCK_US_VALUE

struct key_t {
    u32 pid;
    u32 tgid;
    int user_stack_id;
    int kernel_stack_id;
    u64 state;
};

BPF_HASH(counts, struct key_t, u64);
BPF_HASH(start, u32, u64);
BPF_STACK_TRACE(stack_traces, STACK_STORAGE_SIZE);

int oncpu(struct pt_regs *ctx, struct task_struct *prev)
{
    u32 pid = prev->pid;
    u32 tgid = prev->tgid;
    u64 ts = bpf_ktime_get_ns();

    FILTER_PID

    // record previous thread sleep time
    if (prev->STATE_FIELD & STATE_FILTER) {
        start.update(&pid, &ts);
    }

    // calculate current thread off-CPU time
    u32 cur_pid = bpf_get_current_pid_tgid();
    u32 cur_tgid = bpf_get_current_pid_tgid() >> 32;
    FILTER_PID_CUR
    u64 *tsp = start.lookup(&cur_pid);
    if (tsp == 0) {
        return 0;   // missed start
    }

    u64 delta = bpf_ktime_get_ns() - *tsp;
    start.delete(&cur_pid);

    delta /= 1000U;
    if (FILTER_US_MIN || FILTER_US_MAX) {
        return 0;
    }

    struct key_t key = {};
    key.pid = cur_pid;
    key.tgid = cur_tgid;
    key.state = prev->STATE_FIELD;
    key.user_stack_id = stack_traces.get_stackid(ctx, BPF_F_USER_STACK);
    key.kernel_stack_id = stack_traces.get_stackid(ctx, 0);

    counts.atomic_increment(key, delta);
    return 0;
}
"""

if args.pid:
    bpf_text = bpf_text.replace('FILTER_PID',
                                'if (tgid != %d) { return 0; }' % args.pid)
    bpf_text = bpf_text.replace('FILTER_PID_CUR',
                                'if (cur_tgid != %d) { return 0; }' % args.pid)
elif args.tid:
    bpf_text = bpf_text.replace('FILTER_PID',
                                'if (pid != %d) { return 0; }' % args.tid)
    bpf_text = bpf_text.replace('FILTER_PID_CUR',
                                'if (cur_pid != %d) { return 0; }' % args.tid)
else:
    bpf_text = bpf_text.replace('FILTER_PID', '')
    bpf_text = bpf_text.replace('FILTER_PID_CUR', '')

state_filter = args.state if args.state else \
    (TASK_INTERRUPTIBLE | TASK_UNINTERRUPTIBLE | TASK_WAKEKILL)
bpf_text = bpf_text.replace('STATE_FILTER', str(state_filter))

bpf_text = bpf_text.replace('MINBLOCK_US_VALUE', '1')
bpf_text = bpf_text.replace('MAXBLOCK_US_VALUE', str(1 << 63))
bpf_text = bpf_text.replace('STACK_STORAGE_SIZE', str(args.stack_storage_size))

min_us = 1
max_us = 1 << 63
bpf_text = bpf_text.replace('FILTER_US_MIN', 'delta < %d' % min_us)
bpf_text = bpf_text.replace('FILTER_US_MAX', 'delta > %d' % max_us)

# task state field
if BPF.kernel_struct_has_field(b'task_struct', b'__state') == 1:
    bpf_text = bpf_text.replace('STATE_FIELD', '__state')
else:
    bpf_text = bpf_text.replace('STATE_FIELD', 'state')

if args.ebpf:
    print(bpf_text)
    exit()

b = BPF(text=bpf_text)
b.attach_kprobe(event_re="^finish_task_switch$|^finish_task_switch\.isra\.\d$",
                fn_name="oncpu")

if args.microseconds:
    label = "usecs"
    divisor = 1
elif args.milliseconds:
    label = "msecs"
    divisor = 1000
else:
    label = "msecs"
    divisor = 1000

print("Tracing off-CPU time (us) of", end="")
if args.pid:
    print(" PID %d" % args.pid, end="")
elif args.tid:
    print(" TID %d" % args.tid, end="")
else:
    print(" all threads", end="")
print(" by kernel + user stack for %d secs." % args.duration)


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
has_enomem = False
counts = b.get_table("counts")
stack_traces = b.get_table("stack_traces")


def get_state_name(state):
    states = []
    if state & TASK_INTERRUPTIBLE:
        states.append("S")
    if state & TASK_UNINTERRUPTIBLE:
        states.append("D")
    if state & TASK_WAKEKILL:
        states.append("K")
    return "|".join(states) if states else str(state)


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

        # folded output
        line = []
        if kernel_stack:
            line.extend([BPF.sym(addr, k.tgid) for addr in reversed(kernel_stack)])
        if user_stack:
            line.extend([BPF.ksym(addr) for addr in reversed(user_stack)])

        print("%s %d" % (";".join(line), v.value / divisor))
else:
    for k, v in sorted(counts.items(), key=lambda counts: counts[1].value):
        # user stack
        user_stack = list(stack_traces.walk(k.user_stack_id)) \
            if k.user_stack_id >= 0 else []
        # kernel stack
        kernel_stack = list(stack_traces.walk(k.kernel_stack_id)) \
            if k.kernel_stack_id >= 0 else []

        if not user_stack and not kernel_stack:
            missing_stacks += 1
            continue

        state_name = get_state_name(k.state)
        print("    %-16s [%s] (%s, pid %d, tgid %d, %s)" % (
            "offcpu", state_name,
            b.get_table("counts").key_str(k), k.pid, k.tgid, label))

        # kernel stack
        for addr in kernel_stack:
            sym = BPF.ksym(addr)
            print("    %-16x %s" % (addr, sym))

        # user stack
        for addr in user_stack:
            sym = BPF.sym(addr, k.tgid)
            print("    %-16x %s" % (addr, sym))

        print("        %d\n" % (v.value / divisor))

if missing_stacks > 0:
    enomem_stacks = bpf_text.count("16 ENOMEMs")  # approximate
    print("WARNING: %d stack traces could not be displayed." % missing_stacks)

print("Detaching...")
