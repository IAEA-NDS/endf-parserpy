.. _arrays_as_list_sec:


Arrays as Lists
===============

One early design choice for the development of
endf-parserpy was to represent arrays
stored in an ENDF file as Python :class:`dict`.
For example, consider the following
:ref:`recipe <endf6_recipe_sec>`
snippet:

.. code:: text

    for i=1 to 3:
        [MAT, 1,451/ HSUB[i]] TEXT
    endfor

The strings associated with the ``HSUB`` array
will be stored in a dictionary under keys 1, 2, 3.
In this way, the index ranges in the data structure
are perfectly aligned with the recipe definition.
The perfect correspondence, however, comes with the
disadvantage that the :ref:`manipulation of array data <modifying_arrays_sec>`
is a bit more cumbersome than necessary. Furthermore,
the arrays associated with TAB1 and TAB2 records,
e.g. ``INT`` and ``NBT``, are stored as :class:`list`,
and having two different data types for arrays is
somewhat confusing.

Therefore, an option has been implemented to
represent all arrays as :class:`list`, which can
be enabled by passing the ``array_type="list"`` argument
to the constructor of the :class:`~endf_parserpy.EndfParserPy`
class:

.. code:: python

   from endf_parserpy import EndfParserPy
   parser = EndfParserPy(array_type="list")

Using this option, The :func:`~endf_parserpy.EndfParserPy.parse` and
:func:`~endf_parserpy.EndfParserPy.parsefile` methods will
return dictionaries in which  *all* arrays are stored as :class:`list`.
Analogously for writing via the :func:`~endf_parserpy.EndfParserPy.writefile` and
:func:`~endf_parserpy.EndfParserPy.write`
methods, the dictionaries with ENDF data are expected to
contain *all* arrays as :class:`list`.

If you are using the ``array_type="list"`` option, be aware of the following:

- ENDF data loaded into a dictionary
  using a parser object initialized with ``EndfParserPy(array_type="list"``
  can't be written to an ENDF file with a parser object initialized with
  ``EndfParserPy(array_type="dict")`` and vice-versa. It is recommended to
  choose one parser mode and use it consistently throughout a project.
- An inner array without elements, e.g. the Legendre coefficients
  ``al[i]`` of an MF4 incident energy with ``NL[i]=0``, is an empty list
  in list mode, whereas it is absent in dict mode.
- :ref:`EndfPath notation <endf_path_class>` and the
  :ref:`EndfDict <endf_dict_class>` class can also be used with
  ENDF dictionaries in list mode. However, all arrays and sections are
  then zero-based, irrespective of the loop start and stop limits
  stated in the ENDF recipes. For instance, the EndfPath to refer to
  the first element of ``HSUB`` above (being part of an MF1/MT451 section)
  is given by ``1/451/HSUB/0`` if using ``array_type="list"`` whereas it
  would be ``1/451/HSUB/1`` if using ``array_type="dict"``.
- If you make use of the :ref:`EndfDict <endf_dict_class>` class,
  especially if you want to manipulate ENDF data through it, ensure
  to initialize it with the ``array_type="list"`` argument, e.g.,
  ``endf_dict = EndfDict(orig_endf_dict, array_type="list")``.
  If you forget this extra argument, intuitive assignments, such as
  ``endf_dict['1/451/MOD/3'] = 4`` won't work and will yield an error message.


.. _arrays_as_numpy_sec:

Arrays as numpy arrays
----------------------

The :class:`~endf_parserpy.EndfParserCpp` and
:class:`~endf_parserpy.EndfParserPy` classes additionally
support the option ``array_type="numpy"``, which requires the
`numpy <https://numpy.org>`_ package. Arrays are then indexed in the
same way as with ``array_type="list"``, i.e., zero-based, but arrays
of numbers are returned as numpy arrays. The C++ parser creates them
in a single step instead of element by element, which is faster for
large arrays:

.. code:: python

   from endf_parserpy import EndfParserCpp
   parser = EndfParserCpp(array_type="numpy")
   endf_dict = parser.parsefile("n_2925_29-Cu-63.endf")
   xstable = endf_dict[3][1]["xstable"]
   xstable["xs"]   # numpy array of dtype float64
   xstable["NBT"]  # numpy array of dtype int64

The type of each array depends only on the recipe, the parser options
and the format flags of the record that holds it (such as ``LS`` below),
never on the numerical values:

- Arrays of floats, including the columns of TAB1 records, are
  ``float64`` arrays, and arrays of integers, such as ``NBT`` and
  ``INT``, are ``int64`` arrays.
- A matrix that occupies a rectangular block of a record, e.g.
  the covariance matrix ``F`` of an MF33 subsection with ``LB=5`` and
  ``LS=0``, is a two-dimensional array. A triangular matrix, e.g. ``F``
  with ``LB=5`` and ``LS=1``, is a list of one-dimensional arrays, one
  per row.
- Arrays of arrays, e.g. the Legendre coefficients for each incident
  energy, are lists of numpy arrays. Arrays of sections or strings are
  lists, as with ``array_type="list"``.
- With ``preserve_value_strings=True``, arrays of floats remain lists
  (of :class:`~endf_parserpy.EndfFloat` objects), as numpy
  arrays cannot store the original strings; arrays of integers are still
  numpy arrays.

Data parsed with ``array_type="numpy"`` can be written with a parser
created with ``array_type="numpy"`` or ``array_type="list"``, which give
the same output for the same data. For writing, numpy arrays and lists
can be used interchangeably; numpy arrays of any integer type are
accepted for integer fields, and numpy arrays of any integer or float type
for float fields, as well as numpy scalars of these types.

Both parsers return the same result with ``array_type="numpy"``, also
for recipes passed with the ``recipes`` argument of
:class:`~endf_parserpy.EndfParserPy`: the form of an array is
determined by the place in the recipe where it is assigned, e.g. the
covariance matrix ``F`` above is a two-dimensional array if it was read
by the definition for ``LS=0``, and the arrays of the Legendre
coefficients of an incident energy without coefficients are empty
``float64`` arrays.
