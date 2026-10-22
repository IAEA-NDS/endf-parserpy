#ifndef INDEX_SHIFTER_HPP
#define INDEX_SHIFTER_HPP


#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>
#include <map>
#include <string>
#include <vector>
#include <climits>
#include <cstring>


namespace py = pybind11;


// Fast item access for exact Python dict/list objects. In all other cases
// (missing key, index out of range, subclasses which may override
// __getitem__ or __missing__) the generic accessor is used, so that the
// behavior including the raised Python exceptions remains the same.
inline py::object index_shifter_get_item(const py::dict& obj, int key) {
    if (PyDict_CheckExact(obj.ptr())) {
        PyObject* pykey = PyLong_FromLong(key);
        if (pykey == nullptr) throw py::error_already_set();
        PyObject* item = PyDict_GetItemWithError(obj.ptr(), pykey);
        Py_DECREF(pykey);
        if (item != nullptr) return py::reinterpret_borrow<py::object>(item);
        if (PyErr_Occurred()) throw py::error_already_set();
    }
    return obj[py::cast(key)];
}

inline py::object index_shifter_get_item(const py::list& obj, int key) {
    if (PyList_CheckExact(obj.ptr()) && key >= 0 && key < PyList_GET_SIZE(obj.ptr())) {
        return py::reinterpret_borrow<py::object>(PyList_GET_ITEM(obj.ptr(), key));
    }
    return obj[py::cast(key)];
}

inline py::object index_shifter_get_item(const py::dict& obj, const py::str& key) {
    if (PyDict_CheckExact(obj.ptr())) {
        PyObject* item = PyDict_GetItemWithError(obj.ptr(), key.ptr());
        if (item != nullptr) return py::reinterpret_borrow<py::object>(item);
        if (PyErr_Occurred()) throw py::error_already_set();
    }
    return obj[key];
}

// In list mode, an array may also be given as an object other than a list
// that supports the buffer protocol, in particular a numpy array as
// produced by parsing with array_type="numpy". Such an object is indexed
// directly. Converting it to a list with py::cast<py::list>, as done for
// other objects, gives the same elements, but converts the whole array on
// every access of an element.
inline bool index_shifter_is_buffer_array(const py::object& obj) {
    return ! PyList_Check(obj.ptr()) && PyObject_CheckBuffer(obj.ptr());
}

// Other sequences than lists (e.g. tuples, read-only views of lists) are
// indexed directly as well when values are only read. Converting them with
// py::cast<py::list> copied the whole sequence on every access of an
// element, which made writing take time quadratic in the length of the
// array. Mapping types, which also implement __getitem__, are excluded, as
// their conversion to a list (of the keys) differs from indexing. When
// default values have to be inserted, which is impossible for e.g. a
// tuple, the previous conversion (insertion into a temporary list) is kept.
inline bool index_shifter_is_other_sequence(const py::object& obj) {
    PyObject* p = obj.ptr();
    if (PyList_Check(p) || PyDict_Check(p) || ! PySequence_Check(p)) return false;
    if (PyTuple_Check(p)) return true;
    int has_keys = PyObject_HasAttrString(p, "keys");
    return has_keys == 0;
}

inline py::object index_shifter_get_item(const py::object& obj, int key) {
    return obj[py::cast(key)];
}


// Fast reading of the elements of numpy arrays. Only objects of the exact
// type numpy.ndarray are read directly from memory, not subclasses, whose
// indexing may differ (e.g. numpy.matrix or masked arrays), and only arrays
// whose dtype is one of numpy's builtin descriptors (native byte order) of
// float64, float32 and the integer types. The type is first recognized by
// its name, so that numpy is never imported here for other objects. Data,
// shape and strides are read from the array object (public fields of
// PyArrayObject); no Python code runs in between.

enum CppNdarrayKind {
    NDKIND_NONE = 0, NDKIND_FLOAT64, NDKIND_FLOAT32, NDKIND_SIGNED, NDKIND_UNSIGNED
};

struct CppNdarrayView {
    const char* data;
    int ndim;
    const Py_intptr_t* dims;
    const Py_intptr_t* strides;
    int kind;
    int itemsize;
};

