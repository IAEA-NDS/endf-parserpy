############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/07/08
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

from .custom_exceptions import InvalidIntegerError, InvalidFloatError
from math import log10, floor
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
    omitted are supported.

    Parameters
    ----------
    valstr : str
        String that should be converted to :class:`float`.
    read_opts : Optional[dict]
        Dictionary with field/value pairs to influence
        conversion process. Supported options are
        ``accept_spaces`` and ``preserve_value_strings``.
        Consider the equally named options of the
        :class:`~endf_parserpy.EndfParserPy` class for
        an explanation of their meaning.

    Returns
    -------
        float
            :class:`float` that corresponds to string
            representation of number.
    """
    orig_valstr = valstr
    if read_opts is None:
        read_opts = {}
    accept_spaces = read_opts.get("accept_spaces", True)
    preserve_value_strings = read_opts.get("preserve_value_strings", False)
    width = read_opts.get("width", None)
    if width is not None:
        valstr = valstr[:width]
    if valstr.strip() == "":
        return 0.0
    if accept_spaces:
        valstr = valstr.replace(" ", "")
    for i, c in enumerate(valstr):
        if i > 0 and (c == "+" or c == "-"):
            if valstr[i - 1].isdigit():
                valstr = valstr[:i] + "E" + valstr[i:]
    try:
        if preserve_value_strings:
            return EndfFloat(valstr, orig_valstr)
        else:
            return float(valstr)
    except ValueError as valerr:
        raise InvalidFloatError(valerr)


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
    zerostart = zerostop = numstr.index("e") + 2
    numstr_len = len(numstr)
    while numstr[zerostop] == "0":
        zerostop += 1
        if zerostop == numstr_len:
            break
    if zerostop < numstr_len:
        numstr = numstr[:zerostart] + numstr[zerostop:]
    else:
        numstr = numstr[:zerostart] + "0"
    # remove `e` character if requested
    if not keep_E:
        numstr = numstr.replace("e", "")
    return numstr


def float2expformstr(val, write_opts=None):
    width = write_opts.get("width", 11)
    abuse_signpos = write_opts.get("abuse_signpos", False)
    keep_E = write_opts.get("keep_E", False)

    # get number of digits in exponent
    expnumstr = f"{val:.6e}"
    expnumstr = expnumstr[expnumstr.index("e") + 2 :]
    exp_len = 1
    for i, c in enumerate(expnumstr):
        if c != "0":
            exp_len = len(expnumstr) - i
            break
    # calculate available digits after comma
    prec = width - exp_len - 4
    if abuse_signpos and val >= 0:
        prec += 1
    if keep_E:
        prec -= 1
    # produce the number
    numstr = f"{{:.{prec}e}}".format(val)
    numstr = _fortranify_expformstr(numstr, keep_E)
    numstr_len = len(numstr)
    # deal with special case of the sort 9.9999e-9 vs 1.00000-10
    if abuse_signpos:
        if numstr_len > width:
            numstr = f"{{:.{prec-1}e}}".format(val)
            numstr = _fortranify_expformstr(numstr, keep_E)
    else:
        if numstr_len > width or (val > 0 and numstr_len == width):
            numstr = f"{{:.{prec-1}e}}".format(val)
            numstr = _fortranify_expformstr(numstr, keep_E)

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
    if isinstance(val, EndfFloat):
        orig_str = val.get_original_string()
        if width != len(orig_str):
            raise InvalidFloatError(
                f"Length of string representation of float number "
                f"'{orig_str}' incompatible with specified width={width}"
            )
        return orig_str
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
    vals = []
    for i in range(0, n * width, width):
        vals.append(fortstr2float(line[i : i + width], read_opts=read_opts))
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
    line = ""
    for i, v in enumerate(vals):
        line += float2fortstr(v, write_opts=write_opts)
    return line
