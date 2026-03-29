/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include "perf_tools/tsc_calculator.h"

namespace perf_tools {

bool TscCalculator::Calculate(const PerfStats& stats) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (is_calculated_) {
    return true;
  }

  if (stats.callstacks.empty()) {
    return false;
  }

  samples_.push_back(stats);
  const int size = static_cast<int>(samples_.size());

  if (size >= kStartNum && size < kStartNum + kCalSize) {
    const auto& beg_frame = samples_.front().callstacks[0];
    const auto& end_frame = samples_.back().callstacks[0];
    if (!beg_frame || !end_frame) {
      return false;
    }
    tsc_ratio_ += (static_cast<double>(end_frame->start.monotonic_tsc) -
                   static_cast<double>(beg_frame->start.monotonic_tsc)) /
                  (samples_.back().wall_time_creation_s -
                   samples_.front().wall_time_creation_s);
  } else if (size >= kStartNum + kCalSize) {
    tsc_ratio_ = tsc_ratio_ / kCalSize;
    is_calculated_ = true;
  }

  return is_calculated_;
}

bool TscCalculator::IsCalculated() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return is_calculated_;
}

double TscCalculator::GetRatio() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return tsc_ratio_;
}

void TscCalculator::Reset() {
  std::lock_guard<std::mutex> lock(mutex_);
  is_calculated_ = false;
  tsc_ratio_ = 0.0;
  samples_.clear();
}

}  // namespace perf_tools
