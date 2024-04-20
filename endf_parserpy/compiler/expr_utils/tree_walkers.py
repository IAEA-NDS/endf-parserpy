############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/04/20
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree


def _transform_nodes(node, func, inplace, *args, **kwargs):
    if isinstance(node, Tree):
        if not inplace:
            node = node.copy()
        tc = [
            _transform_nodes(v, func, inplace, *args, **kwargs) for v in node.children
        ]
        node.children = [v for v in tc if v is not None]
    return func(node, *args, **kwargs)


def transform_nodes(node, func, *args, **kwargs):
    return _transform_nodes(node, func, False, *args, **kwargs)


def transform_nodes_inplace(node, func, *args, **kwargs):
    return _transform_nodes(node, func, True, *args, **kwargs)
