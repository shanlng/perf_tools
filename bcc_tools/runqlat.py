#!/usr/bin/python
# @lint-avoid-python-3-compatibility-imports
#
# runqlat   Run queue (scheduler) latency as a histogram.
#           For Linux, uses BCC, eBPF.
#
# USAGE: runqlat [-h] [-T] [-m] [-P] [-L] [-z] [-p PID] [interval] [count]
#
# This measures the time a task spends waiting on a run queue for a turn
# on-CPU, and shows this time as a histogram.
#
# Copyright 2016 Netflix, Inc.
# Licensed under the Apache License, Version 2.0

from __future__ import print_function
from bcc import BPF
from time import sleep, strftime
import argparse
import signal

examples = """examples:
    ./runqlat            # summarize run queue latency as a histogram
    ./runqlat 1 10       # print 1 second summaries, 10 times
    ./runqlat -mT 1      # 1s summaries, milliseconds, and timestamps
    ./runqlat -P         # show each PID separately
    ./runqlat -p 185     # trace PID 185 only
"""
parser = argparse.ArgumentParser(
    description="Summarize run queue (scheduler) latency as a histogram",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog=examples)
parser.add_argument("-T", "--timestamp", action="store_true",
                    help="include timestamp on output")
parser.add_argument("-m", "--milliseconds", action="store_true",
                    help="millisecond histogram")
parser.add_argument("-P", "--pids", action="store_true",
                    help="print a histogram per process ID")
parser.add_argument("--pidnss", action="store_true",
                    help="print a histogram per PID namespace")
parser.add_argument("-L", "--tids", action="store_true",
                    help="print a histogram per thread ID")
parser.add_argument("-p", "--pid", help="trace this PID only")
parser.add_argument("-z", "--taskname", type=str, help="name of task")
parser.add_argument("interval", nargs="?", default=99999999,
                    help="output interval, in seconds")
parser.add_argument("count", nargs="?", default=99999999,
                    help="number of outputs")
parser.add_argument("--ebpf", action="store_true", help=argparse.SUPPRESS)
args = parser.parse_args()
countdown = int(args.count)
debug = 0

bpf_text = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>
#include <linux/nsproxy.h>
#include <linux/pid_namespace.h>
#include <linux/init_task.h>

typedef struct pid_key {
    u64 id;
    u64 slot;
} pid_key_t;

typedef struct pidns_key {
    u64 id;
    u64 slot;
} pidns_key_t;

BPF_HASH(start, u32);
STORAGE

struct rq;

static int trace_enqueue(u32 tgid, u32 pid)
{
    if (FILTER || pid == 0)
        return 0;
    u64 ts = bpf_ktime_get_ns();
    start.update(&pid, &ts);
    return 0;
}

static __always_inline unsigned int pid_namespace(struct task_struct *task)
{

#ifdef INIT_PID_LINK
    struct pid_link pids;
    unsigned int level;
    struct upid upid;
    struct ns_common ns;

    bpf_probe_read_kernel(&pids, sizeof(pids), &task->pids[PIDTYPE_PID]);
    bpf_probe_read_kernel(&level, sizeof(level), &pids.pid->level);
    bpf_probe_read_kernel(&upid, sizeof(upid), &pids.pid->numbers[level]);
    bpf_probe_read_kernel(&ns, sizeof(ns), &upid.ns->ns);

    return ns.inum;
#else
    struct pid *pid;
    unsigned int level;
    struct upid upid;
    struct ns_common ns;

    bpf_probe_read_kernel(&pid, sizeof(pid), &task->thread_pid);
    bpf_probe_read_kernel(&level, sizeof(level), &pid->level);
    bpf_probe_read_kernel(&upid, sizeof(upid), &pid->numbers[level]);
    bpf_probe_read_kernel(&ns, sizeof(ns), &upid.ns->ns);

    return ns.inum;
#endif
}
"""

bpf_text_kprobe = """
int trace_wake_up_new_task(struct pt_regs *ctx, struct task_struct *p)
{
    return trace_enqueue(p->tgid, p->pid);
}

int trace_ttwu_do_wakeup(struct pt_regs *ctx, struct rq *rq, struct task_struct *p,
    int wake_flags)
{
    return trace_enqueue(p->tgid, p->pid);
}

int trace_run(struct pt_regs *ctx, struct task_struct *prev)
{
    u32 pid, tgid;

    // ivcsw: treat like an enqueue event and store timestamp
    if (prev->STATE_FIELD == TASK_RUNNING) {
        tgid = prev->tgid;
        pid = prev->pid;
        if (!(FILTER || pid == 0)) {
            u64 ts = bpf_ktime_get_ns();
            start.update(&pid, &ts);
        }
    }

    tgid = bpf_get_current_pid_tgid() >> 32;
    pid = bpf_get_current_pid_tgid();
    if (FILTER || pid == 0)
        return 0;
    u64 *tsp, delta;

    tsp = start.lookup(&pid);
    if (tsp == 0) {
        return 0;   // missed enqueue
    }
    delta = bpf_ktime_get_ns() - *tsp;
    FACTOR

    STORE

    start.delete(&pid);
    return 0;
}
"""

bpf_text_raw_tp = """
RAW_TRACEPOINT_PROBE(sched_wakeup)
{
    struct task_struct *p = (struct task_struct *)ctx->args[0];
    return trace_enqueue(p->tgid, p->pid);
}

