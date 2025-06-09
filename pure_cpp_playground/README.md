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
[to_pyobj() method](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_type_matrix2d/definition.py#L91) of that class and assigns the result to correct fieldname in the `cpp_current_dict` variable (of type `py::dict`).


### Migration to a pure C++ class

So far, the responsibility of the `py::dict` (and `py::list` for TAB1 and TAB2 records) is to act as a
flexible data container to establish a potentially nested hierarchy of variables read from ENDF files.
Of central importance is the variable `cpp_current_dict` (of type py::dict), which holds the
current `py::dict` associated with the current level of nesting (in a hierarchy of nested `py::dict`s).
For parsing, this variable is initialized in [_prepare_section_func_wrapper](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/code_generator_parsing.py#L138)
which is registered as a function whenever a new section
(e.g. MT section, or subsection therein is encoutered while reading an ENDF file),
see
[here](https://github.com/IAEA-NDS/endf-parserpy/blob/9b0ca230438069ce77404483852abee5fceedd2c/endf_parserpy/compiler/code_generator_parsing.py#L180).
As a reminder, there is also a counterpart, which is the function
[_finalize_section_func_wrapper](https://github.com/IAEA-NDS/endf-parserpy/blob/9b0ca230438069ce77404483852abee5fceedd2c/endf_parserpy/compiler/code_generator_parsing.py#L154)
called whenever the end of a section or subsection is reached. At present, it is precisely at the end of a section where the C++ variables stored in classes like
[Matrix2d](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_type_matrix2d/definition.py#L15) and
[NestedVector](https://github.com/IAEA-NDS/endf-parserpy/blob/27b8e79fcdeccf6966c188a9e88f9cb5bd56a7ab/endf_parserpy/compiler/cpp_types/cpp_type_nested_vector/definition.py#L15) are copied into Python data structures. For a pure C++ code, these assignments need to be modified.

**A possible approach to eliminate the Python dependencies.**
As a starting point, a
[JsonValue](https://github.com/IAEA-NDS/endf-parserpy/blob/9b0ca230438069ce77404483852abee5fceedd2c/pure_cpp_playground/jsonvalue.cpp)
class which could potentially be used instead as data type for the `cpp_current_dict` variable (which is at present of type `py::dict`).
Once we are happy with this class, we can move it as a file to the
[cpp_templates](https://github.com/IAEA-NDS/endf-parserpy/tree/9b0ca230438069ce77404483852abee5fceedd2c/endf_parserpy/compiler/cpp_templates)
folder in a similar way as it is already done for, e.g.,
[IndexShifter](https://github.com/IAEA-NDS/endf-parserpy/blob/9b0ca230438069ce77404483852abee5fceedd2c/endf_parserpy/compiler/cpp_templates/index_shifter.hpp) class.
These classes are automatically embedded in the generated C++ code by the function
[_module_header](https://github.com/IAEA-NDS/endf-parserpy/blob/9b0ca230438069ce77404483852abee5fceedd2c/endf_parserpy/compiler/cpp_boilerplate.py#L27) responsible to include global definitions (boilerplate code).


To be continued...

### Overall approach to implementing pure C++ parser code generator

For the time being, the functionality to output the ENDF data as Python dictionaries should certainly remain available.
Nevertheless, for rapid development we may just directly replace the Python functionality in the `feature_pure_cpp` branch
until we are satisified with the result and pure C++ code generation works.
Afterwards, we can refactor the code to ensure that C++ code generation with and without Python dependencies can
live side-by-side in this package.
