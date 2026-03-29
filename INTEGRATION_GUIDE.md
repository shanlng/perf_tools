# Perf Tools 集成指南

## 概述

Perf Tools是一个轻量级的C++性能分析工具库，提供以下核心功能：
- Chrome tracing格式输出
- TSC（Time Stamp Counter）比率计算
- 抽象数据订阅接口

## 快速开始

### 方式1：作为子目录集成

将perf_tools目录复制到你的项目中，然后在CMakeLists.txt中添加：

```cmake
add_subdirectory(perf_tools)
target_link_libraries(your_target PRIVATE perf_tools::perf_tools)
```

### 方式2：作为已安装库集成

1. 先构建并安装perf_tools：

```bash
cd perf_tools
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=/usr/local
make
sudo make install
```

2. 在你的项目中使用：

```cmake
find_package(perf_tools REQUIRED)
target_link_libraries(your_target PRIVATE perf_tools::perf_tools)
```

### 方式3：手动埋点（无需集成整个库）

如果你只需要核心功能，可以直接复制以下文件到你的项目：
- `include/perf_tools/perf_types.h`
- `include/perf_tools/perf_exporter.h`
- `include/perf_tools/tsc_calculator.h`
- `src/perf_exporter.cc`
- `src/tsc_calculator.cc`
- `third_party/json/json.hpp`

然后在你的CMakeLists.txt中添加：

```cmake
add_library(perf_tools STATIC
    perf_exporter.cc
    tsc_calculator.cc
)
target_include_directories(perf_tools PUBLIC include)
```

## 基本使用

```cpp
#include "perf_tools/perf_types.h"
#include "perf_tools/perf_exporter.h"
#include "perf_tools/tsc_calculator.h"

// 创建TSC计算器
perf_tools::TscCalculator calculator;

// 创建Chrome tracing导出器
perf_tools::ChromeTraceExporter exporter("output.json");

// 打开导出文件
if (!exporter.Open()) {
    // 处理错误
}

// 处理性能数据
for (const auto& stats : received_stats) {
    // 计算TSC比率
    calculator.Calculate(stats);
    
    // 导出数据
    if (calculator.IsCalculated()) {
        exporter.ExportPerfStats(stats, calculator.GetRatio());
    }
}

// 关闭导出器
exporter.Close();
```

## 实现自定义数据订阅接口

要将perf_tools集成到你的系统中，需要实现`PerfDataSubscriber`接口：

```cpp
#include "perf_tools/perf_subscriber.h"
#include "perf_tools/perf_types.h"

class MyDataSubscriber : public perf_tools::PerfDataSubscriber {
public:
    MyDataSubscriber() = default;
    ~MyDataSubscriber() override = default;

    bool Start() override {
        // 启动你的数据源（如消息队列、共享内存等）
        running_ = true;
        return true;
    }

    void Stop() override {
        running_ = false;
    }

    bool IsRunning() const override {
        return running_;
    }

    void SetCallback(perf_tools::PerfDataCallbackPtr callback) override {
        callback_ = callback;
    }

    void SetHandler(perf_tools::PerfDataHandler handler) override {
        handler_ = handler;
    }

    std::vector<std::string> GetAvailableChannels() const override {
        // 返回可用的数据通道
        return {"channel1", "channel2"};
    }

    bool SubscribeChannel(const std::string& channel) override {
        // 订阅指定通道
        return true;
    }

    void UnsubscribeChannel(const std::string& channel) override {
        // 取消订阅
    }

private:
    bool running_ = false;
    perf_tools::PerfDataCallbackPtr callback_;
    perf_tools::PerfDataHandler handler_;
};
```

## 数据格式说明

### Frame结构

```cpp
struct Frame {
  int64_t frame_identifier = 0;      // 帧标识符
  uint64_t thread_id = 0;            // 线程ID
  uint32_t process_id = 0;           // 进程ID
  std::string function_name;         // 函数名
  Snapshot start;                    // 开始时间快照
  Snapshot end;                      // 结束时间快照
  std::vector<std::shared_ptr<Frame>> children;  // 子帧
  std::unordered_map<std::string, std::string> keyvalues;  // 键值对
  TimeUsage time_usage;              // 时间使用统计
};
```

### Snapshot结构

```cpp
struct Snapshot {
  SnapshotType type = SnapshotType::kTscOnly;
  uint64_t monotonic_tsc = 0;        // TSC时间戳
  uint32_t tsc_core = 0;             // TSC核心
  double cpu_time = 0.0;             // CPU时间
  double real_time = 0.0;            // 实际时间
  RUsage rusage;                     // 资源使用情况
};
```

## API参考

### TscCalculator

计算TSC频率比率的计算器。

- `Calculate(const PerfStats& stats)` - 添加样本并计算比率
- `IsCalculated() const` - 检查比率是否已计算完成
- `GetRatio() const` - 获取计算的比率
- `Reset()` - 重置计算器状态

### ChromeTraceExporter

Chrome tracing格式导出器。

- `ChromeTraceExporter(const std::string& output_path)` - 构造函数
- `Open()` - 打开输出文件
- `Close()` - 关闭输出文件
- `IsOpen() const` - 检查文件是否已打开
- `ExportFrame(...)` - 导出单个Frame
- `ExportPerfStats(...)` - 导出PerfStats

### PerfDataSubscriber

数据订阅抽象接口。

- `Start()` - 启动订阅
- `Stop()` - 停止订阅
- `IsRunning() const` - 检查是否正在运行
- `SetCallback(...)` - 设置回调接口
- `SetHandler(...)` - 设置处理函数
- `GetAvailableChannels() const` - 获取可用通道
- `SubscribeChannel(...)` - 订阅通道
- `UnsubscribeChannel(...)` - 取消订阅通道

## 最佳实践

1. **TSC比率计算**：至少需要8个样本才能开始计算，需要16个样本才能完成计算
2. **线程安全**：所有组件都是线程安全的
3. **资源管理**：确保在程序结束前关闭导出器
4. **错误处理**：检查所有操作的返回值

## 故障排除

### 问题：导出的JSON文件为空
- 确保在导出数据前调用了`calculator.Calculate()`
- 确保`calculator.IsCalculated()`返回true
- 检查是否调用了`exporter.Open()`

### 问题：TSC比率计算失败
- 确保提供了足够的样本（至少16个）
- 检查`wall_time_creation_s`字段是否有值
- 确保Frame的TSC时间戳有效
