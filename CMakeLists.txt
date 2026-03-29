cmake_minimum_required(VERSION 3.14)
project(perf_tools VERSION 1.0.0 LANGUAGES CXX)

# C++17 required
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Options
option(PERF_TOOLS_BUILD_EXAMPLES "Build examples" ON)
option(PERF_TOOLS_BUILD_TESTS "Build tests" OFF)

# Include directories
set(PERF_TOOLS_INCLUDE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/include)
set(PERF_TOOLS_THIRD_PARTY_DIR ${CMAKE_CURRENT_SOURCE_DIR}/third_party)

# nlohmann/json (vendored)
add_library(nlohmann_json INTERFACE)
target_include_directories(nlohmann_json INTERFACE
    $<BUILD_INTERFACE:${PERF_TOOLS_THIRD_PARTY_DIR}/json>
    $<INSTALL_INTERFACE:include/third_party/json>
)

# perf_tools library
add_library(perf_tools STATIC
    src/perf_exporter.cc
    src/tsc_calculator.cc
)

target_include_directories(perf_tools
    PUBLIC
        $<BUILD_INTERFACE:${PERF_TOOLS_INCLUDE_DIR}>
        $<INSTALL_INTERFACE:include>
    PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)

target_link_libraries(perf_tools PUBLIC nlohmann_json)
target_compile_features(perf_tools PUBLIC cxx_std_17)

# Examples
if(PERF_TOOLS_BUILD_EXAMPLES)
    add_executable(perf_example examples/example_usage.cc)
    target_link_libraries(perf_example PRIVATE perf_tools)
endif()

# Tests
if(PERF_TOOLS_BUILD_TESTS)
    enable_testing()
    find_package(GTest REQUIRED)
    
    add_executable(perf_tools_test tests/perf_tools_test.cc)
    target_link_libraries(perf_tools_test PRIVATE perf_tools GTest::gtest_main)
    
    include(GoogleTest)
    gtest_discover_tests(perf_tools_test)
endif()

# Install
include(GNUInstallDirs)

install(TARGETS perf_tools nlohmann_json
    EXPORT perf_toolsTargets
    LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR}
    ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR}
    RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

install(DIRECTORY include/perf_tools
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}
)

install(DIRECTORY third_party/json
    DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/third_party
)

# CMake package config
include(CMakePackageConfigHelpers)

configure_package_config_file(
    cmake/perf_toolsConfig.cmake.in
    ${CMAKE_CURRENT_BINARY_DIR}/perf_toolsConfig.cmake
    INSTALL_DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/perf_tools
)

write_basic_package_version_file(
    ${CMAKE_CURRENT_BINARY_DIR}/perf_toolsConfigVersion.cmake
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY SameMajorVersion
)

install(FILES
    ${CMAKE_CURRENT_BINARY_DIR}/perf_toolsConfig.cmake
    ${CMAKE_CURRENT_BINARY_DIR}/perf_toolsConfigVersion.cmake
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/perf_tools
)

install(EXPORT perf_toolsTargets
    FILE perf_toolsTargets.cmake
    NAMESPACE perf_tools::
    DESTINATION ${CMAKE_INSTALL_LIBDIR}/cmake/perf_tools
)

# Export for build tree
export(EXPORT perf_toolsTargets
    FILE ${CMAKE_CURRENT_BINARY_DIR}/perf_toolsTargets.cmake
    NAMESPACE perf_tools::
)
