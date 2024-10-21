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
            // Extract PyObject from handle
            PyObject *source = src.ptr();
            // Try converting into a Python float value
            PyObject *tmp = PyNumber_Float(source);
            if (!tmp)
                return false;
            // Now try to convert into a C++ double
            double float_value = PyFloat_AsDouble(tmp);
            // Instantiate EndfFloatCpp class
            value = EndfFloatCpp(float_value);
            Py_DECREF(tmp);
            // Ensure return code was OK (to avoid out-of-range errors etc) */
            return !(float_value == -1 && PyErr_Occurred());
        }

        static handle cast(EndfFloatCpp src, return_value_policy, handle) {
            return PyFloat_FromDouble(static_cast<double>(src));
        }
    };


}} // namespace PYBIND11_NAMESPACE::detail


#endif // CPP_ENDF_FLOAT_HPP
