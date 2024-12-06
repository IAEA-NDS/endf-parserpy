.. _working_with_legacy_formats_sec:

Working with Legacy Formats
===========================

The ENDF format evolved over decades with the current version being ENDF-6.
While the :doc:`ENDF recipes <../overview/mapping_endf_recipes>` shipped with
``endf-parserpy`` only implement the current ENDF-6 format standard,
users can provide their own recipe definitions to enable the parsing and
writing of legacy nuclear data files that are either based on earlier ENDF
format versions or rely on non-standard customizations of the official ENDF
format.

In this tutorial, we take the *European Activation File 2007* (EAF-2007)
as an example of nuclear data stored in a legacy format and demonstrate
how it can be parsed with ``endf-parserpy``. Noteworthy, we will also
explain how one can work around the limitation of endf-parserpy not
supporting several materials in a single file.

The format underlying EAF-2007 is described in `this document
<https://www.oecd-nea.org/dbdata/data/manual-endf/EAF-format(Based_on_UKAEA-FUS-535).pdf>`_.
To try out the following code blocks, download the
`abridged version <https://raw.githubusercontent.com/IAEA-NDS/endf-parserpy/6a7e85470fcc2c711b7e953af43253118bd8766b/examples/data/eaf2007_abridged.endf>`_
of the EAF-2007 file stored in the ``examples/data`` directory of the
``endf-parserpy`` GitHub repository.

The EAF-2007 file contains cross section data in MF=3 sections
for various materials. The structure of an MT section in MF=3
follows closely the ENDF-6 format (:endf6manshort:`122`) but is
additionally prefixed by two TEXT records (:endf6manshort:`52`)
with human-readable extra information. Therefore, as a first step,
we can create an :doc:`ENDF recipe <../overview/mapping_endf_recipes>`
for this specific MF=3/MT section structure:

.. code:: python

   recipes = dict()
   recipes[3] = """
   for i=1 to 2:
       [MAT, 3,MT / DESCRIPTION[i]]TEXT
   endfor
   [MAT, 3, MT/ ZA, AWR, 0, LFS, 0, 0] HEAD
   [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
   SEND
   """

The formal language underlying recipe definitions is described
in detail in this `ArXiV preprint <https://arxiv.org/abs/2312.08249>`_.

We can now instantiate an :class:`~endf_parserpy.EndfParser` class
making use of the ``recipes`` dictionary:

.. code:: python

   from endf_parserpy import EndfParser
   parser = EndfParser(
       recipes=recipes,
       ignore_missing_tpid=True,
       ignore_send_records=True
   )

Please note that this ``parser`` instance will only be able to
parse the custom MF=3 sections according to the structure defined
above and nothing else. For supporting other MF/MT sections, it
would be necessary to augment the ``recipes`` dictionary with
additional recipe definitions. For example, see `here
<https://github.com/IAEA-NDS/endf-parserpy/blob/09e2f3bcc706ce5dd1ce565e55ede021546304c6/endf_parserpy/endf_recipes/endf6/__init__.py>`_
how it is done for the entire `ENDF-6 formats standard
<https://www.nndc.bnl.gov/endfdocs/ENDF-102-2023.pdf>`_.

In the instantiation of the :class:`~endf_parserpy.EndfParser` class,
we also specified ``ignore_missing_tpid=True`` to tolerate the absence of a TPID
record, which is not present in the EAF-2007 file. The TPID record
is a TEXT record in the first line of an ENDF file that can be used for a
free-form text comment.

The specification of ``ignore_send_records=True`` is an essential ingredient
to deal with several materials in a single ENDF file, as is the case for the
EAF-2007 file. With this option active, we can split the file into several
chunks, one for each material, and disregard the SEND/FEND/MEND/TEND records.
For splitting up the file into chunks, we can use the following code snippet:

.. code:: python

   with open("data/eaf2007_abridged.endf", "r") as f:
       lines = f.readlines()

   # split up the various materials
   mat_dict = {}
   for l in lines:
       curmat = int(l[66:70])
       if curmat > 0:
           curlines = mat_dict.setdefault(curmat, [])
           curlines.append(l)

After loading the file content into a list of strings, the dictionary
``mat_dict`` is populated with lists of strings associated with the various
materials. Because of the argument ``ignore_send_records=True`` passed
to the :class:`~endf_parserpy.EndfParser` class, we can strip away any
kind of section end record. Technically, these records are filtered out by
only dealing with records that contain a material number (``MAT``)
greater than zero.

Finally, we can loop over the materials stored in ``mat_dict`` under
keys given by the material number and individually parse the list
of strings associated with each material.

.. code:: python

   parsed_mat_dict = {}
   for matnr in mat_dict.keys():
       parsed_mat = parser.parse(mat_dict[matnr])
       parsed_mat_dict[matnr] = parsed_mat

As a result, ``parsed_mat_dict`` contains for each material
a dictionary with values stored under the symbol names
as defined in the ENDF recipe above. For instance, to see
what variable names are present in the MF=3/MT=16 section
of material ``102``, run the following code:

.. code:: python

   parsed_mat_dict[102][3][16].keys()


In summary, this tutorial showed how to parse a nuclear data file (EAF-2007)
given in a legacy format by creating a custom ENDF recipe definition.
It was also demonstrated how to work around the limitation of
``endf-parserpy`` not supporting several materials in a single file.
Finally, below we provide the full code example including all code snippets
explained step-by-step in this tutorial:

.. code:: python

   from endf_parserpy import EndfParser

   recipes = dict()
   recipes[3] = """
   for i=1 to 2:
       [MAT, 3,MT / DESCRIPTION[i]]TEXT
   endfor
   [MAT, 3, MT/ ZA, AWR, 0, LFS, 0, 0] HEAD
   [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
   SEND
   """

   parser = EndfParser(
       recipes=recipes,
       ignore_missing_tpid=True,
       ignore_send_records=True
   )

   with open("data/eaf2007_abridged.endf", "r") as f:
       lines = f.readlines()

   # split up the various materials
   mat_dict = {}
   for l in lines:
       curmat = int(l[66:70])
       if curmat > 0:
           curlines = mat_dict.setdefault(curmat, [])
           curlines.append(l)

   # parse each material
   parsed_mat_dict = {}
   for matnr in mat_dict.keys():
       parsed_mat = parser.parse(mat_dict[matnr])
       parsed_mat_dict[matnr] = parsed_mat


   # inspect parsed sections, e.g. MF=3/MT=16 of material 102
   parsed_mat_dict[102][3][16].keys()
