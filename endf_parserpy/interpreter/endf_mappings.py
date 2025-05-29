############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/05/29
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.lexer import Token
from endf_parserpy.utils.tree_utils import is_tree, get_name, get_child, get_child_value
from .logging_utils import write_info
from .meta_control_utils import cycle_for_loop
from .lookahead_management import should_proceed, in_lookahead
from .meta_control_utils import open_section, close_section
from .custom_exceptions import (
    VariableNotFoundError,
    UnexpectedControlRecordError,
    MoreListElementsExpectedError,
    UnconsumedListElementsError,
)
from .endf_mapping_core import map_record_helper, map_text_record_helper
from endf_parserpy.utils.accessories import EndfPath


def check_ctrl_spec(record_line_node, record_dic, datadic, rwmode):
    ctrl_spec = get_child(record_line_node, "ctrl_spec")
    dic = record_dic if rwmode == "read" else datadic
    # if MAT not found in local scope, scan the outer ones
    while "MAT" not in dic and "__up" in dic:
        dic = dic["__up"]
    for v in ("MAT", "MF", "MT"):
        if v not in dic:
            raise VariableNotFoundError(f"Variable {v} missing in dictionary.", v)
    cur_mat = dic["MAT"]
    cur_mf = dic["MF"]
    cur_mt = dic["MT"]
    exp_mat = get_child_value(ctrl_spec, "MAT_SPEC")
    exp_mf = get_child_value(ctrl_spec, "MF_SPEC")
    exp_mt = get_child_value(ctrl_spec, "MT_SPEC")
    if exp_mat != "MAT" and int(exp_mat) != cur_mat:
        raise UnexpectedControlRecordError(
            f"Expected MAT {exp_mat} but encountered {cur_mat}"
        )
    if exp_mf != "MF" and int(exp_mf) != cur_mf:
        raise UnexpectedControlRecordError(
            f"Expected MF {exp_mf} but encountered {cur_mf}"
        )
    if exp_mt != "MT" and int(exp_mt) != cur_mt:
        raise UnexpectedControlRecordError(
            f"Expected MT {exp_mt} but encountered {cur_mt}"
        )


def map_text_dic(
    text_line_node,
    text_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    logger=None,
):
    text_dic = {} if text_dic is None else text_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(text_line_node, text_dic, datadic, rwmode)
    textfields = get_child(text_line_node, "text_fields").children
    expr_list = []
    for textfield in textfields:
        if get_name(textfield) == "textplaceholder":
            expr_list.append(textfield)
    cn = ("HL",)
    return map_text_record_helper(
        expr_list, cn, text_dic, datadic, loop_vars, rwmode, parse_opts
    )


def map_head_dic(
    head_line_node,
    head_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    logger=None,
):
    head_dic = {} if head_dic is None else head_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(head_line_node, head_dic, datadic, rwmode)
    expr_list = get_child(head_line_node, "record_fields").children
    cn = ("C1", "C2", "L1", "L2", "N1", "N2")
    return map_record_helper(
        expr_list, cn, head_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )


def map_cont_dic(
    cont_line_node,
    cont_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    logger=None,
):
    cont_dic = {} if cont_dic is None else cont_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(cont_line_node, cont_dic, datadic, rwmode)
    expr_list = get_child(cont_line_node, "record_fields").children
    cn = ("C1", "C2", "L1", "L2", "N1", "N2")
    return map_record_helper(
        expr_list, cn, cont_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )


def map_dir_dic(
    dir_line_node,
    dir_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    logger=None,
):
    dir_dic = {} if dir_dic is None else dir_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(dir_line_node, dir_dic, datadic, rwmode)
    expr_list = get_child(dir_line_node, "dir_fields").children
    cn = ("L1", "L2", "N1", "N2")
    return map_record_helper(
        expr_list, cn, dir_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )


def map_intg_dic(
    intg_line_node,
    intg_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    logger=None,
):
    intg_dic = {} if intg_dic is None else intg_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(intg_line_node, intg_dic, datadic, rwmode)
    expr_list = get_child(intg_line_node, "intg_fields").children
    cn = ("II", "JJ", "KIJ")
    return map_record_helper(
        expr_list, cn, intg_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )


