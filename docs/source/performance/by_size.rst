.. warning::

   **Placeholder.** These numbers come from a few small test files
   of the repository, not from ENDF/B-VIII.1; they only show the
   layout of the page. The measurement over the sublibraries of
   ENDF/B-VIII.1 replaces them.

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
     - 1 (1)
     - 46.3 / 58.1
     - 46.5 / 59.6
     - 41.2 / 57.9
     - 0.93 / 1.64
     - 1.09 / 1.45
     - 1.10 / 1.65
   * - 100 kB – 1 MB
     - 1 (1)
     - 430 / 185
     - 369 / 150
     - 415 / 175
     - 10.2 / 5.60
     - 10.5 / 6.31
     - 9.82 / 6.15
   * - 1 MB – 10 MB
     - 2 (2)
     - 214 / 113
     - 397 / 122
     - 538 / 139
     - 1.70 / 1.43
     - 1.55 / 1.07
     - 1.49 / 1.02

Throughput in MB/s, parsing / writing, over all sublibraries.
