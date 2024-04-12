############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/12
# Last modified:   2024/04/12
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


def fillout_template(template, params=None, idx=None):
    if params is None:
        return template
    if idx is not None:
        params = {
            k: v[idx] for k, v in params.items() if idx in v and v[idx] is not None
        }
        res = template.format(**params)
    return res


def indent_code(code, indent):
    if indent >= 0:
        code_lines = [" " * indent + s for s in code.split("\n")]
    else:
        code_lines = [s[(-indent):] for s in code.split("\n")]
    code_lines = [s if s.strip() != "" else s.strip() for s in code_lines]
    return "\n".join(code_lines)


def line(code, indent=0):
    return " " * indent + code.strip().rstrip("\n") + "\n"


def statement(code, indent=0):
    return " " * indent + code.strip().rstrip(";\n") + ";\n"


def comment(text, indent=0):
    return " " * indent + "// " + text + "\n"


def open_block(indent=0):
    return " " * indent + "{\n"


def close_block(indent=0):
    return " " * indent + "}\n"


def block(code, indent=4, escape=False):
    obr = "{\n" if not escape else "{{\n"
    cbr = "}\n" if not escape else "}}\n"
    return obr + indent_code(code, indent) + cbr


def block_repeat(code, num, extra_params=None, indent=0):
    if num <= 0:
        return ""
    if isinstance(code, str):
        code = [code] * num
    code = [*code]
    if extra_params is not None:
        for i in range(num):
            code[i] = fillout_template(code[i], extra_params, idx=i)
    return concat(code)


def nested_block_repeat(code, num, extra_params=None, indent=4):
    if num <= 0:
        return ""
    if isinstance(code, str):
        code = [code] * num
    code = [*code]
    if extra_params is not None:
        for i in range(num):
            code[i] = fillout_template(code[i], extra_params, idx=i)
    result_code = block(code[num - 1], indent)
    for i in range(num - 2, -1, -1):
        result_code = block(concat([code[i], result_code]))
    return result_code


def logical_not(logical_expression):
    if logical_expression.strip("() ") == "true":
        return ""
    return "(! " + logical_expression + ")"


def logical_or(logical_expressions):
    return "(" + " || ".join(logical_expressions) + ")"


def logical_and(logical_expressions):
    return "(" + " && ".join(logical_expressions) + ")"


def throw_runtime_error(message):
    return f"""throw std::runtime_error("{message}");\n"""


def concat(codes):
    return "".join(codes)


def conditional_branches(conditions, codes, default=None, escape=False):
    obr = "{" if not escape else "{{"
    cbr = "}" if not escape else "}}"
    if_cond = conditions[0]
    code = f"if ({if_cond}) {obr}\n"
    code += indent_code(codes[0], 4)
    for elif_cond, elif_body in zip(conditions[1:], codes[1:]):
        code += f"\n{cbr} else if ({elif_cond}) {obr}\n"
        code += indent_code(elif_body, 4)
    if default is not None:
        code += f"\n{cbr} else {obr}\n"
        code += indent_code(default, 4)
    code += f"{cbr}\n"
    return code


def ifelse(condition, code, other_code):
    return conditional_branches([condition], [code], default=other_code)


def pureif(condition, code, escape=False):
    if condition.strip("() ") == "":
        return ""
    return conditional_branches([condition], [code], escape=escape)
