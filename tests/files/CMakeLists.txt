# Copyright (c) Facebook, Inc. and its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

add_library(velox_exception Exceptions.cpp VeloxException.cpp "Exceptions.h")
add_library(velox::exception ALIAS velox_exception)

target_link_libraries(
  velox_exception
  velox_flag_definitions
  velox_process
  glog::glog
  Folly::folly
  fmt::fmt
  gflags::gflags)

add_library(
  velox_common_base
  BitUtil.cpp
  Counters.cpp
  Fs.cpp
  # comments can be in args
  RandomUtil.cpp
  RawVector.cpp
  RuntimeMetrics.cpp
  SimdUtil.cpp
  StatsReporter.cpp
  SuccinctPrinter.cpp)

target_link_libraries(velox_common_base PUBLIC velox_exception PRIVATE velox_process xsimd)

# todo interface targets must inherit the sources of linked targets?
add_library(velox_interface INTERFACE)
add_executable(velox_interface_test test.cpp)

if(${VELOX_BUILD_TESTING})
add_executable(velox_common_base something::conditional)
  add_subdirectory(tests)
endif()

if(${VELOX_ENABLE_BENCHMARKS})
  add_subdirectory(benchmarks)
endif()
