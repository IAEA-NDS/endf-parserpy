############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2025/06/01
# Last modified:   2025/07/10
# License:         MIT
# Copyright (c) 2025 International Atomic Energy Agency (IAEA)
#
############################################################

import logging
import inspect
import warnings
from .interpreter.endf_parser import EndfParserPy
from .cpp_parsers.endf_parser_cpp import EndfParserCpp


def _check_param(
    parser, param, expect_values, parser_args, do_raise=False, warn_slow=False
):
    value = parser_args[param]
    if value in expect_values:
        return True
    if do_raise:
        if len(expect_values) > 1:
            expect_values_str = "in (" + ",".join(str(v) for v in expect_values) + ")"
        elif len(expect_values) == 1:
            expect_values_str = str(expect_values[0])
        else:
            raise ValueError("expect_values must be non-empty list")
        raise ValueError(
            f"`{param}` expected to be {expect_values_str} for {parser} parser "
            f"but received {param}={value}."
        )
    if warn_slow:
        warnings.warn(
            f"Argument {param}={value} forces the selection of the (slow) Python parser",
            UserWarning,
        )

    return False


def _none_to_defaults(thedict, defaults):
    for k, d in defaults.items():
        if k not in thedict or thedict[k] is None:
            thedict[k] = d


class EndfParserFactory:
    """Factory class to create ENDF parsers.

    This class provides the :meth:`~EndfParserFactory.create`
    method for creating an ENDF parser object.
    """

    @staticmethod
    def create(
        select="fastest",
        warn_slow=True,
        require_compat=False,
        ignore_number_mismatch=False,
        ignore_zero_mismatch=True,
        ignore_varspec_mismatch=True,
        fuzzy_matching=False,  # Python only
        abuse_signpos=False,
        skip_intzero=False,
        prefer_noexp=False,
        accept_spaces=True,
        ignore_blank_lines=True,
        ignore_send_records=False,
        ignore_missing_tpid=False,
        keep_E=False,
        preserve_value_strings=False,
        include_linenum=True,
        width=11,  # Python only
        check_arrays=False,  # Python only
        strict_datatypes=False,
        array_type="dict",
        explain_missing_variable=None,  # Python only
        cache_dir=None,  # Python only
        print_cache_info=None,  # Python only
        endf_format="endf6-ext",
        recipes=None,  # Python only
        parsing_funs=None,  # Python only
        loglevel=None,  # Python only
        validate_control_records=False,  # C++ only
    ):
        """Create an ENDF parser instance.

        This function creates an ENDF parser object,
        which is either an instance of the
        :class:`~endf_parserpy.EndfParserPy` (Python parser) or
        :class:`~endf_parserpy.EndfParserCpp` (C++ parser) class
        depending on the supplied arguments. The three parameters
        described below control the behavior of the parser factory.
        All other parameters are arguments to the constructor of the
        :class:`~endf_parserpy.EndfParserPy` or
        :class:`~endf_parserpy.EndfParserCpp` class
        and most of them are available for both classes.

        Parameters
        ----------
        select : string
            Can be ``fastest``, ``cpp``, or ``python``. If ``fastest``,
            selects the C++ parser if possible and falls back
            on the Python parser otherwise. If ``cpp`` or ``python``,
            selects C++ or Python parser, respectively, and fails
            if requested parser type cannot be selected.
        warn_slow : bool
            If ``True``, issues a :exc:`UserWarning` if user requested
            fastest parser but C++ parser is not available or incompatible
            with parser arguments.
        require_compat : bool
            If ``True``, only instantiate parser class if parser arguments
            are compatible with both Python and C++ parser and
            raise a :exc:`ValueError` exception otherwise.
        """
        params = inspect.signature(EndfParserFactory.create).parameters.keys()
        real_params = dict(locals())
        parser_args = {p: real_params[p] for p in params}
        del parser_args["select"]
        del parser_args["warn_slow"]
        del parser_args["require_compat"]

        epf = EndfParserFactory

        if require_compat:
            msg_tmpl = (
                "Argument compatibility with both Python and C++ parser enforced "
                "(require_compat=True) but the arguments provided are not compatible "
                "with the {} parser for the following reason: {}"
            )
            try:
                epf.python_compatible_args(parser_args, do_raise=True)

            except ValueError as exc:
                raise ValueError(msg_tmpl.format("Python", str(exc)))

            try:
                epf.cpp_compatible_args(parser_args, do_raise=True)

            except ValueError as exc:
                raise ValueError(msg_tmpl.format("C++", str(exc)))

        if select == "python":
            epf.python_compatible_args(parser_args, do_raise=True)
            return epf.get_python_parser(parser_args)

        if select == "cpp":
            epf.cpp_compatible_args(parser_args, do_raise=True)
            return epf.get_cpp_parser(parser_args)

        if select == "fastest":
            if not epf.cpp_compatible_args(
                parser_args, do_raise=False, warn_slow=warn_slow
            ):
                epf.python_compatible_args(parser_args, do_raise=True)
                return epf.get_python_parser(parser_args)
            try:
                return epf.get_cpp_parser(parser_args)
            except ImportError:
                if warn_slow:
                    warnings.warn(
                        "C++ parser not available, forced to use slow Python parser",
                        UserWarning,
                    )
                epf.python_compatible_args(parser_args, do_raise=True)
                return epf.get_python_parser(parser_args)

        raise ValueError(
            "value of `select` argument must be one of `python`, `cpp`, `fastest`"
        )

    @staticmethod
    def python_compatible_args(parser_args, do_raise=False):
        return _check_param(
            "Python", "validate_control_records", [False], parser_args, do_raise
        )

    @staticmethod
    def get_python_parser(parser_args):
        parser_args = parser_args.copy()
        _none_to_defaults(
            parser_args,
            {
                "check_arrays": True,
                "explain_missing_variable": True,
                "print_cache_info": True,
                "loglevel": logging.WARNING,
            },
        )
        parser_args.pop("validate_control_records", None)
        return EndfParserPy(**parser_args)

    @staticmethod
    def cpp_compatible_args(parser_args, do_raise=False, warn_slow=False):
        return (
            _check_param(
                "C++", "fuzzy_matching", [False], parser_args, do_raise, warn_slow
            )
            and _check_param("C++", "width", [11], parser_args, do_raise, warn_slow)
            and _check_param(
                "C++", "check_arrays", [False], parser_args, do_raise, warn_slow
            )
            and _check_param(
                "C++", "strict_datatypes", [False], parser_args, do_raise, warn_slow
            )
            and _check_param(
                "C++",
                "explain_missing_variable",
                [None, False],
                parser_args,
                do_raise,
                warn_slow,
            )
            and _check_param("C++", "recipes", [None], parser_args, do_raise, warn_slow)
            and _check_param(
                "C++", "parsing_funs", [None], parser_args, do_raise, warn_slow
            )
            and _check_param(
                "C++", "loglevel", [None], parser_args, do_raise, warn_slow
            )
        )

    @staticmethod
    def get_cpp_parser(parser_args):
        parser_args = parser_args.copy()
        parser_args.pop("fuzzy_matching", None)
        parser_args.pop("width", None)
        parser_args.pop("check_arrays", None)
        parser_args.pop("strict_datatypes", None)
        parser_args.pop("explain_missing_variable", None)
        parser_args.pop("print_cache_info", [None])
        parser_args.pop("cache_dir")
        parser_args.pop("recipes", None)
        parser_args.pop("parsing_funs", None)
        parser_args.pop("loglevel", None)
        return EndfParserCpp(**parser_args)
