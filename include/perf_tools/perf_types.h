#pragma once
/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include <cstdint>
#include <functional>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace perf_tools {

enum class SnapshotType {
  kFull = 0,
  kTscOnly = 1
};

struct RUsage {
  double utime_s = 0.0;
  double stime_s = 0.0;
  int64_t utime_tv_sec = 0;
  int32_t utime_tv_usec = 0;
  int64_t stime_tv_sec = 0;
  int32_t stime_tv_usec = 0;
  int64_t maxrss = 0;
  int64_t inblock = 0;
  int64_t oublock = 0;
  int64_t vcsw = 0;
  int64_t ivcsw = 0;
  int64_t minflt = 0;
  int64_t majflt = 0;
};

struct Snapshot {
  SnapshotType type = SnapshotType::kTscOnly;
  uint64_t monotonic_tsc = 0;
  uint32_t tsc_core = 0;
  double cpu_time = 0.0;
  double real_time = 0.0;
  RUsage rusage;
};

struct TimeUsage {
  double cpu_time_used_ms = 0.0;
  double real_time_used_ms = 0.0;
  double usage = 0.0;
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

struct CuptiFrame {
  uint32_t process_id = 0;
  uint64_t thread_id = 0;
  uint64_t start_timestamp = 0;
  uint64_t end_timestamp = 0;
  std::string function_name;
};

struct GpuContext {
  std::vector<CuptiFrame> cudaapis;
  std::vector<CuptiFrame> tensorrts;
};

struct PerfStats {
  int64_t frame_identifier = 0;
  std::vector<std::shared_ptr<Frame>> callstacks;
  double wall_time_creation_s = 0.0;
  int64_t wall_time_creation_tv_sec = 0;
  int64_t wall_time_creation_tv_nsec = 0;
  GpuContext gpu_context;
};

using PerfStatsPtr = std::shared_ptr<PerfStats>;
using FramePtr = std::shared_ptr<Frame>;

}  // namespace perf_tools
