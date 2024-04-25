############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/25
# Last modified:   2024/04/25
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from .cpp_type_scalar import CppTypeScalar
from .cpp_type_nested_vector import CppTypeNestedVector
from .cpp_type_matrix2d import CppTypeMatrix2d

VARTYPE_INFO = {
    "Matrix2d": CppTypeMatrix2d,
    "NestedVector": CppTypeNestedVector,
    "Scalar": CppTypeScalar,
}


def get_vartype_names():
    return tuple(VARTYPE_INFO.keys())


def get_vartype_definition(vartype_name):
    return VARTYPE_INFO[vartype_name].definition


def get_query_module(vartype_name):
    return VARTYPE_INFO[vartype_name].query


def get_assign_module(vartype_name):
    return VARTYPE_INFO[vartype_name].assign


def get_vartype_module(vartype_name):
    return VARTYPE_INFO[vartype_name]


# tuples convenient for loops


def get_vartype_definitions():
    return tuple(get_vartype_definition(vn) for vn in get_vartype_names())


def get_query_modules():
    return tuple(get_query_module(vn) for vn in get_vartype_names())


def get_assign_modules():
    return tuple(get_assign_module(vn) for vn in get_vartype_names())


def get_vartype_modules():
    return tuple(get_vartype_module(vn) for vn in get_vartype_names())
