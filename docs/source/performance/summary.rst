.. warning::

   **Placeholder.** These numbers come from a few small test files
   of the repository, not from ENDF/B-VIII.1; they only show the
   layout of the page. The measurement over the sublibraries of
   ENDF/B-VIII.1 replaces them.

.. list-table::
   :header-rows: 1

   * - Sublibrary
     - ``EndfParserCpp`` ``dict``
     - ``EndfParserCpp`` ``list``
     - ``EndfParserCpp`` ``numpy``
     - ``EndfParserPy`` ``dict``\ :sup:`*`
     - ``EndfParserPy`` ``list``\ :sup:`*`
     - ``EndfParserPy`` ``numpy``\ :sup:`*`
   * - Neutrons
     - 214 / 113
     - 397 / 122
     - 538 / 139
     - 1.70 / 1.43
     - 1.55 / 1.07
     - 1.49 / 1.02
   * - Thermal neutron scattering
     - 430 / 185
     - 369 / 150
     - 415 / 175
     - 10.2 / 5.60
     - 10.5 / 6.31
     - 9.82 / 6.15
   * - Decay data
     - 46.3 / 58.1
     - 46.5 / 59.6
     - 41.2 / 57.9
     - 0.93 / 1.64
     - 1.09 / 1.45
     - 1.10 / 1.65
   * - **All**
     - 221 / 116
     - 389 / 124
     - 514 / 141
     - 1.81 / 1.52
     - 1.65 / 1.14
     - 1.59 / 1.09

Throughput in MB/s (1 MB = 10\ :sup:`6` bytes), parsing / writing:
the bytes of the files over the time of ``parsefile``, and the bytes
written over the time of ``write``, summed over the files of the
sublibrary.

\ :sup:`*` On the sample of 4 files (see below).

Measured on 2026-11-17 with endf-parserpy 0.18.0 (development version v0.18.0-227-ge16c324).
