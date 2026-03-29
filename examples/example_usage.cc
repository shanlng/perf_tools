/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

/**
 * @example example_usage.cc
 * @brief Perf Tools库使用示例
 */

#include <iostream>
#include <memory>

#include "perf_tools/perf_types.h"
#include "perf_tools/perf_exporter.h"
#include "perf_tools/tsc_calculator.h"
#include "perf_tools/perf_subscriber.h"

namespace {

class ExamplePerfDataCallback : public perf_tools::PerfDataCallback {
 public:
  void OnPerfData(const perf_tools::PerfStats& stats) override {
    std::cout << "Received PerfStats with " << stats.callstacks.size()
              << " callstacks" << std::endl;
  }

  void OnError(const std::string& error) override {
    std::cerr << "Error: " << error << std::endl;
  }
};

}  // namespace

int main() {
  // 1. 创建TSC计算器
  perf_tools::TscCalculator calculator;

  // 2. 创建Chrome tracing导出器
  perf_tools::ChromeTraceExporter exporter("perf_output.json");

  // 3. 打开导出文件
  if (!exporter.Open()) {
    std::cerr << "Failed to open exporter" << std::endl;
    return 1;
  }

  // 4. 模拟接收性能数据
  for (int i = 0; i < 16; ++i) {
    perf_tools::PerfStats stats;
    stats.wall_time_creation_s = 1.0 + i * 0.1;

    auto frame = std::make_shared<perf_tools::Frame>();
    frame->function_name = "example_function_" + std::to_string(i);
    frame->thread_id = 12345;
    frame->process_id = 100;
    frame->start.monotonic_tsc = 1000000 + i * 1000;
    frame->end.monotonic_tsc = 1000000 + i * 1000 + 500;

    // 添加子帧
    auto child = std::make_shared<perf_tools::Frame>();
    child->function_name = "child_function";
    child->thread_id = 12345;
    child->process_id = 100;
    child->start.monotonic_tsc = frame->start.monotonic_tsc + 100;
    child->end.monotonic_tsc = frame->start.monotonic_tsc + 300;
    frame->children.push_back(child);

    // 添加键值对
    frame->keyvalues["iteration"] = std::to_string(i);

    stats.callstacks.push_back(frame);

    // 计算TSC比率
    if (calculator.Calculate(stats)) {
      std::cout << "TSC ratio calculated: " << calculator.GetRatio() << std::endl;
    }

    // 导出数据
    if (calculator.IsCalculated()) {
      exporter.ExportPerfStats(stats, calculator.GetRatio());
    }
  }

  // 5. 关闭导出器
  exporter.Close();

  std::cout << "Performance data exported to perf_output.json" << std::endl;

  // 6. 使用回调接口示例
  auto callback = std::make_shared<ExamplePerfDataCallback>();
  perf_tools::PerfStats sample_stats;
  callback->OnPerfData(sample_stats);

  return 0;
}
