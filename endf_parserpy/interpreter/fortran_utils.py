############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2026/10/21
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from .custom_exceptions import InvalidIntegerError, InvalidFloatError
from math import log10, floor, isfinite
import re
from copy import deepcopy
from ..utils.math_utils import EndfFloat


def read_fort_int(valstr):
    if valstr.strip() == "":
        return 0
    else:
        try:
            return int(valstr)
        except ValueError as valerr:
            raise InvalidIntegerError(valerr)


def fortstr2float(valstr, read_opts=None):
    """Convert a Fortran number string to float.

    Convert a number string to a :class:`float`.
    Fortran number strings with the ``e`` character
    omitted are supported, and so are (unless
    disabled via ``accept_d_exponent``) Fortran
    double-precision exponents introduced by the
    character ``d`` or ``D`` (e.g. ``5.438673D-4``).

    Parameters
    ----------
    valstr : str
        String that should be converted to :class:`float`.
    read_opts : Optional[dict]
        Dictionary with field/value pairs to influence
        conversion process. Supported options are
        ``accept_spaces``, ``accept_nan_inf``, ``accept_d_exponent``,
        ``preserve_value_strings`` and ``width``.
        Consider the equally named options of the
        :class:`~endf_parserpy.EndfParserPy` class for
        an explanation of their meaning.

    Returns
    -------
        float
            :class:`float` that corresponds to string
            representation of number.
    """
    if read_opts is None:
        read_opts = {}
    return _fortstr2float(valstr, *_fortstr2float_opts(read_opts))


def _fortstr2float_opts(read_opts):
    return (
        read_opts.get("accept_spaces", True),
        read_opts.get("preserve_value_strings", False),
        read_opts.get("accept_nan_inf", True),
        read_opts.get("accept_d_exponent", True),
        read_opts.get("width", None),
    )


# A number of the form ` 1.234567+8`, `-12.5`, `1.5-3 ` (only spaces
# around it): the steps in _fortstr2float yield the mantissa followed
# by `E` and the exponent (if present), so it is converted directly.
_match_plain_number = re.compile(
    " *([+-]?(?:[0-9]*\\.)?[0-9]+)(?:([+-][0-9]+))? *"
).fullmatch


def _fortstr2float(
    valstr,
    accept_spaces,
    preserve_value_strings,
    accept_nan_inf,
    accept_d_exponent,
    width,
):
    orig_valstr = valstr
    if width is not None:
        valstr = valstr[:width]
    m = _match_plain_number(valstr)
    if m is not None:
        mantissa, exponent = m.groups()
        if exponent is not None:
            valstr = mantissa + "E" + exponent
        else:
            valstr = mantissa
        val = float(valstr)
        if not accept_nan_inf and not isfinite(val):
            raise InvalidFloatError(
                f"non-finite value (overflow / inf / NaN) in field: '{orig_valstr}'. "
                f"Set `accept_nan_inf=True` to allow non-finite values."
            )
        if preserve_value_strings:
            return EndfFloat(valstr, orig_valstr)
        return val
    if valstr.strip() == "":
        return 0.0
    if accept_spaces:
        valstr = valstr.replace(" ", "")
    if accept_d_exponent:
        # Fortran double-precision exponent, e.g. 5.438673D-4
        valstr = valstr.replace("D", "E").replace("d", "e")
    for i, c in enumerate(valstr):
        if i > 0 and (c == "+" or c == "-"):
            if valstr[i - 1].isdigit():
                valstr = valstr[:i] + "E" + valstr[i:]
    try:
        val = float(valstr)
    except ValueError as valerr:
        raise InvalidFloatError(valerr)
    if not accept_nan_inf and not isfinite(val):
        raise InvalidFloatError(
            f"non-finite value (overflow / inf / NaN) in field: '{orig_valstr}'. "
            f"Set `accept_nan_inf=True` to allow non-finite values."
        )
    if preserve_value_strings:
        return EndfFloat(valstr, orig_valstr)
    return val


