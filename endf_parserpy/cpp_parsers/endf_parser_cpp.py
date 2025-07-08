############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/05/29
# Last modified:   2025/07/08
# License:         MIT
# Copyright (c) 2024-2025 International Atomic Energy Agency (IAEA)
#
############################################################

import importlib
import os
from endf_parserpy.utils.accessories import EndfDict
from ..endf_parser_base import EndfParserBase


class EndfParserCpp(EndfParserBase):
    """Class for parsing and writing ENDF-6 formatted data.

    This class provides functions for (1) parsing ENDF-6 formatted
    data, and (2) converting data given in a :class:`dict` object
    into the ENDF-6 format.
    The ENDF-6 formatted data may be given in a text file, a string
    or a list of strings containing the individual lines. The essential
    methods of this class are :func:`parsefile` and :func:`writefile`.

    This class closely mirrors the functionality of the
    :class:`~endf_parserpy.EndfParserPy` class but relies
    on compiled functions for parsing and writing. Tests indicated
    that these functions are usually at least 50x faster than the
    corresponding functions in the
    :class:`~endf_parserpy.EndfParserPy` class and in some
    cases several hundred times faster.

    Please note that this class may not be usable if the compilation
    of the C++ module codes failed during package installation. Further
    note that most but not all options of the
    :class:`~endf_parserpy.endf_parser.EndfParserPy` class
    are implemented in this class.
    """

    def __init__(
        self,
        ignore_number_mismatch=False,
        ignore_zero_mismatch=True,
        ignore_varspec_mismatch=True,
        accept_spaces=True,
        ignore_blank_lines=False,
        ignore_send_records=False,
        ignore_missing_tpid=False,
        validate_control_records=False,
        abuse_signpos=False,
        keep_E=False,
        preserve_value_strings=False,
        include_linenum=True,
        array_type="dict",
        skip_intzero=False,
        prefer_noexp=False,
        endf_format="endf6-ext",
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
        abuse_signpos: bool
            Permit positive numbers to start in the first character slot
            of an ENDF-6 field, which is usually reserved for the sign,
            to enhance numerical precision. *(writing)*
        keep_E : bool
            If ```True```, include the `e` character in scientific notation,
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
        array_type : str
            The Python datatype to use for representing arrays read from
            ENDF-6 files. The two options are ``"dict"`` (default) and
            ``"list"``.  *(parsing)*
        skip_intzero: bool
            For numbers written out in decimal notation, eliminate
            the integer part if zero, e.g. `0.12` becomes `.12` to
            increase attainable precision. *(writing)*
        prefer_noexp: bool
            Switch to decimal representation (i.e. non-scientific) if it leads
            to an increase of accuracy, e.g. `1.234567-1` becomes `0.12345678`.
            *(writing)*
        endf_format : str
            Allow the user to pick specific ENDF format flavors.
            The default `endf6-ext` tolerates deviations from the
            ENDF-6 format encountered in some nuclear data libraries.
            Other choices are `endf6` for strict compliance with the
            ENDF-6 formats manual and `jendl` with JENDL specific
            conventions, which are also implemented in `endf6-ext`.
        """
        self.read_opts = {
            "ignore_number_mismatch": ignore_number_mismatch,
            "ignore_zero_mismatch": ignore_zero_mismatch,
            "ignore_varspec_mismatch": ignore_varspec_mismatch,
            "accept_spaces": accept_spaces,
            "ignore_blank_lines": ignore_blank_lines,
            "ignore_send_records": ignore_send_records,
            "ignore_missing_tpid": ignore_missing_tpid,
            "preserve_value_strings": preserve_value_strings,
            "validate_control_records": validate_control_records,
            "array_type": array_type,
        }
        self.write_opts = {
            "abuse_signpos": abuse_signpos,
            "keep_E": keep_E,
            "include_linenum": include_linenum,
            "skip_intzero": skip_intzero,
            "prefer_noexp": prefer_noexp,
            "preserve_value_strings": preserve_value_strings,
            "array_type": array_type,
        }
        subpackage = "endf_parserpy.cpp_parsers"
        endf_format = endf_format.replace("-", "_")
        # import the parsing functions
        try:
            self._parse_endf = self._dynamic_import(
                f"{subpackage}.{endf_format}", "parse_endf"
            )
            self._parse_endf_file = self._dynamic_import(
                f"{subpackage}.{endf_format}", "parse_endf_file"
            )
            self._write_endf = self._dynamic_import(
                f"{subpackage}.{endf_format}", "write_endf"
            )
            self._write_endf_file = self._dynamic_import(
                f"{subpackage}.{endf_format}", "write_endf_file"
            )
        except ImportError as exc:
            raise type(exc)(
                "Unable to import the cpp module responsible "
                + "for parsing and reading ENDF-6 files. "
                + "Probably the module could not be compiled "
                + "during package installation. Please use the "
                + "EndfParserPy class instead."
            ) from exc

    def _dynamic_import(self, module_name, attribute_name):
        module = importlib.import_module(module_name)
        if attribute_name:
            return getattr(module, attribute_name)
        return module

    def parse(self, lines, exclude=None, include=None):
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

        Returns
        -------
        dict
            See explanation in :func:`parsefile`.
        """
        if isinstance(lines, list):
            lines = "\n".join(lines)
        return self._parse_endf(lines, exclude, include, self.read_opts)

    def parsefile(self, filename, exclude=None, include=None):
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

        Returns
        -------
        dict
            A nested dictionary. The keys of the first level are
            MF numbers and of the second level MT numbers.
            The structure of the :class:`dict` stored under a specific
            `MF`/`MT` combination is determined by the
            corresponding ENDF recipe.
        """
        return self._parse_endf_file(str(filename), exclude, include, self.read_opts)

    def write(self, endf_dict, exclude=None, include=None):
        """Convert data into the ENDF-6 format.

        All parameters are explained in the description of
        :func:`writefile`.

        Returns
        -------
        list[str]
            List of lines with the ENDF-6 formatted data.
        """
        if isinstance(endf_dict, EndfDict):
            endf_dict = endf_dict.unwrap()
        cont = self._write_endf(endf_dict, exclude, include, self.write_opts)
        lines = cont.split("\n")
        if lines[-1] == "":
            lines.pop()
        return lines

    def writefile(
        self, filename, endf_dict, exclude=None, include=None, overwrite=False
    ):
        """Write data to an ENDF-6 file.

        Parameters
        ----------
        filename : str
            Path of the file to be created.
        endf_dict : dict
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
        if isinstance(endf_dict, EndfDict):
            endf_dict = endf_dict.unwrap()
        if os.path.exists(filename) and not overwrite:
            raise FileExistsError(
                f"File `{filename}` already exists. "
                "Change overwrite option to True if you "
                "really want to overwrite this file."
            )
        return self._write_endf_file(
            str(filename), endf_dict, exclude, include, self.write_opts
        )
