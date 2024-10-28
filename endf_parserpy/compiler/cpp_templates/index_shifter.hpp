#ifndef INDEX_SHIFTER_HPP
#define INDEX_SHIFTER_HPP


#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <map>
#include <string>


namespace py = pybind11;


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

    bool key_exists(py::list obj, int key) {
        return key < obj.size();
    }

    bool key_exists(py::dict obj, int key) {
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
        V pyobj, const std::vector<int>& recipe_indices, py::object defval, int i
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
        if (i+1 < recipe_indices.size()) {
            auto& next_level = get_next_level(index_value);
            if (! defval.is_none() & ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, V());
            }
            return next_level.setdefault_i(
                py::cast<V>(pyobj[py::cast(py_index_value)]), recipe_indices, defval, i+1
            );
        } else {
            if (! defval.is_none() & ! key_exists(pyobj, py_index_value)) {
                insert_obj(pyobj, py_index_value, defval);
            }
            return pyobj[py::cast(py_index_value)];
        }
    }

public:
    IndexShifter()
        : start_index(0), accessed(false), list_mode(false) {}

    IndexShifter(bool list_mode)
        : start_index(0), accessed(false), list_mode(list_mode) {}

    IndexShifter(const IndexShifter &other)
        : start_index(other.start_index), accessed(other.accessed),
          list_mode(other.list_mode), next_level(other.next_level) {}

    IndexShifter& operator=(const IndexShifter& other) {
        if (this != &other) {
            start_index = other.start_index;
            accessed = other.accessed;
            list_mode = other.list_mode;
            next_level = other.next_level;
        }
        return *this;
    }

    py::object setdefault(py::object pyobj, const std::vector<int> recipe_indices, py::object defval) {
        if (list_mode) {
            return setdefault_i(pyobj.cast<py::list>(), recipe_indices, defval, 0);
        } else {
            return setdefault_i(pyobj.cast<py::dict>(), recipe_indices, defval, 0);
        }
    }

    py::object get_value(py::object pyobj, const std::vector<int> recipe_indices) {
        return setdefault(pyobj, recipe_indices, py::none());
    }

};


class IndexShifterStore {

private:
    using IndexShifterMap = std::map<std::string, IndexShifter>;

    bool list_mode;
    py::dict refdict;
    IndexShifterMap index_shifter_map;

public:
    IndexShifterStore()
        : list_mode(false) {}

    IndexShifterStore(py::dict refdict, bool list_mode)
        : refdict(refdict), list_mode(list_mode) {}

    IndexShifterStore(const IndexShifterStore &other)
        : list_mode(other.list_mode), refdict(other.refdict),
          index_shifter_map(other.index_shifter_map) {}

    IndexShifterStore& operator=(const IndexShifterStore &other) {
        if (this != &other) {
            list_mode = other.list_mode;
            refdict = other.refdict;
            index_shifter_map = other.index_shifter_map;
        }
        return *this;
    }

    py::object setdefault(std::string varname, std::vector<int> indices, py::object defval) {
        if (!defval.is_none() && !refdict.contains(varname)) {
            if (indices.empty()) {
                refdict[py::cast(varname)] = defval;
                return defval;
            } else if (list_mode) {
                refdict[py::cast(varname)] = py::list();
            } else {
                refdict[py::cast(varname)] = py::dict();
            }
        }
        auto pyobj = refdict[py::cast(varname)];
        if (indices.empty()) {
            return pyobj;
        }
        IndexShifterMap::iterator it = index_shifter_map.find(varname);
        if (it == index_shifter_map.end()) {
            index_shifter_map[varname] = IndexShifter(list_mode);
        }
        auto &index_shifter = index_shifter_map[varname];
        return index_shifter.setdefault(pyobj, indices, defval);
    }

    py::object get_value(std::string varname, std::vector<int> indices, py::object defval=py::none()) {
        if (! defval.is_none() & ! refdict.contains(varname)) {
            return defval;
        }
        return setdefault(varname, indices, py::none());
    }

};


#endif // INDEX_SHIFTER_HPP