def float2basicnumstr(val, write_opts=None):
    width = write_opts.get("width", 11)
    abuse_signpos = write_opts.get("abuse_signpos", False)
    skip_intzero = write_opts.get("skip_intzero", False)
    intpart = int(val)
    len_intpart = len(str(abs(intpart)))
    is_integer = intpart == val

    if is_integer:
        if intpart == 0:
            return "0".rjust(width)
        numstr = "{:d}".format(int(val))

    else:
        effwidth = width
        if val < 0 or not abuse_signpos:
            effwidth -= 1
        should_skip_zero = skip_intzero and intpart == 0
        if should_skip_zero:
            effwidth += 1
        # -1 due to the decimal point
        floatwidth = max(effwidth - 1 - len_intpart, 0)
        numstr = f"{{:.{floatwidth}f}}".format(val)
        if "." in numstr:
            if should_skip_zero:
                dotpos = numstr.index(".")
                numstr = numstr[: dotpos - 1] + numstr[dotpos:]
            numstr = numstr.rstrip("0").rstrip(".")
            # next line to deal with case -.00 and .00
            if numstr in ("+", "-", ""):
                numstr = "0"

    if val >= 0 and not abuse_signpos:
        numstr = " " + numstr
    numstr = numstr.rjust(width)
    return numstr


def _fortranify_expformstr(numstr, keep_E=False):
    # remove the unnecessary zeros in exponent
    epos = numstr.index("e")
    expdigits = numstr[epos + 2 :].lstrip("0") or "0"
    # remove `e` character if requested
    if keep_E:
        return numstr[: epos + 2] + expdigits
    return numstr[:epos] + numstr[epos + 1 : epos + 2] + expdigits


def _is_carried_mantissa(numstr):
    # whether the mantissa is 1 followed by zeros only, e.g. "-1.0000e-9"
    mantissa = numstr.lstrip(" +-")
    if mantissa[:1] != "1":
        return False
    for c in mantissa[1:]:
        if c != "0" and c != ".":
            return c in "eE+-"
    return True


def _fits_width(numstr, val, width, abuse_signpos):
    # a non-negative number needs a leading space unless abuse_signpos
    if abuse_signpos:
        return len(numstr) <= width
    return not (len(numstr) > width or (val >= 0 and len(numstr) == width))


def float2expformstr(val, write_opts=None):
    width = write_opts.get("width", 11)
    abuse_signpos = write_opts.get("abuse_signpos", False)
    keep_E = write_opts.get("keep_E", False)

    # get number of digits in exponent
    numstr6 = f"{val:.6e}"
    epos = numstr6.index("e")
    exp_len = len(numstr6[epos + 2 :].lstrip("0")) or 1
    # calculate available digits after comma
    prec = width - exp_len - 4
    if abuse_signpos and val >= 0:
        prec += 1
    if keep_E:
        prec -= 1
    # produce the number (the string for precision 6 is already available)
    if prec == 6:
        numstr = numstr6
    else:
        numstr = f"{{:.{prec}e}}".format(val)
        epos = numstr.index("e")
    # same as _fortranify_expformstr(numstr, keep_E)
    expdigits = numstr[epos + 2 :].lstrip("0") or "0"
    if keep_E:
        numstr = numstr[: epos + 2] + expdigits
    else:
        numstr = numstr[:epos] + numstr[epos + 1 : epos + 2] + expdigits

    # deal with special case of the sort 9.9999e-9 vs 1.00000-10
    # (same as `not _fits_width(numstr, val, width, abuse_signpos)`)
    numstr_len = len(numstr)
    if abuse_signpos:
        fits = numstr_len <= width
    else:
        fits = not (numstr_len > width or (val >= 0 and numstr_len == width))
    if not fits:
        prec -= 1
        numstr = f"{{:.{prec}e}}".format(val)
        numstr = _fortranify_expformstr(numstr, keep_E)
    # Use the largest precision for which the number still fits. A carry in
    # the rounding changes the length of the exponent: 9.99999949e-10 needs
    # more digits to fill the field than its precision-6 estimate suggests
    # (1.00000e-9), and 9999999500 fits with more digits (9.9999995+9) than
    # with fewer (1.000000+10). Without a carry (the mantissa is not
    # 1.000...), one more digit makes the number one character longer, so
    # that it no longer fits; the loop is then skipped.
    # (_is_carried_mantissa is false unless the mantissa starts with 1)
    while (
        prec < 20 and numstr.lstrip(" +-")[:1] == "1" and _is_carried_mantissa(numstr)
    ):
        candidate = f"{{:.{prec+1}e}}".format(val)
        candidate = _fortranify_expformstr(candidate, keep_E)
        if not _fits_width(candidate, val, width, abuse_signpos):
            break
        numstr = candidate
        prec += 1

    return numstr.rjust(width)


