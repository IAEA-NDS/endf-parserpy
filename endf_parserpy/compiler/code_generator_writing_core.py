############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/15
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2024-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from endf_parserpy.recipe_parser.tree import Tree
from endf_parserpy.recipe_parser.tree import Token
from endf_parserpy.utils.tree_utils import get_child, get_name
from .expr_utils.equation_utils import get_variables_in_expr
from .expr_utils.custom_nodes import VariableToken
from .expr_utils.tree_walkers import transform_nodes
from .expr_utils.node_trafos import node2cppstr, CppFloatValue
from .expr_utils.conversion import convert_to_exprtree
from .node_checks import (
    is_extvar,
    is_loop,
    is_section,
    is_list,
    is_abbreviation,
)
from .lookahead_management import in_lookahead
from . import endf2cpp_aux as aux
from .endf2cpp_aux_writing import write_section_verbatim
from .cpp_types import cpp_varaux
from .cpp_types.cpp_varops_query import get_idxstr
from .cpp_types.cpp_dtype_aux import map_dtype
from .cpp_types.cpp_varaux import get_cpp_varname
from . import cpp_primitives as cpp
from .variable_management import (
    expand_abbreviation,
    get_var_types,
)


def _own_dtype(node, vardict, dtype):
    # In arithmetic, a variable enters with its own type (as when
    # reading), e.g. an integer variable in an expression for a float
    # field remains an integer, so that the arithmetic is exact.
    vartypes = get_var_types(node, vardict)
    if vartypes is None:
        return dtype
    dtypes = set(v[0] for v in vartypes)
    if dtypes == {int} or dtypes == {float}:
        return dtypes.pop()
    return dtype


def _count_name(node, name, abbrevs, depth=0):
    # occurrences of a variable name in node (with any number of indices),
    # also in the indices of variables and in the expressions of the
    # abbreviations used in node
    if isinstance(node, Token):
        count = 0
        if node.type in ("VARNAME", "VARIABLE"):
            count += 1 if str(node) == name else 0
            if str(node) in abbrevs and depth < 20:
                count += _count_name(abbrevs[str(node)], name, abbrevs, depth + 1)
        for idx in getattr(node, "indices", ()):
            count += _count_name(idx, name, abbrevs, depth)
        return count
    return sum(_count_name(c, name, abbrevs, depth) for c in node.children)


def _abbreviations(node, abbrevs):
    # the abbreviations defined in node added to abbrevs (by name)
    if isinstance(node, Token):
        return
    if is_abbreviation(node):
        abbrevs[str(get_child(node, "VARNAME"))] = get_child(node, "expr")
    for c in node.children:
        _abbreviations(c, abbrevs)


def _contains_lookahead(node):
    if isinstance(node, Token):
        return False
    if node.data == "lookahead_option":
        return True
    return any(_contains_lookahead(c) for c in node.children)


def _hoisting_loop(vartok, site, vardict):
    # The outermost loop around the field `site` (in the same scope) in
    # which the variable occurs only in this field (as any variable with
    # this name, in any expression, condition, loop bound, index or
    # abbreviation), or None. The loop must not contain a lookahead, whose
    # records are generated twice.
    name = str(vartok)
    abbrevs = {str(k): v for k, v in vardict.get("__abbrevs", {}).items()}
    loop = None
    curnode = site
    while getattr(curnode, "parent", None) is not None:
        parent = curnode.parent
        # sections and the bodies of named LIST records have their own
        # IndexShifterStore
        if is_section(parent):
            break
        if is_list(parent) and get_name(curnode) == "list_body":
            if get_child(parent, "list_name", nofail=True) is not None:
                break
        if is_loop(parent):
            if _contains_lookahead(parent):
                break
            _abbreviations(parent, abbrevs)
            if _count_name(parent, name, abbrevs) != 1:
                break
            loop = parent
        curnode = parent
    return loop


def _accessor_registry(vardict):
    # accessors of a generated function by loop and variable name, shared
    # by all scopes of the function (stored with its basic operations)
    curdict = vardict
    while "__basic_ops" not in curdict:
        if "__up" not in curdict:
            return None
        curdict = curdict["__up"]
    return curdict["__basic_ops"].setdefault("array_accessors", {})


