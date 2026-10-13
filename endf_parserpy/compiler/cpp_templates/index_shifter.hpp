#ifndef INDEX_SHIFTER_HPP
#define INDEX_SHIFTER_HPP


#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <map>
#include <string>


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

    IndexShifter& get_next_level(int idx) {
        if (idx == next_level.size()) {
            next_level.push_back(IndexShifter(list_mode));
        }
        return next_level[idx];
    }

    bool key_exists(const py::list& obj, int key) {
        return key < obj.size();
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

    template <typename V>
    py::object setdefault_i(
        const V& pyobj, const std::vector<int>& recipe_indices, const py::object& defval, int i
    ) {
        int py_index_value = recipe_indices[i];
        if (!accessed) {
            accessed = true;
            start_index = py_index_value;
        }
        int index_value = py_index_value - start_index;
        if (list_mode) {
            py_index_value = index_value;
            if (py_index_value < 0) {
                throw std::out_of_range("list index out of range");
            }
        }
        bool has_defval = ! defval.is_none();
        if (i+1 < recipe_indices.size()) {
            auto& next_level = get_next_level(index_value);
            if (has_defval && ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, V());
            }
            return next_level.setdefault_i(
                index_shifter_as<V>(index_shifter_get_item(pyobj, py_index_value)),
                recipe_indices, defval, i+1
            );
        } else {
            if (has_defval && ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, defval);
            }
            return index_shifter_get_item(pyobj, py_index_value);
        }
    }

public:
    IndexShifter()
        : start_index(0), accessed(false), list_mode(false) {}

    IndexShifter(bool list_mode)
        : start_index(0), accessed(false), list_mode(list_mode) {}

    py::object setdefault(const py::object& pyobj, const std::vector<int>& recipe_indices, const py::object& defval) {
        if (list_mode) {
            return setdefault_i(index_shifter_as<py::list>(pyobj), recipe_indices, defval, 0);
        } else {
            return setdefault_i(index_shifter_as<py::dict>(pyobj), recipe_indices, defval, 0);
        }
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


#endif // INDEX_SHIFTER_HPP
