#!/usr/bin/env bash

###############################################################################
# Copyright 2024 AutoX. All Rights Reserved.
###############################################################################
#
# bcc_manager.sh - Unified BCC tools manager for AutoX modules
#
# USAGE:
#   bcc_manager.sh start <module_name> <process_keyword> [options]
#   bcc_manager.sh stop  <module_name>
#   bcc_manager.sh status
#
# OPTIONS:
#   --profile           Enable CPU profiling (profile.py)
#   --offcputime        Enable off-CPU time analysis (offcputime.py)
#   --runqlat           Enable run queue latency (runqlat.py)
#   --syscount          Enable syscall counting (syscount.py)
#   --funclatency=FUNC  Enable function latency for FUNC
#   --frequency=HZ      Sampling frequency for profile (default: 49)
#   --top=N             Top N syscalls to show (default: 20)
#
# Examples:
#   bcc_manager.sh start camera camera_node --profile --offcputime
#   bcc_manager.sh start perception perception_main --syscount --runqlat
#   bcc_manager.sh stop camera
#   bcc_manager.sh status
#
###############################################################################

STORAGE_DIR="/storage/data/perf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse arguments
ACTION=$1
MODULE=$2
PROCESS_KEYWORD=$3
shift 3 2>/dev/null

# Defaults
ENABLE_PROFILE=0
ENABLE_OFFCPUTIME=0
ENABLE_RUNQLAT=0
ENABLE_SYSCOUNT=0
FUNC_PATTERN=""
PROFILE_FREQ=49
TOP_N=20

while [[ $# -gt 0 ]]; do
    case $1 in
        --profile)       ENABLE_PROFILE=1; shift ;;
        --offcputime)    ENABLE_OFFCPUTIME=1; shift ;;
        --runqlat)       ENABLE_RUNQLAT=1; shift ;;
        --syscount)      ENABLE_SYSCOUNT=1; shift ;;
        --funclatency=*) FUNC_PATTERN="${1#*=}"; shift ;;
        --frequency=*)   PROFILE_FREQ="${1#*=}"; shift ;;
        --top=*)         TOP_N="${1#*=}"; shift ;;
        *)               echo "Unknown option: $1"; exit 1 ;;
    esac
done

function check_already_running()
{
    local pattern=$1
    local count
    count=$(ps -elf | grep -c "$pattern")
    if [ "$count" -gt 1 ]; then
        return 0  # already running
    fi
    return 1
}

function create_log_dir()
{
    local module=$1
    local log_date
    log_date=$(date +%Y%m%d_%H:%M:%S)

    if [ ! -d "$STORAGE_DIR" ]; then
        mkdir -p "$STORAGE_DIR"
    fi

    local module_dir="$STORAGE_DIR/$module"
    if [ ! -d "$module_dir" ]; then
        mkdir -p "$module_dir"
    fi

    LOG_DIR="$module_dir/$log_date"
    mkdir -p "$LOG_DIR"
    echo "$LOG_DIR"
}

function get_pid()
{
    local keyword=$1
    ps -elf | grep "$keyword" | head -n 1 | awk '{print $4}'
}

function kill_tool()
{
    local pattern=$1
    ps -elf | grep "$pattern" | awk '{print $4}' | while read -r pid; do
        if [ -n "$pid" ]; then
            sudo kill -2 "$pid" 2>/dev/null
            echo "  Killed PID $pid ($pattern)"
        fi
    done
}

