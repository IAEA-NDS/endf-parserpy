.. _data_navigation:

Data Navigation
===============

The core functionality of ``endf-parserpy`` is to
map the nuclear data stored in an ENDF-6 file into a nested
Python dictionary. These dictionaries can be somewhat
deeply nested and hence the navigation in them to access or
manipulate data cumbersome. endf-parserpy introduces
the concept of an :class:`~endf_parserpy.EndfPath`
for referencing a piece of data in a dictionary associated
with ENDF-6 data.

.. _endf_path_class:

EndfPath
--------

Most people are familiar with the hierarchical organization
of data in file systems by nesting directories, and how
a file can be referenced by the provision of a *path*.
Similarly, it is convenient to use a path for referring to a
variable or section in an ENDF-6 dictionary. The path is
constructed by combining the keys of the nested dictionaries
to a single string using a ``/`` character as separator.
For instance, there may be a variable ``AJ`` in a Python dictionary
``endf_dict`` accessible via:

.. code::

   endf_dict[2][151]['isotope'][1]['range'][1]['spingroup'][1]['AJ']

The corresponding :class:`~endf_parserpy.EndfPath` would be given by

``2/151/isotope/1/range/1/spingroup/1/AJ``

Some objects in a nested dictionary can be considered as an array
of objects and we may want to use `numpy <https://numpy.org/>`_-like syntax.
Therefore, a path should also support notation
of the form ``isotope[1]``, which is equivalent to ``isotope/1``.
Making use of this alternative notation, the path above
could be equally written as:

``2/151/isotope[1]/range[1]/spingroup[1]/AJ``

The class :class:`~endf_parserpy.EndfPath` provides
a container for the storage of a path. However, paths become
only useful when they can actually be used
to navigate dictionaries with ENDF-6 data and retrieve the desired data
from them. The :class:`~endf_parserpy.EndfDict` class helps with this requirement.

.. _endf_path_sections:

Sections of a material
~~~~~~~~~~~~~~~~~~~~~~

The first two keys of a path into a material, ``MF/MT``, select a
section by its *label*. Some flavors let a label occur several times in
a material: GENDF tapes, for instance, hold one MF3/MT102 section per
product of a nuclide production (see :doc:`GENDF files <../guide/gendf_files>`).
Such a material is a list of sections in the order of the file (its *list
form*, see :func:`~endf_parserpy.to_list_form`), and a path can select a
section in three ways:

- ``MF/MT``, e.g. ``3/102``: the section with this label, which must be
  unique in the material; otherwise an
  :class:`~endf_parserpy.tape.AmbiguousSectionError` is raised;
- ``MF/MT#k``, e.g. ``3/102#2``: the ``k``-th section with this label;
- ``#k``, e.g. ``#0``: the section at position ``k`` of the material.

The rest of the path addresses data within the section as before, e.g.
``3/102#2/IZAM``. ``k`` counts from 0.

.. important::

   **The positions do not count the tape head.** ``#0`` is the first
   section after the tape head (MF0/MT0), as in
   :class:`~endf_parserpy.EndfFile`, whose materials have no tape head.
   A material returned by ``parse`` in the list form has the tape head as
   its element 0, so that the position ``#k`` is the list element
   ``material[k + 1]``, and an integer index of the list, or of an
   :class:`~endf_parserpy.utils.accessories.EndfList` wrapping it, counts
   the tape head. The tape head itself is selected by its label, ``0/0``.
   :func:`~endf_parserpy.iter_sections` yields every section with its
   position, so that the offset need not be computed by hand.

.. code:: python

   from endf_parserpy import EndfParserPy, EndfPath, iter_sections

   parser = EndfParserPy(endf_format="gendf")
   material = parser.parsefile("am241.gendf")   # a list of sections
   EndfPath("3/102#2/IZAM").get(material)        # the third MF3/MT102
   EndfPath("#1").get(material) is material[2]   # True: the head is material[0]
   for entry in iter_sections(material):
       print(f"#{entry.position}: {entry.mf}/{entry.mt}#{entry.occurrence}")

On a material in the nested form ``{MF: {MT: section}}``, a path is
walked by its keys as before, and ``MF/MT#0`` and ``#k`` work as well;
the position is that in the canonical order, by ascending MF and then
MT, again without the tape head.

