### Pure C++ parser development playground


## Install

In the shell, change to the directory `pure_cpp_playground`,
create a virtual environment
```console
python -m venv venv
```

Activate the environment if on Linux or MacOS like so:
```console
source venv/bin/activate  # for Linux or MacOS
```
or, if on Windows:
```console
venv/Scripts/activate.bat
```

Install into the environment the only two
dependencies of the endf-parserpy package:
```console
pip install -r requirements.txt
```

The venv can be deactivated by
```console
deactivate
```

## Iterative development

Make sure that the venv is activated.

To create the C++ parsing code, run
```console
python create_code.py
```

This will create the file `parser.cpp` which will
still contain Python dependencies. The most obvious
ones are the reliance on `py::dict` and `py::list`
which are used to create a nested data structure
capturing the hierarchical data stored in the ENDF file.

The objective for this development is to change the
Python source code in
[endf_parserpy/compiler](https://github.com/IAEA-NDS/endf-parserpy/tree/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler)
so that it does not make use of `py::dict` and `py::list` anymore.

If only the capability for parsing ENDF files is desired (assuming for the time being
this to be true), the starting point to investigate the C++ code generation are the files

- [code_generator_core.py](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_core.py)
- [code_generator_parsing.py](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_parsing.py)
- [code_generator_parsing_core.py](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_parsing_core.py)

### Overview of Pyton functions for C++ code generation

In particular, there is the function
[_finalize_section_func_wrapper](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_parsing.py#L154)
which calls the function [generate_endf_dict_assignments](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_parsing_core.py#L34)
for creating the C++ code that constructs the Python dictionary using `py::dict` data types.
This function calls the function [cpp_varops_assign.store_var_in_endf_dict2](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_varops_assign.py#L79)
which dispatches to responsibility to create this assingment code a specific Python class depending on the datatype of the
variable read from the ENDF file (e.g. scalar, array, matrix). The assignment code for these classes is stored in
`cpp_type_scalar`, `cpp_type_nested_vector`, and `cpp_type_matrix2d`. For instance, consider the following
routine for [cpp_type_matrix2d](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_type_matrix2d/assign.py#L226)
This routine corresponds to an underlying C++ class, and creates code that calls the
[to_pyobj() method](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_type_matrix2d/definition.py#L91) of that class.


















