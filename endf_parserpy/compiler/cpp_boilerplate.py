############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/18
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from . import cpp_primitives as cpp


def module_header():
    code = r"""
    #include <pybind11/pybind11.h>
    #include <pybind11/stl.h> // Necessary for STL containers like std::map

    #include <stdexcept>
    #include <iostream>
    #include <sstream>
    #include <fstream>
    #include <vector>
    #include <string>

    namespace py = pybind11;


    double endfstr2float(const char* str) {
        char tbuf[13];
        int j = 0;
        bool in_number = false;
        bool in_exponent = false;
        for (int i=0; i < 11; i++) {
            char c = str[i];
            if (c == ' ') continue;
            if (in_number) {
                if (!in_exponent) {
                    if (c=='+' || c=='-') {
                        tbuf[j++] = 'e';
                        in_exponent = true;
                    } else if (c=='e' || c=='E') {
                        in_exponent = true;
                    }
                }
            } else {
                if (c == '.' || (c >= '0' && c <= '9')) {
                    in_number = true;
                }
            }
            tbuf[j++] = c;
        }
        if (j==0) tbuf[j++] = '0';
        tbuf[j++] = '\0';
        return std::stod(tbuf);
    }


    int endfstr2int(const std::string& str) {
        if (str.find_first_not_of(' ') == std::string::npos) {
            return 0;
        }
        return std::stoi(str);
    }


    double cpp_read_float_field(const std::string& str, const char fieldnum) {
        return endfstr2float(str.substr(fieldnum*11, 11).c_str());
    }


    double cpp_read_int_field(const std::string& str, const char fieldnum) {
        return endfstr2int(str.substr(fieldnum*11, 11));
    }


    double cpp_read_custom_int_field(const std::string& str, int start_pos, int length) {
        return endfstr2int(str.substr(start_pos, length));
    }


    std::string cpp_read_line(std::istream& cont) {
        std::string line;
        std::getline(cont, line);
        return line;
    }


    void cpp_read_send(std::istream& cont) {
        std::string line = cpp_read_line(cont);
        int mtnum = std::stoi(line.substr(72, 3));
        if (cpp_read_float_field(line, 0) != 0.0 ||
            cpp_read_float_field(line, 1) != 0.0 ||
            cpp_read_int_field(line, 2) != 0 ||
            cpp_read_int_field(line, 3) != 0 ||
            cpp_read_int_field(line, 4) != 0 ||
            cpp_read_int_field(line, 5) != 0 ||
            mtnum != 0) {

            std::cout << line << std::endl;  // debug
            throw std::runtime_error("expected SEND record");
        }
    }


    std::vector<int> cpp_read_int_vec(std::istream& cont, const int numel) {
        int j = 0;
        std::vector<int> res;
        std::string line = cpp_read_line(cont);
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_int_field(line, j++));
            if (j > 5 && i+1 < numel) {
                line = cpp_read_line(cont);
                j = 0;
            }
        }
        return res;
    }


    std::vector<double> cpp_read_float_vec(std::istream& cont, const int numel) {
        int j = 0;
        std::vector<double> res;
        std::string line = cpp_read_line(cont);
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_float_field(line, j++));
            if (j > 5 && i+1 < numel) {
                line = cpp_read_line(cont);
                j = 0;
            }
        }
        return res;
    }


    template<typename T>
    class CustomVector : public std::vector<T> {
        private:
            int startIndex;
            int lastIndex;

        public:
            // default constructor
            CustomVector() : startIndex(0), lastIndex(-1) {}

            // copy constructor
            CustomVector(const CustomVector<T>& other) :
                std::vector<T>(other), startIndex(other.startIndex),
                lastIndex(other.lastIndex) {}

            // assignment constructor
            CustomVector<T>& operator=(const CustomVector<T>& other) {
                if (this != &other) {
                    std::vector<T>::operator=(other);
                    startIndex = other.startIndex;
                    lastIndex = other.lastIndex;
                }
                return *this;
            }

            void set_start_index(int start) {
                this->startIndex = start;
            }

            int get_start_index() {
                return this->startIndex;
            }

            void set_last_index(int lastIndex) {
                this->lastIndex = lastIndex;
            }

            int get_last_index() {
                return this->lastIndex;
            }

            T& operator[](int index) {
                if (! contains(index)) {
                    throw std::out_of_range("index out of range 1");
                }
                return std::vector<T>::operator[](index - startIndex);
            }

            T& at(int index) {
                return std::vector<T>::at(index - startIndex);
            }

            T& prepare(int index) {
                if (contains(index)) return (*this)[index];
                T cpp_curel;
                set(index, cpp_curel);
                return (*this)[index];
            }

            void set(int index, const T& value) {
                bool is_first = false;
                if (this->lastIndex == -1) {
                    this->startIndex = index;
                    this->lastIndex = index;
                    is_first = true;
                }
                if (index == startIndex + (int)this->size()) {
                    std::vector<T>::push_back(value);
                    if (! is_first) {
                        this->lastIndex++;
                    }
                } else if (index >= startIndex && index < startIndex + (int)this->size())  {
                    std::vector<T>::operator[](index - startIndex) = value;
                } else {
                    throw std::out_of_range("index out of range 2");
                }
            }

            bool contains(int index) {
                return (this->startIndex <= index && index <= this->lastIndex);
            }
    };


    """
    return cpp.indent_code(code, -4)


def parsefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
    py::dict {fun_name}(std::istream& cont) {{
        std::vector<int> cpp_intvec;
        std::vector<double> cpp_floatvec;
        py::dict cpp_parent_dict;
        py::dict cpp_current_dict;
        py::dict cpp_workdict;
        int cpp_idxnum;
        int cpp_int_val;
        std::string cpp_line;
        double cpp_float_val;
    """,
        -4,
    )
    return code


def parsefun_footer():
    code = cpp.indent_code(
        """
        return cpp_current_dict;
    }
    """,
        -4,
    )
    return code


def register_cpp_parsefuns(parsefuns):
    code = "\n\nPYBIND11_MODULE(cpp_parsefuns, m) {\n"
    for parsefun in parsefuns:
        curcode = f"""m.def("{parsefun}", &{parsefun}, "parsing function");\n"""
        code += cpp.indent_code(curcode, 4)
    code += "\n}"
    return code


def generate_cmake_content():
    code = cpp.indent_code(
        """
    cmake_minimum_required(VERSION 3.12)
    project(cpp_parsefuns)

    find_package(pybind11 REQUIRED)

    # Create the C++ executable
    pybind11_add_module(cpp_parsefuns SHARED cpp_parsefuns.cpp)

    # Link against Python libraries
    # target_link_libraries(example PRIVATE Python::Python)
    set_property(TARGET cpp_parsefuns PROPERTY CXX_STANDARD 11)
    """,
        -4,
    )
    return code
