.. _gendf_files_sec:

GENDF Files
===========

GENDF (groupwise ENDF) is the output format of the multigroup
modules GROUPR and GAMINR of NJOY2016:

- GROUPR gives neutron and photon production data;
- GAMINR gives photo-atomic data.

A GENDF tape keeps the line layout of ENDF-6: 11-character fields,
the MAT/MF/MT columns, and HEAD and LIST records. Its content is
multigroup data instead of pointwise data:

- the group structures;
- the group fluxes;
- group cross sections and ratio quantities, such as nubar;
- spectra;
- transfer matrices.

The ENDF-6 formats manual does not describe GENDF. The ``gendf``
flavor follows the records as GROUPR and GAMINR write them
(subroutines ``groupr`` and ``displa`` of ``groupr.f90``, ``gaminr``
and ``dspla`` of ``gaminr.f90``).

The ``gendf`` flavor has no :ref:`layout version <layout_versions_sec>`
yet: its layout may still change in a later release.

Reading a GENDF tape
--------------------

Two properties of GENDF tapes differ from ENDF-6:

- **Framing.** NJOY writes no SEND record after MF1/MT451, and no FEND
  records between the MFs of a material.
- **Section order.** The sections are written in the order in which
  they were requested, which need not be ascending in MF and MT.

GROUPR also writes the data of every temperature as a separate
material with the same MAT number. Therefore,
:func:`~endf_parserpy.EndfParserPy.parsefile`, ``parse_tape_file`` and
``endf-cli validate``, which check the framing of ENDF-6, do not read
GENDF tapes. Read them with :class:`~endf_parserpy.EndfFile` instead,
with a parser that ignores the position of the end records:

.. code:: python

   from endf_parserpy import EndfFile, EndfParserPy

   parser = EndfParserPy(endf_format="gendf", ignore_send_records=True)
   with EndfFile("gendf.tape", parser=parser) as tape:
       material = tape[0]            # the first material (temperature)
       mf1 = material[1, 451]
       print(mf1["TEMPIN"], mf1["NGN"], mf1["SIGZ"])
       sec = material[3, 1]          # total cross section

``tape.by_mat(mat, occurrence=k)`` selects the ``k``-th temperature of
a material (see :doc:`multi-material files <multimaterial_files>`).

The parsers also read and write a single section, given as a short
tape with the usual end records. The tool
``tools/check_gendf_roundtrip.py`` of the source repository does this
for every section of a tape.

Dictionary layout
-----------------

MF1/MT451:

.. list-table::
   :header-rows: 1

   * - Key
     - Content
   * - ``ZA``, ``AWR``
     - ZA number and mass ratio of the material
   * - ``NZ``
     - number of sigma zero values (GAMINR: 1)
   * - ``NTW``
     - number of title words (1)
   * - ``TEMPIN``
     - temperature in Kelvin (GAMINR: 0)
   * - ``NGN``
     - number of groups of the first group structure: the neutron groups
       (GAMINR: the photon groups)
   * - ``NGG``
     - number of photon groups (0 if none)
   * - ``TITLE[k]``
     - title word, 0.0 for GROUPR. For GAMINR, it is text read as a
       number and has no meaning
   * - ``SIGZ[k]``, k=1..NZ
     - sigma zero values in barn (GAMINR: 1e12)
   * - ``EGN[k]``, k=1..NGN+1
     - group boundaries in eV
   * - ``EGG[k]``, k=1..NGG+1
     - photon group boundaries in eV (one value 0.0 if NGG=0)

The HEAD record of this section has ``-1`` in its N1 field, the marker
of a GENDF tape.

All other sections (MF3, MF5, MF6, MF12, MF13, MF16, MF21 to MF26) have
a HEAD record and one LIST record per group:

.. list-table::
   :header-rows: 1

   * - Key
     - Content
   * - ``ZA``
     - ZA number
   * - ``IZAM`` (MF23, MF26: ``AWR``)
     - ZAM of the product of a nuclide production in MF3, otherwise 0.
       GAMINR writes the mass ratio there, which is why the key is
       ``AWR`` in MF23 and MF26
   * - ``NL``
     - number of Legendre orders (MF5/MT455: number of delayed-neutron
       families)
   * - ``NZ``
     - number of sigma zero values of the section
   * - ``LRFLAG``
     - LR flag of the reaction in the evaluation
   * - ``NGI``
     - number of groups of the incident particle
   * - ``TEMPIN``
     - temperature, the same in every record
   * - ``IG[i]``
     - incident group of record ``i``
   * - ``NG2[i]``
     - number of positions of record ``i``
   * - ``IG2LO[i]``
     - first secondary group of record ``i``; 0 for a production record
       (see below)
   * - ``ANS[i,it,iz,il]``
     - values of record ``i`` at position ``it``, sigma zero ``iz`` and
       Legendre order ``il-1``