def get_array_accessor(vartok, site, vardict):
    """Name of a CppArrayAccessor of an array variable in a loop.

    If the value of an indexed variable in the field ``site`` of a record
    in a loop is retrieved from the dictionary, and the variable occurs
    nowhere else in the loop, an accessor of the variable is declared
    before the outermost such loop (see :func:`_hoisting_loop`), whose
    ``get`` retrieves an element with less overhead than ``get_value``
    with the same result. The accessor does nothing before its first use,
    so that a loop without iterations is not affected. ``None`` if this
    is not applicable.
    """
    if site is None or len(vartok.indices) == 0 or in_lookahead(vardict):
        return None
    registry = _accessor_registry(vardict)
    if registry is None:
        return None
    loop = _hoisting_loop(vartok, site, vardict)
    if loop is None:
        return None
    key = (id(loop), str(vartok))
    if key not in registry:
        accname = f"cpp_wacc_{len(registry) + 1}"
        registry[key] = accname
        loop.append_precode(
            cpp.statement(
                f"CppArrayAccessor<{len(vartok.indices)}> {accname}"
                + f'(cpp_index_shifter_store, "{vartok}")'
            )
        )
    return registry[key]


def get_node_value_using_endf_dict(
    node,
    index_shifter_store,
    dtype,
    vardict,
    defaults=None,
    idx=None,
    in_arithmetic=False,
    site=None,
):
    defaults = {} if defaults is None else defaults
    if not isinstance(node, VariableToken):
        return node2cppstr(node)
    if in_arithmetic and dtype in (int, float):
        dtype = _own_dtype(node, vardict, dtype)

    # if variable is of loopvartype, we do not read it
    # from the Python dictionary but directly from the cpp variable
    vartypes = get_var_types(node, vardict)
    if vartypes is not None and any(v[0] == "loopvartype" for v in vartypes):
        assert len(vartypes) == 1
        return get_cpp_varname(node, vardict, dtype=vartypes[0][0])

    varname = str(node)
    idxstrs = []
    for i, idxtok in enumerate(node.indices):
        curidxstr = get_idxstr(node, i, vardict)
        idxstrs.append(curidxstr)

    if dtype in (int, float) and dtype not in defaults and idx is None:
        accname = get_array_accessor(node, site, vardict)
        if accname is not None:
            idcs = ", ".join(idxstrs)
            valcode = f"{accname}.get<{map_dtype(dtype)}>({{{idcs}}})"
            return CppFloatValue(valcode) if dtype == float else valcode

    idcsarg = "std::vector<int>({" + ", ".join(idxstrs) + "})"
    defval = "py::none()" if dtype not in defaults else f"py::cast({defaults[dtype]})"
    retobj = f'{index_shifter_store}.get_value("{varname}", {idcsarg}, {defval})'

    # if the accessed object is a container
    # the idx specification allows to get a specific
    # element of this container rather than the entire container.
    if idx is not None:
        retobj += f"[py::cast({idx})]"
    if dtype is None:
        return retobj
    else:
        dtypestr = map_dtype(dtype)
        if dtype in ("intvec", "floatvec"):
            # tables of TAB1/TAB2 records, fast path for numpy arrays
            valcode = f"cpp_cast_vector<{dtypestr}>({retobj})"
        elif dtype == str:
            # text: each character becomes the byte with the same code
            valcode = f'cpp_text_from_pyobj({retobj}, "{varname}")'
        else:
            valcode = f"py::cast<{dtypestr}>({retobj})"
        # values of float fields enter arithmetic as doubles, see `cpp_operand`
        return CppFloatValue(valcode) if dtype == float else valcode


def get_expr_value_using_endf_dict(
    node, index_shifter_store, dtype, vardict, defaults=None, idx=None, site=None
):
    node = convert_to_exprtree(node)
    node = transform_nodes(node, expand_abbreviation, vardict)
    valcode = transform_nodes(
        node,
        get_node_value_using_endf_dict,
        index_shifter_store,
        dtype,
        vardict,
        defaults,
        idx=idx,
        in_arithmetic=contains_arithmetic(node),
        site=site,
    )
    return valcode


def contains_arithmetic(node):
    """Whether the (converted) expression tree contains an operation."""
    return isinstance(node, Tree)


def get_mat_from_mfmt_section(mfmt_dict):
    code = f"get_mat_from_mfmt_section({mfmt_dict}, mf, mt)"
    return code


def generate_section_writing_code(funname, write_opts):
    code = cpp.ifelse(
        f"py::isinstance<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)])",
        cpp.concat(
            [
                # inject MF and MT number into Pyton dictionary if missing
                cpp.pureif(
                    cpp.logical_not('mt_dict.contains("MF")'),
                    cpp.statement('mt_dict["MF"] = mf'),
                ),
                cpp.pureif(
                    cpp.logical_not('mt_dict.contains("MT")'),
                    cpp.statement('mt_dict["MT"] = mt'),
                ),
                # call the mf/mt section specific write function
                cpp.statement(
                    f"{funname}_ostream(cont, py::cast<py::dict>(endf_dict[py::cast(mf)][py::cast(mt)]), {write_opts})"
                ),
            ]
        ),
        write_section_verbatim(
            "cont",
            "py::cast<py::list>(endf_dict[py::cast(mf)][py::cast(mt)])",
            "write_opts",
        ),
    )
    return code
