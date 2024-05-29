.. _endf6_recipe_sec:

Mappings by ENDF-6 Recipes
==========================

Endf-parserpy relies on a `formal description
<https://arxiv.org/abs/2312.08249>`_ of the `ENDF-6 format`_
for parsing ENDF-6 files and mapping their data into Python dictionaries
(:class:`dict`).
From the user perspective, the formal description
contains all the information for understanding the structure
of the dictionaries. Also, appropriately structured
dictionaries can be written out as ENDF-6 files.
This section explains the link between the formal ENDF-6
description and the corresponding structure of dictionaries.

What is an ENDF-6 recipe?
-------------------------

The entire ENDF-6 format description is subdivided into
*ENDF-6 recipes*. An ENDF-6 recipe often contains the
format description for an entire MF section (dedicated to a
certain nuclear quantity type). However, sometimes the format description
is different for different MT sections within the same
MF section and then one ENDF-6 recipe is provided for each
of those MT sections. To get a first idea of how these
ENDF-6 recipes look like, take a glimpse at
:ref:`this recipe <mf1mt451_recipe>` explained later on
this page. All of the currently implemented recipes are available
in `this subdirectory <ENDF-6 recipes_>`_ of
endf-parserpy's `GitHub repository`_.
In the following, we explain how the corresponding
structure of the Python dictionary can be inferred
from such recipes.

.. note::

   ENDF-6 recipes are an essential part of
   endf-parserpy to enable a proper parsing of ENDF-6 files.
   However, the following information is *not* a
   prerequisite for a satisfactory understanding of the
   guides and tutorials.


Structure of Python dictionaries with ENDF-6 data
-------------------------------------------------

The structure of a dictionary returned by a call to
the :func:`~endf_parserpy.EndfParser.parsefile` method
or expected by :func:`~endf_parserpy.EndfParser.writefile` method
of the
:class:`~endf_parserpy.EndfParser` class
contains as first level the integer keys corresponding to
MF numbers and as second level
integer keys corresponding to MT numbers, see the :endf6manpage:`32`.
Suppose the variable ``endf_dict`` contains
such a dictionary, then ``endf_dict[3][1]`` would refer
to the dictionary that includes  the variables associated with
MF=3 (cross section) and MT=1 (total cross section).

The structure of a dictionary associated with an MF/MT
combination is determined by the form of the corresponding
ENDF-6 recipe. Each ENDF-6 recipe contains a sequence of
ENDF records and potentially syntactic elements
for expressing `repetitions and conditional presence
<https://arxiv.org/pdf/2312.08249.pdf#page=12>`_
of such records.
As you will see, detailed knowledge of ENDF records is
not strictly necessary to understand how a specific
ENDF-6 recipe is linked to the structure of the
associated dictionary.

.. _basic_mapping_of_variables:

Basic mapping of variables
~~~~~~~~~~~~~~~~~~~~~~~~~~

The following `ENDF-6 recipe for MF=1/MT=451
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf1_mt451.py>`_
(general description) will serve as the basis for the explanation
of how the dictionary structure is determined by a recipe:

.. _mf1mt451_recipe:

