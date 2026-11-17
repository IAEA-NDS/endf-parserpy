.. rubric:: Neutrons

2 files, 3.75 MB; the sample: 2 files, 3.75 MB.

.. list-table::
   :header-rows: 1
   :widths: 4 1 3 1 3 1

   * - Parser, ``array_type``
     - Files
     - Parse
     - MB/s
     - Write
     - MB/s
   * - ``EndfParserCpp`` ``dict``
     - 2
     - 17.5 ms ±11.5 %
     - 214
     - 33.2 ms ±11.8 %
     - 113
   * - ``EndfParserCpp`` ``list``
     - 2
     - 9.43 ms ±9.8 %
     - 397
     - 30.6 ms ±5.0 %
     - 122
   * - ``EndfParserCpp`` ``numpy``
     - 2
     - 6.96 ms ±8.5 %
     - 538
     - 27.0 ms ±10.3 %
     - 139
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 2
     - 2.20 s ±5.4 %
     - 1.70
     - 2.62 s ±4.3 %
     - 1.43
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 2
     - 2.43 s ±5.8 %
     - 1.55
     - 3.51 s ±3.7 %
     - 1.07
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 2
     - 2.52 s ±3.4 %
     - 1.49
     - 3.67 s ±7.2 %
     - 1.02

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 126
     - 79
   * - ``list``
     - 257
     - 115
   * - ``numpy``
     - 362
     - 136

.. rubric:: Thermal neutron scattering

1 file, 0.31 MB; the sample: 1 file, 0.31 MB.

.. list-table::
   :header-rows: 1
   :widths: 4 1 3 1 3 1

   * - Parser, ``array_type``
     - Files
     - Parse
     - MB/s
     - Write
     - MB/s
   * - ``EndfParserCpp`` ``dict``
     - 1
     - 0.72 ms ±14.1 %
     - 430
     - 1.68 ms ±10.8 %
     - 185
   * - ``EndfParserCpp`` ``list``
     - 1
     - 0.84 ms ±9.1 %
     - 369
     - 2.07 ms ±12.0 %
     - 150
   * - ``EndfParserCpp`` ``numpy``
     - 1
     - 0.75 ms ±11.9 %
     - 415
     - 1.78 ms ±10.0 %
     - 175
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 1
     - 30.5 ms ±4.8 %
     - 10.2
     - 55.4 ms ±5.6 %
     - 5.60
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 1
     - 29.6 ms ±5.5 %
     - 10.5
     - 49.2 ms ±2.5 %
     - 6.31
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 1
     - 31.6 ms ±10.5 %
     - 9.82
     - 50.5 ms ±7.0 %
     - 6.15

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 42
     - 33
   * - ``list``
     - 35
     - 24
   * - ``numpy``
     - 42
     - 28

.. rubric:: Decay data

1 file, 0.01 MB; the sample: 1 file, 0.01 MB.

.. list-table::
   :header-rows: 1
   :widths: 4 1 3 1 3 1

   * - Parser, ``array_type``
     - Files
     - Parse
     - MB/s
     - Write
     - MB/s
   * - ``EndfParserCpp`` ``dict``
     - 1
     - 0.18 ms ±8.0 %
     - 46.3
     - 0.15 ms ±8.9 %
     - 58.1
   * - ``EndfParserCpp`` ``list``
     - 1
     - 0.17 ms ±5.4 %
     - 46.5
     - 0.15 ms ±4.7 %
     - 59.6
   * - ``EndfParserCpp`` ``numpy``
     - 1
     - 0.20 ms ±10.3 %
     - 41.2
     - 0.15 ms ±8.0 %
     - 57.9
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 1
     - 8.74 ms ±17.5 %
     - 0.93
     - 5.29 ms ±13.1 %
     - 1.64
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 1
     - 7.45 ms ±31.8 %
     - 1.09
     - 5.96 ms ±6.2 %
     - 1.45
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 1
     - 7.41 ms ±32.6 %
     - 1.10
     - 5.24 ms ±1.8 %
     - 1.65

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 50
     - 35
   * - ``list``
     - 43
     - 41
   * - ``numpy``
     - 38
     - 35
