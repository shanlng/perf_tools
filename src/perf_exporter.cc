/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include "perf_tools/perf_exporter.h"

#include <iomanip>
#include <sstream>

namespace perf_tools {

ChromeTraceExporter::ChromeTraceExporter(const std::string& output_path)
    : output_path_(output_path) {}

ChromeTraceExporter::~ChromeTraceExporter() {
  Close();
}

bool ChromeTraceExporter::Open() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (is_open_) {
    return true;
  }

  output_file_.open(output_path_, std::ios::out | std::ios::trunc);
  if (!output_file_.is_open()) {
    return false;
  }

  output_file_ << "{\"traceEvents\":[\n";
  is_open_ = true;
  first_event_ = true;
  return true;
}

void ChromeTraceExporter::Close() {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!is_open_) {
    return;
  }

  output_file_ << "\n]}\n";
  output_file_.close();
  is_open_ = false;
}

bool ChromeTraceExporter::IsOpen() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return is_open_;
}

void ChromeTraceExporter::ExportFrame(const Frame& frame, double tsc_ratio,
                                       uint64_t base_tsc) {
  if (!is_open_ || tsc_ratio <= 0.0) {
    return;
  }

  const double duration_us =
      (static_cast<double>(frame.end.monotonic_tsc) -
       static_cast<double>(frame.start.monotonic_tsc)) /
      tsc_ratio * 1.0e6;

  double timestamp_us = 0.0;
  if (base_tsc > 0) {
    timestamp_us = (static_cast<double>(frame.start.monotonic_tsc) -
                    static_cast<double>(base_tsc)) /
                   tsc_ratio * 1.0e6;
  }

  if (timestamp_us < 0.0) {
    return;
  }

  WriteTraceEvent(frame.function_name, "PERF", "X", timestamp_us,
                  frame.thread_id, frame.process_id, duration_us,
                  frame.keyvalues);

  for (const auto& child : frame.children) {
    if (child) {
      ExportFrame(*child, tsc_ratio, base_tsc);
    }
  }
}

void ChromeTraceExporter::ExportPerfStats(const PerfStats& stats,
                                           double tsc_ratio) {
  if (!is_open_ || tsc_ratio <= 0.0 || stats.callstacks.empty()) {
    return;
  }

  uint64_t base_tsc = 0;
  if (!stats.callstacks.empty() && stats.callstacks[0]) {
    base_tsc = stats.callstacks[0]->start.monotonic_tsc;
  }

  for (const auto& frame : stats.callstacks) {
    if (frame) {
      ExportFrame(*frame, tsc_ratio, base_tsc);
    }
  }
}

void ChromeTraceExporter::WriteTraceEvent(
    const std::string& name, const std::string& cat,
    const std::string& phase, double timestamp_us, uint64_t thread_id,
    uint32_t process_id, double duration_us,
    const std::unordered_map<std::string, std::string>& args) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!is_open_) {
    return;
  }

  if (!first_event_) {
    output_file_ << ",\n";
  }
  first_event_ = false;

  output_file_ << "{\"name\":\"" << name << "\","
               << "\"cat\":\"" << cat << "\","
               << "\"ph\":\"" << phase << "\","
               << "\"ts\":" << std::fixed << std::setprecision(3) << timestamp_us
               << ",\"tid\":" << thread_id
               << ",\"pid\":" << process_id
               << ",\"dur\":" << duration_us;

  if (!args.empty()) {
    output_file_ << ",\"args\":{";
    bool first_arg = true;
    for (const auto& [key, value] : args) {
      if (!first_arg) {
        output_file_ << ",";
      }
      first_arg = false;
      output_file_ << "\"" << key << "\":\"" << value << "\"";
    }
    output_file_ << "}";
  }

  output_file_ << "}";
}

}  // namespace perf_tools
