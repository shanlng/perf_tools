/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include "perf_tools/tsc_calculator.h"

#include <gtest/gtest.h>

namespace perf_tools {

class TscCalculatorTest : public ::testing::Test {
 protected:
  void SetUp() override {
    calculator_ = std::make_unique<TscCalculator>();
  }

  PerfStats CreateSampleStats(uint64_t base_tsc, double wall_time) {
    PerfStats stats;
    stats.wall_time_creation_s = wall_time;
    
    auto frame = std::make_shared<Frame>();
    frame->start.monotonic_tsc = base_tsc;
    frame->end.monotonic_tsc = base_tsc + 1000;
    frame->function_name = "test_function";
    frame->thread_id = 12345;
    frame->process_id = 100;
    
    stats.callstacks.push_back(frame);
    return stats;
  }

  std::unique_ptr<TscCalculator> calculator_;
};

TEST_F(TscCalculatorTest, InitialState) {
  EXPECT_FALSE(calculator_->IsCalculated());
  EXPECT_DOUBLE_EQ(calculator_->GetRatio(), 0.0);
}

TEST_F(TscCalculatorTest, CalculateWithSamples) {
  for (int i = 0; i < 16; ++i) {
    auto stats = CreateSampleStats(1000000 + i * 1000, 1.0 + i * 0.1);
    calculator_->Calculate(stats);
  }
  
  EXPECT_TRUE(calculator_->IsCalculated());
  EXPECT_GT(calculator_->GetRatio(), 0.0);
}

TEST_F(TscCalculatorTest, Reset) {
  for (int i = 0; i < 16; ++i) {
    auto stats = CreateSampleStats(1000000 + i * 1000, 1.0 + i * 0.1);
    calculator_->Calculate(stats);
  }
  
  calculator_->Reset();
  EXPECT_FALSE(calculator_->IsCalculated());
  EXPECT_DOUBLE_EQ(calculator_->GetRatio(), 0.0);
}

TEST_F(TscCalculatorTest, EmptyCallstacks) {
  PerfStats stats;
  EXPECT_FALSE(calculator_->Calculate(stats));
}

}  // namespace perf_tools
