.. _format_validation_sec:


ENDF-6 Format Validation
========================

.. _ENDF-6 format specification: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf

A contributor to a nuclear data library project
wants to be sure that their ENDF-6 file conforms
with the `ENDF-6 format specification`_.
Format validation with the ``endf_parserpy`` package
is very simple. If an attempt to read an ENDF-6 file
with strict validation settings fails,
the file does not comply with the ENDF-6 format standard.

.. note::

   Successful format validation does not mean
   that the file is sensible from the physics point
   of view. Issues, such as negative cross sections
   or a violation of sum rules, can still be present
   in a properly formatted ENDF-6 file.


The following code snippet exemplifies how to read an
ENDF-6 file with strict validation settings:

.. code::

   from endf_parserpy import EndfParserPy

   parser = EndfParserPy(
       ignore_number_mismatch=False,
       ignore_zero_mismatch=False,
       ignore_varspec_mismatch=False,
       fuzzy_matching=False,
       accept_spaces=False,
       ignore_blank_lines=False,
       ignore_send_records=False,
       ignore_missing_tpid=False,
       accept_nan_inf=False,
       accept_d_exponent=False,
       accept_non_ascii=False,
    )

    parser.parsefile('input.endf')

For an explanation of the arguments,
consult the :ref:`detailed documentation <endf_parser_class>` of
the EndfParserPy class.

For routine validation from the shell, the ``endf-cli validate``
subcommand applies the same strict defaults out of the box, so the
above is equivalent to::

   endf-cli validate input.endf

See :ref:`command_line_interface` for details, including how to
relax individual flags on the command line.

If the :func:`~endf_parserpy.EndfParserPy.parsefile` method fails,
it provides detailed output to facilitate locating
the issue. Let's look at an example output of
:func:`~endf_parserpy.EndfParserPy.parsefile`
in the case of a format violation:


.. code::

    endf_parserpy.custom_exceptions.InvalidIntegerError:
    Here is the parser record log until failure:

    -------- Line 0 -----------
    Template:  [ MAT , 4 , MT / ZA , AWR , 0 , LTT , 0 , 0 ] HEAD
    Line:     " 6.415500+4 1.535920+2          1          1          0          06434 4  2    1"

    -------- Line 1 -----------
    Template:  [ MAT , 4 , MT / 0.0 , AWR ? , LI , LCT , 0 , 0 ] CONT
    Line:     " 0.000000+0 1.535920+2          0          2        441         206434 4  2    2"

    -------- Line 2 -----------
    Template:  [ MAT , 4 , MT / 0.0 , 0.0 , 0 , 0 , NR , NE / Eint ] TAB2
    Line:     " 1.000000+0 4.340500-3 8.478030-6-9.08196-19 0.000000+0 0.000000+06434 4  2    3"

    Error message: invalid literal for int() with base 10: ' 8.478030-6'


This output tells us that the parser expected an integer but received something
that looks like a float. The output further shows the lines encountered in the
ENDF-6 file (after ``Line:``) and which lines of an :ref:`ENDF-6 recipe <endf6_recipe_sec>`
(after ``Template:``) they are supposed to match.

The last line printed out (``Line 2``) caused the failure.
From the last three numbers displayed in the string after ``Line:``,
we see that the issue occured in the third line of an MF=4/MT=2 section.
The comparison of the template with the actual line of the ENDF-6 recipe
tells us that the ENDF record encountered is incompatible with the recipe
specification for several reasons.
The first two slots (behind the slash) are supposed to be zero according
to the ENDF-6 recipe but non-zero values are present in the file.
Further, the next four slots are supposed to be of type ``int``
but float numbers are present in the file.

