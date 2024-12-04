.. _guide_perfect_precision:

Perfect Precision Control
=========================

Various parser options exist to define globally the
output format of float numbers, which were covered
in the section on :ref:`Writing ENDF files <writing_endf_file_subsec>`.
They are typically used to avoid precision loss
in a read/write operation in cases where the original ENDF file
adopts an unconventional number format.
However, as these options apply globally, even numbers
formatted according to common convention
(e.g. ``1.234567-8``) are potentially written out in
a different style. For these cases, it would be a more
satisfying approach to keep the numbers as they were
encountered in the source ENDF file.
With this approach, :ref:`comparisons <guide_file_comparison>`
between source and target ENDF files to ensure no precision was lost
become unnecessary.

The ``endf-parserpy`` package can keep track
of the string representation of any float number read from an ENDF file
and it also permits the user to use a custom string representation for
any float number written to an ENDF file. In the following, we explain
in more detail how these capabilities can be used.

Keeping track of float strings while reading
--------------------------------------------

To keep track of string representations of float numbers while
reading an ENDF file, we need to initialize the
:class:`~endf_parserpy.EndfParser` class with the
``preserve_value_strings=True`` option:

.. code:: Python

   from endf_parserpy import EndfParser
   parser = EndfParser(preserve_value_strings=True)


Using this option, all :class:`float` numbers will be stored
as :class:`~endf_parserpy.EndfFloat` objects
in the dictionary obtained by the :func:`~endf_parserpy.EndfParser.parsefile`
or :func:`~endf_parserpy.EndfParser.parse` method, e.g.

.. code:: Python

   endf_dict = parser.parsefile('input.endf')

The string representation of an :class:`~endf_parserpy.EndfFloat` object
can be retrieved by using the :func:`~endf_parserpy.EndfFloat.get_original_string` method.
For example, for the ``AWR`` variable stored in MF1/MT451:

.. code:: Python

   endf_float_obj = endf_dict[1][451]['AWR']
   endf_float_obj.get_original_string()

Importantly, even though :class:`~endf_parserpy.EndfFloat` objects
represent :class:`float` numbers, they can't be used in arithmetic
operations. Trying to do so will yield an error message.
This limitation is a design feature to prevent the user or any
processing script to inadvertently break the association with the
original string representation. If the float values represented
by :class:`~endf_parserpy.EndfFloat` objects should enter arithmetic
expressions, they must be explicilty converted to :class:`float` types:

.. code:: Python

   float_number = float(endf_float_obj)


Comparisons between :class:`~endf_parserpy.EndfFloat` objects and  Python numeric datatypes
:class:`float` and :class:`int` will work without problems, though. Here are a few examples:

.. code:: Python

   from endf_parserpy import EndfFloat
   endf_float_obj = EndfFloat(7, '7')
   assert endf_float_obj == 7
   assert 3 <= endf_float_obj
   assert endf_float_obj < 10


Perfect precision control for writing
-------------------------------------

Writing an ENDF file is **not** influenced by the
``preserve_value_strings`` parameter of the
:class:`~endf_parserpy.EndfParser` constructor but only depends
on whether a :class:`float` is represented as an
:class:`~endf_parserpy.EndfFloat` object or not.
For instance, when writing ENDF formatted data via the
:func:`~endf_parserpy.EndfParser.writefile` method,

.. code:: Python

   parser.writefile('output.endf', endf_dict)

the parser will *always* use the original string representation
if a :class:`float` value is represented by an :class:`~endf_parserpy.EndfFloat`
object. On the other hand, values represented by the :class:`float` Python data type
will be formatted according to the global formatting options, such as ``prefer_noexp``,
explained in the section on :ref:`Writing ENDF files <writing_endf_file_subsec>`.

Importantly, this means that no precision is lost in a read/write sequence such as the
following, as the original string representations are copied verbatim into the target
ENDF File:

.. code:: Python

   from endf_parserpy import EndfParser
   parser = EndfParser(preserve_value_strings=True)
   endf_dict = parser.parsefile('input.endf')
   parser.writefile('output.endf', endf_dict)


Finally, if one wants to modify a number in an ENDF file and control the
string formatting oneself, one can create an :class:`~endf_parserpy.EndfFloat` object
and assign it to the appropriate place in a nested ENDF dictionary.
For example, the following code snippet demonstrates this for the
assignment of a number to the ``AWR`` variable:

.. code:: Python

   from endf_parserpy import EndfFloat
   A = 56  # mass and charge number
   Z = 26  # for iron-56
   ZA = 1000.0*Z + A
   endf_dict[1][451]['AWR'] = EndfFloat(ZA, "26056".rjust(11))
   parser.writefile('output.endf', endf_dict)


Using default options during the :class:`~endf_parserpy.EndfParser` object initialization,
the ``AWR`` variable would be written as ``2.605600+4``.
However, the storage as an :class:`~endf_parserpy.EndfFloat` object
with the string representation explicitly stated ensures that
it is written as ``26056`` right-aligned in the appropriate
11-character slot field.

.. note::

   During the creation of an :class:`~endf_parserpy.EndfFloat` object,
   no checking is performed whether the provided string qualifies as
   a syntactic valid number.
