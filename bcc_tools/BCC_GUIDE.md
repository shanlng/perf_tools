# BCC Tools 使用教程

AutoX 车载系统性能分析工具集，基于 eBPF/BCC 框架实现。

## 目录

1. [环境要求](#环境要求)
2. [工具概览](#工具概览)
3. [工具详解](#工具详解)
   - [funclatency - 函数延迟分析](#funclatency)
   - [runqlat - 调度队列延迟](#runqlat)
   - [syscount - 系统调用统计](#syscount)
   - [offcputime - 离 CPU 时间分析](#offcputime)
   - [profile - CPU 采样分析](#profile)
4. [统一管理脚本](#统一管理脚本)
5. [典型诊断场景](#典型诊断场景)
6. [火焰图生成](#火焰图生成)
7. [注意事项](#注意事项)

---

## 环境要求

```bash
# 确认 BCC 已安装
python3 -c "from bcc import BPF; print('BCC OK')"

# 确认内核支持
uname -r  # 需要 4.9+ 内核，推荐 4.14+

# 权限：所有工具需要 root 或 CAP_BPF + CAP_PERFMON
sudo -v
```

---

## 工具概览

| 工具 | 用途 | 分析粒度 | 关键事件 |
|---|---|---|---|
| `funclatency` | 函数调用延迟 | 函数级 | kprobe/uprobe entry+return |
| `runqlat` | CPU 调度等待 | 任务级 | sched_switch/sched_wakeup |
| `syscount` | 系统调用统计 | syscall 级 | sys_enter/sys_exit |
| `offcputime` | 线程阻塞原因 | 栈帧级 | finish_task_switch |
| `profile` | CPU 热点采样 | 栈帧级 | perf CPU_CLOCK |

---

## 工具详解

### funclatency

测量指定函数的调用耗时，输出延迟分布直方图。

**支持追踪目标：**
- 内核函数：`do_sys_open`, `vfs_read`, `__alloc_pages_nodemask` 等
- 用户库函数：`c:read`, `c:malloc`, `c:*printf` 等

**基本用法：**
```bash
# 追踪内核函数 do_sys_open 的延迟（纳秒）
sudo ./funclatency do_sys_open

# 追踪 C 库 read() 函数（微秒）
sudo ./funclatency -u c:read

# 毫秒级输出 + 时间戳，每 5 秒输出一次
sudo ./funclatency -mT -i 5 vfs_read

# 只看 PID 为 1234 的进程
sudo ./funclatency -p 1234 vfs_read

# 通配符匹配：追踪所有 vfs_fstat* 函数
sudo ./funclatency 'vfs_fstat*'

# 持续 30 秒，每 5 秒输出
sudo ./funclatency -i 5 -d 30 do_sys_open

# 支持嵌套/递归调用追踪（栈深度 3）
sudo ./funclatency -l 3 do_sys_open
```

**输出解读：**
```
Tracing 1 functions for "do_sys_open"... Hit Ctrl-C to end.

     msecs               : count     distribution
         0 -> 1          : 45       |****************************************|
         2 -> 3          : 3        |***                                     |
         4 -> 7          : 1        |*                                       |

avg = 0 msecs, total: 49 msecs, count: 49
```

- 上方为对数直方图（log2 buckets），展示延迟分布
- 下方为平均值、总延迟、调用次数

**自动驾驶场景应用：**
```bash
# Camera select 调用延迟
sudo ./funclatency -mT -i 10 -p $CAM_PID kern_select

# 内存页分配延迟（高延迟说明内存压力大）
sudo ./funclatency -mT -i 10 -p $PID __alloc_pages_nodemask

# 内存回收延迟
sudo ./funclatency -mT -i 10 -p $PID shrink_inactive_list
```

---

### runqlat

测量任务从进入就绪队列到被调度执行的等待时间。

**基本用法：**
```bash
# 全系统 run queue 延迟直方图（微秒）
sudo ./runqlat

# 毫秒输出 + 时间戳，每 1 秒输出，共 10 次
sudo ./runqlat -mT 1 10

# 只看 PID 185
sudo ./runqlat -p 185

# 按 PID 分组显示
sudo ./runqlat -P

# 按线程 ID 分组
sudo ./runqlat -L
```

**输出解读：**
```
Tracing run queue latency... Hit Ctrl-C to end.

     usecs               : count     distribution
         0 -> 1          : 1023     |****************************************|
         2 -> 3          : 45       |**                                      |
         4 -> 7          : 12       |*                                       |
         8 -> 15         : 3        |                                        |
```

**延迟含义：**
- 0-10us：正常，CPU 资源充足
- 10-100us：轻度争用
- 100us-1ms：中度争用，可能需要降低 CPU 负载
- >1ms：严重争用，系统过载

**自动驾驶场景应用：**
```bash
# Camera 线程调度延迟（高延迟可能导致帧丢失）
sudo ./runqlat -mT -p $CAM_PID 1

# Perception 线程按线程 ID 分组
sudo ./runqlat -p $PERCEPTION_PID -L -mT 1
```

---

### syscount

统计系统调用次数和延迟。

**基本用法：**
```bash
# 按 syscall 统计调用次数，显示 top 10
sudo ./syscount

# 显示 top 20
sudo ./syscount --top=20

# 按进程统计
sudo ./syscount -P

# 统计延迟（只记录超过 105ms 的慢调用）
sudo ./syscount -L

# 延迟模式 + 毫秒显示
sudo ./syscount -L -m

# 只统计某个进程
sudo ./syscount -p 1234

# 只统计失败的 syscall
sudo ./syscount -x

# 每 5 秒输出一次
sudo ./syscount -i 5

# 列出所有可追踪的 syscall 名称
sudo ./syscount -l
```

**输出解读：**
```
Tracing syscalls, printing top 10... Ctrl+C to quit.
[14:30:15]
SYSCALL                 COUNT
read                     12450
write                     8923
ioctl                     5612
poll                      3456
...
```

**延迟模式输出：**
```
[14:30:15]
SYSCALL                 COUNT       TIME (us)
ppoll                       3       234567.890
futex                       2       156789.123
```

**自动驾驶场景应用：**
```bash
# Camera 进程的慢系统调用分析
sudo ./syscount -p $CAM_PID -L -m --top=20

# 按进程分析整个系统的 syscall 热点
sudo ./syscount -P --top=20 -i 5
```

---

### offcputime

当线程离开 CPU 时捕获调用栈，分析线程阻塞原因。这是 **runqlat 的升级版**，能区分：
- 调度等待（run queue 竞争）
- I/O 阻塞（读写磁盘/网络）
- 锁等待（mutex/futex）
- 主动休眠（nanosleep）

**基本用法：**
```bash
# 采样所有线程的 off-CPU 栈，持续直到 Ctrl-C
sudo ./offcputime

# 采样 5 秒
sudo ./offcputime 5

# 只看 PID 185
sudo ./offcputime -p 185

# 只看线程 188
sudo ./offcputime -t 188

# 输出 folded 格式（用于火焰图）
sudo ./offcputime -f 5

# 微秒级输出
sudo ./offcputime -u 5

# 只追踪 TASK_UNINTERRUPTIBLE 状态（D 状态，通常是 I/O 阻塞）
sudo ./offcputime --state 2 5

# 只追踪 TASK_INTERRUPTIBLE 状态（S 状态，可中断等待）
sudo ./offcputime --state 1 5
```

**输出解读（folded 格式，适合火焰图）：**
```
finish_task_switch;__schedule;schedule;io_schedule;... 23456
```

每行一个调用栈，末尾数字是该栈累计的 off-CPU 时间（微秒）。

**任务状态码：**

| 状态值 | 名称 | 含义 |
|---|---|---|
| 1 | S (TASK_INTERRUPTIBLE) | 可中断睡眠（锁、信号等待） |
| 2 | D (TASK_UNINTERRUPTIBLE) | 不可中断睡眠（I/O 等待） |
| 4 | T (TASK_STOPPED) | 停止（被 ptrace/信号） |
| 128 | K (TASK_WAKEKILL) | 致命信号唤醒 |

**自动驾驶场景应用：**
```bash
# Camera 线程为什么阻塞？
sudo ./offcputime -p $CAM_PID -f 10 > offcpu_folded.txt

# 只看 I/O 阻塞（D 状态）
sudo ./offcputime -p $CAM_PID --state 2 -f 10 > io_blocked.txt
```

---

### profile

定时采样 CPU 上运行的线程栈，生成 CPU 热点分析。这是生成 **CPU 火焰图** 的标准方法。

**基本用法：**
```bash
# 默认 49Hz 采样
sudo ./profile

# 99Hz 采样，持续 5 秒
sudo ./profile -F 99 5

# 只看 PID 185
sudo ./profile -p 185

# 只看线程 188
sudo ./profile -t 188

# 只采样用户空间栈
sudo ./profile -U

# 只采样内核空间栈
sudo ./profile -K

# folded 格式输出（火焰图输入）
sudo ./profile -f 5

# 内核/用户栈之间插入分隔符
sudo ./profile -fd 5
```

**输出解读（folded 格式）：**
```
schedule;io_schedule;__blkdev_direct_IO;...;read 345
```

每行一个调用栈，末尾数字是该栈被采样到的次数。

**频率选择建议：**
- 49 Hz：轻量级，对系统影响 < 1%
- 99 Hz：推荐的生产环境频率
- 997 Hz：详细分析，注意性能开销

**自动驾驶场景应用：**
```bash
# Perception 模块的 CPU 热点
sudo ./profile -p $PERCEPTION_PID -F 99 -f 5 > cpu_profile.txt

# 只分析用户空间（排除内核开销干扰）
sudo ./profile -p $PID -U -f 5 > user_cpu.txt
```

---

## 统一管理脚本

`bcc_manager.sh` 提供一键启动/停止多个 BCC 工具的功能。

**用法：**
```bash
# 启动：对 camera 模块运行 profile + offcputime
sudo ./bcc_manager.sh start camera camera_node --profile --offcputime

# 启动：对 perception 模块运行全套分析
sudo ./bcc_manager.sh start perception perception_main \
    --profile --offcputime --runqlat --syscount

# 启动：对 camera 模块增加 funclatency
sudo ./bcc_manager.sh start camera camera_node \
    --syscount --funclatency=kern_select

# 查看所有正在运行的 BCC 工具
sudo ./bcc_manager.sh status

# 停止 camera 模块的所有 BCC 工具
sudo ./bcc_manager.sh stop camera
```

**日志位置：**
```
/storage/data/perf/<module>/<timestamp>/
├── pid.txt           # 进程 ID
├── ps.txt            # 完整进程列表
├── threads.txt       # 相关线程列表
├── syscount.txt      # syscall 统计
├── runqlat.txt       # 调度延迟
├── profile.txt       # CPU 采样
├── offcputime.txt    # 离 CPU 栈
└── funclatency.txt   # 函数延迟
```

---

## 典型诊断场景

### 场景 1：帧率下降 / 延迟增加

```bash
# 第一步：确认是 CPU 竞争还是 I/O 阻塞
sudo ./runqlat -mT -p $PID 1

# 第二步：如果是调度问题，用 profile 找 CPU 热点
sudo ./profile -p $PID -F 99 -f 5 > hotspot.txt

# 第三步：如果 runqlat 正常但仍有延迟，用 offcputime 找阻塞原因
sudo ./offcputime -p $PID -f 5 > blocked.txt

# 第四步：检查是否 syscall 过多
sudo ./syscount -p $PID -L -m --top=20
```

### 场景 2：内存压力导致的卡顿

```bash
# 页面分配延迟
sudo ./funclatency -mT -i 10 -p $PID __alloc_pages_nodemask

# 内存回收延迟
sudo ./funclatency -mT -i 10 -p $PID shrink_inactive_list

# OOM 事件（需要 oomkill 工具）
sudo ./oomkill
```

### 场景 3：系统调用瓶颈

```bash
# 找出最慢的系统调用
sudo ./syscount -L -m --top=20

# 特定进程的 syscall 分析
sudo ./syscount -p $PID -L -m

# 找出失败的 syscall
sudo ./syscount -p $PID -x
```

---

## 火焰图生成

BCC 工具的 folded 输出可以配合 Brendan Gregg 的 FlameGraph 工具生成可视化火焰图。

```bash
# 1. 安装 FlameGraph
git clone https://github.com/brendangregg/FlameGraph.git

# 2. 采集 CPU 火焰图数据
sudo ./profile -p $PID -F 99 -f 30 > cpu_folded.txt

# 3. 生成 SVG
FlameGraph/flamegraph.pl cpu_folded.txt > cpu_flame.svg

# 4. 采集 Off-CPU 火焰图数据
sudo ./offcputime -p $PID -f 30 > offcpu_folded.txt

# 5. 生成 Off-CPU 火焰图
FlameGraph/flamegraph.pl --color=io --title="Off-CPU Time" \
    offcpu_folded.txt > offcpu_flame.svg
```

---

## 注意事项

### 性能开销

| 工具 | 典型开销 | 说明 |
|---|---|---|
| `funclatency` | <1% CPU | 取决于函数调用频率 |
| `runqlat` | <0.5% CPU | 仅在调度事件时触发 |
| `syscount` | <1% CPU | 每次 syscall 触发 |
| `offcputime` | 1-3% CPU | 每次上下文切换触发 |
| `profile` | 0.5-2% CPU | 取决于采样频率 |

### 安全注意事项

1. **生产环境建议频率 ≤ 99Hz**，避免影响实时性
2. **长时间运行前先短时间测试**，确认不影响目标模块
3. **优先使用 PID 过滤**，减少数据量和开销
4. **磁盘写入日志时注意空间**，profile 数据量较大

### 常见问题

**Q: 提示 "BPF program is too large"**
A: 内核版本较低，BPF 程序复杂度受限。升级内核或减少追踪目标。

**Q: 提示 "cannot attach kprobe"**
A: 函数可能被内联。尝试 `kallsyms` 中存在的函数名，或加 `--ebpf` 查看实际生成的 BPF 代码。

**Q: profile 输出为空**
A: 目标进程可能处于 sleep 状态。确认进程正在运行。

**Q: offcputime 提示 stack traces could not be displayed**
A: 栈太深或 BPF stack map 满了。尝试增大 `--stack-storage-size` 或限制 PID。

---

## 文件清单

```
bcc_tools/
├── funclatency.py    # 函数延迟分析（移植自 onboard/system/bcc）
├── runqlat.py        # 调度队列延迟（移植自 onboard/system/bcc）
├── syscount.py       # 系统调用统计（移植自 onboard/system/bcc）
├── offcputime.py     # 离 CPU 时间分析（新增）
├── profile.py        # CPU 采样分析（新增）
├── bcc_manager.sh    # 统一管理脚本（新增）
├── BUILD             # Bazel 构建文件
└── BCC_GUIDE.md      # 本文档
```
