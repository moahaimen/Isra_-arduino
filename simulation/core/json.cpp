#include "core/json.h"

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>

namespace sim {

namespace {

class Parser {
public:
    explicit Parser(const std::string& s) : s_(s) {}

    JsonValue parse() {
        JsonValue v = value();
        skip_ws();
        if (pos_ != s_.size()) fail("trailing characters");
        return v;
    }

private:
    const std::string& s_;
    size_t pos_ = 0;

    [[noreturn]] void fail(const char* msg) {
        throw std::runtime_error(std::string("JSON parse error: ") + msg + " at offset " +
                                 std::to_string(pos_));
    }
    void skip_ws() {
        while (pos_ < s_.size() && (s_[pos_] == ' ' || s_[pos_] == '\n' || s_[pos_] == '\r' || s_[pos_] == '\t'))
            ++pos_;
    }
    char peek() {
        skip_ws();
        if (pos_ >= s_.size()) fail("unexpected end");
        return s_[pos_];
    }
    void expect(char c) {
        if (peek() != c) fail("unexpected character");
        ++pos_;
    }
    bool match_word(const char* w) {
        size_t n = std::char_traits<char>::length(w);
        if (s_.compare(pos_, n, w) == 0) {
            pos_ += n;
            return true;
        }
        return false;
    }

    JsonValue value() {
        char c = peek();
        JsonValue v;
        if (c == '{') {
            v.type = JsonValue::OBJECT;
            ++pos_;
            if (peek() == '}') { ++pos_; return v; }
            while (true) {
                std::string key = string_lit();
                expect(':');
                v.obj[key] = value();
                char d = peek();
                ++pos_;
                if (d == '}') break;
                if (d != ',') fail("expected , or }");
            }
        } else if (c == '[') {
            v.type = JsonValue::ARRAY;
            ++pos_;
            if (peek() == ']') { ++pos_; return v; }
            while (true) {
                v.arr.push_back(value());
                char d = peek();
                ++pos_;
                if (d == ']') break;
                if (d != ',') fail("expected , or ]");
            }
        } else if (c == '"') {
            v.type = JsonValue::STRING;
            v.str = string_lit();
        } else if (match_word("true")) {
            v.type = JsonValue::BOOL;
            v.b = true;
        } else if (match_word("false")) {
            v.type = JsonValue::BOOL;
            v.b = false;
        } else if (match_word("null")) {
            v.type = JsonValue::NUL;
        } else {
            v.type = JsonValue::NUMBER;
            const char* start = s_.c_str() + pos_;
            char* end = nullptr;
            v.num = std::strtod(start, &end);
            if (end == start) fail("invalid value");
            pos_ += static_cast<size_t>(end - start);
        }
        return v;
    }

    std::string string_lit() {
        expect('"');
        std::string out;
        while (pos_ < s_.size() && s_[pos_] != '"') {
            char c = s_[pos_++];
            if (c == '\\') {
                if (pos_ >= s_.size()) fail("bad escape");
                char e = s_[pos_++];
                switch (e) {
                    case 'n': out += '\n'; break;
                    case 't': out += '\t'; break;
                    case 'r': out += '\r'; break;
                    case 'b': out += '\b'; break;
                    case 'f': out += '\f'; break;
                    case 'u': {
                        // Only the ASCII subset is needed for our files.
                        unsigned code = static_cast<unsigned>(std::strtoul(s_.substr(pos_, 4).c_str(), nullptr, 16));
                        pos_ += 4;
                        out += static_cast<char>(code < 128 ? code : '?');
                        break;
                    }
                    default: out += e;
                }
            } else {
                out += c;
            }
        }
        if (pos_ >= s_.size()) fail("unterminated string");
        ++pos_;
        return out;
    }
};

}  // namespace

const JsonValue& JsonValue::at(const std::string& key) const {
    auto it = obj.find(key);
    if (type != OBJECT || it == obj.end()) throw std::runtime_error("JSON key not found: " + key);
    return it->second;
}

double JsonValue::as_number() const {
    if (type == NUMBER) return num;
    if (type == BOOL) return b ? 1.0 : 0.0;
    if (type == STRING) return std::strtod(str.c_str(), nullptr);
    throw std::runtime_error("JSON value is not a number");
}

std::string JsonValue::as_string() const {
    if (type == STRING) return str;
    if (type == BOOL) return b ? "true" : "false";
    if (type == NUMBER) {
        char buf[64];
        std::snprintf(buf, sizeof(buf), "%.17g", num);
        return buf;
    }
    if (type == NUL) return "";
    throw std::runtime_error("JSON value is not a scalar");
}

bool JsonValue::as_bool() const {
    if (type == BOOL) return b;
    if (type == NUMBER) return num != 0.0;
    if (type == STRING) return str == "true" || str == "1" || str == "on";
    return false;
}

JsonValue json_parse(const std::string& text) { return Parser(text).parse(); }

JsonValue json_parse_file(const std::string& path) {
    std::ifstream in(path);
    if (!in) throw std::runtime_error("cannot open JSON file: " + path);
    std::stringstream ss;
    ss << in.rdbuf();
    return json_parse(ss.str());
}

std::string json_escape(const std::string& s) {
    std::string out;
    for (char c : s) {
        if (c == '"' || c == '\\') {
            out += '\\';
            out += c;
        } else if (c == '\n') {
            out += "\\n";
        } else {
            out += c;
        }
    }
    return out;
}

}  // namespace sim
