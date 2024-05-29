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

   from endf_parserpy import EndfParser

   parser = EndfParser(
       ignore_number_mismatch=False,
       ignore_zero_mismatch=False,
       ignore_varspec_mismatch=False,
       fuzzy_matching=False,
       accept_spaces=False
    )

    parser.parsefile('input.endf')

For an explanation of the arguments,
consult the :ref:`detailed documentation <endf_parser_class>` of
the EndfParser class.

If the :func:`~endf_parserpy.EndfParser.parsefile` method fails,
it provides detailed output to facilitate locating
the issue. Let's look at an example output of
:func:`~endf_parserpy.EndfParser.parsefile`
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
