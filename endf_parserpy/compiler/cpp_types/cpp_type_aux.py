############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/01
# Last modified:   2024/05/01
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


def map_dtype(dtype):
    if dtype == float:
        dtype = "double"
    elif dtype == int:
        dtype = "int"
    elif dtype == str:
        dtype = "std::string"
    elif dtype == "loopvartype":
        dtype = "int"
    elif dtype == "intvec":
        dtype = "std::vector<int>"
    elif dtype == "floatvec":
        dtype = "std::vector<double>"
    else:
        raise TypeError(f"unknown dtype {dtype}")
    return dtype


def get_dtype_str(dtype):
    if dtype == float:
        return "double"
    elif dtype == int:
        return "int"
    elif dtype == str:
        return "string"
    elif dtype == "loopvartype":
        return "int"
    elif dtype == "intvec":
        return "intvec"
    elif dtype == "floatvec":
        return "floatvec"
    raise TypeError(f"unknown dtype {dtype}")


def get_dtype_idx(dtype):
    if dtype == float:
        return 0
    elif dtype == int:
        return 1
    elif dtype == str:
        return 2
    elif dtype == "loopvartype":
        return 3
    elif dtype == "intvec":
        return 4
    elif dtype == "floatvec":
        return 5
    raise TypeError(f"unknown dtype {dtype}")