class CppNdarrayTypes {
public:
    PyTypeObject* type;

    static CppNdarrayTypes& get() {
        // allocated once and never destroyed (the descriptors are kept)
        static CppNdarrayTypes* inst = new CppNdarrayTypes();
        return *inst;
    }

    bool find(PyObject* descr, int& kind, int& itemsize) const {
        for (int i = 0; i < num; i++) {
            if (entries[i].descr == descr) {
                kind = entries[i].kind;
                itemsize = entries[i].itemsize;
                return true;
            }
        }
        return false;
    }

private:
    struct Entry { PyObject* descr; int kind; int itemsize; };
    Entry entries[12];
    int num;

    void add(py::detail::npy_api& api, int typenum, int kind, int itemsize) {
        PyObject* descr = api.PyArray_DescrFromType_(typenum);
        if (descr == nullptr) throw py::error_already_set();
        entries[num].descr = descr;  // reference kept
        entries[num].kind = kind;
        entries[num].itemsize = itemsize;
        num++;
    }

    CppNdarrayTypes() : num(0) {
        typedef py::detail::npy_api api_t;
        api_t& api = api_t::get();
        type = api.PyArray_Type_;
        add(api, api_t::NPY_DOUBLE_, NDKIND_FLOAT64, sizeof(double));
        add(api, api_t::NPY_FLOAT_, NDKIND_FLOAT32, sizeof(float));
        add(api, api_t::NPY_BYTE_, NDKIND_SIGNED, sizeof(signed char));
        add(api, api_t::NPY_UBYTE_, NDKIND_UNSIGNED, sizeof(unsigned char));
        add(api, api_t::NPY_SHORT_, NDKIND_SIGNED, sizeof(short));
        add(api, api_t::NPY_USHORT_, NDKIND_UNSIGNED, sizeof(unsigned short));
        add(api, api_t::NPY_INT_, NDKIND_SIGNED, sizeof(int));
        add(api, api_t::NPY_UINT_, NDKIND_UNSIGNED, sizeof(unsigned int));
        add(api, api_t::NPY_LONG_, NDKIND_SIGNED, sizeof(long));
        add(api, api_t::NPY_ULONG_, NDKIND_UNSIGNED, sizeof(unsigned long));
        add(api, api_t::NPY_LONGLONG_, NDKIND_SIGNED, sizeof(long long));
        add(api, api_t::NPY_ULONGLONG_, NDKIND_UNSIGNED, sizeof(unsigned long long));
    }
};

// whether obj is a numpy array readable by the fast path; fills view
inline bool cpp_ndarray_view(PyObject* obj, CppNdarrayView& view) {
    static PyTypeObject* ndarray_type = nullptr;
    PyTypeObject* tp = Py_TYPE(obj);
    if (tp != ndarray_type) {
        if (ndarray_type != nullptr || std::strcmp(tp->tp_name, "numpy.ndarray") != 0) {
            return false;
        }
        if (tp != CppNdarrayTypes::get().type) return false;
        ndarray_type = tp;
    }
    const py::detail::PyArray_Proxy* arr = py::detail::array_proxy(obj);
    if (! CppNdarrayTypes::get().find(arr->descr, view.kind, view.itemsize)) return false;
    view.data = arr->data;
    view.ndim = arr->nd;
    view.dims = reinterpret_cast<const Py_intptr_t*>(arr->dimensions);
    view.strides = reinterpret_cast<const Py_intptr_t*>(arr->strides);
    return true;
}

inline long long cpp_ndarray_read_signed(const char* ptr, int size) {
    switch (size) {
        case 1: { signed char v; std::memcpy(&v, ptr, 1); return v; }
        case 2: { short v; std::memcpy(&v, ptr, 2); return v; }
        case 4: { int v; std::memcpy(&v, ptr, 4); return v; }
        default: { long long v; std::memcpy(&v, ptr, 8); return v; }
    }
}

