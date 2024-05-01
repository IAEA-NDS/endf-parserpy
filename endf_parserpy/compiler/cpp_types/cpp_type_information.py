############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/25
# Last modified:   2024/05/01
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

import importlib


_THIS_PCKG = "endf_parserpy.compiler.cpp_types"


# to avoid nasty circular imports issues, this class
# only loads a module when the class defined
# therein is currently needed
class LazyModuleClass:

    def __init__(self, module_name, class_name):
        self.module_name = module_name
        self.module = None
        self.class_name = class_name

    def __call__(self):
        if self.module is None:
            self.module = importlib.import_module(self.module_name)
        return getattr(self.module, self.class_name)


VARTYPE_INFO = {
    "Matrix2d": LazyModuleClass(f"{_THIS_PCKG}.cpp_type_matrix2d", "CppTypeMatrix2d"),
    "NestedVector": LazyModuleClass(
        f"{_THIS_PCKG}.cpp_type_nested_vector", "CppTypeNestedVector"
    ),
    "Scalar": LazyModuleClass(f"{_THIS_PCKG}.cpp_type_scalar", "CppTypeScalar"),
}


def get_vartype_names():
    return tuple(VARTYPE_INFO.keys())


def get_vartype_definition(vartype_name):
    return VARTYPE_INFO[vartype_name]().definition


def get_query_module(vartype_name):
    return VARTYPE_INFO[vartype_name]().query


def get_assign_module(vartype_name):
    return VARTYPE_INFO[vartype_name]().assign


def get_vartype_module(vartype_name):
    return VARTYPE_INFO[vartype_name]()


# tuples convenient for loops


def get_vartype_definitions():
    return tuple(get_vartype_definition(vn) for vn in get_vartype_names())


def get_query_modules():
    return tuple(get_query_module(vn) for vn in get_vartype_names())


def get_assign_modules():
    return tuple(get_assign_module(vn) for vn in get_vartype_names())


def get_vartype_modules():
    return tuple(get_vartype_module(vn) for vn in get_vartype_names())
