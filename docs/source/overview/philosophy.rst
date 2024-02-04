.. _ENDF-6 format: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf
.. _ENDF-6 formats manual: https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf
.. _Lark: https://github.com/lark-parser/lark

Philosophy
==========

The `ENDF-6 format`_
is broadly adopted by major nuclear data library projects
for storing and distributing evaluated nuclear data,
yet notoriously cumbersome to work with because
of its origin in an era when information
technology was markedly different and much more
limited than nowadays.

endf-parserpy's mission is to remove this
technological barrier between evaluated nuclear data
and humans by providing at least the following capabilities:


Desired technical capabilities
------------------------------

1) Easy translation between ENDF-6 and other formats, such as JSON
2) Convenient access to any information in ENDF-6 files
3) Support of the entire `ENDF-6 format`_ standard
4) Straightforward creation and manipulation of ENDF-6 files

The first capability makes evaluated nuclear data
more inclusive by allowing users to work with
nuclear data in the format that is most convenient
for them. This capability also addresses
to some extent the second one, as suitable data
structures facilitate the access to the data.
Access to any information and the loss-free
translation into other file formats requires
the support for the entire `ENDF-6 format`_ standard.
Finally, the fourth capability makes nuclear data
development more inclusive and lowers the entrance barrier
to new contributors.

Design considerations
---------------------

The technical and comprehensive nature of the
`ENDF-6 formats manual`_
with more than 400 pages, occassionally updated
due to format extensions, gives rise to the
following three questions:

1) How can the support for the entire `ENDF-6 format`_ be implemented
   as fast as possible, given the comprehensive nature of the format?
2) How can the probability of implementation errors due to misunderstanding the format descriptions be eliminated to a large degree?
3) How can the package be designed to enable the seamless accommodation of future format extensions?

The consideration of these questions led to the following
design choices for the implementation of the desired technical
capabilities.

--------------------------------------------------------


Design choices
--------------

1. Bijective ENDF-6 / dictionary mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

A Python dictionary stores associations between keys
(e.g. strings) and objects.
It is therefore a suitable data structure for storing
the nuclear quantities in ENDF-6 files under
the symbol names defined in the ENDF-6 manual.
Because Python offers powerful facilities to create,
combine and manipulate data in dictionaries,
these facilities can also be leveraged
for ENDF-6 data if available in a dictionary.

Therefore, it was decided that the core functionality
of endf-parserpy should be the capability to
map the entirety of data present in an ENDF-6 file
into a Python dictionary. It should also be possible
to translate the data of such a dictionary into the
`ENDF-6 format`_ without loss of information.
The reading and writing functionality should
be symmetric by design. If the package supports
reading a specific type of nuclear data into a dictionary,
it should also allow for translating this data type
into the `ENDF-6 format`_.


2. Rely on a formal ENDF format description
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The descriptions in the `ENDF-6 formats manual`_ can
be formalized to enable automatic interpretation
by computer programs. This package should leverage
such a formal ENDF-6 description for the translation
between ENDF-6 files and Python dictionaries.
The mapping logic is then implemented generically
for all elements of the formal format description.

This approach makes asymmetries in reading and writing
capabilities impossible. It further ensures that the
package implements the ENDF-6 format specification
correctly by design as the automated interpretation
of the format description removes the possibility
that a programmer implements any part of the ENDF-6 format
wrongly due to misunderstanding the description of the
format.

This design choice also implies that
support for ENDF-6 format extensions can be seamlessly
implemented by updating the formal ENDF-6 descriptions.
The design of the formal ENDF format specification
language is explained in an `arxiv preprint
<https://arxiv.org/abs/2312.08249>`_.
Endf-parserpy leverages the parsing package
`Lark`_ for the interpretation of the formal ENDF-6 format
description.


3. No classes to encapsulate ENDF-6 data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While object-oriented design (closely coupling data and specific
methods for these data) is often advantageous,
it was not regarded as good fit for ENDF-6 data.
The set of possible operations is too large to implement all
of them and there is not a clear argument that any subset of
operations should be favored by coupling it more closely
to the data than others. In addition, the usage of
custom classes make generic Python functions for data
transformation and manipulation less likely to be applicable out of the
box and more hand-tailored code becomes necessary.

For these reasons, it was decided to organize ENDF-6 data
exclusively using the basic Python data types
:class:`int`, :class:`float`,
:class:`str`, :class:`dict` and :class:`list`.
Dictionaries provide the associations
between symbol names and numerical values (being either
:class:`int` or :class:`float`). Tabulated functions, such as
cross sections as a function of incident energy, can be
realized with the :class:`list` datatype or as dictionaries
with contiguous integer keys. The nesting of dictionaries
can be used to organize ENDF-6 data in sections, subsections,
etc.
As these datatypes are all standard in Python,
programmers can easily operate with them, without the need
to digest additional documentation.
The exclusive reliance on basic Python data types allows for
the use of generic code (that doesn't know anything about
ENDF-6) for the translation to other representations.
For instance, the conversion to the JSON format can be achieved
by standard Python functionality with a few lines of code.

