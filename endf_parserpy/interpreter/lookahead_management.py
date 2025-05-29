############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/05/25
# Last modified:   2025/05/29
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import (
    MutableMapping,
    MutableSequence,
    MutableSet,
)
from .logging_utils import write_info
from endf_parserpy.utils.tree_utils import (
    reconstruct_tree_str,
)
from .endf_mapping_utils import (
    get_child,
    eval_expr_without_unknown_var,
)
from .custom_exceptions import UnexpectedControlRecordError


def in_lookahead(loop_vars):
    return "__lookahead" in loop_vars


def should_proceed(datadic, loop_vars, action_type):
    if "__lookahead" in loop_vars:
        if loop_vars["__lookahead"] == 0:
            return False
        elif action_type == "endf_action":
            loop_vars["__lookahead"] -= 1
    return True


def perform_lookahead(
    tree,
    tree_handler,
    datadic,
    loop_vars,
    parse_opts,
    set_parser_state,
    get_parser_state,
    logger=None,
):
    if_head = get_child(tree, "if_head")
    if_body = get_child(tree, "if_body")
    orig_parser_state = get_parser_state()
    write_info(logger, "Start lookahead for if head " + reconstruct_tree_str(if_head))
    lookahead_option = get_child(tree, "lookahead_option", nofail=True)
    lookahead_expr = get_child(lookahead_option, "expr")
    lookahead = eval_expr_without_unknown_var(
        lookahead_expr, datadic, loop_vars, parse_opts
    )
    if int(lookahead) != lookahead:
        raise ValueError(
            "lookahead argument must evaluate to an integer" + f"(got {lookahead})"
        )
    lookahead = int(lookahead)

    if "__lookahead" in loop_vars:
        raise ValueError(
            "Nested if statements with several " + "lookahead options are not allowed"
        )

    # any change of the parser state will be isolated
    # from the original parser state via the LookaheadObject class
    new_state = {
        k: LookaheadObject.wrap_mutable(v) for k, v in orig_parser_state.items()
    }

    # less strict parsing in lookahead.
    # problems will be captured later on (if requested by user)
    # when if body will be selected and executed
    new_state["parse_opts"]["ignore_all_mismatches"] = True

    set_parser_state(new_state)
    datadic = new_state["datadic"]
    loop_vars = new_state["loop_vars"]
    loop_vars["__lookahead"] = lookahead

    try:
        tree_handler(if_body)
    except UnexpectedControlRecordError:
        pass

    del loop_vars["__lookahead"]
    return datadic, loop_vars, orig_parser_state


def undo_lookahead_changes(datadic, loop_vars, orig_parser_state, set_parser_state):
    if orig_parser_state is not None:
        set_parser_state(orig_parser_state)
        datadic = orig_parser_state["datadic"]
        loop_vars = orig_parser_state["loop_vars"]
    return datadic, loop_vars


class LookaheadObject:

    def __new__(self, orig_obj):
        if isinstance(orig_obj, MutableMapping):
            return super().__new__(LookaheadDict)
        if isinstance(orig_obj, MutableSequence):
            return super().__new__(LookaheadList)
        if isinstance(orig_obj, MutableSet):
            return super().__new__(LookaheadSet)

    def __init__(self, orig_obj):
        raise NotImplementedError("This constructor will never be called")

    @staticmethod
    def is_mutable_type(obj):
        mutable_types = (MutableMapping, MutableSequence, MutableSet)
        return isinstance(obj, mutable_types)

    @staticmethod
    def wrap_mutable(obj):
        if LookaheadObject.is_mutable_type(obj) and not isinstance(
            obj, LookaheadObject
        ):
            return LookaheadObject(obj)
        return obj


class LookaheadDict(MutableMapping, LookaheadObject):

    def __init__(self, orig_dict):
        self._orig_dict = orig_dict
        self._update_dict = {}

    def __getitem__(self, key):
        if key in self._update_dict:
            return self._update_dict[key]
        value = self._orig_dict[key]
        value = LookaheadObject.wrap_mutable(value)
        if isinstance(value, LookaheadObject):
            self._update_dict[key] = value
        return value

    def __setitem__(self, key, value):
        value = LookaheadObject.wrap_mutable(value)
        self._update_dict[key] = value

    def __delitem__(self, key):
        if key in self._orig_dict:
            raise NotImplementedError(
                "Not possible to delete elements from LookaheadDict "
                "if they have already existed in the original dict."
            )
        del self._update_dict[key]

    def __iter__(self):
        visited = set()
        for key in self._update_dict:
            visited.add(key)
            yield key
        for key in self._orig_dict:
            if key not in visited:
                yield key

    def __len__(self):
        common_keys = set(k in self._orig_dict for k in self._update_dict)
        return len(self._orig_dict) - len(common_keys)


class LookaheadList(MutableSequence, LookaheadObject):

    def __init__(self, orig_list):
        self._orig_list = orig_list
        self._list_updates = {}

    def __getitem__(self, index):
        if index in self._list_updates:
            return self._list_updates[index]
        value = self._orig_list[index]
        value = LookaheadObject.wrap_mutable(value)
        if isinstance(value, LookaheadObject):
            self._list_updates[index] = value
        return value

    def __setitem__(self, index, value):
        value = LookaheadObject.wrap_mutable(value)
        self._list_updates[index] = value

    def __delitem__(self, index):
        raise NotImplementedError(
            "Not possible to delete elements from a LookaheadList"
        )

    def __len__(self):
        orig_len = len(self._orig_list)
        add_len = sum(k >= orig_len for k in self._list_updates)
        return orig_len + add_len

    def insert(self, index, value):
        if index != len(self):
            raise NotImplementedError(
                "Insertion only allowed at end in a LookaheadList"
            )
        value = LookaheadObject.wrap_mutable(value)
        self._list_updates[index] = value


class LookaheadSet(MutableSet, LookaheadObject):

    def __init__(self, orig_set):
        self._orig_set = orig_set
        self._update_set = set()

    def __contains__(self, value):
        if value in self._update_set:
            return True
        return value in self._orig_set

    def __iter__(self):
        visited = set()
        for value in self._update_set:
            visited.add(value)
            yield value
        for value in self._orig_set:
            if value not in visited:
                yield value

    def __len__(self):
        return len(self._orig_set) + len(self._update_set)

    def add(self, value):
        if LookaheadObject.is_mutable_type(value):
            raise NotImplementedError(
                "Adding mutable types to LookaheadSet not implemented"
            )
        if value not in self._orig_set:
            self._update_set.add(value)

    def discard(self, value):
        if value in self._orig_set:
            raise NotImplementedError(
                "Not possible to delete elements from LookaheadSet "
                "if they have already existed in the original dict."
            )
        return self._update_set.discard(value)