inline unsigned long long cpp_ndarray_read_unsigned(const char* ptr, int size) {
    switch (size) {
        case 1: { unsigned char v; std::memcpy(&v, ptr, 1); return v; }
        case 2: { unsigned short v; std::memcpy(&v, ptr, 2); return v; }
        case 4: { unsigned int v; std::memcpy(&v, ptr, 4); return v; }
        default: { unsigned long long v; std::memcpy(&v, ptr, 8); return v; }
    }
}

// Python float or int with the value of the element at ptr, which is
// converted in the same way as the numpy scalar obtained by indexing; an
// empty object for float32 (a numpy.float32 is converted differently than
// a Python float in integer fields) and for integers outside the range of
// int (so that the error is the same), for which the generic access is used
inline py::object cpp_ndarray_element(const CppNdarrayView& view, const char* ptr) {
    PyObject* res = nullptr;
    switch (view.kind) {
        case NDKIND_FLOAT64: {
            double v;
            std::memcpy(&v, ptr, sizeof(double));
            res = PyFloat_FromDouble(v);
            break;
        }
        case NDKIND_SIGNED: {
            long long v = cpp_ndarray_read_signed(ptr, view.itemsize);
            if (v < INT_MIN || v > INT_MAX) return py::object();
            res = PyLong_FromLongLong(v);
            break;
        }
        case NDKIND_UNSIGNED: {
            unsigned long long v = cpp_ndarray_read_unsigned(ptr, view.itemsize);
            if (v > static_cast<unsigned long long>(INT_MAX)) return py::object();
            res = PyLong_FromLongLong(static_cast<long long>(v));
            break;
        }
        default:
            return py::object();
    }
    if (res == nullptr) throw py::error_already_set();
    return py::reinterpret_steal<py::object>(res);
}

// element i of a one-dimensional numpy array, or an empty object if the
// generic access is to be used (also for an index out of range)
inline py::object cpp_ndarray_get_item(const py::object& obj, int i) {
    CppNdarrayView view;
    if (! cpp_ndarray_view(obj.ptr(), view) || view.ndim != 1 || i < 0 || i >= view.dims[0]) {
        return py::object();
    }
    return cpp_ndarray_element(view, view.data + i * view.strides[0]);
}

// Conversion of a TAB1/TAB2 table to std::vector<EndfFloatCpp> or
// std::vector<int>, equivalent to py::cast<V>(obj), filling the vector in
// a single loop from a one-dimensional numpy array readable by the fast
// path (for floats also of float32, as the target type is known; for
// integers only of an integer type and with all values in the range of
// int)
inline bool cpp_ndarray_to_vector(const CppNdarrayView& view, std::vector<EndfFloatCpp>& vec) {
    const Py_intptr_t n = view.dims[0];
    vec.reserve(n);
    for (Py_intptr_t i = 0; i < n; i++) {
        const char* ptr = view.data + i * view.strides[0];
        double v;
        switch (view.kind) {
            case NDKIND_FLOAT64: std::memcpy(&v, ptr, sizeof(double)); break;
            case NDKIND_FLOAT32: { float f; std::memcpy(&f, ptr, sizeof(float)); v = f; break; }
            case NDKIND_SIGNED: v = static_cast<double>(cpp_ndarray_read_signed(ptr, view.itemsize)); break;
            case NDKIND_UNSIGNED: v = static_cast<double>(cpp_ndarray_read_unsigned(ptr, view.itemsize)); break;
            default: return false;
        }
        vec.push_back(EndfFloatCpp(v));
    }
    return true;
}

inline bool cpp_ndarray_to_vector(const CppNdarrayView& view, std::vector<int>& vec) {
    if (view.kind != NDKIND_SIGNED && view.kind != NDKIND_UNSIGNED) return false;
    const Py_intptr_t n = view.dims[0];
    vec.reserve(n);
    for (Py_intptr_t i = 0; i < n; i++) {
        const char* ptr = view.data + i * view.strides[0];
        if (view.kind == NDKIND_SIGNED) {
            long long v = cpp_ndarray_read_signed(ptr, view.itemsize);
            if (v < INT_MIN || v > INT_MAX) return false;
            vec.push_back(static_cast<int>(v));
        } else {
            unsigned long long v = cpp_ndarray_read_unsigned(ptr, view.itemsize);
            if (v > static_cast<unsigned long long>(INT_MAX)) return false;
            vec.push_back(static_cast<int>(v));
        }
    }
    return true;
}

