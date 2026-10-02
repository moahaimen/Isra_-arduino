cmake_minimum_required(VERSION 3.16)
project(edge_sim CXX)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()
# No -ffast-math: floating-point results must be reproducible.
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O2")
set(SIM_SOURCES
  simulation/core/json.cpp
  simulation/core/simulator.cpp
  simulation/config/sim_config.cpp
  simulation/workload/workload.cpp
  simulation/detector/detector.cpp
  simulation/energy/energy_model.cpp
  simulation/logging/event_log.cpp)
add_library(simcore STATIC ${SIM_SOURCES})
target_include_directories(simcore PUBLIC simulation)
add_executable(edge_sim simulation/app/sim_main.cpp)
target_link_libraries(edge_sim simcore)
add_executable(unit_tests tests/cpp/unit_tests.cpp)
target_link_libraries(unit_tests simcore)
add_executable(firmware_host_check firmware/host_check.cpp)
target_include_directories(firmware_host_check PRIVATE simulation firmware)
add_executable(r2_features tests/cpp/r2_features_main.cpp)
target_include_directories(r2_features PRIVATE simulation)
