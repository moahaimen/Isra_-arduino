// JSONL event log with deterministic formatting.
//
// Every line is {"t":<ms>,"ev":"<TYPE>", ...fields}. Times use 3 decimals
// (microsecond resolution) and other reals 4 decimals so that identical runs
// produce byte-identical logs.
#pragma once

#include <cstdint>
#include <cstdio>
#include <string>

namespace sim {

enum LogLevel { LOG_NONE = 0, LOG_DECISIONS = 1, LOG_FULL = 2 };

class EventLog {
public:
    EventLog() = default;
    ~EventLog() { close(); }
    bool open(const std::string& path, LogLevel level);
    void close();
    LogLevel level() const { return level_; }
    bool enabled(LogLevel need) const { return f_ != nullptr && level_ >= need; }

    // Builder interface: begin(...).kv(...).kv(...).end()
    EventLog& begin(double t_ms, const char* ev);
    EventLog& kv(const char* k, const char* v);
    EventLog& kv(const char* k, const std::string& v) { return kv(k, v.c_str()); }
    EventLog& kv(const char* k, int64_t v);
    EventLog& kv(const char* k, uint64_t v);
    EventLog& kv(const char* k, int v) { return kv(k, static_cast<int64_t>(v)); }
    EventLog& kvb(const char* k, bool v);
    EventLog& kvf(const char* k, double v, int decimals = 4);
    void end();
    uint64_t lines() const { return lines_; }

private:
    std::FILE* f_ = nullptr;
    LogLevel level_ = LOG_NONE;
    std::string buf_;
    uint64_t lines_ = 0;
};

}  // namespace sim
