############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/11
# Last modified:   2026/11/11
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""The summary of the field mismatches tolerated in a parse.

With the options ``ignore_zero_mismatch``, ``ignore_number_mismatch`` and
``ignore_varspec_mismatch``, the parsers accept a value in an ENDF-6 file
that differs from the value given by the recipe: a value other than zero
in a field given as ``0`` or ``0.0``, a value other than a desired number
(e.g. ``0.0?``), or a value of a variable marked with ``?`` (e.g.
``AWR?``) that differs from the value read before. The value found is not
stored, so that writing the data gives the expected value instead.

Both parsers collect these mismatches during a call of ``parse`` or
``parsefile`` and report them in a single
:class:`EndfToleratedMismatchWarning` at the end of the call, whose text
is produced by :func:`format_tolerated_mismatches`, so that it is the
same for both parsers.
"""

import os
import re
import sys
import warnings
from collections import namedtuple
from fractions import Fraction


class EndfToleratedMismatchWarning(UserWarning):
    """Warning about the field mismatches tolerated in a parse.

    Issued once per call of ``parse`` or ``parsefile`` of
    :class:`~endf_parserpy.EndfParserPy` and
    :class:`~endf_parserpy.EndfParserCpp` (and once per section parsed
    by :class:`~endf_parserpy.EndfFile`) if mismatches were tolerated.
    The mismatches are available as the tuple ``mismatches`` of
    :class:`ToleratedMismatch` records, and ``source`` is the name of the
    file parsed (``None`` for data parsed from a string). To turn the
    warning into an error or to silence it, use the filters of the
    :mod:`warnings` module, e.g.
    ``warnings.simplefilter("error", EndfToleratedMismatchWarning)``.
    """

    def __init__(self, message, mismatches=(), source=None):
        super().__init__(message)
        self.mismatches = tuple(mismatches)
        self.source = source

    def __reduce__(self):
        return (type(self), (str(self), self.mismatches, self.source))


ToleratedMismatch = namedtuple(
    "ToleratedMismatch",
    ("mat", "mf", "mt", "field", "variable", "kind", "line", "expected", "found"),
)
ToleratedMismatch.__doc__ = """A field mismatch tolerated in a parse.

