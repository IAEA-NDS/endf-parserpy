#ifndef CPP_ENDF_FLOAT_HPP
#define CPP_ENDF_FLOAT_HPP


#include <pybind11/pybind11.h>
#include <iostream>
#include <string>


namespace py = pybind11;


#define DOUBLE_TYPE EndfFloatCpp


// This class must be in sync with the
// Python class EndfFloat class in endf_parserpy.utils.math_utils

class EndfFloatCpp {
public:
    EndfFloatCpp()
        : _value(0.0), _orig_str("") {}

    EndfFloatCpp(double value)
        : _value(value), _orig_str("") {}

    EndfFloatCpp(double value, const std::string& orig_str)
        : _value(value), _orig_str(orig_str) {}

    EndfFloatCpp(const EndfFloatCpp& other)
        : _value(other._value), _orig_str(other._orig_str) {}

    std::string get_original_string() const {
        return _orig_str; }
    bool operator==(const EndfFloatCpp& other) const {
        return static_cast<double>(_value) == static_cast<double>(other._value);
    }

    bool operator!=(const EndfFloatCpp& other) const {
        return static_cast<double>(_value) != static_cast<double>(other._value);
    }

    bool operator<(const EndfFloatCpp& other) const {
        return static_cast<double>(_value) < static_cast<double>(other._value);
    }


    template<typename T>
    bool operator==(T other) const {
        return static_cast<double>(_value) == static_cast<double>(other);
    }

    template<typename T>
    bool operator!=(T other) const {
        return static_cast<double>(_value) != static_cast<double>(other);
    }

    template<typename T>
    bool operator<(T other) const {
        return static_cast<double>(_value) < static_cast<double>(other);
    }

    friend std::ostream& operator<<(std::ostream& os, const EndfFloatCpp& obj) {
        os << static_cast<double>(obj);
        return os;
    }

    operator double() const {
        return _value;
    }

    operator int() const {
        return static_cast<int>(_value);
    }

private:
    double _value;
    std::string _orig_str;
};


namespace PYBIND11_NAMESPACE { namespace detail {

    // Establish conversion between Python float and EndfFloatCpp
    template <> struct type_caster<EndfFloatCpp> {
    public:
        PYBIND11_TYPE_CASTER(EndfFloatCpp, const_name("EndfFloatCpp"));

        bool load(handle src, bool) {
            static py::object PyEndfFloat = (
                py::module::import("endf_parserpy.utils.math_utils").attr("EndfFloat")
            );
            if (py::isinstance<py::float_>(src)) {
                py::float_ tmp = py::cast<py::float_>(src);
                double float_value = tmp.cast<double>();
                value = EndfFloatCpp(float_value);
                return !(float_value == -1 && PyErr_Occurred());
            } else if (py::isinstance(src, PyEndfFloat)) {
				auto float_method = src.attr("__float__");
				double float_value = float_method().cast<double>();
				std::string orig_str = src.attr("get_original_string")().cast<std::string>();
				value = EndfFloatCpp(float_value, orig_str);
                return true;
            }
            return false;
        }

        static handle cast(const EndfFloatCpp& src, return_value_policy, handle) {
            static py::object PyEndfFloat = (
                py::module::import("endf_parserpy.utils.math_utils").attr("EndfFloat")
            );
            double float_value = static_cast<double>(src);
            std::string orig_str = src.get_original_string();
            if (orig_str.empty()) {
                return py::float_(static_cast<double>(src)).release();
            } else {
                py::object endf_float = PyEndfFloat(
                   py::float_(float_value), py::str(orig_str)
                );
                return endf_float.release();
            }
        }
    };


}} // namespace PYBIND11_NAMESPACE::detail


#endif // CPP_ENDF_FLOAT_HPP