def float2fortstr(val, write_opts=None):
    """Convert a float value to string.

    This function converts a :class:`float` value
    to a string representation. Various options
    are supported to influence the conversion
    process.

    Parameters
    ----------

    val : float
        The float variable/number whose string
        representation is desired.
    write_opts : dict
        Python dictionary with field/value
        pairs to influence conversion process.
        Supported field names are ``prefer_noexp``,
        ``width``, ``abuse_signpos``, ``keep_E``,
        and ``skip_intzero``. Consider the equally
        named arguments of the :class:`~endf_parserpy.EndfParserPy`
        constructor for an explanation of these options.

    Returns
    -------
    str
        String representation of the :class:`float` number
    """
    width = write_opts.get("width", 11)
    if type(val) is not float and isinstance(val, EndfFloat):
        orig_str = val.get_original_string()
        if width != len(orig_str):
            raise InvalidFloatError(
                f"Length of string representation of float number "
                f"'{orig_str}' incompatible with specified width={width}"
            )
        return orig_str
    # Non-finite values (NaN, +/-inf) cannot be represented in the standard
    # ENDF compact float format. Emit a textual right-aligned representation
    # that fortstr2float can read back; matches the convention seen in some
    # real evaluations that store "NaN" verbatim in the 11-char field.
    if not isfinite(val):
        from math import isnan

        if isnan(val):
            repr_str = "NaN"
        elif val > 0:
            repr_str = "Inf"
        else:
            repr_str = "-Inf"
        return repr_str.rjust(width)
    if val == 0:
        # negative zero is written as zero
        val = 0.0
    prefer_noexp = write_opts.get("prefer_noexp", False)
    valstr_exp = float2expformstr(val, write_opts=write_opts)
    if not prefer_noexp:
        return valstr_exp
    valstr_basic = float2basicnumstr(val, write_opts=write_opts)
    if len(valstr_basic) > width:
        return valstr_exp
    delta1 = abs(fortstr2float(valstr_basic) - val)
    delta2 = abs(fortstr2float(valstr_exp) - val)
    if delta2 < delta1:
        return valstr_exp
    valstr_basic = valstr_basic.rjust(width)
    return valstr_basic


def read_fort_floats(line, n=6, read_opts=None):
    """Read several floats from a string.

    The string representations of each number
    are assumed to be stored one-after-another
    in text fields of a fixed size.

    Parameters
    ----------
    line : str
        String containing numbers to read
    n : int
        Number of float numbers to read
    read_opts : Optional[dict]
        The field ``width`` specifies the number
        of character-slots assigned to each float.
        For the other available options, see the
        help of :func:`fortstr2float`.

    Returns
    -------
    list[float]
        A list with the extracted :class:`float` numbers
    """
    width = read_opts.get("width", 11)
    assert isinstance(line, str)
    opts = _fortstr2float_opts(read_opts)
    accept_nan_inf = opts[2]
    preserve_value_strings = opts[1]
    if not accept_nan_inf or preserve_value_strings or opts[4] not in (None, width):
        return [
            _fortstr2float(line[i : i + width], *opts)
            for i in range(0, n * width, width)
        ]
    # same as _fortstr2float, with the conversion of plain numbers inline
    vals = []
    for i in range(0, n * width, width):
        valstr = line[i : i + width]
        m = _match_plain_number(valstr)
        if m is not None:
            mantissa, exponent = m.groups()
            if exponent is not None:
                vals.append(float(mantissa + "E" + exponent))
            else:
                vals.append(float(mantissa))
        else:
            vals.append(_fortstr2float(valstr, *opts))
    return vals


def write_fort_floats(vals, write_opts=None):
    """Write several floats to a string.

    Floats are written as text fields of fixed width
    one-after-another.

    Parameters
    ----------
    vals : list[float]
    write_opts : Optional[dict]
        Dictionary with options to influence number formatting,
        see help of :func:`float2fortstr` for available options.

    Returns
    -------
    str
        String with numbers written one-after-another
        in text fields of fixed width.
    """
    return "".join([float2fortstr(v, write_opts=write_opts) for v in vals])
