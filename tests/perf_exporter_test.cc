/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include "perf_tools/perf_exporter.h"

#include <fstream>
#include <gtest/gtest.h>

namespace perf_tools {

class ChromeTraceExporterTest : public ::testing::Test {
 protected:
  void SetUp() override {
    output_path_ = "/tmp/test_trace.json";
  }

  void TearDown() override {
    std::remove(output_path_.c_str());
  }

  std::string output_path_;
};

TEST_F(ChromeTraceExporterTest, OpenClose) {
  ChromeTraceExporter exporter(output_path_);
  EXPECT_TRUE(exporter.Open());
  EXPECT_TRUE(exporter.IsOpen());
  exporter.Close();
  EXPECT_FALSE(exporter.IsOpen());
}

TEST_F(ChromeTraceExporterTest, ExportFrame) {
  ChromeTraceExporter exporter(output_path_);
  ASSERT_TRUE(exporter.Open());

  Frame frame;
  frame.function_name = "test_function";
  frame.thread_id = 12345;
  frame.process_id = 100;
  frame.start.monotonic_tsc = 1000000;
  frame.end.monotonic_tsc = 1001000;

  exporter.ExportFrame(frame, 1000.0, 1000000);
  exporter.Close();

  std::ifstream file(output_path_);
  EXPECT_TRUE(file.is_open());
  std::string content((std::istreambuf_iterator<char>(file)),
                      std::istreambuf_iterator<char>());
  EXPECT_TRUE(content.find("test_function") != std::string::npos);
}

TEST_F(ChromeTraceExporterTest, ExportPerfStats) {
  ChromeTraceExporter exporter(output_path_);
  ASSERT_TRUE(exporter.Open());

  PerfStats stats;
  auto frame = std::make_shared<Frame>();
  frame->function_name = "main_function";
  frame->thread_id = 12345;
  frame->process_id = 100;
  frame->start.monotonic_tsc = 1000000;
  frame->end.monotonic_tsc = 1001000;
  stats.callstacks.push_back(frame);

  exporter.ExportPerfStats(stats, 1000.0);
  exporter.Close();

  std::ifstream file(output_path_);
  EXPECT_TRUE(file.is_open());
  std::string content((std::istreambuf_iterator<char>(file)),
                      std::istreambuf_iterator<char>());
  EXPECT_TRUE(content.find("main_function") != std::string::npos);
}

}  // namespace perf_tools
