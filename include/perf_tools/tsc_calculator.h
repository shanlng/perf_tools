#pragma once
/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include <cstdint>
#include <memory>
#include <mutex>
#include <vector>

#include "perf_tools/perf_types.h"

namespace perf_tools {

class TscCalculator {
 public:
  TscCalculator() = default;
  ~TscCalculator() = default;

  bool Calculate(const PerfStats& stats);
  bool IsCalculated() const;
  double GetRatio() const;
  void Reset();

 private:
  static constexpr int kStartNum = 8;
  static constexpr int kCalSize = 8;

  mutable std::mutex mutex_;
  bool is_calculated_ = false;
  double tsc_ratio_ = 0.0;
  std::vector<PerfStats> samples_;
};

}  // namespace perf_tools
