############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/03/28
# Last modified:   2024/03/28
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################

from lark.tree import Tree


def transform_nodes(node, func, *args, **kwargs):
    if isinstance(node, Tree):
        node = node.copy()
        tc = [transform_nodes(v, func, *args, **kwargs) for v in node.children]
        node.children = [v for v in tc if v is not None]
    return func(node, *args, **kwargs)
