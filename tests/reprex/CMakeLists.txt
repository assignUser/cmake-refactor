cmake_minimum_required(VERSION 3.18)

project(Circular-Example)
set(BUILD_SHARED_LIBS ON)

include_directories(.)

add_subdirectory(velox/io)
add_subdirectory(velox/util)
add_executable(main velox/main.cpp)
target_link_libraries(main util)