template <typename V>
inline V cpp_cast_vector(const py::object& obj) {
    CppNdarrayView view;
    if (cpp_ndarray_view(obj.ptr(), view) && view.ndim == 1) {
        V vec;
        if (cpp_ndarray_to_vector(view, vec)) return vec;
    }
    return py::cast<V>(obj);
}

// equivalent of py::cast<V>(obj) without overhead if obj is already of type V
template <typename V>
inline V index_shifter_as(const py::object& obj);

template <>
inline py::dict index_shifter_as<py::dict>(const py::object& obj) {
    if (PyDict_Check(obj.ptr())) return py::reinterpret_borrow<py::dict>(obj);
    return py::cast<py::dict>(obj);
}

template <>
inline py::list index_shifter_as<py::list>(const py::object& obj) {
    if (PyList_Check(obj.ptr())) return py::reinterpret_borrow<py::list>(obj);
    return py::cast<py::list>(obj);
}


class IndexShifter {

private:
    int start_index;
    bool accessed;
    bool list_mode;
    std::vector<IndexShifter> next_level;

    // index bookkeeping of the next level for the element at position idx
    // (relative to the first index accessed at this level); elements may be
    // skipped, e.g. inner arrays without elements, and with dict arrays an
    // element may precede the first one accessed (list mode rejects negative
    // positions in shift_index)
    IndexShifter& get_next_level(int idx) {
        if (idx < 0) {
            next_level.insert(next_level.begin(), -idx, IndexShifter(list_mode));
            start_index += idx;
            idx = 0;
        } else if (idx >= static_cast<int>(next_level.size())) {
            next_level.resize(idx + 1, IndexShifter(list_mode));
        }
        return next_level[idx];
    }

    // element access, for numpy arrays with the fast path
    py::object get_item(const py::list& obj, int key) {
        return index_shifter_get_item(obj, key);
    }

    py::object get_item(const py::dict& obj, int key) {
        return index_shifter_get_item(obj, key);
    }

    py::object get_item(const py::object& obj, int key) {
        py::object item = cpp_ndarray_get_item(obj, key);
        if (item) return item;
        return index_shifter_get_item(obj, key);
    }

    // element (key, recipe_indices[i+1]) of a two-dimensional numpy array,
    // with the index bookkeeping of the next level as in the recursion;
    // an empty object if the generic access is to be used
    py::object get_item_2d(const py::list&, IndexShifter&, int, const std::vector<int>&, int) {
        return py::object();
    }

    py::object get_item_2d(const py::dict&, IndexShifter&, int, const std::vector<int>&, int) {
        return py::object();
    }

    py::object get_item_2d(
        const py::object& obj, IndexShifter& next, int key, const std::vector<int>& recipe_indices, int i
    ) {
        CppNdarrayView view;
        if (i + 2 != static_cast<int>(recipe_indices.size()) || ! cpp_ndarray_view(obj.ptr(), view)
            || view.ndim != 2 || key < 0 || key >= view.dims[0]) {
            return py::object();
        }
        int index_value;
        int col = next.shift_index(recipe_indices[i+1], index_value);
        if (col < 0 || col >= view.dims[1]) return py::object();
        return cpp_ndarray_element(view, view.data + key * view.strides[0] + col * view.strides[1]);
    }

    // position in the Python container of the element with the recipe
    // index py_index_value (index_value: position relative to the first
    // recipe index accessed at this level)
    int shift_index(int py_index_value, int& index_value) {
        if (!accessed) {
            accessed = true;
            start_index = py_index_value;
        }
        index_value = py_index_value - start_index;
        if (list_mode) {
            py_index_value = index_value;
            if (py_index_value < 0) {
                throw std::out_of_range("list index out of range");
            }
        }
        return py_index_value;
    }

    bool key_exists(const py::list& obj, int key) {
        return key < obj.size();
    }

    bool key_exists(const py::object& obj, int key) {
        return key < py::len(obj);
    }

