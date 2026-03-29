# Perf Tools 设计文档

## 1. 概述

Perf Tools是一个独立的C++性能分析工具库，基于`~/code/onboard/xrt/tools/perf_recorder`的代码进行重构设计。主要改进：

- 移除protobuf依赖，使用纯C++结构体
- 提供抽象接口供其他项目集成
- 保持Chrome tracing格式输出和TSC比率计算核心功能

## 2. 目录结构

```
perf_tools/
├── include/
│   └── perf_tools/
│       ├── perf_types.h          # 核心数据结构定义
│       ├── perf_exporter.h       # Chrome tracing导出器
│       ├── tsc_calculator.h      # TSC比率计算器
│       └── perf_subscriber.h     # 数据订阅抽象接口
├── src/
│   ├── perf_exporter.cc          # 导出器实现
│   └── tsc_calculator.cc         # 计算器实现
├── tests/
│   ├── perf_types_test.cc        # 数据结构测试
│   ├── tsc_calculator_test.cc    # 计算器测试
│   └── perf_exporter_test.cc     # 导出器测试
├── examples/
│   └── example_usage.cc          # 使用示例
├── BUILD                         # Bazel构建文件
├── README.md                     # 项目说明
└── INTEGRATION_GUIDE.md          # 集成指南
```

## 3. 数据结构设计

### 3.1 原始proto结构（参考）

```protobuf
message Snapshot {
  SnapshotType type = 4;
  uint64 monotonic_tsc = 1;
  uint32 tsc_core = 2;
  double cpu_time = 5;
  double real_time = 6;
  RUsage rusage = 3;
}

message Frame {
  int64 frame_identifier = 1;
  uint64 thread_id = 2;
  string function_name = 3;
  Snapshot start = 4;
  Snapshot end = 5;
  repeated Frame children = 6;
  map<string, Snapshot> samples = 7;
  map<string, string> keyvalues = 8;
  fixed32 process_id = 9;
  TimeUsage time_usage = 10;
}

message PerfStats {
  int64 frame_identifier = 1;
  repeated Frame callstacks = 2;
  double wall_time_creation_s = 3;
  int64 wall_time_creation_tv_sec = 4;
  int64 wall_time_creation_tv_nsec = 5;
  GpuContext gpu_context = 6;
}
```

### 3.2 C++结构体设计

```cpp
namespace perf_tools {

enum class SnapshotType {
  kFull = 0,
  kTscOnly = 1
};

struct RUsage {
  double utime_s = 0.0;
  double stime_s = 0.0;
  // ... 其他字段
};

struct Snapshot {
  SnapshotType type = SnapshotType::kTscOnly;
  uint64_t monotonic_tsc = 0;
  uint32_t tsc_core = 0;
  double cpu_time = 0.0;
  double real_time = 0.0;
  RUsage rusage;
};

struct Frame {
  int64_t frame_identifier = 0;
  uint64_t thread_id = 0;
  uint32_t process_id = 0;
  std::string function_name;
  Snapshot start;
  Snapshot end;
  std::vector<std::shared_ptr<Frame>> children;
  std::unordered_map<std::string, Snapshot> samples;
  std::unordered_map<std::string, std::string> keyvalues;
  TimeUsage time_usage;
};

struct PerfStats {
  int64_t frame_identifier = 0;
  std::vector<std::shared_ptr<Frame>> callstacks;
  double wall_time_creation_s = 0.0;
  int64_t wall_time_creation_tv_sec = 0;
  int64_t wall_time_creation_tv_nsec = 0;
  GpuContext gpu_context;
};

}  // namespace perf_tools
```

## 4. 核心组件

### 4.1 TscCalculator

TSC比率计算器，用于计算TSC频率与实际时间的比率。

**算法说明：**
1. 收集前8个样本
2. 使用接下来的8个样本计算TSC比率
3. 取平均值作为最终比率

**公式：**
```
tsc_ratio = (end_tsc - start_tsc) / (end_wall_time - start_wall_time)
```

### 4.2 ChromeTraceExporter

Chrome tracing格式导出器，将性能数据导出为JSON格式。

**输出格式：**
```json
{
  "traceEvents": [
    {
      "name": "function_name",
      "cat": "PERF",
      "ph": "X",
      "ts": 12345.678,
      "tid": 12345,
      "pid": 100,
      "dur": 500.0,
      "args": {
        "key": "value"
      }
    }
  ]
}
```

### 4.3 PerfDataSubscriber

数据订阅抽象接口，用于从不同数据源获取性能数据。

**接口设计：**
```cpp
class PerfDataCallback {
public:
  virtual void OnPerfData(const PerfStats& stats) = 0;
  virtual void OnError(const std::string& error) = 0;
};

class PerfDataSubscriber {
public:
  virtual bool Start() = 0;
  virtual void Stop() = 0;
  virtual void SetCallback(PerfDataCallbackPtr callback) = 0;
  // ... 其他接口
};
```

## 5. 集成方式

### 5.1 作为Bazel依赖

```python
cc_library(
    name = "your_library",
    deps = [
        "//perf_tools:perf_tools",
    ],
)
```

### 5.2 使用示例

```cpp
#include "perf_tools/perf_types.h"
#include "perf_tools/perf_exporter.h"
#include "perf_tools/tsc_calculator.h"

int main() {
    perf_tools::TscCalculator calculator;
    perf_tools::ChromeTraceExporter exporter("output.json");
    
    exporter.Open();
    
    // 处理性能数据
    for (const auto& stats : data) {
        calculator.Calculate(stats);
        if (calculator.IsCalculated()) {
            exporter.ExportPerfStats(stats, calculator.GetRatio());
        }
    }
    
    exporter.Close();
    return 0;
}
```

## 6. 线程安全

- TscCalculator使用互斥锁保护内部状态
- ChromeTraceExporter使用互斥锁保护文件写入
- 所有公共方法都是线程安全的

## 7. 依赖要求

- C++17或更高版本
- 标准库（<mutex>, <memory>, <vector>等）
- Google Test（用于测试）

## 8. 构建与测试

```bash
# 构建所有目标
bazel build //perf_tools:all

# 运行测试
bazel test //perf_tools:all

# 运行示例
bazel run //perf_tools:example_usage
```
