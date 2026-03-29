/******************************************************************************
 * Copyright 2024 AutoX. All Rights Reserved.
 *****************************************************************************/

#include "perf_tools/perf_types.h"

#include <gtest/gtest.h>

namespace perf_tools {

TEST(PerfTypesTest, SnapshotDefaults) {
  Snapshot snapshot;
  EXPECT_EQ(snapshot.type, SnapshotType::kTscOnly);
  EXPECT_EQ(snapshot.monotonic_tsc, 0u);
  EXPECT_EQ(snapshot.tsc_core, 0u);
  EXPECT_DOUBLE_EQ(snapshot.cpu_time, 0.0);
  EXPECT_DOUBLE_EQ(snapshot.real_time, 0.0);
}

TEST(PerfTypesTest, FrameDefaults) {
  Frame frame;
  EXPECT_EQ(frame.frame_identifier, 0);
  EXPECT_EQ(frame.thread_id, 0u);
  EXPECT_EQ(frame.process_id, 0u);
  EXPECT_TRUE(frame.function_name.empty());
  EXPECT_TRUE(frame.children.empty());
  EXPECT_TRUE(frame.samples.empty());
  EXPECT_TRUE(frame.keyvalues.empty());
}

TEST(PerfTypesTest, PerfStatsDefaults) {
  PerfStats stats;
  EXPECT_EQ(stats.frame_identifier, 0);
  EXPECT_TRUE(stats.callstacks.empty());
  EXPECT_DOUBLE_EQ(stats.wall_time_creation_s, 0.0);
  EXPECT_EQ(stats.wall_time_creation_tv_sec, 0);
  EXPECT_EQ(stats.wall_time_creation_tv_nsec, 0);
}

TEST(PerfTypesTest, FrameHierarchy) {
  auto parent = std::make_shared<Frame>();
  parent->function_name = "parent";
  parent->thread_id = 100;
  
  auto child1 = std::make_shared<Frame>();
  child1->function_name = "child1";
  child1->thread_id = 100;
  
  auto child2 = std::make_shared<Frame>();
  child2->function_name = "child2";
  child2->thread_id = 100;
  
  parent->children.push_back(child1);
  parent->children.push_back(child2);
  
  EXPECT_EQ(parent->children.size(), 2u);
  EXPECT_EQ(parent->children[0]->function_name, "child1");
  EXPECT_EQ(parent->children[1]->function_name, "child2");
}

TEST(PerfTypesTest, PerfStatsWithCallstacks) {
  PerfStats stats;
  stats.wall_time_creation_s = 123.456;
  
  auto frame1 = std::make_shared<Frame>();
  frame1->function_name = "func1";
  
  auto frame2 = std::make_shared<Frame>();
  frame2->function_name = "func2";
  
  stats.callstacks.push_back(frame1);
  stats.callstacks.push_back(frame2);
  
  EXPECT_EQ(stats.callstacks.size(), 2u);
  EXPECT_EQ(stats.callstacks[0]->function_name, "func1");
  EXPECT_EQ(stats.callstacks[1]->function_name, "func2");
}

}  // namespace perf_tools