    bool key_exists(const py::dict& obj, int key) {
        return obj.contains(py::cast(key));
    }

    void insert_obj(py::list pyobj, int key, py::object elem) {
        if (key == pyobj.size()) {
            pyobj.append(elem);
        } else {
            pyobj[key] = elem;
        }
    }

    void insert_obj(py::dict pyobj, int key, py::object elem) {
        pyobj[py::cast(key)] = elem;
    }

    void insert_obj(py::object pyobj, int key, py::object elem) {
        if (key == py::len(pyobj)) {
            pyobj.attr("append")(elem);
        } else {
            pyobj[py::cast(key)] = elem;
        }
    }

    // empty container for a missing element of pyobj
    static py::object new_container(const py::list&) { return py::list(); }
    static py::object new_container(const py::dict&) { return py::dict(); }
    static py::object new_container(const py::object&) { return py::list(); }

    py::object setdefault_any(
        const py::object& pyobj, const std::vector<int>& recipe_indices, const py::object& defval, int i
    ) {
        if (list_mode) {
            if (index_shifter_is_buffer_array(pyobj)
                || (defval.is_none() && index_shifter_is_other_sequence(pyobj))) {
                return setdefault_i(pyobj, recipe_indices, defval, i);
            }
            return setdefault_i(index_shifter_as<py::list>(pyobj), recipe_indices, defval, i);
        } else {
            return setdefault_i(index_shifter_as<py::dict>(pyobj), recipe_indices, defval, i);
        }
    }

    template <typename V>
    py::object setdefault_i(
        const V& pyobj, const std::vector<int>& recipe_indices, const py::object& defval, int i
    ) {
        int index_value;
        int py_index_value = shift_index(recipe_indices[i], index_value);
        bool has_defval = ! defval.is_none();
        if (i+1 < recipe_indices.size()) {
            auto& next_level = get_next_level(index_value);
            if (has_defval && ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, new_container(pyobj));
            }
            if (! has_defval) {
                py::object item = get_item_2d(pyobj, next_level, py_index_value, recipe_indices, i);
                if (item) return item;
            }
            return next_level.setdefault_any(
                index_shifter_get_item(pyobj, py_index_value),
                recipe_indices, defval, i+1
            );
        } else {
            if (has_defval && ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, defval);
            }
            if (has_defval) {
                return index_shifter_get_item(pyobj, py_index_value);
            }
            return get_item(pyobj, py_index_value);
        }
    }

public:
    // register the position of the element with the given recipe indices
    // (one index per level, from the first) without accessing it, so that
    // the start index of each level is the first index of the loop that
    // creates the elements, also if an element remains empty
    void register_element(const std::vector<int>& recipe_indices, int i=0) {
        int index_value;
        shift_index(recipe_indices[i], index_value);
        if (i+1 < static_cast<int>(recipe_indices.size())) {
            get_next_level(index_value).register_element(recipe_indices, i+1);
        }
    }

    IndexShifter()
        : start_index(0), accessed(false), list_mode(false) {}

    IndexShifter(bool list_mode)
        : start_index(0), accessed(false), list_mode(list_mode) {}

    py::object setdefault(const py::object& pyobj, const std::vector<int>& recipe_indices, const py::object& defval) {
        return setdefault_any(pyobj, recipe_indices, defval, 0);
    }

    py::object get_value(const py::object& pyobj, const std::vector<int>& recipe_indices) {
        return setdefault(pyobj, recipe_indices, py::none());
    }

};


class IndexShifterStore {

private:
    using IndexShifterMap = std::map<std::string, IndexShifter>;

    bool list_mode;
    py::dict refdict;
    IndexShifterMap index_shifter_map;

    py::object lookup(const std::string& varname, const py::str& key, const std::vector<int>& indices) {
        py::object pyobj = index_shifter_get_item(refdict, key);
        if (indices.empty()) {
            return pyobj;
        }
        IndexShifterMap::iterator it = index_shifter_map.find(varname);
        if (it == index_shifter_map.end()) {
            it = index_shifter_map.insert(std::make_pair(varname, IndexShifter(list_mode))).first;
        }
        return it->second.setdefault(pyobj, indices, py::none());
    }

public:
    IndexShifterStore()
        : list_mode(false) {}