``mat``, ``mf`` and ``mt`` are the numbers of the section; ``field`` is
the name of the field of the line (``"C1"``, ``"C2"``, ``"L1"``,
``"L2"``, ``"N1"`` or ``"N2"``) or ``"body"`` for a value in the body of
a LIST record; ``variable`` names the variables of the field (e.g.
``"AWR"``), ``None`` for a field without variables; ``kind`` is one of
``"zero"``, ``"number"`` and ``"varspec"`` (see
:data:`MISMATCH_KINDS`); ``line`` is the number (counting from 1) of the
line of the input holding the value, ``expected`` the value given by the
recipe and ``found`` the value in the input.
"""


# the kinds of tolerated mismatches and the options tolerating them
MISMATCH_KINDS = {
    "zero": "ignore_zero_mismatch",
    "number": "ignore_number_mismatch",
    "varspec": "ignore_varspec_mismatch",
}

# the names of the six fields of a line, by their position
FIELD_NAMES = ("C1", "C2", "L1", "L2", "N1", "N2")

# the field name of a value in the body of a LIST record
BODY_FIELD = "body"

# the number of groups given in the summary
MAX_GROUPS = 10

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def field_variables(exprstr):
    """The variables of the expression of a field, e.g. ``"AWR"`` for
    ``AWR?``, separated by commas in the order of their first
    appearance, or ``None`` if there are none."""
    names = []
    for name in _IDENTIFIER.findall(exprstr):
        if name not in names:
            names.append(name)
    return ",".join(names) if names else None


def plain_value(value):
    """A value of a mismatch as a Python number: an integer as ``int``,
    any other number as ``float`` (an exact fraction that is an integer
    as ``int``)."""
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, Fraction):
        return int(value) if value.denominator == 1 else float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return value


def _format_value(value):
    if isinstance(value, float):
        return repr(value)
    return str(value)


def group_tolerated_mismatches(mismatches):
    """Group mismatches by MAT, MF, MT, field, variable and kind.

    Returns a list of ``(key, count, example)`` tuples, in which ``key``
    is the tuple ``(mat, mf, mt, field, variable, kind)``, ``count`` the
    number of mismatches of the group and ``example`` the mismatch of
    the group in the first line. The groups are sorted by the line of
    their example.
    """
    groups = {}
    for m in mismatches:
        key = (m.mat, m.mf, m.mt, m.field, m.variable, m.kind)
        entry = groups.get(key)
        if entry is None:
            groups[key] = [1, m]
        else:
            entry[0] += 1
            if m.line < entry[1].line:
                entry[1] = m
    result = [(key, count, example) for key, (count, example) in groups.items()]
    result.sort(key=lambda g: (g[2].line, str(g[0])))
    return result


def _plural(count, word, plural=None):
    if count == 1:
        return f"{count} {word}"
    return f"{count} {plural if plural is not None else word + 's'}"


def format_group(key, count, example, line_label="line"):
    """One line of the summary for a group (see
    :func:`group_tolerated_mismatches`)."""
    mat, mf, mt, field, variable, kind = key
    what = field if variable is None else f"{field} ({variable})"
    return (
        f"MAT {mat} MF{mf}/MT{mt} {what}: {_plural(count, kind + ' mismatch', kind + ' mismatches')}, "
        f"e.g. {line_label} {example.line}: expected {_format_value(example.expected)}, "
        f"found {_format_value(example.found)}"
    )


def kind_totals(mismatches):
    """The numbers of mismatches by kind, as a dictionary in the order of
    :data:`MISMATCH_KINDS` with only the kinds that occur."""
    totals = {kind: 0 for kind in MISMATCH_KINDS}
    for m in mismatches:
        totals[m.kind] = totals.get(m.kind, 0) + 1
    return {kind: n for kind, n in totals.items() if n > 0}


def format_tolerated_mismatches(mismatches, source=None, max_groups=MAX_GROUPS):
    """The text of the summary of tolerated mismatches.

    ``source`` (e.g. the name of the file) is named in the first line if
    given. At most ``max_groups`` groups are listed, followed by a line
    with the number of the other groups.
    """
    totals = kind_totals(mismatches)
    by_kind = ", ".join(
        f"{kind}: {n} ({MISMATCH_KINDS[kind]})" for kind, n in totals.items()
    )
    groups = group_tolerated_mismatches(mismatches)
    where = f" in {source}" if source is not None else ""
    lines = [
        f"{_plural(len(mismatches), 'field mismatch', 'field mismatches')} tolerated{where} "
        f"({by_kind}), in {_plural(len(groups), 'group')}; the values found are not "
        "kept, writing the data gives the expected values:"
    ]
    for key, count, example in groups[:max_groups]:
        lines.append("  " + format_group(key, count, example))
    more = len(groups) - max_groups
    if more > 0:
        lines.append(f"  ... and {_plural(more, 'more group')}")
    return "\n".join(lines)


_PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + os.sep


def _stacklevel_outside_package():
    # the stacklevel of warnings.warn (called by the caller of this
    # function) that names the first frame outside of the package, i.e.
    # the code calling the package
    frame = sys._getframe(1)
    level = 1
    while frame is not None and frame.f_code.co_filename.startswith(_PACKAGE_DIR):
        frame = frame.f_back
        level += 1
    return level


def warn_tolerated_mismatches(mismatches, source=None):
    """Issue the :class:`EndfToleratedMismatchWarning` for the mismatches,
    if there are any (see :func:`format_tolerated_mismatches` for
    ``source``). The warning is attributed to the code outside of the
    package that called it, so that the default filter of the
    :mod:`warnings` module shows a warning once per text and call site.
    """
    if not mismatches:
        return
    message = format_tolerated_mismatches(mismatches, source)
    warnings.warn(
        EndfToleratedMismatchWarning(message, mismatches, source),
        stacklevel=_stacklevel_outside_package(),
    )


def parse_and_collect(parser, text, exclude=None, include=None):
    """Parse ``text`` with ``parser`` and return the result and the list of
    the tolerated mismatches, without issuing the warning. For a parser
    that does not collect them (a class derived from
    :class:`~endf_parserpy.EndfParserBase` other than the two parsers of
    the package), the list is empty and the parser may warn itself."""
    collect = getattr(parser, "_parse_and_collect", None)
    if collect is not None:
        return collect(text, exclude, include)
    if exclude is None and include is None:
        return parser.parse(text), []
    return parser.parse(text, exclude=exclude, include=include), []
