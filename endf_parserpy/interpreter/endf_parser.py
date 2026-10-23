############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2026/10/23
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import Mapping
import logging
import warnings
import re
from .logging_utils import setup_logger, write_info, RingBuffer
from platformdirs import user_cache_dir
from os.path import exists as file_exists
from endf_parserpy.utils.tree_utils import (
    is_tree,
    get_child,
    get_child_value,
    retrieve_value,
)
from endf_parserpy.utils.accessories import EndfDict, EndfPath
from .endf_mappings import (
    map_cont_dic,
    map_head_dic,
    map_text_dic,
    map_dir_dic,
    map_intg_dic,
    map_tab1_dic,
    map_tab2_dic,
    map_list_dic,
)
from .endf_mapping_utils import eval_expr_without_unknown_var, get_varname
from .meta_control_utils import (
    cycle_for_loop,
    cycle_repeat_loop,
    evaluate_if_clause,
    open_section,
    close_section,
    initialize_working_vars,
    introduce_abbreviation,
    remove_working_vars,
)
from .lookahead_management import should_proceed
from .endf_utils import (
    read_cont,
    write_cont,
    read_ctrl,
    get_ctrl,
    write_head,
    read_head,
    read_text,
    write_text,
    read_intg,
    write_intg,
    read_dir,
    write_dir,
    read_tab1,
    write_tab1,
    read_tab2,
    write_tab2,
    read_send,
    write_send,
    write_fend,
    write_mend,
    write_tend,
    read_list,
    write_list,
    split_sections,
    skip_blank_lines,
    add_linenumbers_to_section,
)
from .custom_exceptions import (
    InconsistentSectionBracketsError,
    StopException,
    ParserException,
    VariableNotFoundError,
    UnexpectedControlRecordError,
    MissingSectionError,
)
from .endf_recipe_utils import (
    get_recipe_parsetree_dic,
    get_responsible_recipe_parsetree,
    get_responsible_recipe_parsefun,
)
from endf_parserpy.endf_recipes import get_recipe_dict
from endf_parserpy.utils.debugging_utils import TrackingDict
from .helpers import array_dict_to_list
from .numpy_annotation import annotate_recipe_tree
from .custom_exceptions import RecipeAnnotationError
from .numpy_arrays import (
    mark_assignments,
    convert_arrays,
    fill_empty_elements,
    numpy_to_python,
)
from ..endf_parser_base import (
    EndfParserBase,
    _record_init_kwargs,
    _check_array_type,
)


def _annotate_tree(tree, raise_error=False):
    """Annotate a recipe tree for the creation of array elements.

    The annotation (see numpy_annotation) is done once per tree. If the
    recipe contains a construct that the annotation does not support
    (``RecipeAnnotationError``), the tree remains without annotation,
    and the arrays are parsed and written as before the annotation was
    introduced, i.e. elements of nested arrays are only created when
    values are assigned to them. With ``raise_error=True`` (used for
    ``array_type="numpy"``, whose result is determined by the annotation),
    the error is raised instead. Returns whether the tree is annotated.
    """
    state = getattr(tree, "_np_annotated", None)
    if state is None:
        try:
            annotate_recipe_tree(tree)
            state = True
        except RecipeAnnotationError as exc:
            state = exc
        tree._np_annotated = state
    if state is not True:
        if raise_error:
            raise RecipeAnnotationError(str(state))
        return False
    return True


