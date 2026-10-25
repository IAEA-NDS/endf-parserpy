#ifndef CPP_ENDF_FLOAT_HPP
#define CPP_ENDF_FLOAT_HPP


#include <pybind11/pybind11.h>
#include <iostream>
#include <string>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>


namespace py = pybind11;


#define DOUBLE_TYPE EndfFloatCpp


// This class must be in sync with the
// Python class EndfFloat class in endf_parserpy.utils.math_utils
//
// The original string is stored inline instead of in a std::string, so
// that the class is trivially copyable: arrays of values (NestedArray,
// std::vector) are copied and relocated with memcpy, without constructing
// and destroying a string per element. Strings of up to 15 bytes are
// stored completely; this covers the 11 characters of every string from
// parsing and every string that can be written (exactly 11 characters).
// Of a longer string, which is only used in the error message of the
// writer, the true length (as long as it fits into 32 bits) and its
// beginning are kept: the first 15 bytes for lengths below 255, the first
// 11 bytes for longer strings, whose length is stored in the last four
// bytes of the buffer. An empty string means no original string.

class EndfFloatCpp {
public:
    EndfFloatCpp()
        : _value(0.0), _n(0) {}

    EndfFloatCpp(double value)
        : _value(value), _n(0) {}

    EndfFloatCpp(double value, const char* orig_str, std::size_t len)
        : _value(value) {
        set_original_string(orig_str, len);
    }

    EndfFloatCpp(double value, const std::string& orig_str)
        : _value(value) {
        set_original_string(orig_str.data(), orig_str.size());
    }

    // the stored part of the original string, which is the complete
    // string if original_string_size() <= max_stored_size
    std::string get_original_string() const {
        return std::string(_s, original_string_stored_size()); }

    bool has_original_string() const {
        return _n != 0; }

    // true length of the original string
    std::size_t original_string_size() const {
        if (_n != long_marker) return _n;
        std::uint32_t len;
        std::memcpy(&len, _s + long_stored_size, sizeof(len));
        return len;
    }

    // number of bytes of the original string available at
    // original_string_data()
    std::size_t original_string_stored_size() const {
        if (_n <= max_stored_size) return _n;
        if (_n == long_marker) return long_stored_size;
        return max_stored_size;
    }

    const char* original_string_data() const {
        return _s; }

    // (enumerators rather than static data members, so that no
    // out-of-class definition is needed in C++11)
    enum : std::size_t { max_stored_size = 15 };

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
    enum : std::size_t {
        long_marker = 255,
        long_stored_size = max_stored_size - sizeof(std::uint32_t)
    };

    void set_original_string(const char* str, std::size_t len) {
        if (len <= max_stored_size) {
            std::memcpy(_s, str, len);
            _n = static_cast<unsigned char>(len);
        } else if (len < long_marker) {
            std::memcpy(_s, str, max_stored_size);
            _n = static_cast<unsigned char>(len);
        } else {
            std::uint32_t len32 = (len > UINT32_MAX)
                ? UINT32_MAX : static_cast<std::uint32_t>(len);
            std::memcpy(_s, str, long_stored_size);
            std::memcpy(_s + long_stored_size, &len32, sizeof(len32));
            _n = long_marker;
        }
    }

    double _value;
    char _s[max_stored_size];
    unsigned char _n;  // length, or long_marker for a length of 255 or more
};

static_assert(std::is_trivially_copyable<EndfFloatCpp>::value,
              "EndfFloatCpp must be trivially copyable");
static_assert(sizeof(EndfFloatCpp) == 24, "unexpected size of EndfFloatCpp");


// Fast creation of and access to instances of the Python class EndfFloat
// (endf_parserpy.utils.math_utils), used by the type caster below.
// EndfFloat.__init__(value, orig_str) only assigns the instance attributes
// _value = float(value) and _orig_str = orig_str, and __float__ and
// get_original_string return them. The fast path creates the instance with
// tp_new (object.__new__) and assigns the two attributes in the same order,
// without executing the Python code of __init__; it reads the attributes
// directly for instances of exactly this class. On first use, the fast
// creation is checked against a regular instantiation (same attributes in
// the same order); if they differ, e.g. after a change of the Python
// class, the regular (slow) path is used.

inline PyObject* cpp_interned_pystr(const char* s) {
    PyObject* res = PyUnicode_InternFromString(s);
    if (res == nullptr) throw py::error_already_set();
    return res;
}

struct CppEndfFloatPy {
    py::object cls;
    PyObject* key_value;     // "_value", never released
    PyObject* key_orig_str;  // "_orig_str", never released
    PyObject* empty_args;    // (), never released
    bool fast_ok;

    static CppEndfFloatPy& get() {
        // allocated once and intentionally never destroyed, so that no
        // Python object is released after the interpreter has finalized
        static CppEndfFloatPy* inst = new CppEndfFloatPy();
        return *inst;
    }

    py::object create_fast(double value, const char* orig_str, std::size_t len) {
        PyTypeObject* tp = reinterpret_cast<PyTypeObject*>(cls.ptr());
        py::object obj = py::reinterpret_steal<py::object>(tp->tp_new(tp, empty_args, nullptr));
        if (! obj) throw py::error_already_set();
        py::float_ pyval(value);
        py::str pystr(orig_str, len);
        if (PyObject_SetAttr(obj.ptr(), key_value, pyval.ptr()) != 0) throw py::error_already_set();
        if (PyObject_SetAttr(obj.ptr(), key_orig_str, pystr.ptr()) != 0) throw py::error_already_set();
        return obj;
    }

