#pragma once
/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include <functional>
#include <memory>
#include <string>
#include <vector>

#include "perf_tools/perf_types.h"

namespace perf_tools {

class PerfDataCallback {
 public:
  virtual ~PerfDataCallback() = default;
  virtual void OnPerfData(const PerfStats& stats) = 0;
  virtual void OnError(const std::string& error) = 0;
};

using PerfDataCallbackPtr = std::shared_ptr<PerfDataCallback>;
using PerfDataHandler = std::function<void(const PerfStats&)>;

class PerfDataSubscriber {
 public:
  virtual ~PerfDataSubscriber() = default;

  virtual bool Start() = 0;
  virtual void Stop() = 0;
  virtual bool IsRunning() const = 0;

  virtual void SetCallback(PerfDataCallbackPtr callback) = 0;
  virtual void SetHandler(PerfDataHandler handler) = 0;

  virtual std::vector<std::string> GetAvailableChannels() const = 0;
  virtual bool SubscribeChannel(const std::string& channel) = 0;
  virtual void UnsubscribeChannel(const std::string& channel) = 0;
};

using PerfDataSubscriberPtr = std::shared_ptr<PerfDataSubscriber>;

class PerfDataSubscriberFactory {
 public:
  virtual ~PerfDataSubscriberFactory() = default;
  virtual PerfDataSubscriberPtr Create() = 0;
};

using PerfDataSubscriberFactoryPtr = std::shared_ptr<PerfDataSubscriberFactory>;

template <typename T>
class PerfDataSubscriberFactoryImpl : public PerfDataSubscriberFactory {
 public:
  PerfDataSubscriberPtr Create() override {
    return std::make_shared<T>();
  }
};

}  // namespace perf_tools