def map_tab2_dic(
    tab2_line_node,
    tab2_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    path="",
    logger=None,
):
    tab2_dic = {} if tab2_dic is None else tab2_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(tab2_line_node, tab2_dic, datadic, rwmode)
    tab2_fields = get_child(tab2_line_node, "tab2_fields")
    tab2_cont_fields = get_child(tab2_fields, "record_fields")
    # we remove NR because we can infer it from the length of the NBT array
    # we keep NZ because it contains the number of following TAB1/LIST records
    # NOTE: -(2+1) because a comma separates NR and NZ
    expr_list = tab2_cont_fields.children[:-3] + tab2_cont_fields.children[-1:]
    cn = ("C1", "C2", "L1", "L2", "N2")
    main_ret = map_record_helper(
        expr_list, cn, tab2_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )
    # treat parsing of table body as additional action step,
    # so don't parse list body if lookahead counter exhausted
    if not should_proceed(datadic, loop_vars, "endf_action"):
        return main_ret
    # tab2_def_fields contains the name of the Z variable
    # we don't need it because the following TAB1/LIST records
    # contain the name of this variable at position of C2
    tab2_def_fields = get_child(tab2_fields, "tab2_def").children
    tab2_name_node = get_child(tab2_line_node, "table_name", nofail=True)
    # open section if desired
    if tab2_name_node is not None:
        create_missing = rwmode == "read"
        path = EndfPath(path)
        datadic, path = open_section(
            tab2_name_node,
            datadic,
            loop_vars,
            parse_opts,
            create_missing,
            path=path,
            logger=logger,
        )
    # deal with the mapping of the variable names in the table first
    cn = ("NBT", "INT")
    tab2_def_fields = get_child(tab2_fields, "tab2_def").children
    expr_list = [Token("VARNAME", "NBT"), Token("VARNAME", "INT")]
    tbl_dic = {} if rwmode != "read" else tab2_dic["table"]
    try:
        tbl_ret = map_record_helper(
            expr_list, cn, tbl_dic, datadic, loop_vars, rwmode, parse_opts, logger
        )
    except VariableNotFoundError as exc:
        exc.varname = str(path + exc.varname)
        raise exc
    # close section if desired
    if tab2_name_node is not None:
        datadic = close_section(tab2_name_node, datadic, logger=logger)
    if rwmode != "read":
        main_ret["table"] = tbl_ret
    return main_ret


def map_tab1_dic(
    tab1_line_node,
    tab1_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    path="",
    logger=None,
):
    tab1_dic = {} if tab1_dic is None else tab1_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    check_ctrl_spec(tab1_line_node, tab1_dic, datadic, rwmode)
    tab1_fields = get_child(tab1_line_node, "tab1_fields")
    tab1_cont_fields = get_child(tab1_fields, "record_fields")
    tab1_def_fields = get_child(tab1_fields, "tab1_def").children
    tab1_name_node = get_child(tab1_line_node, "table_name", nofail=True)
    # we remove NR and NP (last two elements) because redundant information
    # and not used by write_tab1 and read_tab1 (2+1 because a comma separates NR and NP)
    expr_list = tab1_cont_fields.children[:-3]
    cn = ("C1", "C2", "L1", "L2")
    main_ret = map_record_helper(
        expr_list, cn, tab1_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )
    # treat parsing of table body as additional action step,
    # so don't parse list body if lookahead counter exhausted
    if not should_proceed(datadic, loop_vars, "endf_action"):
        return main_ret
    # open section if desired
    if tab1_name_node is not None:
        create_missing = rwmode == "read"
        path = EndfPath(path)
        datadic, path = open_section(
            tab1_name_node,
            datadic,
            loop_vars,
            parse_opts,
            create_missing,
            path=path,
            logger=logger,
        )
    # deal with the mapping of the variable names in the table first
    cn = ("NBT", "INT", "X", "Y")
    tab1_def_fields = get_child(tab1_fields, "tab1_def").children
    # remove the slash
    tab1_def_fields = [field for field in tab1_def_fields if get_name(field) != "SLASH"]
    expr_list = [Token("VARNAME", "NBT"), Token("VARNAME", "INT")] + list(
        tab1_def_fields
    )
    tbl_dic = {} if rwmode != "read" else tab1_dic["table"]
    try:
        tbl_ret = map_record_helper(
            expr_list, cn, tbl_dic, datadic, loop_vars, rwmode, parse_opts, logger
        )
    except VariableNotFoundError as exc:
        exc.varname = str(path + exc.varname)
        raise exc
    # close section if desired
    if tab1_name_node is not None:
        datadic = close_section(tab1_name_node, datadic, logger=logger)
    if rwmode != "read":
        main_ret["table"] = tbl_ret
    return main_ret


