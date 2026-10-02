// Host-side mocks of the Arduino/mbed APIs used by the firmware sketches.
//
// millis() and delay() run on simulated time so firmware logic can be
// executed on a PC without hardware. The RPC mock records calls made through
// the Portenta RPC library interface (RPC.call / RPC.bind) so the same
// sketch code can be exercised in host tests.
#pragma once

#include <cstdint>
#include <functional>
#include <map>
#include <string>
#include <vector>

namespace sim_mock {

class SimClock {
public:
    static SimClock& instance() {
        static SimClock c;
        return c;
    }
    uint32_t millis() const { return static_cast<uint32_t>(now_ms_); }
    double now_ms() const { return now_ms_; }
    void advance(double ms) { now_ms_ += ms; }
    void reset() { now_ms_ = 0.0; }

private:
    double now_ms_ = 0.0;
};

class RpcMock {
public:
    struct Call {
        double t_ms;
        std::string name;
        std::vector<double> args;
    };
    void bind(const std::string& name, std::function<int(double, double)> fn) { handlers_[name] = fn; }
    int call(const std::string& name, double a, double b) {
        calls.push_back({SimClock::instance().now_ms(), name, {a, b}});
        auto it = handlers_.find(name);
        return it == handlers_.end() ? -1 : it->second(a, b);
    }
    std::vector<Call> calls;

private:
    std::map<std::string, std::function<int(double, double)>> handlers_;
};

}  // namespace sim_mock

inline uint32_t millis() { return sim_mock::SimClock::instance().millis(); }
inline void delay(uint32_t ms) { sim_mock::SimClock::instance().advance(ms); }
