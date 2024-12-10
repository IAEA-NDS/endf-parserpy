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
to the constructor of the :class:`~endf_parserpy.EndfParser`
class:

.. code:: python

   from endf_parserpy import EndfParser
   parser = EndfParser(array_type="list")

Using this option, The :func:`~endf_parserpy.EndfParser.parse` and
:func:`~endf_parserpy.EndfParser.parsefile` methods will
return dictionaries in which  *all* arrays are stored as :class:`list`.
Analogously for writing via the :func:`~endf_parserpy.EndfParser.writefile` and
:func:`~endf_parserpy.EndfParser.write`
methods, the dictionaries with ENDF data are expected to
contain *all* arrays as :class:`list`.

If you are using the ``array_type="list"`` option, be aware of the following:

- ENDF data loaded into a dictionary
  using a parser object initialized with ``EndfParser(array_type="list"``
  can't be written to an ENDF file with a parser object initialized with
  ``EndfParser(array_type="dict")`` and vice-versa. It is recommended to
  choose one parser mode and use it consistently throughout a project.
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
