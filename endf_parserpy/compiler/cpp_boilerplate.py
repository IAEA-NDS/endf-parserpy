############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/12
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
    #include <vector>
    #include <string>

    namespace py = pybind11;


    double endfstr2float(const std::string& str) {
        char tbuf[str.size()+1];
        int j = 0;
        bool in_number = false;
        bool in_exponent = false;
        for (int i=0; i < (int)str.size(); i++) {
            char c = str[i];
            if (c == ' ') continue;
            if (in_number) {
                if (!in_exponent) {
                    if (c=='+' || c=='-') {
                        tbuf[j++] = 'e';
                        in_exponent = true;
                    }
                } else if (c=='e' || c=='E') {
                    in_exponent = true;
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
        return endfstr2float(str.substr(fieldnum*11, 11));
    }


    double cpp_read_int_field(const std::string& str, const char fieldnum) {
        return endfstr2int(str.substr(fieldnum*11, 11));
    }


    std::string* cpp_read_line(std::vector<std::string>& lines, int& linenum) {
        if (lines.size() <= linenum) {
            throw std::runtime_error("expected more lines");
        }
        return &lines[linenum++];
    }


    void cpp_read_send(std::vector<std::string>& lines, int& linenum) {
        std::string* lineptr = cpp_read_line(lines, linenum);
        int mtnum = std::stoi(lineptr->substr(72, 3));
        if (cpp_read_float_field(*lineptr, 0) != 0.0 ||
            cpp_read_float_field(*lineptr, 1) != 0.0 ||
            cpp_read_int_field(*lineptr, 2) != 0 ||
            cpp_read_int_field(*lineptr, 3) != 0 ||
            cpp_read_int_field(*lineptr, 4) != 0 ||
            cpp_read_int_field(*lineptr, 5) != 0 ||
            mtnum != 0) {

            std::cout << linenum << std::endl;
            std::cout << *lineptr << std::endl;
            throw std::runtime_error("expected SEND record");
        }
    }


    std::vector<int> cpp_read_int_vec(std::vector<std::string>& lines, const int numel, int& linenum) {
        int j = 0;
        std::vector<int> res;
        std::string* lineptr = &lines[linenum];
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_int_field(*lineptr, j++));
            if (j > 5) {
                lineptr = &lines[++linenum];
                j = 0;
            }
        }
        if (j != 0) linenum++;
        return res;
    }


    std::vector<double> cpp_read_float_vec(std::vector<std::string>& lines, const int numel, int& linenum) {
        int j = 0;
        std::vector<double> res;
        std:: string* lineptr = &lines[linenum];
        for (int i=0; i < numel; i++) {
            res.push_back(cpp_read_float_field(*lineptr, j++));
            if (j > 5) {
                lineptr = &lines[++linenum];
                j = 0;
            }
        }
        if (j != 0) linenum++;
        return res;
    }

    """
    return cpp.indent_code(code, -4)


def parsefun_header(fun_name):
    code = cpp.indent_code(
        rf"""
    py::dict {fun_name}(std::vector<std::string> cpp_lines) {{
        std::vector<int> cpp_intvec;
        std::vector<double> cpp_floatvec;
        int cpp_linenum = 0;
        std::string *cpp_lineptr;
        py::dict cpp_parent_dict;
        py::dict cpp_current_dict;
        py::dict cpp_workdict;
        int cpp_idxnum;
        int cpp_int_val;
        double cpp_float_val;
    """,
        -4,
    )
    return code


def parsefun_footer():
    code = cpp.indent_code(
        """
        cpp_read_send(cpp_lines, cpp_linenum);
        return cpp_current_dict;
    }
    """,
        -4,
    )
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
