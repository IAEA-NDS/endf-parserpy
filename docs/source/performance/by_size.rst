.. image:: performance/throughput_by_size.svg
   :alt: Throughput in MB/s over the size groups of the files,
         parsing and writing, one line per parser and array_type
   :width: 100%

.. list-table::
   :header-rows: 1

   * - File size
     - Files (sample)
     - ``EndfParserCpp`` ``dict``
     - ``EndfParserCpp`` ``list``
     - ``EndfParserCpp`` ``numpy``
     - ``EndfParserPy`` ``dict``\ :sup:`*`
     - ``EndfParserPy`` ``list``\ :sup:`*`
     - ``EndfParserPy`` ``numpy``\ :sup:`*`
   * - < 100 kB
     - 3855 (24)
     - 96.7 / 88.1
     - 99.5 / 89.4
     - 98.2 / 87.4
     - 2.26 / 2.17
     - 2.12 / 1.72
     - 2.08 / 1.74
   * - 100 kB – 1 MB
     - 562 (44)
     - 285 / 155
     - 360 / 163
     - 427 / 183
     - 1.87 / 1.86
     - 1.77 / 1.34
     - 1.75 / 1.35
   * - 1 MB – 10 MB
     - 648 (18)
     - 316 / 121
     - 498 / 133
     - 617 / 155
     - 1.88 / 1.76
     - 1.76 / 1.04
     - 1.74 / 1.05
   * - ≥ 10 MB
     - 70 (8)
     - 247 / 70.6
     - 403 / 92.6
     - 506 / 114
     - 1.84 / 1.75
     - 1.72 / 0.81
     - 1.71 / 0.81

Throughput in MB/s, parsing / writing, over all sublibraries.