RAW_TRACEPOINT_PROBE(sched_wakeup_new)
{
    struct task_struct *p = (struct task_struct *)ctx->args[0];
    return trace_enqueue(p->tgid, p->pid);
}

RAW_TRACEPOINT_PROBE(sched_switch)
{
    struct task_struct *prev = (struct task_struct *)ctx->args[1];
    struct task_struct *next = (struct task_struct *)ctx->args[2];
    u32 pid, tgid;

    if (prev->STATE_FIELD == TASK_RUNNING) {
        tgid = prev->tgid;
        pid = prev->pid;
        if (!(FILTER || pid == 0)) {
            u64 ts = bpf_ktime_get_ns();
            start.update(&pid, &ts);
        }
    }

    tgid = next->tgid;
    pid = next->pid;
    if (FILTER || pid == 0)
        return 0;
    u64 *tsp, delta;

    tsp = start.lookup(&pid);
    if (tsp == 0) {
        return 0;   // missed enqueue
    }
    delta = bpf_ktime_get_ns() - *tsp;
    FACTOR

    STORE

    start.delete(&pid);
    return 0;
}
"""

is_support_raw_tp = BPF.support_raw_tracepoint()
if is_support_raw_tp:
    bpf_text += bpf_text_raw_tp
else:
    bpf_text += bpf_text_kprobe

# code substitutions
if BPF.kernel_struct_has_field(b'task_struct', b'__state') == 1:
    bpf_text = bpf_text.replace('STATE_FIELD', '__state')
else:
    bpf_text = bpf_text.replace('STATE_FIELD', 'state')
if args.pid:
    bpf_text = bpf_text.replace('FILTER', 'tgid != %s' % args.pid)
else:
    bpf_text = bpf_text.replace('FILTER', '0')
if args.milliseconds:
    bpf_text = bpf_text.replace('FACTOR', 'delta /= 1000000;')
    label = "msecs"
else:
    bpf_text = bpf_text.replace('FACTOR', 'delta /= 1000;')
    label = "usecs"
if args.pids or args.tids:
    section = "pid"
    pid = "tgid"
    if args.tids:
        pid = "pid"
        section = "tid"
    bpf_text = bpf_text.replace('STORAGE', 'BPF_HISTOGRAM(dist, pid_key_t);')
    bpf_text = bpf_text.replace(
        'STORE', 'pid_key_t key = {.id = ' + pid +
        ', .slot = bpf_log2l(delta)}; ' + 'dist.increment(key);')
elif args.pidnss:
    section = "pidns"
    bpf_text = bpf_text.replace('STORAGE', 'BPF_HISTOGRAM(dist, pidns_key_t);')
    bpf_text = bpf_text.replace(
        'STORE', 'pidns_key_t key = ' + '{.id = pid_namespace(prev), ' +
        '.slot = bpf_log2l(delta)}; dist.atomic_increment(key);')
else:
    section = ""
    bpf_text = bpf_text.replace('STORAGE', 'BPF_HISTOGRAM(dist);')
    bpf_text = bpf_text.replace('STORE',
                                'dist.atomic_increment(bpf_log2l(delta));')
if debug or args.ebpf:
    print(bpf_text)
    if args.ebpf:
        exit()

b = BPF(text=bpf_text)
if not is_support_raw_tp:
    b.attach_kprobe(event="ttwu_do_wakeup", fn_name="trace_ttwu_do_wakeup")
    b.attach_kprobe(event="wake_up_new_task", fn_name="trace_wake_up_new_task")
    b.attach_kprobe(
        event_re="^finish_task_switch$|^finish_task_switch\.isra\.\d$",
        fn_name="trace_run")

print("Tracing run queue latency... Hit Ctrl-C to end.")


def signal_ignore(signal, frame):
    print("get kill signal...")
    raise Exception('receive interrupt sig')


signal.signal(signal.SIGINT, signal_ignore)
exiting = 0 if args.interval else 1
dist = b.get_table("dist")
while (1):
    try:
        sleep(int(args.interval))
    except Exception:
        exiting = 1

    print()
    if args.timestamp:
        print("%-8s\n" % strftime("%H:%M:%S"), end="")

    dist.print_log2_hist(label, section, section_print_fn=int)
    dist.clear()

    countdown -= 1
    if exiting or countdown == 0:
        exit()
