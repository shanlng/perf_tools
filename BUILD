load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library", "cc_test")

package(default_visibility = ["//visibility:public"])

cc_library(
    name = "perf_types",
    hdrs = ["include/perf_tools/perf_types.h"],
    includes = ["include"],
)

cc_library(
    name = "tsc_calculator",
    srcs = ["src/tsc_calculator.cc"],
    hdrs = ["include/perf_tools/tsc_calculator.h"],
    includes = ["include"],
    deps = [":perf_types"],
)

cc_library(
    name = "perf_exporter",
    srcs = ["src/perf_exporter.cc"],
    hdrs = ["include/perf_tools/perf_exporter.h"],
    includes = ["include"],
    deps = [":perf_types"],
)

cc_library(
    name = "perf_subscriber",
    hdrs = ["include/perf_tools/perf_subscriber.h"],
    includes = ["include"],
    deps = [":perf_types"],
)

cc_library(
    name = "perf_tools",
    deps = [
        ":perf_exporter",
        ":perf_subscriber",
        ":perf_types",
        ":tsc_calculator",
    ],
)

cc_test(
    name = "tsc_calculator_test",
    size = "small",
    srcs = ["tests/tsc_calculator_test.cc"],
    deps = [
        ":tsc_calculator",
        "@gtest//:gtest_main",
    ],
)

cc_test(
    name = "perf_exporter_test",
    size = "small",
    srcs = ["tests/perf_exporter_test.cc"],
    deps = [
        ":perf_exporter",
        "@gtest//:gtest_main",
    ],
)

cc_test(
    name = "perf_types_test",
    size = "small",
    srcs = ["tests/perf_types_test.cc"],
    deps = [
        ":perf_types",
        "@gtest//:gtest_main",
    ],
)

cc_binary(
    name = "example_usage",
    srcs = ["examples/example_usage.cc"],
    deps = [
        ":perf_tools",
    ],
)