    IndexShifterStore(py::dict refdict, bool list_mode)
        : refdict(refdict), list_mode(list_mode) {}

    py::object setdefault(const std::string& varname, const std::vector<int>& indices, const py::object& defval) {
        py::str key(varname);
        if (!defval.is_none() && !refdict.contains(key)) {
            if (indices.empty()) {
                refdict[key] = defval;
                return defval;
            } else if (list_mode) {
                refdict[key] = py::list();
            } else {
                refdict[key] = py::dict();
            }
        }
        if (defval.is_none()) {
            return lookup(varname, key, indices);
        }
        py::object pyobj = index_shifter_get_item(refdict, key);
        if (indices.empty()) {
            return pyobj;
        }
        IndexShifterMap::iterator it = index_shifter_map.find(varname);
        if (it == index_shifter_map.end()) {
            it = index_shifter_map.insert(std::make_pair(varname, IndexShifter(list_mode))).first;
        }
        return it->second.setdefault(pyobj, indices, defval);
    }

    // with list mode, register the element of a nested array that the
    // parsing code creates before the loop filling it (see
    // IndexShifter::register_element); dict arrays are indexed by the
    // recipe indices themselves
    void register_element(const std::string& varname, const std::vector<int>& indices) {
        if (!list_mode) return;
        IndexShifterMap::iterator it = index_shifter_map.find(varname);
        if (it == index_shifter_map.end()) {
            it = index_shifter_map.insert(std::make_pair(varname, IndexShifter(list_mode))).first;
        }
        it->second.register_element(indices);
    }

    bool has_value(const std::string& varname) {
        return refdict.contains(varname);
    }

    py::object get_value(const std::string& varname, const std::vector<int>& indices, const py::object& defval=py::none()) {
        py::str key(varname);
        if (! defval.is_none() && ! refdict.contains(key)) {
            return defval;
        }
        return lookup(varname, key, indices);
    }

};


// ---------------------------------------------------------------------
// Values of INTG records (writing)
//
// The first n elements of the row of integers of an INTG record, each one
// converted as py::cast<int>(row[py::cast(i)]), so that the row is
// retrieved from the dictionary once per record rather than once per
// field. Exact lists are read with PyList_GET_ITEM, one-dimensional numpy
// arrays of an integer type directly from memory. For other objects, a
// list or array with fewer than n elements, and a numpy array with values
// outside the range of int, the generic access is used for the remaining
// elements, so that the same exception is raised for the same element.
// ---------------------------------------------------------------------

inline std::vector<int> cpp_intg_row_values(const py::object& row, int n) {
    std::vector<int> vals;
    vals.reserve(n);
    PyObject* p = row.ptr();
    CppNdarrayView view;
    if (PyList_CheckExact(p)) {
        if (PyList_GET_SIZE(p) >= n) {
            for (int i = 0; i < n; i++) {
                vals.push_back(py::cast<int>(py::handle(PyList_GET_ITEM(p, i))));
            }
        }
    } else if (cpp_ndarray_view(p, view) && view.ndim == 1 && view.dims[0] >= n
               && (view.kind == NDKIND_SIGNED || view.kind == NDKIND_UNSIGNED)) {
        for (int i = 0; i < n; i++) {
            const char* ptr = view.data + i * view.strides[0];
            long long v;
            if (view.kind == NDKIND_SIGNED) {
                v = cpp_ndarray_read_signed(ptr, view.itemsize);
            } else {
                unsigned long long u = cpp_ndarray_read_unsigned(ptr, view.itemsize);
                if (u > static_cast<unsigned long long>(INT_MAX)) break;
                v = static_cast<long long>(u);
            }
            if (v < INT_MIN || v > INT_MAX) break;
            vals.push_back(static_cast<int>(v));
        }
    }
    for (int i = static_cast<int>(vals.size()); i < n; i++) {
        vals.push_back(py::cast<int>(row[py::cast(i)]));
    }
    return vals;
}


#endif // INDEX_SHIFTER_HPP
