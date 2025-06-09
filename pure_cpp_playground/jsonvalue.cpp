#include <string>
#include <vector>
#include <map>
#include <memory>
#include <iostream>
#include <sstream>
#include <iomanip>


// forward declarations
class JsonValue;
static void write_json(const JsonValue& value, std::ostringstream& oss);


// JsonValue class implementation
class JsonValue {
public:
    enum class Type { Null, Bool, Number, String, Array, Object };

    using Array  = std::vector<JsonValue>;
    using Object = std::map<std::string, JsonValue>;

    // Constructors
    JsonValue() : type_(Type::Null) {}
    JsonValue(bool b) : type_(Type::Bool), b_(b) {}
    JsonValue(double d) : type_(Type::Number), d_(d) {}
    JsonValue(const std::string& s) : type_(Type::String), s_(new std::string(s)) {}
    JsonValue(const char* s) : JsonValue(std::string(s)) {}
    JsonValue(const Array& a) : type_(Type::Array), a_(new Array(a)) {}
    JsonValue(const Object& o) : type_(Type::Object), o_(new Object(o)) {}

    JsonValue(JsonValue&& other) noexcept { move(std::move(other)); }
    JsonValue& operator=(JsonValue&& other) noexcept {
        cleanup(); move(std::move(other)); return *this;
    }

    JsonValue(const JsonValue& other) { copy(other); }
    JsonValue& operator=(const JsonValue& other) {
        if (this != &other) { cleanup(); copy(other); }
        return *this;
    }

    ~JsonValue() { cleanup(); }

    Type type() const { return type_; }

    // Accessors
    bool&       as_bool()  { return b_; }
    double&     as_number(){ return d_; }
    std::string& as_string(){ return *s_; }
    Array&      as_array() { return *a_; }
    Object&     as_object(){ return *o_; }

    const bool&       as_bool()  const { return b_; }
    const double&     as_number()const { return d_; }
    const std::string& as_string()const{ return *s_; }
    const Array&      as_array() const{ return *a_; }
    const Object&     as_object()const{ return *o_; }

    std::string to_string() const {
        std::ostringstream oss;
        write_json(*this, oss);
        return oss.str();
    }

private:
    Type type_;
    union {
        bool b_;
        double d_;
        std::string* s_;
        Array* a_;
        Object* o_;
    };

    void copy(const JsonValue& other) {
        type_ = other.type_;
        switch (type_) {
            case Type::Null: break;
            case Type::Bool: b_ = other.b_; break;
            case Type::Number: d_ = other.d_; break;
            case Type::String: s_ = new std::string(*other.s_); break;
            case Type::Array: a_ = new Array(*other.a_); break;
            case Type::Object: o_ = new Object(*other.o_); break;
        }
    }

    void move(JsonValue&& other) {
        type_ = other.type_;
        switch (type_) {
            case Type::Null: break;
            case Type::Bool: b_ = other.b_; break;
            case Type::Number: d_ = other.d_; break;
            case Type::String: s_ = other.s_; other.s_ = nullptr; break;
            case Type::Array: a_ = other.a_; other.a_ = nullptr; break;
            case Type::Object: o_ = other.o_; other.o_ = nullptr; break;
        }
        other.type_ = Type::Null;
    }

    void cleanup() {
        switch (type_) {
            case Type::String: delete s_; break;
            case Type::Array: delete a_; break;
            case Type::Object: delete o_; break;
            default: break;
        }
        type_ = Type::Null;
    }
};


static void write_json(const JsonValue& value, std::ostringstream& oss) {
    using Type = JsonValue::Type;

    switch (value.type()) {
        case Type::Null:
            oss << "null";
            break;
        case Type::Bool:
            oss << (value.as_bool() ? "true" : "false");
            break;
        case Type::Number:
            oss << std::setprecision(15) << value.as_number();  // JSON spec allows full float
            break;
        case Type::String: {
            const std::string& s = value.as_string();
            oss << '"';
            for (char c : s) {
                switch (c) {
                    case '\"': oss << "\\\""; break;
                    case '\\': oss << "\\\\"; break;
                    case '\b': oss << "\\b"; break;
                    case '\f': oss << "\\f"; break;
                    case '\n': oss << "\\n"; break;
                    case '\r': oss << "\\r"; break;
                    case '\t': oss << "\\t"; break;
                    default:
                        if (static_cast<unsigned char>(c) < 0x20) {
                            oss << "\\u"
                                << std::hex << std::setw(4) << std::setfill('0')
                                << static_cast<int>(c);
                        } else {
                            oss << c;
                        }
                }
            }
            oss << '"';
            break;
        }
        case Type::Array: {
            oss << '[';
            const auto& arr = value.as_array();
            for (size_t i = 0; i < arr.size(); ++i) {
                if (i > 0) oss << ',';
                write_json(arr[i], oss);
            }
            oss << ']';
            break;
        }
        case Type::Object: {
            oss << '{';
            const auto& obj = value.as_object();
            bool first = true;
            for (const auto& pair : obj) {
                if (!first) oss << ',';
                first = false;
                oss << '"' << pair.first << "\":";
                write_json(pair.second, oss);
            }
            oss << '}';
            break;
        }
        default:
            throw std::runtime_error("Unknown JsonValue type in to_string()");
    }
}


int main() {
    JsonValue::Object person;

    person["name"] = JsonValue("Alice");
    person["age"] = JsonValue(30.0);
    person["is_student"] = JsonValue(false);
    person["skills"] = JsonValue(JsonValue::Array{
        JsonValue("C++"), JsonValue("Python"), JsonValue("Data Analysis")
    });


    JsonValue root = person;

    std::cout << root.to_string();


    return 0;
}
