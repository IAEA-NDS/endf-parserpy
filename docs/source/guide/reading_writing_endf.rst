.. _ENDF-6 formats manual: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf

Reading & Writing ENDF-6
========================

A typical workflow with an ENDF-6 file
involves reading the data into a Python dictionary,
performing some actions on the data
and finally writing the modified data
to a new ENDF-6 file. On this page,
we explain how to read and write ENDF-6 data
along with some considerations to be heeded.

Reading an ENDF-6 file
------------------------

An ENDF-6 file can be read with the :func:`~endf_parserpy.EndfParserPy.parsefile()`
method of the :class:`~endf_parserpy.EndfParserPy` class:

.. code:: Python

   from endf_parserpy import EndfParserPy
   parser = EndfParserPy()
   endf_dict = parser.parsefile('input.endf')


The variable ``endf_dict`` is a dictionary (:class:`dict`) in which
all quantities are associated with the symbol names
described in the `ENDF-6 formats manual`_.
The data organization within this dictionary is determined by
:ref:`ENDF-6 recipes <endf6_recipe_sec>`.
An :class:`~endf_parserpy.EndfDict` object,
instantiated by
``view_dict = EndfDict(endf_dict)``, can facilitate
:ref:`data navigation <data_navigation>`.

The parsing process can be influenced by using additional
arguments in the instantiation of the
:class:`~endf_parserpy.EndfParserPy` class.
The default choices of these arguments are forgiving so that
even ENDF-6 files that do not strictly comply with the ENDF-6
format can be read without failure. For the purpose of
:ref:`format validation <format_validation_sec>`, one would
adopt parameters to enforce strict compliance with the ENDF-6 format.

The only argument that is relevant for reading is ``accept_spaces``
whose default is ``True``. With this default, numbers with spaces inserted
will be accepted, such as ``1.234 +3``. However, even ENDF-6 files
with some numbers leaking into neighboring fields may be successfully
read then, but with nonsensical values. Because this issue can be easily
missed by the user, it may be a good idea to enforce failure in such a
situation by adopting the following initialization:

.. code:: Python

   parser = EndfParserPy(accept_spaces=False)


When only one part of the ENDF-6 file is relevant to the user,
the :func:`~endf_parserpy.EndfParserPy.parsefile()` method
can be instructed to only parse
this part for greater speed. For instance, if you are only interested
in MT sections within MF=3,4,5 sections, you can use:

.. code:: Python

   endf_dict = parser.parsefile('input.endf', include=[3, 4, 5])

In the resulting dictionary, only the subdictionaries associated
with the included MF numbers contain keys named according to
symbol names as described in the ENDF-6 manual.
The objects associated with the other MF numbers are lists of
strings with the raw content of the ENDF-6 file, e.g.
``type(endf_dict[6][2]) == list``. Instead of ``include``, you can
also use the ``exclude`` argument, e.g.

.. code:: Python

   endf_dict = parser.parsefile('input.endf', exclude=[3, 4, 5])

to parse everything except MF=3,4,5. Both inclusion and exclusion
can be performed more fine-grained at the level of MT sections.
For example, to include everything of MF=6 and only MT=1 from MF=3,
specify ``include=[6, [3, 1]]``.

If one wants to check which MF/MT sections have been parsed,
one can utilize the
:func:`~endf_parserpy.list_parsed_sections` and
:func:`~endf_parserpy.list_unparsed_sections` function,
respectively:

.. code:: Python

   from endf_parserpy import list_parsed_sections
   from endf_parserpy import list_unparsed_sections
   list_parsed_sections(endf_dict)
   list_unparsed_sections(endf_dict)

.. _writing_endf_file_subsec:

Writing an ENDF-6 file
----------------------

Writing an ENDF-6 file is as simple as reading one.
Assume that the dictionary ``endf_dict`` is of appropriate
structure, e.g., as returned by the
:func:`~endf_parserpy.EndfParserPy.parsefile` method.
The following code snippet demonstrates writing:

.. code:: Python

   from endf_parserpy import EndfParserPy
   parser = EndfParserPy()
   parser.writefile('output.endf', endf_dict)

Also the :func:`~endf_parserpy.EndfParserPy.writefile`
method supports the
``include`` and ``exclude`` argument. If the
``include`` argument is provided, only included
MF/MT sections will be written to the file.
Similarly, if ``exclude`` is provided, only all
non-excluded sections will be written.

If data in the ``endf_dict`` dictionary
have been added or deleted, it is important to
update the directory listing in MF1/MT451 first
before writing to an ENDF-6 file (see :endf6manshort:`57`).
This can be achieved with the
:func:`~endf_parserpy.update_directory` function.

.. code:: Python

   from endf_parserpy import update_directory
   update_directory(endf_dict, parser)

.. note::

   Don't use the ``include`` and ``exclude`` argument
   of the :func:`~endf_parserpy.EndfParserPy.writefile` method
   if it is important that the ENDF directory in MF1/MT451 is in sync with
   the file. Rather remove the sections manually before the
   invocation of :func:`~endf_parserpy.update_directory`.


Finally, we want to discuss how to control the **output precision**
of numerical data. The ENDF-6 format only provides eleven
character slots for the representation of numbers,
limiting the achievable precision. By default, numbers are written
in a specific floating point notation that appears to be commonly adopted
by nuclear data library projects. This notation is of the form
``␣1.234567+8``, with the first character slot being reserved
for a potential minus sign and skipping the ``e``, which would
usually be included to indicate the start of the exponent.

If more output precision is required, several options are available
to tweak the output format, which can be passed as arguments
to the constructor of the :class:`~endf_parserpy.EndfParserPy` class.
With ``abuse_signpos=True``, positive numbers
are allowed to consume the first character slot usually
reserved for the sign.
The argument ``prefer_noexp=True`` will switch to a decimal
notation (i.e. without exponent) if the number can be
represented with more significant digits. The choice
``skip_intzero=True`` will skip the zero of a number
in decimal notation if the integer part is zero, e.g.,
``0.1234`` will become ``.12345``, giving in some situations
one extra digit of precision.
Therefore, for maximal output precision (and ugly display)
initialize the :class:`~endf_parserpy.EndfParserPy` instance like this:

.. code::

   parser = EndfParserPy(abuse_signpose=True, prefer_noexp=True, skip_intzero=True)


If you want to increase compatibility with programming
languages different from Fortran that don't accept the omission
of the ``e`` character in the scientific notation of a number,
include the argument ``keep_E=True``.

Finally, if you want to ensure that you haven't
lost (too much) precision, you can make use of the
:func:`~endf_parserpy.compare_objects` function.
Just read the output file again, and compare it with
the original ``endf_dict``:


.. code:: Python

   from endf_parserpy import compare_objects

   test_dict = parser.parsefile('output.endf')
   compare_objects(endf_dict, test_dict, atol=1e-6, rtol=1e-6, fail_on_diff=False)