    py::object create(double value, const char* orig_str, std::size_t len) {
        if (fast_ok) return create_fast(value, orig_str, len);
        return cls(py::float_(value), py::str(orig_str, len));
    }

    // value and original string of an instance of exactly the class
    // EndfFloat whose attributes have the expected types
    bool read_fast(PyObject* obj, EndfFloatCpp& result) {
        if (! fast_ok || Py_TYPE(obj) != reinterpret_cast<PyTypeObject*>(cls.ptr())) return false;
        py::object v = py::reinterpret_steal<py::object>(PyObject_GetAttr(obj, key_value));
        if (! v) { PyErr_Clear(); return false; }
        py::object s = py::reinterpret_steal<py::object>(PyObject_GetAttr(obj, key_orig_str));
        if (! s) { PyErr_Clear(); return false; }
        if (! PyFloat_CheckExact(v.ptr()) || ! PyUnicode_CheckExact(s.ptr())) return false;
        Py_ssize_t len;
        const char* data = PyUnicode_AsUTF8AndSize(s.ptr(), &len);
        if (data == nullptr) { PyErr_Clear(); return false; }
        result = EndfFloatCpp(PyFloat_AS_DOUBLE(v.ptr()), data, static_cast<std::size_t>(len));
        return true;
    }

private:
    CppEndfFloatPy() : fast_ok(false) {
        cls = py::module::import("endf_parserpy.utils.math_utils").attr("EndfFloat");
        key_value = cpp_interned_pystr("_value");
        key_orig_str = cpp_interned_pystr("_orig_str");
        empty_args = PyTuple_New(0);
        if (empty_args == nullptr) throw py::error_already_set();
        // compare the fast creation with a regular instantiation
        try {
            py::object ref = cls(py::float_(1.5), py::str(" 1.500000+0"));
            py::object test = create_fast(1.5, " 1.500000+0", 11);
            py::object items = py::module::import("builtins").attr("list");
            fast_ok = items(ref.attr("__dict__").attr("items")()).equal(
                items(test.attr("__dict__").attr("items")()));
        } catch (py::error_already_set&) {
            fast_ok = false;
        }
    }
};


namespace PYBIND11_NAMESPACE { namespace detail {

    // Establish conversion between Python float and EndfFloatCpp
    template <> struct type_caster<EndfFloatCpp> {
    public:
        PYBIND11_TYPE_CASTER(EndfFloatCpp, const_name("EndfFloatCpp"));

        bool load(handle src, bool) {
            CppEndfFloatPy& endf_float_py = CppEndfFloatPy::get();
            const py::object& PyEndfFloat = endf_float_py.cls;
            // case 1: cast Python float to EndfFloatCpp
            if (py::isinstance<py::float_>(src)) {
                py::float_ tmp = py::cast<py::float_>(src);
                double float_value = tmp.cast<double>();
                value = EndfFloatCpp(float_value);
                return !(float_value == -1 && PyErr_Occurred());
            }

            // case 2: cast Python int to EndfFloatCpp
            else if (py::isinstance<py::int_>(src)) {
                py::int_ tmp = py::cast<py::int_>(src);
                double int_value = tmp.cast<double>() ;
                value = EndfFloatCpp(int_value);
                return true;
            }

            // case 3: cast Python float to EndfFloatCpp
            else if (py::isinstance(src, PyEndfFloat)) {
                if (endf_float_py.read_fast(src.ptr(), value)) {
                    return true;
                }
				auto float_method = src.attr("__float__");
				double float_value = float_method().cast<double>();
				std::string orig_str = src.attr("get_original_string")().cast<std::string>();
				value = EndfFloatCpp(float_value, orig_str);
                return true;
            }

            // case 4: other integers, i.e. objects implementing __index__,
            // such as numpy integer scalars of any width and signedness
            if (PyIndex_Check(src.ptr())) {
                PyObject* int_obj = PyNumber_Index(src.ptr());
                if (int_obj != nullptr) {
                    double int_value = PyLong_AsDouble(int_obj);
                    Py_DECREF(int_obj);
                    if (! (int_value == -1.0 && PyErr_Occurred())) {
                        value = EndfFloatCpp(int_value);
                        return true;
                    }
                }
                PyErr_Clear();
            }

            // case 5: other floats, i.e. objects implementing __float__,
            // such as numpy.float32 scalars
            PyNumberMethods* num_methods = Py_TYPE(src.ptr())->tp_as_number;
            if (num_methods != nullptr && num_methods->nb_float != nullptr) {
                double float_value = PyFloat_AsDouble(src.ptr());
                if (! (float_value == -1.0 && PyErr_Occurred())) {
                    value = EndfFloatCpp(float_value);
                    return true;
                }
                PyErr_Clear();
            }
            return false;
        }

        static handle cast(const EndfFloatCpp& src, return_value_policy, handle) {
            double float_value = static_cast<double>(src);
            if (! src.has_original_string()) {
                return py::float_(float_value).release();
            } else {
                return CppEndfFloatPy::get().create(
                    float_value, src.original_string_data(),
                    src.original_string_stored_size()).release();
            }
        }
    };


}} // namespace PYBIND11_NAMESPACE::detail


#endif // CPP_ENDF_FLOAT_HPP
