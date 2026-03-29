# AGENTS.md - perf_tools

A lightweight C++ performance analysis library with Chrome tracing format output.

## Build & Test Commands

### Building
```bash
# Standard build
mkdir build && cd build
cmake .. && make

# Build without examples
cmake .. -DPERF_TOOLS_BUILD_EXAMPLES=OFF && make

# Build with tests
cmake .. -DPERF_TOOLS_BUILD_TESTS=ON && make
```

### Testing
```bash
cd build
ctest --verbose
```

### Running Example
```bash
cd build
./perf_example
```

## Code Style Guidelines

### File Structure
- Copyright header: `Copyright 2024 AutoX. All Rights Reserved.`
- Include guard: `#pragma once`
- Namespace: `perf_tools`

### Naming Conventions
- **Classes**: PascalCase (e.g., `ChromeTraceExporter`, `TscCalculator`)
- **Functions/Methods**: PascalCase (e.g., `Calculate`, `ExportFrame`)
- **Member variables**: snake_case with trailing underscore (e.g., `tsc_ratio_`, `is_open_`)
- **Constants**: kPascalCase (e.g., `kStartNum`, `kCalSize`)

### File Extensions
- Headers: `.h`
- Source files: `.cc`

### Includes Order
1. Own header (for `.cc` files)
2. C++ standard library headers
3. Third-party headers (json.hpp)
4. Project headers (using `"perf_tools/..."` path)

### Threading
- All public methods must be thread-safe
- Use `mutable std::mutex mutex_` for const methods requiring locks

## Repository Structure
- `include/perf_tools/` - Public headers
- `src/` - Implementation files
- `third_party/` - Vendored dependencies (json.hpp)
- `examples/` - Usage examples
- `cmake/` - CMake configuration templates

## Key Dependencies
- C++17 standard library
- nlohmann/json (vendored in third_party/)

## Integration
See INTEGRATION_GUIDE.md for:
- CMake integration methods
- Implementing custom data subscribers
- Data format specifications