.. code:: text

    [MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
    [MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
    [MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
    [MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT

    [MAT, 1,451/ ZSYMAM{11}, ALAB{11}, EDATE{10}, {1}, AUTH{33} ]TEXT
    [MAT, 1,451/ {1}, REF{21}, DDATE{10}, {1},
                 RDATE{10}, {12}, ENDATE{8}, {3} ]TEXT
    for i=1 to 3:
        [MAT, 1,451/ HSUB[i]] TEXT
    endfor
    for i=1 to NWD-5:
        [MAT, 1,451/ DESCRIPTION[i]]TEXT
    endfor
    for i=1 to NXC:
        [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
    endfor
    SEND

This recipe is a formalized version of the format specification in
the :endf6manpage:`61`.
Let's assume that the corresponding dictionary
is named ``mf1_mt451_dict`` referring to ``endf_dict[1][451]``.
Each dictionary associated with a specific MF and MT number
will contain the keys ``MAT``, ``MF`` and ``MT``
(:endf6manshort:`30`) with
the appropriate integer values (data type :class:`int`).
Lines of the form ``[ ... / ... ] <record type>`` in an
ENDF-6 recipe represent ENDF records (:endf6manshort:`52`). The variable names
in the six slots after the first slash in an ENDF record
are directly mapped onto equally named keys in the
corresponding dictionary.
For example, the six slots of the first line (the HEAD record)
contain the variable names ``ZA``, ``AWR``, ``LRP``,
``LFI``, ``NLIB`` and ``NMOD``, and equally named keys are expected
to be present in ``mf1_mt451_dict``.
More generally, the variable names introduced in the six
comma-separated slots after the first ``/`` of
*any* ENDF record specification (HEAD, CONT, TEXT, etc.)
are expected to exist as dictionary keys. The only particularity is the
special keyword ``blank`` that represents a blank slot and not a variable name.
Simple variable names are linked to scalar values of type :class:`int` or :class:`float`.
The only exception to this rule are the variables introduced in a TEXT record, which
are associated with character strings (:class:`str`). Variable names suffixed by a string
with square brackets denote *arrays*. In a TEXT record,
variables and also arrays can be additionally suffixed
by curly braces enclosing an integer, which defines the length of the string.

.. _arrays:

Variables with indices: Arrays
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ENDF-6 recipe listed :ref:`above <mf1mt451_recipe>` contains
several examples of array specifications, such as ``DESCRIPTION[i]``,
``MFx[i]`` and ``MTx[i]``. Their names, ``DESCRIPTION``,
``MFx``, etc. are expected to be available as keys in the Python dictionary
corresponding to the ENDF-6 recipe. The objects associated with those
keys are expected to be dictionaries with integer keys.
The range of the available integer keys can be inferred from the
loop statement that involves the variable appearing in the pair of
square brackets. For instance, the counter variable ``i`` runs from
``1`` to the value of variable ``NWD`` and hence the dictionary
stored under the ``DESCRIPTION`` key in ``mf1_mt451_dict`` (see above)
is expected to contain all integers between 1 and the value of ``NWD``
as keys. The third element in ``DESCRIPTION`` could then
be accessed via ``mf1_mt451_dict['DESCRIPTION'][3]``.
Also multidimensional arrays are possible, e.g. ``arr2d[i, j]``
would indicate a two-dimensional array.
Multidimensional arrays are realized by nesting dictionaries
with integer keys.
For example, an array of size 2x2 could be set up like this:

.. code:: python

   arr2d = {1: dict(), 2: dict()}
   arr2d[1] = {1: 1, 2: 2}
   arr2d[2] = {1: 3, 2: 4}


.. _data_types_sec:

Data types
~~~~~~~~~~

The data types of objects linked to the various keys can also be
inferred from an ENDF-6 recipe. The variables in
the first two slots of an ENDF record are of type :class:`float`
and those in the next four slots of type :class:`int`:

.. code:: text

   [ ... / float, float, int, int, int, int ] RECORD_TYPE

The only exception are TEXT records whose variables are
associated with type :class:`str`.

Therefore, considering again the :ref:`ENDF-6 recipe above <mf1mt451_recipe>` as example,
the values under the keys ``ZA``, ``AWR``, ``ELIS``, ``STA``, etc.
are stored as data type :class:`float`, whereas ``LRP``, ``LFI``, ``NLIB``, ``NMOD``,
``LIS``, ``LISO``, etc. stored as data type :class:`int`.
In contrast, the array elements of ``DESCRIPTION`` have the
data type :class:`str` due to the variable name being introduced
in the slot of a TEXT record. Noteworthy, variable names in
TEXT record specifications may be suffixed by an integer
enclosed by curly braces to indicate the length of the
associated string. For example:

.. code:: text

    [MAT, 1,451/ ZSYMAM{11}, ALAB{11}, EDATE{10}, {1}, AUTH{33} ]TEXT

Here, ``ZSYMAM`` is associated with a string with 11 characters,
``EDATE`` with 10 characters, etc.
A TEXT record specification may contain a single
variable name without the curly brace suffix, e.g.:

.. code:: text

   [MAT, 1,451/ DESCRIPTION[i] ]TEXT

The variable is then associated with a string
spanning the full line in the ENDF-6 file
(66 character slots).

.. _particularities_tab1_tab2_record:

Particularities of TAB1 and TAB2 records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There are a couple of particularities in how TAB1 and TAB2 records
(:endf6manshort:`54`)
are mapped into a Python dictionary. To explain, let's consider
a slightly adjusted version of the `ENDF-6 recipe for MT sections of MF=3
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf3.py>`_
(cross sections), compare also with the :endf6manpage:`123`:

.. code:: text

   [MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
   [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs] TAB1
   SEND

For the sake of illustration, let's assume we are dealing
with the dictionary for a total cross section (MT=1),
``mf3_mt1_dict = endf_dict[3][1]``. As seen, a TAB1
record specification contains two extra slots, separated by
a slash, after the six regular comma-separated slots.
The variable names in these extra slots are expected to
be present in the dictionary, i.e. ``mf3_mt1_dict['E']``
and ``mf3_mt1_dict['xs']``. These keys are associated with
one-dimensional arrays that are stored as data type :class:`list`.
Furthermore, there are two additional keys ``NBT`` and ``INT``
expected to be present. These variables establish
the definition of a piecewise interpolation scheme (see :endf6manshort:`44`
for details). The associated objects also need to be of type :class:`list`.
Regarding the regular six slots, the variable names
of the first four slots are mapped into the dictionary
as described in :ref:`an earlier section on this page
<basic_mapping_of_variables>`. Variable names of the last two slots,
here ``NR`` and ``NP`` are ignored because they can be inferred from
the length of the :class:`list` datatypes ``NBT``, ``INT`` and (here)
``E`` and ``XS``.

Matters for the TAB2 record are similar.
Consider the following example:

.. code:: text

   [MAT, 6, MT/ SPI, 0.0, LIDP, 0, NR, NE / Eint ]TAB2

The presence of a TAB2 record specification means that
keys ``NBT`` and ``INT`` must be present in the dictionary
and the associated objects are of type ``list``.
The variable name in the 5th slot (here ``NR``) is ignored
as its value can be inferred from the length of the :class:`list`
stored in ``NBT``.
Furthermore, the variable name after the second slash,
here ``Eint``, is ignored. This string can be regaded as a hint,
which variable name in the following TAB1 record contains
the values of the mesh points. The other variable names
in the remaining slots are mapped into the dictionary
as explained in :ref:`an earlier section on this page
<basic_mapping_of_variables>`. So for the given example
of a TAB2 record specification, keys with names
``SPI``, ``LIDP``, ``NE``, ``NBT`` and ``INT``
are expected to be present in the dictionary.

Finally, there is a feature called
`table body section
<https://arxiv.org/pdf/2312.08249.pdf#page=14>`_.
To explain it, let's consider a slightly extended
version of the MF3/MT1 recipe introduced above:

.. code:: text

   [MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
   [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs] TAB1 (xstable)
   SEND

If a variable name is provided in brackets after a TAB1 or
TAB2 record specification, an equally named key is expected to be present
in the Python dictionary. This key is then associated with
another dictionary that contains ``NBT``, ``INT`` and the two keys named
according to the variable names in the last two slots,
here ``E`` and ``XS``. These variables could be accessed by
``mf3_mt1_section['xstable']['NBT']``, etc.


Particularities of LIST records
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Let's consider the following LIST record specification
(see also :endf6manshort:`53`):

.. code:: text

    [MAT, 4, MT/ T, E[i] , LT, 0, NL[i], 0/ {a[i,l]}{l=1 to NL[i]} ]LIST

As this line is extracted
from the `ENDF-6 recipe for MF=4
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf4.py>`_,
let's assume we deal with an MF=4/MT=2
section whose data is stored in a dictionary ``mf4_mt2_section``.
Variable names introduced after the second slash exist as equally named
keys in the Python dictionary, so ``mf4_mt2_section['a']`` needs to be
available and represents an :ref:`array <arrays>`.
Notation such as ``{...}{l=1 to NL[i]}`` indicates repetitions
(see also `here
<https://arxiv.org/pdf/2312.08249.pdf#page=10>`_),
and helps to infer the ranges of indices for arrays introduced inside
the first curly bracket pair.


Sections
~~~~~~~~

ENDF-6 recipes can also make use of `sections
<https://arxiv.org/pdf/2312.08249.pdf#page=14>`_.
Let's consider
the following recipe to see how it affects the structure of
the corresponding dictionary:

.. code:: text

    [MAT, 10, MT/ ZA, AWR, LIS, 0, NS, 0]HEAD
    for k=1 to NS:
    (subsection[k])
        [MAT, 10, MT/ QM, QI, IZAP, LFS, NR, NP/ E / sigma ]TAB1
    (/subsection[k])
    endfor

The notation ``(subsection[k])`` opens an array of sections
and ``(/subsection[k])`` indicates the end of the section block.
Assume that the corresponding dictionary is given by ``mf10_mt1_section``.
The presence of an opening and closing section statement
leads to the creation of a key whose name is given by the section
name in the section opening statement. In the current example, we have
``mf10_mt1_section['subsection']``. Because the section name
is given by an array, the dictionary ``mf10_mt1_section['subsection']``
contains contiguous integer keys and each of them is linked to
a dictionary, so ``mf10_mt1_section['subsection'][1]``,
``mf10_mt1_section['subsection'][2]``, etc. are dictionaries as well.
The range of the contiguous integer keys can be inferred from the
loop statement containing the variable of the index, so in the
example considered keys from ``1`` to ``NS`` exist.
Variables introduced between the opening and closing section
statement are mapped into the subdictionaries as explained
in the previous section on this page. In the current example,
the following elements are expected to exist:
``mf10_mt1_section['subsection'][1]['QM']``,
``mf10_mt1_section['subsection'][1]['QI']``, etc.


Conditional blocks
~~~~~~~~~~~~~~~~~~

Conditional blocks are associated with `if/elif/else
<https://arxiv.org/pdf/2312.08249.pdf#page=12>`_ statements.
Consider the `recipe for an MF=1/MT=452 section
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf1_mt452.py>`_
(see also :endf6manshort:`63`):

.. code:: text

    [MAT, 1, 452/ ZA, AWR, 0, LNU, 0, 0]HEAD
    if LNU == 1:
        [MAT, 1, 452/ 0.0, 0.0, 0, 0, NC, 0/ {C[k]}{k=1 to NC} ] LIST
    elif LNU == 2:
        [MAT, 1, 452/ 0.0, 0.0, 0, 0, NR, NP/ Eint / nu ]TAB1
    endif
    SEND

Assume the dictionary linked to MF=1/MT=452 is named
``mf1_mt452_section``.
Variable names introduced inside a conditional block will only
be present in this dictionary if the logical expression in the
if-statement is true. In the current example: The variable ``NC``
will only be present as key in ``mf1_mt452_section`` if
``mf1_mt452_section['LNU']`` is equal to 1. Similarly,
keys named ``Eint`` and ``nu`` will only exist if
``mf1_mt452_section['LNU'] == 2``.


.. _ENDF-6 format: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf
.. _ENDF-6 formats manual: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf
.. _ENDF-6 recipes: https://github.com/IAEA-NDS/endf-parserpy/tree/main/endf_parserpy/endf_recipes/endf6/
.. _GitHub repository: https://github.com/IAEA-NDS/endf-parserpy/