A list is taken for a material in the list form if its first element is
a section: a dictionary with the keys ``MF`` and ``MT``, or a list of
strings (a section that was not parsed). Only the object a path is
applied to is examined, so that the arrays within a section, also in the
``array_type="list"`` mode, are addressed as before. On a material in
the list form a path must begin with a section selector: an ``MF`` alone
does not select a section and is an error.

Setting a whole section by its label replaces the section with this
label, or, for a label that the material does not have, inserts the
section directly after the last section whose label is less than or
equal to its own, so that a material in ascending order stays in
ascending order. A copy of a label is never added by a path; the
function :func:`~endf_parserpy.insert_section` does so. A field cannot
be set in a section of a list that does not exist. The functions
:func:`~endf_parserpy.get_section`, :func:`~endf_parserpy.set_section`,
:func:`~endf_parserpy.insert_section`, :func:`~endf_parserpy.remove_section`,
:func:`~endf_parserpy.section_positions` and
:func:`~endf_parserpy.locate_section` do the same without a path.

.. _endf_dict_class:

EndfDict
--------

An instance of :class:`~endf_parserpy.EndfDict`
behaves like a standard :class:`dict` but
enables the use of paths (as described above) to access
data. When the class is instantiated with a dictionary
as argument, it can be regarded as a `view object` of the
original dictionary. Any modification of data through the
:class:`~endf_parserpy.EndfDict` object will lead to the same modification
of the original dictionary (technically speaking:
:class:`~endf_parserpy.EndfDict`
objects manage a reference to the original :class:`dict` or other :class:`~collections.abc.MutableMapping` object).
Suppose that ``endf_dict`` is an instance of
:class:`~endf_parserpy.EndfDict`.
Using the example given above, we could access the variable ``AJ``
via:

.. code:: python

   aj = endf_dict['2/151/isotope[1]/range[1]/spingroup[1]/AJ']


An :class:`~endf_parserpy.EndfDict` instance also
allows keys to be separated by commas
so the same variable could also be accessed via the notation:

.. code:: python

   aj = endf_dict[2, 151, 'isotope', 1, 'range', 1, 'spingroup', 1, 'AJ']


It's also possible to mix these two notation forms, e.g.

.. code:: python

   aj = endf_dict[2, 151, 'isotope/1', 'range[1]', 'spingroup', '1/AJ']


The flexible notation allows to write down specific
instructions in a very intuitive form. Assume that you want
to modify a covariance matrix in the MF=33/MT=1 section.
You could use the following code:

.. code:: python

    F = endf_dict['33/1/subsection[1]/ni_subsection[1]/F']
    F[2, 3] = 0.5

This code works because any dictionary-like object retrieved
from an :class:`~endf_parserpy.EndfDict` object
will be automatically wrapped into an
:class:`~endf_parserpy.EndfDict` object itself
before being returned. Consequently, the extended indexing
capabilities are available for these retrieved objects,
such as demonstrated here by the assignment involving ``F``.

Another useful design feature regarding the construction
of dictionaries is the implicit creation of missing
dictionaries. For example, the assignment

.. code:: python

    endf_dict['2/151/isotope[1]/range[2]/spingroup[3]/AJ'] = 12.

will create all intermediate dictionaries, hence this instruction
even works for an empty dictionary ``endf_dict = EndfDict({})``.

See the documentation of the :class:`endf_parserpy.EndfDict` class
for further details.

Finally, we may want to use abbreviations to read and modify data in
a dictionary with ENDF-6 data. Perhaps we would like to assign
a new value to the ``aj`` variable and expect that the
same value is also assigned to the corresponding location in  ``endf_dict``.
However, this will not be the case. The
:class:`~endf_parserpy.EndfVariable` class
provides a mechanism to achieve this behavior.

EndfVariable
------------

An instance of :class:`~endf_parserpy.EndfVariable`
possesses a ``.value`` attribute
that is always kept in sync with a specific location in
a nested dictionary with ENDF-6 data.
It can be instantiated by providing an :class:`~endf_parserpy.EndfPath` object
and a dictionary:

.. code:: python

   ajvar = EndfVariable('2/151/isotope[1]/range[1]/spingroup[1]/AJ', endf_dict)

Any change of the value of ``AJ`` in ``endf_dict`` will be
reflected in ``ajvar.value`` and vice-versa. This class may
be a good basis for implementing
:ref:`higher-level functionality <high_level_functionality_doc>`,
such as linear interpolation of cross sections with the
link to the original data being preserved.
More technical details are provided in the documentation
of the :class:`endf_parserpy.EndfVariable` class.
