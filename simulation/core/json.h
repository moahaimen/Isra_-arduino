// Minimal JSON reader used for configuration files, workload JSONL and the
// power model. Supports objects, arrays, strings, numbers, booleans and null.
#pragma once

#include <map>
#include <memory>
#include <string>
#include <vector>

namespace sim {

class JsonValue {
public:
    enum Type { NUL, BOOL, NUMBER, STRING, ARRAY, OBJECT };
    Type type = NUL;
    bool b = false;
    double num = 0.0;
    std::string str;
    std::vector<JsonValue> arr;
    std::map<std::string, JsonValue> obj;

    bool has(const std::string& key) const { return type == OBJECT && obj.count(key) > 0; }
    const JsonValue& at(const std::string& key) const;
    double as_number() const;
    std::string as_string() const;  // numbers and bools are rendered as text
    bool as_bool() const;
};

JsonValue json_parse(const std::string& text);
JsonValue json_parse_file(const std::string& path);
std::string json_escape(const std::string& s);

}  // namespace sim