The records ``i = 1, 2, ...`` are counted in the order of the tape.
NJOY omits the groups whose values are all zero and those below the
threshold of the reaction, but always writes the last group
(``IG[i] == NGI``). The record of group ``g`` is therefore found by its
``IG`` value, not by its position.

``ANS`` keeps the array ``ans(il,iz,it)`` of GROUPR. With
``array_type="numpy"``, ``ANS[i]`` is an array of shape
``(NG2[i], NZ, NL)``.

The meaning of the positions ``it``:

- **Position 1** is the group flux of the weighting function.
- **Cross sections** (MF3, MF12, MF13, MF23): position 2 is the cross
  section.
- **Ratio quantities** (MF3/MT251, 252, 253, 452, 455, 456; NG2=3):
  position 2 is the ratio, e.g. nubar, and position 3 the cross section
  of the reaction.
- **Transfer matrices** (MF6, MF16, MF21 to MF26): position ``it`` is
  the cross section from group ``IG[i]`` to the secondary group
  ``IG2LO[i]+it-2``.
- **Spectrum records** (``IG[i] = 0``): GROUPR writes such a record
  when a spectrum does not depend on the incident energy below some
  energy, e.g. for MF6/MT18 from a fission spectrum in MF5, or MF16
  for the photons of fission and capture. All its positions are the
  spectrum for the secondary groups ``IG2LO[i]+it-1``; there is no
  flux.
- **Production records** (``IG2LO[i] = 0``): these follow the spectrum
  record for the groups below that energy. Position 2 is the total
  production cross section, and the row of the matrix is this value
  times the spectrum.
- **MF5** (one record with ``IG[i] = NGI``): for MT18, the fission
  spectrum for the groups ``IG2LO[i]+it-1``; for MT455, the decay
  constants of the families at position 1 and their spectra for the
  groups ``it-1``.

Example: the group cross sections and a dense transfer matrix from the
P0 component at infinite dilution:

.. code:: python

   import numpy as np
   from endf_parserpy import EndfFile, EndfParserPy

   parser = EndfParserPy(
       endf_format="gendf", ignore_send_records=True, array_type="numpy"
   )
   with EndfFile("gendf.tape", parser=parser) as tape:
       material = tape[0]
       ngn = material[1, 451]["NGN"]
       sec = material[3, 1]
       for ig, ans in zip(sec["IG"], sec["ANS"]):
           flux, sigma = ans[0, 0, 0], ans[1, 0, 0]
       sec = material[6, 2]
       matrix = np.zeros((ngn, ngn))
       for ig, ig2lo, ans in zip(sec["IG"], sec["IG2LO"], sec["ANS"]):
           row = ans[1:, 0, 0]
           matrix[ig - 1, ig2lo - 1 : ig2lo - 1 + len(row)] = row

Limitations
-----------

- Writing a whole tape, e.g. with :meth:`~endf_parserpy.EndfFile.export`,
  keeps every data record but does not reproduce the tape byte for
  byte:

  - it writes the framing of ENDF-6 (a SEND record after MF1/MT451 and
    FEND records);
  - it sorts the sections by MF and MT.

- GROUPR writes nuclide production (input ``10/``) as additional MF3
  sections with the MT of the reaction, e.g. several MF3/MT102
  sections that differ in ``IZAM``. The structural index of
  :class:`~endf_parserpy.EndfFile` currently keeps only the last of
  several sections with the same MF/MT in a material. Such sections can
  only be read one by one, as a single section.
- To write the numbers in the forms of NJOY, parse with
  ``preserve_value_strings=True``. Writing from the values with
  ``prefer_noexp=True`` and ``standard_form_on_tie=True`` gives the
  forms of NJOY in most fields, but drops the trailing zeros that NJOY
  keeps in its nine-digit form (``1.4400001`` instead of
  ``1.44000010``).
