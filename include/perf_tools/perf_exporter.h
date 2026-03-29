#pragma once
/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include <fstream>
#include <memory>
#include <mutex>
#include <string>

#include "perf_tools/perf_types.h"

namespace perf_tools {

class ChromeTraceExporter {
 public:
  explicit ChromeTraceExporter(const std::string& output_path);
  ~ChromeTraceExporter();

  bool Open();
  void Close();
  bool IsOpen() const;

  void ExportFrame(const Frame& frame, double tsc_ratio,
                   uint64_t base_tsc = 0);
  void ExportPerfStats(const PerfStats& stats, double tsc_ratio);

 private:
  void WriteTraceEvent(const std::string& name, const std::string& cat,
                       const std::string& phase, double timestamp_us,
                       uint64_t thread_id, uint32_t process_id,
                       double duration_us,
                       const std::unordered_map<std::string, std::string>& args);

  mutable std::mutex mutex_;
  std::string output_path_;
  std::ofstream output_file_;
  bool is_open_ = false;
  bool first_event_ = true;
};

}  // namespace perf_tools
