#include "logging/event_log.h"

#include <cinttypes>

#include "core/json.h"

namespace sim {

bool EventLog::open(const std::string& path, LogLevel level) {
    close();
    level_ = level;
    if (level == LOG_NONE || path.empty()) return true;
    f_ = std::fopen(path.c_str(), "wb");
    return f_ != nullptr;
}

void EventLog::close() {
    if (f_) std::fclose(f_);
    f_ = nullptr;
}

EventLog& EventLog::begin(double t_ms, const char* ev) {
    char tmp[96];
    std::snprintf(tmp, sizeof(tmp), "{\"t\":%.3f,\"ev\":\"%s\"", t_ms, ev);
    buf_ = tmp;
    return *this;
}

EventLog& EventLog::kv(const char* k, const char* v) {
    buf_ += ",\"";
    buf_ += k;
    buf_ += "\":\"";
    buf_ += json_escape(v);
    buf_ += '"';
    return *this;
}

EventLog& EventLog::kv(const char* k, int64_t v) {
    char tmp[64];
    std::snprintf(tmp, sizeof(tmp), ",\"%s\":%" PRId64, k, v);
    buf_ += tmp;
    return *this;
}

EventLog& EventLog::kv(const char* k, uint64_t v) {
    char tmp[64];
    std::snprintf(tmp, sizeof(tmp), ",\"%s\":%" PRIu64, k, v);
    buf_ += tmp;
    return *this;
}

EventLog& EventLog::kvb(const char* k, bool v) {
    buf_ += ",\"";
    buf_ += k;
    buf_ += v ? "\":true" : "\":false";
    return *this;
}

EventLog& EventLog::kvf(const char* k, double v, int decimals) {
    char tmp[96];
    std::snprintf(tmp, sizeof(tmp), ",\"%s\":%.*f", k, decimals, v);
    buf_ += tmp;
    return *this;
}

void EventLog::end() {
    buf_ += "}\n";
    if (f_) std::fwrite(buf_.data(), 1, buf_.size(), f_);
    ++lines_;
}

}  // namespace sim