class EndfParserPy(EndfParserBase):
    """Class for parsing and writing ENDF-6 formatted data.

    This class provides functions for
    (1) parsing ENDF-6 formatted data, and (2) converting data
    given in a :class:`dict`-like object into the ENDF-6 format.
    The ENDF-6 formatted data may be given
    in a text file, a string, or a list of strings containing
    separate lines. The essential methods of this class
    are :func:`parsefile` and :func:`writefile`.
    """

    @_record_init_kwargs
    def __init__(
        self,
        ignore_number_mismatch=False,
        ignore_zero_mismatch=True,
        ignore_varspec_mismatch=True,
        fuzzy_matching=False,
        abuse_signpos=False,
        skip_intzero=False,
        prefer_noexp=False,
        accept_spaces=True,
        ignore_blank_lines=False,
        ignore_send_records=False,
        ignore_missing_tpid=False,
        accept_nan_inf=True,
        accept_d_exponent=True,
        keep_E=False,
        preserve_value_strings=False,
        include_linenum=True,
        width=11,
        check_arrays=True,
        strict_datatypes=False,
        array_type="dict",
        explain_missing_variable=True,
        cache_dir=None,
        print_cache_info=True,
        endf_format="endf6-ext",
        recipes=None,
        parsing_funs=None,
        loglevel=logging.WARNING,
    ):
        """Initializaton of options for parsing and writing ENDF-6 data.

        The process of parsing can be influenced by many options that
        determine how inconsistencies in ENDF-6 formatted data should be
        handled and the degree of flexibility in accepting unusual
        number representations. Parameters pertaining to the parsing process
        are indicated by `(parsing)` in their description.
        The reverse process, writing data into the ENDF-6 format, can also be
        influenced by a variety of options, e.g., impacting the output precision.
        Parameters related to converting data into the ENDF-6 format are
        marked by `(writing)`.


        Parameters
        ------------------
        ignore_number_mismatch: bool
            Tolerate mismatches between numbers in ENDF-6 formatted
            data and the expected numbers according to the ENDF-6 recipes.
            *(parsing)*
        ignore_zero_mismatch: bool
            Tolerate non-zero numbers in ENDF-6 formatted data that
            are required to be zero according to ENDF-6 recipes.
            *(parsing)*
        ignore_varspec_mismatch: bool
            Tolerate distinct numbers that are supposed to be mapped
            to the same symbol name. For the time being, even with this
            option enabled, possible inconsistent variable assignment
            have to be marked with a queston mark in the ENDF-6 recipe.
            *(parsing)*
        fuzzy_matching: bool
            Tolerate small inconsistencies between fields when they
            are linked by a mathematical relationship. *(parsing)*
        abuse_signpos: bool
            Permit positive numbers to start in the first character slot
            of an ENDF-6 field, which is usually reserved for the sign,
            to enhance numerical precision. *(writing)*
        skip_intzero: bool
            For numbers written out in decimal notation, eliminate
            the integer part if zero, e.g. `0.12` becomes `.12` to
            increase attainable precision. *(writing)*
        prefer_noexp: bool
            Switch to decimal representation (i.e. non-scientific) if it leads
            to an increase of accuracy, e.g. `1.234567-1` becomes `0.12345678`.
            *(writing)*
        accept_spaces: bool
            Eliminate spaces in a number before trying to parse it, e.g.
            `1.234 +8` is transformed to `1.234+8`. *(parsing)*
        ignore_blank_lines: bool
            If ``True``, skip blank lines in ENDF-6 formatted input without
            complaining. Otherwise, blank lines will lead to parsing failure.
            *(parsing)*
        ignore_send_records: bool
            If ``True``, the correct positioning of SEND/FEND/MEND/TEND
            to indicate the end of a section is not checked. *(parsing)*
        ignore_missing_tpid: bool
            If ``True``, the parser will tolerate a missing TPID
            record at the beginning of the file. *(parsing)*
        accept_nan_inf: bool
            If ``True`` (default), allow non-finite numeric values
            (``NaN``, ``+inf``, ``-inf`` literals as well as values
            that overflow to ``±inf``) in float fields. If ``False``,
            such values raise an :class:`InvalidFloatError` during
            parsing. *(parsing)*
        accept_d_exponent: bool
            If ``True`` (default), accept a Fortran double-precision
            exponent introduced by ``D`` or ``d`` in float fields, e.g.
            ``5.438673D-4`` is read as ``5.438673e-4``. Such numbers do
            not conform to the ENDF-6 format but are found in some
            evaluated data files. If ``False``, they raise an
            :class:`InvalidFloatError` during parsing. On writing, the
            ``D`` character is never emitted (output is formatted
            according to ``keep_E``), unless the original string
            representation is preserved and written verbatim (see
            ``preserve_value_strings``). *(parsing)*
        keep_E : bool
            If ``True``, include the `e` character in scientific notation,
            e.g. `1.23e-8` instead of `1.23-8`. The inclusion establishes
            compatibility with programming languages different from Fortran
            while the omission enhances numerical precision. *(writing)*
        preserve_value_strings : bool
            If ``True``, also the string representations of float numbers will
            be recorded during the parsing process (via the
            :class:`~endf_parserpy.interpreter.fortran_utils.EndfFloat` class).
            These string representations when available will be used verbatim
            for outputting ENDF-6 formatted data (irrespective of the
            ``preserve_value_strings`` option), overruling any of the other
            options provided for controling the output format of floats.
            *(parsing)*
        include_linenum : bool
            Controls whether the 5-digit line number should be
            included at the end of each line. *(writing)*
        width : int
            The number of character slots in an ENDF-6 field. The ENDF-6
            format requires 11 but the user may opt for a different width
            for their storage/application needs. *(parsing, writing)*
        check_arrays : bool
            Ensures that index ranges provided in the Python :class:`dict`
            passed as argument to the :func:`write` and :func:`writefile`
            method are consistent with the values of counter variables.
            If ``True``, a :class:`dict` containing larger index ranges than
            expected by counter variables will lead to failure, otherwise
            the presence of additional indices will be ignored. *(writing)*
        strict_datatypes : bool
            Strict data type checking will lead to failure if a `float`
            needs to be cast to an `int`. If `false`, the writing process
            will only fail if the a value in the `float` cannot be
            perfectly represented by an `int`. *(writing)*
        array_type : str
            The Python datatype to use for representing arrays read from
            ENDF-6 files. The options are ``"dict"`` (default), ``"list"``
            and ``"numpy"``. The additional option ``"list_slow"`` yields
            the same result as ``"list"`` via a slower implementation and
            exists for debugging purposes. Any other value raises a
            :class:`ValueError`.
            With ``"numpy"``, arrays are indexed as with ``"list"``, but
            arrays of numbers are returned as numpy arrays (the
            ``numpy`` package must be installed, otherwise an
            :class:`ImportError` is raised), in the same form as by
            :class:`~endf_parserpy.EndfParserCpp`: arrays of integers as
            ``int64`` arrays and arrays of floats, including the columns of
            TAB1 records, as ``float64`` arrays. A matrix stored in a
            rectangular block of a record, e.g. a covariance matrix in
            MF33 with ``LB=5, LS=0``, is a two-dimensional array; a
            triangular matrix is a list of one-dimensional arrays (its
            rows). Arrays of arrays are lists of numpy arrays, and arrays
            of other elements, such as sections or strings, are lists as
            with ``"list"``. If ``preserve_value_strings=True``, arrays of
            floats are returned as lists, as with ``"list"``; arrays of
            integers are still numpy arrays. The form of each array
            follows the place in the recipe where it is assigned, as in
            the C++ parser (also for custom recipes). The results of
            functions in ``parsing_funs`` are not converted.
            When writing with ``"list"`` or ``"numpy"``, numpy arrays and
            scalars (of any integer type for integer fields, of any
            integer or float type for float fields) and lists and Python
            numbers can be used interchangeably. *(parsing, writing)*
        explain_missing_variable : bool
            If the :func:`write` or :func:`writefile` method
            fail because a variable is missing in the dictionary,
            print available explanation if this argument is ``True``.
        cache_dir
            Directory to store the parsing trees associated with ENDF-6 recipes
            If `None`, the directory will be automatically determined
            relying on the `appdirs` package. If `false`, no cache directory
            will be used and ENDF-6 recipes will be compiled on the fly
            whenever this class is instantiated. Finally, the user can
            provide a custom directory as a string.
        print_cache_info : bool
            If ``True``, print out a message regarding the location of the
            cache directory if it was automatically determined.
        endf_format : str
            Allow the user to pick specific ENDF format flavors.
            The default `endf6-ext` tolerates deviations from the
            ENDF-6 format encountered in some nuclear data libraries.
            Other choices are `endf6` for strict compliance with the
            ENDF-6 formats manual and `jendl` with JENDL specific
            conventions, which are also implemented in `endf6-ext`.
        recipes : dict_like
            The default ENDF-6 recipes can be overrided by providing a
            nested dictionary with custom recipes. Inspect the default
            recipe dictionary to see the required structure
            (`from endf_parserpy.endf_recipes import endf_recipe_dictionary`)
        loglevel : int
            Controls the level of detail for logging output. Default is
            `logging.WARN`. Many ENDF-6 files in nuclear data libraries
            contain auxiliary information in unused fields (expected to be zero),
            which will trigger warnings. Use `logging.ERROR` to suppress
            these warnings (you will need to `import logging`).
        """
        _check_array_type(array_type)
        if array_type == "numpy":
            try:
                import numpy  # noqa: F401
            except ImportError as exc:
                raise ImportError(
                    "array_type `numpy` requires the numpy package, "
                    "which could not be imported"
                ) from exc
        # obtain the parsing tree for the language
        # in which ENDF reading recipes are formulated
        if recipes is None:
            recipes = get_recipe_dict(endf_format)
        self.tree_dic = get_recipe_parsetree_dic(recipes, cache_dir, print_cache_info)
        self.parsing_funs = parsing_funs if parsing_funs is not None else {}
        # array_type="numpy": kinds of the variables recorded while parsing
        self._numpy_forms = None

        # endf record treatment
        endf_actions = {}
        endf_actions["head_or_cont_line"] = self.process_head_or_cont_line
        endf_actions["text_line"] = self.process_text_line
        endf_actions["dir_line"] = self.process_dir_line
        endf_actions["intg_line"] = self.process_intg_line
        endf_actions["tab1_line"] = self.process_tab1_line
        endf_actions["tab2_line"] = self.process_tab2_line
        endf_actions["list_line"] = self.process_list_line
        endf_actions["send_line"] = self.process_send_line
        endf_actions["stop_line"] = self.process_stop_line
        self.endf_actions = endf_actions
        # program flow
        meta_actions = {}
        meta_actions["for_loop"] = self.process_for_loop
        meta_actions["repeat_loop"] = self.process_repeat_loop
        meta_actions["if_clause"] = self.process_if_clause
        meta_actions["section"] = self.process_section
        meta_actions["abbreviation"] = self.process_abbreviation
        meta_actions["comment_block"] = self.process_comment_block
        self.meta_actions = meta_actions

        self.parse_opts = {
            "ignore_zero_mismatch": ignore_zero_mismatch,
            "ignore_number_mismatch": ignore_number_mismatch,
            "ignore_varspec_mismatch": ignore_varspec_mismatch,
            "fuzzy_matching": fuzzy_matching,
            "array_type": array_type,
        }
        self.write_opts = {
            "abuse_signpos": abuse_signpos,
            "skip_intzero": skip_intzero,
            "prefer_noexp": prefer_noexp,
            "keep_E": keep_E,
            "preserve_value_strings": preserve_value_strings,
            "include_linenum": include_linenum,
            "width": width,
            "check_arrays": check_arrays,
            "strict_datatypes": strict_datatypes,
        }
        self.read_opts = {
            "accept_spaces": accept_spaces,
            "ignore_blank_lines": ignore_blank_lines,
            "ignore_send_records": ignore_send_records,
            "ignore_missing_tpid": ignore_missing_tpid,
            "accept_nan_inf": accept_nan_inf,
            "accept_d_exponent": accept_d_exponent,
            "width": width,
            "preserve_value_strings": preserve_value_strings,
        }
        self.explain_missing_variable = explain_missing_variable
        self.variable_descriptions = EndfDict()
        self.current_path = None
        # set up the logging functionality
        if not hasattr(EndfParserPy, "instance_counter"):
            EndfParserPy.instance_counter = 0
        EndfParserPy.instance_counter += 1
        self.name = f"EndfParserPyInstance{EndfParserPy.instance_counter}"
        self.logger = setup_logger(self.name, loglevel)

    def explain(self, varpath, stdout=True):
        """Explain the meaning of a variable.

        ENDF-6 recipes can contain the descriptions of variables,
        which are automatically read while calling the
        :func:`parsefile`, :func:`parse`, :func:`write`
        and :func:`writefile` method. Given the path to a
        variable, this function can output the associated
        description.

        Parameters
        ----------
        varpath : EndfPath
            The EndfPath to the variable or an object accepted
            by the constructor of the EndfPath class.
        stdout : bool
            If ``True``, print the description on stdout.
            Otherwise, return the description.

        Returns
        -------
        str
            If ``stdout=True`` return ``None``,
            otherwise the description as a ``str``.
        """
        varpath = EndfPath(varpath)
        vardescr = self.variable_descriptions
        search_state = [0]
        search_dicts = [vardescr]
        level = 0
        while level >= 0:
            search_state[level] += 1
            ss = search_state[level]
            sd = search_dicts[level]
            p = varpath[level]
            if level == len(varpath) - 1:
                if sd.exists(p) and isinstance(sd[p], str):
                    if stdout:
                        print(sd[p])
                        return
                    else:
                        return sd[p]
                search_dicts.pop()
                search_state.pop()
                level -= 1
            elif ss == 3:
                search_dicts.pop()
                search_state.pop()
                level -= 1
            else:
                ps = p if ss == 1 else "*"
                if sd.exists(ps):
                    search_dicts.append(sd[ps])
                    search_state.append(0)
                    level += 1

        if stdout:
            print(f"No description for `{str(varpath)}` available")
        return None

    def process_comment_block(self, tree):
        def extract_info(comment):
            rex = r" *#(?P<indentstr>( *var *"
            rex += r"(?P<varname>[a-zA-Z0-9/*]+) *(\[[^]]*\])?"
            rex += " *:)?)?"
            rex += "(?P<comment>.*)"
            dic = re.match(rex, comment).groupdict()
            return dic["varname"], dic["comment"], len(dic["indentstr"])

        idx = 0
        comment_lines = get_child_value(tree, "COMMENT").splitlines()
        while idx < len(comment_lines):
            comment_line = comment_lines[idx]
            varname, comment, indent = extract_info(comment_line)
            if varname is not None:
                if comment.strip() != "":
                    firstindent = indent + len(comment) - len(comment.lstrip())
                    curdescr = [comment.lstrip()]
                else:
                    idx += 1
                    comment_line = comment_lines[idx]
                    tmp, comment, indent = extract_info(comment_line)
                    if tmp is not None:
                        raise ValueError(f"empty explaination of {varname}")
                    firstindent = len(comment) - len(comment.lstrip())
                    curdescr = [comment[firstindent:]]
                idx += 1
                while idx < len(comment_lines):
                    comment_line = comment_lines[idx]
                    newvarname, comment, _ = extract_info(comment_line)
                    if newvarname is not None:
                        idx -= 1
                        break
                    curindent = len(comment) - len(comment.lstrip())
                    maxindent = min(firstindent, curindent)
                    curdescr.append(comment[maxindent:])
                    idx += 1
                vardescrs = self.variable_descriptions
                vardescrs[self.current_path, varname] = "\n".join(curdescr).strip()
            idx += 1

    def process_stop_line(self, tree):
        if self.rwmode == "read":
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
        else:
            self.logbuffer.save_reduced_record_log(tree)
        stop_message = retrieve_value(tree, "STOP_MESSAGE")
        stop_message = stop_message if stop_message is not None else "stop instruction"
        raise StopException(stop_message)

    def process_text_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a TEXT record", self.ofs)
            text_dic, self.ofs = read_text(
                self.lines, self.ofs, with_ctrl=True, read_opts=self.read_opts
            )
            text_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_text_dic(
                tree,
                text_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            text_dic = map_text_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            text_dic.update(get_ctrl(self.datadic))
            newlines = write_text(text_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_head_or_cont_line(self, tree):
        line_type = get_child_value(tree, "CONT_SUBTYPE")
        if line_type == "HEAD":
            self.process_head_line(tree)
        elif line_type == "CONT":
            self.process_cont_line(tree)
        else:
            raise TypeError("parser code / grammar mismatch")

    def process_head_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a HEAD record", self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            cont_dic, self.ofs = read_head(
                self.lines,
                self.ofs,
                with_ctrl=True,
                read_opts=self.read_opts,
            )
            cont_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            if self.logger.isEnabledFor(logging.INFO):
                write_info(
                    self.logger,
                    "Content of the HEAD record: " + str(cont_dic),
                    self.ofs,
                )
            map_head_dic(
                tree,
                cont_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            head_dic = map_head_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            head_dic.update(get_ctrl(self.datadic))
            newlines = write_head(head_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_cont_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a CONT record", self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            cont_dic, self.ofs = read_cont(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
            cont_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Content of the CONT record: " + str(cont_dic))
            map_cont_dic(
                tree,
                cont_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            cont_dic = map_cont_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            cont_dic.update(get_ctrl(self.datadic))
            newlines = write_cont(cont_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_dir_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            dir_dic, self.ofs = read_dir(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
            dir_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_dir_dic(
                tree,
                dir_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            dir_dic = map_dir_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            dir_dic.update(get_ctrl(self.datadic))
            newlines = write_dir(dir_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_intg_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            ndigit = eval_expr_without_unknown_var(
                get_child(tree, "ndigit_expr"), self.datadic, self.loop_vars
            )
            intg_dic, self.ofs = read_intg(
                self.lines,
                self.ofs,
                ndigit=ndigit,
                read_opts=self.read_opts,
            )
            intg_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_intg_dic(
                tree,
                intg_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            intg_dic = map_intg_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            intg_dic.update(get_ctrl(self.datadic))
            ndigit = eval_expr_without_unknown_var(
                get_child(tree, "ndigit_expr"), self.datadic, self.loop_vars
            )
            newlines = write_intg(
                intg_dic, with_ctrl=True, ndigit=ndigit, write_opts=self.write_opts
            )
            self.lines += newlines

    def process_tab1_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a TAB1 record", self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            tab1_dic, self.ofs = read_tab1(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
            tab1_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_tab1_dic(
                tree,
                tab1_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            tab1_dic = map_tab1_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                path=self.current_path,
                logger=self.logger,
            )
            tab1_dic.update(get_ctrl(self.datadic))
            newlines = write_tab1(tab1_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_tab2_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a TAB2 record", self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            tab2_dic, self.ofs = read_tab2(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
            tab2_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_tab2_dic(
                tree,
                tab2_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            tab2_dic = map_tab2_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            tab2_dic.update(get_ctrl(self.datadic))
            newlines = write_tab2(tab2_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_list_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars["__ofs"] = self.ofs
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, "Reading a LIST record", self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            list_dic, self.ofs = read_list(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
            list_dic.update(self.logbuffer.get_last_entry(key_prefix="__"))
            map_list_dic(
                tree,
                list_dic,
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            list_dic = map_list_dic(
                tree,
                {},
                self.datadic,
                self.loop_vars,
                self.rwmode,
                parse_opts=self.parse_opts,
                logger=self.logger,
            )
            list_dic.update(get_ctrl(self.datadic))
            newlines = write_list(list_dic, with_ctrl=True, write_opts=self.write_opts)
            self.lines += newlines

    def process_send_line(self, tree):
        if self.rwmode == "read":
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            read_send(
                self.lines,
                self.ofs,
                read_opts=self.read_opts,
            )
        else:
            self.logbuffer.save_reduced_record_log(tree)
            newlines = write_send(
                self.datadic,
                with_ctrl=True,
                zero_as_blank=self.zero_as_blank,
                write_opts=self.write_opts,
            )
            self.lines += newlines

    def process_section(self, tree):
        self.loop_vars["__ofs"] = self.ofs
        section_head = get_child(tree, "section_head")
        if self.rwmode == "write":
            self.logbuffer.save_reduced_record_log(section_head)
        section_tail = get_child(tree, "section_tail")
        varname = get_varname(section_head)
        varname2 = get_varname(section_tail)
        if varname != varname2:
            raise InconsistentSectionBracketsError(
                "The section name in the tail does not correspond to "
                + f"the one in the head (`{varname}` vs `{varname2}`)"
            )

        create_missing = self.rwmode == "read"
        previous_path = self.current_path
        self.datadic, self.current_path = open_section(
            section_head,
            self.datadic,
            self.loop_vars,
            self.parse_opts,
            create_missing,
            path=self.current_path,
            logger=self.logger,
        )
        section_body = get_child(tree, "section_body")
        initialize_working_vars(self.datadic)
        self.run_instruction(section_body)
        remove_working_vars(self.datadic)
        self.datadic = close_section(section_head, self.datadic, logger=self.logger)
        self.current_path = previous_path

    def process_for_loop(self, tree):
        if self.rwmode == "write":
            for_head = get_child(tree, "for_head")
            self.logbuffer.save_reduced_record_log(for_head)
        return cycle_for_loop(
            tree,
            self.run_instruction,
            self.datadic,
            self.loop_vars,
            self.parse_opts,
            logger=self.logger,
        )

    def process_repeat_loop(self, tree):
        if self.rwmode == "write":
            repeat_head = get_child(tree, "repeat_head")
            self.logbuffer.save_reduced_record_log(repeat_head)
        return cycle_repeat_loop(
            tree,
            self.run_instruction,
            self.datadic,
            self.loop_vars,
            self.parse_opts,
            logger=self.logger,
        )

    def process_if_clause(self, tree):
        evaluate_if_clause(
            tree,
            self.datadic,
            self.loop_vars,
            self.parse_opts,
            self.run_instruction,
            set_parser_state=self.set_parser_state,
            get_parser_state=self.get_parser_state,
            logger=self.logger,
        )

    def process_abbreviation(self, tree):
        introduce_abbreviation(tree, self.datadic)

    def run_instruction(self, tree):
        if tree.data in self.endf_actions:
            if should_proceed(self.datadic, self.loop_vars, action_type="endf_action"):
                self.endf_actions[tree.data](tree)
                if self._numpy_forms is not None:
                    marks = getattr(tree, "_np_marks", None)
                    if marks is not None and "__lookahead" not in self.loop_vars:
                        mark_assignments(self._numpy_forms, self.datadic, marks)
        elif tree.data in self.meta_actions:
            if should_proceed(self.datadic, self.loop_vars, action_type="meta_action"):
                self.meta_actions[tree.data](tree)
        else:
            for child in tree.children:
                if is_tree(child):
                    if should_proceed(
                        self.datadic, self.loop_vars, action_type="unspecified"
                    ):
                        self.run_instruction(child)
                    else:
                        break

    def reset_parser_state(self, rwmode="read", lines=None, datadic=None):
        self.loop_vars = {}
        datadic = datadic if datadic is not None else {}
        lines = lines if lines is not None else []
        self.loop_vars = {"__ofs": 0}
        self.datadic = datadic
        self.lines = lines
        self.rwmode = rwmode
        self.ofs = 0
        self.logbuffer = RingBuffer(capacity=20)
        self.current_path = None

    def get_parser_state(self):
        return {
            "loop_vars": self.loop_vars,
            "datadic": self.datadic,
            "lines": self.lines,
            "rwmode": self.rwmode,
            "ofs": self.ofs,
            "logbuffer_state": self.logbuffer.dump_state(),
            "parse_opts": self.parse_opts,
            "current_path": self.current_path,
        }

    def set_parser_state(self, parser_state):
        self.loop_vars = parser_state["loop_vars"]
        self.datadic = parser_state["datadic"]
        self.lines = parser_state["lines"]
        self.rwmode = parser_state["rwmode"]
        self.ofs = parser_state["ofs"]
        self.logbuffer.load_state(parser_state["logbuffer_state"])
        self.parse_opts = parser_state["parse_opts"]
        self.current_path = parser_state["current_path"]

    def should_skip_section(self, mf, mt, exclude=None, include=None):
        if include is not None:
            if isinstance(include, int):
                include = (include,)
            include = tuple(tuple(p) if hasattr(p, "__iter__") else p for p in include)
        if exclude is not None:
            if isinstance(exclude, int):
                exclude = (exclude,)
            exclude = tuple(tuple(p) if hasattr(p, "__iter__") else p for p in exclude)

        if exclude is None:
            if include is not None:
                if mf not in include and (mf, mt) not in include:
                    return True
        # exclude not None
        else:
            if mf in exclude:
                return True
            elif (mf, mt) in exclude:
                return True
        return False

    def parse(self, lines, exclude=None, include=None, nofail=False):
        """Parse ENDF-6 formatted data.

        Parameters
        ----------
        lines : Union[str, list[str]]
            The lines of text containing the ENDF-6 formatted data.
            This argument can be either a list of strings with each
            string storing a single line, or a string containing
            all ENDF-6 formatted data including linebreaks.
        exclude : Union[None, tuple[Union[int, tuple[int, int]]]]
            See explanation of parameter ``exclude`` in
            :func:`parsefile` for details.
        include : Union[None, tuple[Union[int, tuple[int, int]]]]
            See explanation of parameter ``include`` in
            :func:`parsefile` for details.
        nofail : bool
            See explanation of parameter ``nofail`` in
            :func:`parsefile` for details.
        """
        if isinstance(lines, str):
            lines = lines.split("\n")
        self._remove_array_state_opts()
        array_type = self.parse_opts["array_type"]
        self.parse_opts["internal_array_type"] = (
            "list" if array_type == "list_slow" else "dict"
        )
        numpy_mode = array_type == "numpy"
        # the elements of nested arrays are created where the C++ code
        # creates them (see numpy_arrays), unless the recipe cannot be
        # annotated (see _annotate_tree)
        if numpy_mode:
            import numpy

            keep_floats = self.read_opts["preserve_value_strings"]
            self.parse_opts["numpy_marks"] = True
            self.parse_opts["numpy_keep_floats"] = keep_floats
        tree_dic = self.tree_dic
        self.variable_descriptions = EndfDict()
        mfmt_dic = split_sections(lines, read_opts=self.read_opts)
        for mf in mfmt_dic:
            if self.logger.isEnabledFor(logging.INFO):
                write_info(self.logger, f"Parsing section MF{mf}")
            for mt in mfmt_dic[mf]:
                cur_ctrl = read_ctrl(mfmt_dic[mf][mt][0], read_opts=self.read_opts)
                if self.logger.isEnabledFor(logging.INFO):
                    write_info(self.logger, f"Parsing subsection MF/MT {mf}/{mt}")
                curlines = mfmt_dic[mf][mt]
                cur_tree = get_responsible_recipe_parsetree(tree_dic, mf, mt)
                cur_parsefun = get_responsible_recipe_parsefun(
                    self.parsing_funs, mf, mt
                )
                should_skip = self.should_skip_section(mf, mt, exclude, include)
                if cur_parsefun is not None and not should_skip:
                    try:
                        curlines += write_send(
                            cur_ctrl, with_ctrl=True, write_opts=self.write_opts
                        )
                        curlines = "".join(curlines)
                        cur_dict = cur_parsefun(curlines)
                        cur_dict.update(cur_ctrl)
                        mfmt_dic[mf][mt] = cur_dict
                    except Exception as exc:
                        raise type(exc)(
                            f"parsing function for MF={mf}/MT={mt} failed "
                            + "with error message:\n"
                            + str(exc)
                        )
                elif cur_tree is not None and not should_skip:
                    # we add the SEND line so that parsing fails
                    # if the MT section cannot be completely parsed
                    curlines += write_send(
                        cur_ctrl, with_ctrl=True, write_opts=self.write_opts
                    )
                    self.reset_parser_state(rwmode="read", lines=curlines)
                    self.current_path = EndfPath((mf, mt))
                    if _annotate_tree(cur_tree, raise_error=numpy_mode):
                        array_forms = {}
                        self.parse_opts["array_forms"] = array_forms
                        if numpy_mode:
                            self._numpy_forms = array_forms
                    else:
                        array_forms = {}
                        self.parse_opts.pop("array_forms", None)
                    try:
                        initialize_working_vars(self.datadic)
                        self.datadic.update(cur_ctrl)
                        self.run_instruction(cur_tree)
                        remove_working_vars(self.datadic)
                        mfmt_dic[mf][mt] = self.datadic
                        if array_type == "list" or numpy_mode:
                            array_dict_to_list(mfmt_dic[mf][mt])
                        if array_type == "list":
                            fill_empty_elements(array_forms)
                        if numpy_mode:
                            convert_arrays(numpy, array_forms, keep_floats)
                    except ParserException as exc:
                        if not nofail:
                            logstr = self.logbuffer.display_record_logs()
                            self._remove_array_state_opts()
                            raise type(exc)(
                                "\nHere is the parser record log until failure:\n\n"
                                + logstr
                                + "Error message: "
                                + str(exc)
                            )
        self._remove_array_state_opts()
        return mfmt_dic

    def _remove_array_state_opts(self):
        # also called at the start of parse() and write(): these options
        # change how arrays are treated (see numpy_arrays), so they must
        # not linger if an error path of a previous call left them behind
        self.parse_opts.pop("internal_array_type", None)
        self.parse_opts.pop("array_forms", None)
        self.parse_opts.pop("numpy_marks", None)
        self.parse_opts.pop("numpy_keep_floats", None)
        self.parse_opts.pop("array_write", None)
        self._numpy_forms = None

    def write(self, endf_dic, exclude=None, include=None, zero_as_blank=False):
        """Convert data into the ENDF-6 format.

        All parameters are explained in the description of
        :func:`writefile`.

        Returns
        -------
        list[str]
            List of lines with the ENDF-6 formatted data.
        """
        if isinstance(endf_dic, EndfDict):
            endf_dic = endf_dic.unwrap()
        self.zero_as_blank = zero_as_blank
        self._remove_array_state_opts()
        array_type = self.parse_opts["array_type"]
        in_list_mode = array_type in ("list", "list_slow", "numpy")
        if in_list_mode:
            # numpy arrays and scalars are written like lists and
            # Python numbers with the same values
            endf_dic = numpy_to_python(endf_dic)
        self.parse_opts["internal_array_type"] = "list" if in_list_mode else "dict"
        if in_list_mode:
            # the start indices of nested arrays are those of their
            # elements created before loops when parsing (see numpy_arrays)
            self.parse_opts["array_forms"] = {}
            self.parse_opts["array_write"] = True
        self.reset_parser_state(rwmode="write", datadic={})
        self.variable_descriptions = EndfDict()
        should_check_arrays = self.write_opts["check_arrays"]
        tree_dic = self.tree_dic
        lines = []
        for mf in sorted(endf_dic):
            some_mf_output = False
            for mt in sorted(endf_dic[mf]):
                should_skip = self.should_skip_section(mf, mt, exclude, include)
                if should_skip:
                    continue
                cur_tree = get_responsible_recipe_parsetree(tree_dic, mf, mt)
                is_parsed = isinstance(endf_dic[mf][mt], Mapping)
                if cur_tree is not None and is_parsed:
                    if in_list_mode:
                        _annotate_tree(cur_tree)
                    datadic = endf_dic[mf][mt]
                    if should_check_arrays:
                        datadic = TrackingDict(datadic)
                    self.reset_parser_state(rwmode="write", datadic=datadic)
                    self.current_path = EndfPath((mf, mt))
                    datadic.setdefault("MF", mf)
                    if datadic["MF"] != mf:
                        raise UnexpectedControlRecordError(
                            f"expected MF={mf} but found MF={datadic['MF']}"
                        )
                    datadic.setdefault("MT", mt)
                    if datadic["MT"] != mt:
                        raise UnexpectedControlRecordError(
                            f"expected MT={mt} but found MT={datadic['MT']}"
                        )
                    try:
                        initialize_working_vars(self.datadic)
                        self.run_instruction(cur_tree)
                        remove_working_vars(self.datadic)
                    except Exception as exc:
                        logstr = self.logbuffer.display_reduced_record_logs()
                        errmsg = (
                            "\nHere is the parser record log until failure:\n"
                            + "--------------------------------------------\n"
                            + logstr
                            + "\n"
                            + "Error message: "
                            + str(exc)
                        )
                        if isinstance(
                            exc, (VariableNotFoundError, MissingSectionError)
                        ):
                            if self.explain_missing_variable:
                                if isinstance(exc, VariableNotFoundError):
                                    varpath = self.current_path + exc.varname
                                    eltype = "variable"
                                elif isinstance(exc, MissingSectionError):
                                    varpath = self.current_path + exc.section_name
                                    eltype = exc.section_type
                                explanation = self.explain(varpath, stdout=False)
                                if explanation is None:
                                    explanation = "No explanation available"
                                explain_header = (
                                    f"Explanation of missing {eltype} `{varpath}`"
                                )
                            errmsg += "\n\n" + explain_header + "\n"
                            errmsg += "-" * len(explain_header) + "\n"
                            errmsg += explanation
                        self._remove_array_state_opts()
                        raise type(exc)(errmsg)
                    # check if arrays have been written in their entirety
                    if should_check_arrays:
                        self.datadic.verify_complete_retrieval()
                    # add the NS number to the lines except last one
                    # because the SEND (=section end) record already
                    # contains it. For mf=0 (tape head), no SEND present
                    curlines = self.lines[:-1] if mf != 0 else self.lines
                    curlines = add_linenumbers_to_section(
                        curlines, write_opts=self.write_opts
                    )
                    # prepare the SEND (=section end) line
                    if mf != 0:
                        curline_send = self.lines[-1]
                        curlines.append(curline_send)
                    lines.extend(curlines)
                    # NOTE: the SEND record is part of the recipe
                    # and therefore will be added by the parser in
                    # process_send_line method. Hence there is no
                    # need to add it here, in contrast to the
                    # branch of the if-statement below to deal
                    # with non-parsable MF/MF sections.
                else:
                    # nothing is parsed here, but in the spirit of
                    # defensive coding, we reset the parser nevertheless
                    self.reset_parser_state(rwmode="write")
                    # if no recipe is available to parse a
                    # MF/MT section, it will be preserved as a
                    # list of strings in the parse step
                    # and we output that unchanged
                    curlines = endf_dic[mf][mt].copy()
                    curlines = add_linenumbers_to_section(
                        curlines, write_opts=self.write_opts
                    )
                    lines.extend(curlines)
                    # update the MAT, MF, MT number
                    self.datadic = read_ctrl(lines[-1], read_opts=self.read_opts)
                    # add the SEND record in between the MT subections
                    # if it was not a tape head record (mf=0)
                    if mf != 0:
                        lines.extend(
                            write_send(
                                self.datadic,
                                with_ctrl=True,
                                zero_as_blank=zero_as_blank,
                                write_opts=self.write_opts,
                            )
                        )
                some_mf_output = True
            # we output the file end (fend) record only if something has been written
            # to this mf section and it is not the tape head (mf=0)
            if some_mf_output and mf != 0:
                lines.extend(
                    write_fend(
                        self.datadic,
                        with_ctrl=True,
                        zero_as_blank=zero_as_blank,
                        write_opts=self.write_opts,
                    )
                )

        lines.extend(
            write_mend(
                with_ctrl=True,
                zero_as_blank=zero_as_blank,
                write_opts=self.write_opts,
            )
        )
        lines.extend(
            write_tend(
                with_ctrl=True,
                zero_as_blank=zero_as_blank,
                write_opts=self.write_opts,
            )
        )
        del self.zero_as_blank
        self._remove_array_state_opts()
        return lines

    def parsefile(self, filename, exclude=None, include=None, nofail=False):
        """Parse ENDF-6 formatted data stored in a file.

        Parameters
        ----------
        filename : str
            Path to the ENDF-6 file
        exclude : Union[None, tuple[Union[int, tuple[int, int]]]]
            MF/MT sections to exclude in the parsing process.
            Excluded sections will only be available as a list of strings.
            The default `None` indicates that nothing should be excluded.
            If a `tuple` is provided, integers in that tuple denote the
            `MF` sections to be excluded. In addition to integers,
            also tuples composed of two integers can be provided to
            indicate the `MF`/`MT` combinations that should be excluded.
            For instance, ``(3,)`` would exclude MF section 3 and
            ``(3, (2, 151))`` would exclude MF section 3 and additionally
            MF=2/MT=151.
            Useful to speed up the parsing process or to ensure
            a verbatim copy of data in a read/write sequence.
        include : Union[None, tuple[Union[int, tuple[int, int]]]]
            The MF/MT section to include in the parsing.
            All the other sections will be only present as a list of
            strings. This argument is only active if ``exclude=None``.
            The MF and MF/MT sections are specified exactly in the
            same way as for the ``exclude`` argument.
        nofail : bool
            If this argument is ``True``, the parser will attempt to
            parse *all* MF/MT sections desired by the user, irrespective
            of failure in the parsing of any section. Sections where
            parsing failed will only be available as list of strings.
            On the other hand, ``nofail=false`` instructs the parser
            to abort immediately upon the first parsing failure.

        Returns
        -------
        dict
            A nested dictionary. The keys of the first level are
            MF numbers and of the second level MT numbers.
            The structure of the :class:`dict` stored under a specific
            `MF`/`MT` combination is determined by the
            corresponding ENDF recipe.
        """
        with open(filename, "r") as fin:
            lines = fin.readlines()
        return self.parse(lines, exclude, include, nofail=nofail)

    def writefile(
        self,
        filename,
        endf_dic,
        exclude=None,
        include=None,
        zero_as_blank=False,
        overwrite=False,
    ):
        """Write data to an ENDF-6 file.

        Parameters
        ----------
        filename : str
            Path of the file to be created.
        endf_dic : dict
            Nested dictionary with nuclear data. Keys of first level
            are MF numbers and the keys of second level MT numbers.
            The structure of the :class:`dict` stored under an MF/MT combination
            depends on the corresponding ENDF recipe.
        exclude : Union[None, tuple[Union[int, tuple[int, int]]]]
            A section will only be written to the file if
            not excluded. For an explanation of how to specify
            MF/MT sections to be excluded, see the ``exclude`` argument
            of :func:`parsefile`.
        include : Union[None, tuple[Union[int, tuple[int, int]]]]
            This argument is only considered if ``exclude=None``.
            If this argument is ``None``, all sections will be written
            to the file. Otherwise, only the indicated sections will
            be written to the file. For an explanation of how to
            define which sections to include, see the ``include`` argument
            of :func:`parsefile`.
        overwrite : bool
            Existing files will only be overwritten if this argument
            is ``True``, otherwise this function will abort.
        """
        if file_exists(filename) and not overwrite:
            raise FileExistsError(
                f"file {filename} already exists. "
                "Change overwrite option to True if you "
                "really want to overwrite this file."
            )
        else:
            lines = self.write(endf_dic, exclude, include, zero_as_blank)
            # newline="" disables newline translation: the ENDF text is
            # written with LF on every platform, never CRLF on Windows
            with open(filename, "w", newline="") as fout:
                fout.write("\n".join(lines))


# DEPRECATED NAME


warnings.simplefilter("always", DeprecationWarning)


class BasicEndfParser(EndfParserPy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "The name of the Python parser class is now `EndfParserPy`. "
            "The alias `BasicEndfParser` should not be used anymore.",
            DeprecationWarning,
        )


class EndfParser(EndfParserPy):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        warnings.warn(
            "The name of the Python parser class is now `EndfParserPy`. "
            "The alias `EndfParser` should not be used anymore.",
            DeprecationWarning,
        )
