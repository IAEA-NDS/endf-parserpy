from lark.tree import Tree
from lark.lexer import Token

def is_token(tree):
    return isinstance(tree, Token)

def is_tree(tree):
    return isinstance(tree, Tree)

def get_name(tree):
    if is_token(tree):
        return str(tree.type)
    if is_tree(tree):
        return str(tree.data)
    else:
        raise TypeError('argument should have type Token or Tree')

def get_value(token):
    return token.value

def get_child_names(tree):
    return (get_name(t) for t in tree.children) 

def get_child(tree, name, nofail=False):
    for child in tree.children:
        if get_name(child) == name:
            return child
    if nofail:
        return None
    else:
        raise IndexError(f'name {name} not found among child nodes')

def get_child_value(tree, name):
    for child in tree.children:
        if is_token(child):
            if get_name(child) == name:
                return child.value
    raise IndexError(f'child with name {name} not found') 

def get_child_value_by_pos(tree, pos):
    ch = tree.children
    if pos >= 0 and pos < len(ch):
        if is_token(ch[pos]):
            return str(ch[pos])
    return None