If the format violation can be fixed by a few modifications in a text
editor, you could now search in the ENDF-6 file for some substring of the
string displayed after ``Line:``. In the case of this example,
however, the problem is more complex and appeared because the file
contained a sequence of extra ENDF records whose presence is no
longer supported by the current ENDF-6 format standard. Locating such
issues requires strong knowledge of the format and some detective
skills. However, if you :ref:`create ENDF-6 files from scratch
<create_endf_file_sec>` with the endf-parserpy package, you will obtain a
correctly formatted file by design.


.. _tolerated_mismatches_sec:

Tolerated mismatches
--------------------

With their default options, both parsers accept some values that differ
from the values given by the ENDF-6 recipe:

- ``ignore_zero_mismatch=True``: a value other than zero in a field given
  as ``0`` or ``0.0`` in the recipe (kind ``zero``);
- ``ignore_varspec_mismatch=True``: a value of a variable marked with
  ``?`` in the recipe, e.g. ``AWR?``, that differs from the value read
  before (kind ``varspec``);
- ``ignore_number_mismatch=True`` (``False`` by default): a value other
  than a desired number such as ``0.0?`` (kind ``number``).

The values found in these fields are not kept, so that writing the data
gives the values expected by the recipe instead. Each call of
:func:`~endf_parserpy.EndfParserPy.parse` or
:func:`~endf_parserpy.EndfParserPy.parsefile` (of
:class:`~endf_parserpy.EndfParserPy` as of
:class:`~endf_parserpy.EndfParserCpp`) that tolerates mismatches issues
one :class:`~endf_parserpy.EndfToleratedMismatchWarning` at its end. The
warning gives the number of mismatches of each kind and lists them
grouped by material, section, field (and variable) and kind, each group
with the number of its mismatches and the first of them, i.e. the line
of the input and the expected and the found value. A long list is
truncated after ten groups. The text is the same for both parsers, e.g.
for ``n-092_U_238.endf`` of ENDF/B-VIII.1:

.. code:: text

   7 field mismatches tolerated in n-092_U_238.endf (zero: 7
   (ignore_zero_mismatch)), in 2 groups; the values found are not kept,
   writing the data gives the expected values:
     MAT 9237 MF34/MT2 N1: 5 zero mismatches, e.g. line 162657: expected 0, found 1
     MAT 9237 MF34/MT51 N1: 2 zero mismatches, e.g. line 164012: expected 0, found 1

(the first line is a single line in the warning). A mismatch found while
the parser looks ahead to decide which branch of the recipe applies is
not counted; only the record as finally read is. A parse that fails with
an error gives no warning. :class:`~endf_parserpy.EndfFile` parses the
sections one by one and issues a warning for each section with
mismatches when it is parsed, and the tape functions such as
:func:`~endf_parserpy.parse_tape_file` one for each material; their line
numbers are those of the file.

The warning can be filtered with the :mod:`warnings` module, e.g. to
turn it into an error or to silence it:

.. code:: Python

   import warnings
   from endf_parserpy import EndfParserCpp, EndfToleratedMismatchWarning

   parser = EndfParserCpp()
   with warnings.catch_warnings():
       warnings.simplefilter("error", EndfToleratedMismatchWarning)
       endf_dict = parser.parsefile("input.endf")

   warnings.filterwarnings("ignore", category=EndfToleratedMismatchWarning)

The attribute ``mismatches`` of the warning holds the mismatches as
:class:`~endf_parserpy.utils.tolerated_mismatches.ToleratedMismatch`
records, e.g. for a survey of a library:

.. code:: Python

   with warnings.catch_warnings(record=True) as caught:
       warnings.simplefilter("always", EndfToleratedMismatchWarning)
       parser.parsefile("input.endf")
   for w in caught:
       for m in w.message.mismatches:
           print(m.mf, m.mt, m.field, m.kind, m.line, m.expected, m.found)

With the strict options shown above, a mismatch is an error, not a
warning. :class:`~endf_parserpy.EndfParserPy` logs the details of each
tolerated mismatch (message, record template and line) at the level
``logging.DEBUG``.
