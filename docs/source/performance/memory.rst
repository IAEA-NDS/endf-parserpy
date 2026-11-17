.. warning::

   **Placeholder.** These numbers come from a few small test files
   of the repository, not from ENDF/B-VIII.1; they only show the
   layout of the page. The measurement over the sublibraries of
   ENDF/B-VIII.1 replaces them.

.. list-table::
   :header-rows: 1

   * - Sublibrary
     - File size
     - ``EndfParserCpp`` ``dict``
     - ``EndfParserCpp`` ``list``
     - ``EndfParserCpp`` ``numpy``
     - ``EndfParserPy`` ``dict``\ :sup:`*`
     - ``EndfParserPy`` ``list``\ :sup:`*`
     - ``EndfParserPy`` ``numpy``\ :sup:`*`
   * - Neutrons
     - 1 MB – 10 MB
     - 9.3
     - 4.5
     - 2.2
     - 7.1
     - 5.3
     - 5.0
   * - Thermal neutron scattering
     - 100 kB – 1 MB
     - 0.9
     - 0.9
     - 0.9
     - 0.9
     - 0.9
     - 0.9
   * - Decay data
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 66.0
     - 66.0
     - 65.5

The peak memory of parsing over the file size: the median per
sublibrary and size group of the increase of the peak resident
memory of the process while parsing a file, divided by the size of
the file.

.. list-table::
   :header-rows: 1

   * - Sublibrary
     - Largest file
     - ``EndfParserCpp`` ``dict``
     - ``EndfParserCpp`` ``list``
     - ``EndfParserCpp`` ``numpy``
     - ``EndfParserPy`` ``dict``\ :sup:`*`
     - ``EndfParserPy`` ``list``\ :sup:`*`
     - ``EndfParserPy`` ``numpy``\ :sup:`*`
   * - Neutrons
     - n_2925_29-Cu-63.endf (2.03 MB)
     - 20.4 MB
     - 11.5 MB
     - 4.96 MB
     - 24.2 MB
     - 18.7 MB
     - 17.9 MB
   * - Thermal neutron scattering
     - tsl_Al.endf (0.31 MB)
     - 0.27 MB
     - 0.27 MB
     - 0.27 MB
     - 0.27 MB
     - 0.27 MB
     - 0.27 MB
   * - Decay data
     - dec-094_Pu_244.endf (0.01 MB)
     - 0.00 MB
     - 0.00 MB
     - 0.00 MB
     - 0.54 MB
     - 0.54 MB
     - 0.53 MB

The increase of the peak resident memory while parsing the largest
file of each sublibrary (— if it is not in the sample).
