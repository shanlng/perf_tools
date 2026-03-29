# Perf Tools - 独立性能分析工具库

一个轻量级的C++性能分析工具库，提供Chrome tracing格式输出和TSC（Time Stamp Counter）比率计算功能。

## 特性

- 纯C++结构体实现，无protobuf依赖
- Chrome tracing JSON格式输出
- TSC比率自动计算
- 抽象订阅接口，支持多种数据源集成
- 线程安全设计
- CMake构建系统

## 目录结构

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
├── third_party/
│   └── json/
│       └── json.hpp              # nlohmann/json (vendored)
├── examples/
│   └── example_usage.cc          # 使用示例
├── cmake/
│   └── perf_toolsConfig.cmake.in # CMake导出配置
├── CMakeLists.txt                # CMake构建文件
├── README.md                     # 本文档
└── INTEGRATION_GUIDE.md          # 集成指南
```

## 核心数据结构

### Snapshot
时间快照，记录TSC计数和时间信息。

### Frame
性能帧，包含函数调用信息和子调用栈。

### PerfStats
性能统计数据，包含多个Frame和时间戳信息。

## 抽象接口

### PerfDataSubscriber
数据订阅接口，用于从不同数据源获取性能数据。

### PerfDataCallback
数据回调接口，处理接收到的性能数据。

## 快速开始

### 构建库

```bash
mkdir build && cd build
cmake ..
make
```

### 运行示例

```bash
./build/perf_example
```

### 使用示例

```cpp
#include "perf_tools/perf_types.h"
#include "perf_tools/perf_exporter.h"
#include "perf_tools/tsc_calculator.h"

// 创建TSC计算器
perf_tools::TscCalculator calculator;
calculator.Calculate(/* PerfStats数据 */);

// 创建导出器
perf_tools::ChromeTraceExporter exporter("output.json");

// 导出Frame
exporter.ExportFrame(frame, calculator.GetRatio());
```

## 集成到你的项目

详见 [INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)

### 方式1：作为子目录

```cmake
add_subdirectory(perf_tools)
target_link_libraries(your_target PRIVATE perf_tools::perf_tools)
```

### 方式2：作为已安装库

```cmake
find_package(perf_tools REQUIRED)
target_link_libraries(your_target PRIVATE perf_tools::perf_tools)
```

## 依赖

- C++17或更高版本
- CMake 3.14+
- nlohmann/json (已包含在third_party中)
- Google Test (可选，用于测试)
