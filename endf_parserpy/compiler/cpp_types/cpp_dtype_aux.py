############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/01
# Last modified:   2024/10/21
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


_DTYPE_INFO = {
    # tuple organization: string representation, cpp type, dtype index
    float: ("double", "EndfFloatCpp", 0),
    int: ("int", "int", 1),
    str: ("string", "std::string", 2),
    "loopvartype": ("int", "int", 3),
    "intvec": ("intvec", "std::vector<int>", 4),
    "floatvec": ("floatvec", "std::vector<EndfFloatCpp>", 5),
}


def get_dtype_str(dtype):
    return _DTYPE_INFO[dtype][0]


def map_dtype(dtype):
    return _DTYPE_INFO[dtype][1]


def get_dtype_idx(dtype):
    return _DTYPE_INFO[dtype][2]


def get_available_dtypes():
    return tuple(_DTYPE_INFO)