function start_bcc()
{
    local module=$1
    local keyword=$2

    # Check if already running
    if check_already_running "bcc_mgr_${module}"; then
        echo "BCC tools already running for module '$module'"
        return 1
    fi

    local log_dir
    log_dir=$(create_log_dir "$module")

    # Save process info
    local pid
    pid=$(get_pid "$keyword")
    if [ -z "$pid" ]; then
        echo "ERROR: Cannot find process for keyword '$keyword'"
        return 1
    fi

    echo "Module: $module, PID: $pid, Log: $log_dir"
    echo "$pid" > "$log_dir/pid.txt"
    ps -eTlf > "$log_dir/ps.txt"
    ps -eTlf | grep "$pid" > "$log_dir/threads.txt"

    # syscount
    if [ "$ENABLE_SYSCOUNT" -eq 1 ]; then
        if check_already_running "syscnt_${module}"; then
            echo "  syscount already running"
        else
            echo "  Starting syscount (pid=$pid, top=$TOP_N)..."
            sudo "$SCRIPT_DIR/syscount.py" \
                -z "syscnt_${module}" \
                --top="$TOP_N" \
                --pid="$pid" \
                -L -m \
                > "$log_dir/syscount.txt" 2>&1 &
        fi
    fi

    # runqlat
    if [ "$ENABLE_RUNQLAT" -eq 1 ]; then
        if check_already_running "runqlat_${module}"; then
            echo "  runqlat already running"
        else
            echo "  Starting runqlat (pid=$pid)..."
            sudo "$SCRIPT_DIR/runqlat.py" \
                -z "runqlat_${module}" \
                -p "$pid" \
                -mT -L 10 \
                > "$log_dir/runqlat.txt" 2>&1 &
        fi
    fi

    # profile
    if [ "$ENABLE_PROFILE" -eq 1 ]; then
        if check_already_running "profile_${module}"; then
            echo "  profile already running"
        else
            echo "  Starting profile (pid=$pid, freq=${PROFILE_FREQ}Hz)..."
            sudo "$SCRIPT_DIR/profile.py" \
                -p "$pid" \
                -F "$PROFILE_FREQ" \
                -f \
                > "$log_dir/profile.txt" 2>&1 &
        fi
    fi

    # offcputime
    if [ "$ENABLE_OFFCPUTIME" -eq 1 ]; then
        if check_already_running "offcpu_${module}"; then
            echo "  offcputime already running"
        else
            echo "  Starting offcputime (pid=$pid)..."
            sudo "$SCRIPT_DIR/offcputime.py" \
                -p "$pid" \
                -f \
                > "$log_dir/offcputime.txt" 2>&1 &
        fi
    fi

    # funclatency
    if [ -n "$FUNC_PATTERN" ]; then
        if check_already_running "funclat_${module}"; then
            echo "  funclatency already running"
        else
            echo "  Starting funclatency ($FUNC_PATTERN, pid=$pid)..."
            sudo "$SCRIPT_DIR/funclatency.py" \
                -z "funclat_${module}" \
                -m -i 10 -T -p "$pid" \
                "$FUNC_PATTERN" \
                > "$log_dir/funclatency.txt" 2>&1 &
        fi
    fi

    echo ""
    echo "BCC tools started for module '$module'. Logs: $log_dir"
    echo "Run 'bcc_manager.sh stop $module' to stop."
}

function stop_bcc()
{
    local module=$1

    echo "Stopping BCC tools for module '$module'..."
    kill_tool "syscnt_${module}"
    kill_tool "runqlat_${module}"
    kill_tool "profile_${module}"
    kill_tool "offcpu_${module}"
    kill_tool "funclat_${module}"
    echo "Done."
}

function show_status()
{
    echo "=== BCC Tools Status ==="
    echo ""
    echo "syscount processes:"
    ps -elf | grep "syscnt_" | grep -v grep
    echo ""
    echo "runqlat processes:"
    ps -elf | grep "runqlat_" | grep -v grep
    echo ""
    echo "profile processes:"
    ps -elf | grep "profile_" | grep -v grep
    echo ""
    echo "offcputime processes:"
    ps -elf | grep "offcpu_" | grep -v grep
    echo ""
    echo "funclatency processes:"
    ps -elf | grep "funclat_" | grep -v grep
    echo ""
    echo "Log directories:"
    ls -la "$STORAGE_DIR" 2>/dev/null || echo "  (no perf logs found)"
}

# Main
case "$ACTION" in
    start)
        if [ -z "$MODULE" ] || [ -z "$PROCESS_KEYWORD" ]; then
            echo "Usage: $0 start <module_name> <process_keyword> [options]"
            exit 1
        fi
        start_bcc "$MODULE" "$PROCESS_KEYWORD"
        ;;
    stop)
        if [ -z "$MODULE" ]; then
            echo "Usage: $0 stop <module_name>"
            exit 1
        fi
        stop_bcc "$MODULE"
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|status} [args]"
        echo ""
        echo "  start <module> <keyword> [--profile] [--offcputime] [--runqlat] [--syscount] [--funclatency=FUNC]"
        echo "  stop  <module>"
        echo "  status"
        exit 1
        ;;
esac
