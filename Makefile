# Convenience wrapper. The canonical build is CMake:
#   cmake -S . -B build && cmake --build build -j
CXX ?= g++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
SRC = simulation/core/json.cpp simulation/core/simulator.cpp simulation/config/sim_config.cpp \
      simulation/workload/workload.cpp simulation/detector/detector.cpp \
      simulation/energy/energy_model.cpp simulation/logging/event_log.cpp

all: build/edge_sim build/unit_tests build/firmware_host_check

build/edge_sim: $(SRC) simulation/app/sim_main.cpp $(wildcard simulation/*/*.h)
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isimulation $(SRC) simulation/app/sim_main.cpp -o $@

build/unit_tests: $(SRC) tests/cpp/unit_tests.cpp $(wildcard simulation/*/*.h)
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isimulation $(SRC) tests/cpp/unit_tests.cpp -o $@

build/firmware_host_check: firmware/host_check.cpp $(wildcard firmware/*.h) simulation/watcher/watcher.h simulation/security/security_gate.h
	mkdir -p build
	$(CXX) $(CXXFLAGS) -Isimulation -Ifirmware firmware/host_check.cpp -o $@

clean:
	rm -rf build
.PHONY: all clean