def map_list_dic(
    list_line_node,
    list_dic=None,
    datadic=None,
    loop_vars=None,
    rwmode="read",
    parse_opts=None,
    run_instruction=None,
    path="",
    logger=None,
):
    list_dic = {} if list_dic is None else list_dic
    datadic = {} if datadic is None else datadic
    loop_vars = {} if loop_vars is None else loop_vars
    val_idx = 0

    # we embed recurisve helper function here so that
    # it can see the variables list_dic, datadic and loop_vars.
    # helper function for map_list_dic to recursively parse the list_body
    def parse_list_body_node(node):
        nonlocal val_idx
        nonlocal list_dic
        node_type = get_name(node)

        list_dic.setdefault("vals", [])
        if node_type == "expr":
            if rwmode == "read":
                vals = list_dic["vals"]
                numvals = len(vals)
                if val_idx >= numvals:
                    raise MoreListElementsExpectedError(
                        f"All {numvals} values in the list body present in the ENDF file "
                        + "have already been consumed. "
                        + "You may check the index specifications of your list body. "
                    )
                # maybe a bit hacky and clunky, but the method can do the job
                # of assigning a value of the list body to the appropriate variable in datadic
                map_record_helper(
                    [node],
                    ("val",),
                    {"val": vals[val_idx]},
                    datadic,
                    loop_vars,
                    rwmode,
                    parse_opts,
                    logger,
                )
            else:
                list_val = map_record_helper(
                    [node], ("val",), {}, datadic, loop_vars, rwmode, parse_opts, logger
                )
                list_dic["vals"].append(list_val["val"])

            val_idx += 1
            return

        # sometimes the expectation is that within a list body (list in LIST record)
        # a line must be padded with zeros until the end before a new subrecord
        # starts on the next line
        elif node_type == "LINEPADDING":
            num_skip_elems = (6 - val_idx % 6) % 6
            if rwmode == "read":
                # we do nothing here because we only need to skip some
                # elements, what we do afterwards
                pass
            else:
                list_dic["vals"].extend([0.0] * num_skip_elems)
            # skip over the elements
            val_idx = val_idx + num_skip_elems
            return

        elif node_type == "list_loop":
            cycle_for_loop(
                node,
                parse_list_body_node,
                datadic,
                loop_vars,
                parse_opts,
                loop_name="list_loop",
                head_name="list_for_head",
                body_name="list_body",
                logger=logger,
            )

        elif is_tree(node) and node_type == "list_body":
            for child in node.children:
                parse_list_body_node(child)

        # we are fine with a new line and a comma
        elif node_type in ("NEWLINE", "COMMA"):
            return
        else:
            raise ValueError(
                f"A node of type {node_type} must not appear in a list_body"
            )

    check_ctrl_spec(list_line_node, list_dic, datadic, rwmode)
    expr_list = get_child(list_line_node, "record_fields").children
    cn = ("C1", "C2", "L1", "L2", "N1", "N2", "vals")
    map_record_helper(
        expr_list, cn, list_dic, datadic, loop_vars, rwmode, parse_opts, logger
    )

    # treat parsing of list_body as additional action step,
    # so don't parse list body if lookahead counter exhausted
    if not should_proceed(datadic, loop_vars, "endf_action"):
        if rwmode != "read":
            return list_dic
        else:
            return datadic

    write_info(logger, f"Entering list body (lookahead={in_lookahead(loop_vars)})")

    # enter subsection if demanded
    list_name_node = get_child(list_line_node, "list_name", nofail=True)
    if list_name_node is not None:
        create_missing = rwmode == "read"
        path = EndfPath(path)
        datadic, path = open_section(
            list_name_node,
            datadic,
            loop_vars,
            parse_opts,
            create_missing,
            path=path,
            logger=logger,
        )
    # parse the list body
    list_body_node = get_child(list_line_node, "list_body")
    try:
        parse_list_body_node(list_body_node)
    except VariableNotFoundError as exc:
        exc.varname = str(path + exc.varname)
        raise exc
    # close subsection if opened
    if list_name_node is not None:
        datadic = close_section(list_name_node, datadic, logger=logger)

    numels_in_list = len(list_dic["vals"])
    if val_idx < numels_in_list:
        raise UnconsumedListElementsError(
            f"Not all values in the list_body were consumed and "
            "associated with variables in datadic "
            f"(read {val_idx} out of {numels_in_list})"
        )
    if rwmode != "read":
        return list_dic
    else:
        return datadic
