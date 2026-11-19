.. rubric:: Neutrons

558 files, 1342.4 MB; the sample: 12 files, 62.2 MB.

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
     - 558
     - 4.41 s ±3.0 %
     - 304
     - 9.90 s ±3.3 %
     - 145
   * - ``EndfParserCpp`` ``list``
     - 558
     - 2.57 s ±2.6 %
     - 522
     - 9.21 s ±1.6 %
     - 155
   * - ``EndfParserCpp`` ``numpy``
     - 558
     - 1.78 s ±3.6 %
     - 756
     - 7.96 s ±2.0 %
     - 180
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 12
     - 34.8 s ±1.3 %
     - 1.79
     - 39.7 s ±1.0 %
     - 1.67
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 12
     - 37.4 s ±0.7 %
     - 1.66
     - 1.5 min ±0.2 %
     - 0.74
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 12
     - 37.5 s ±0.6 %
     - 1.66
     - 1.5 min ±0.5 %
     - 0.75

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 156
     - 84
   * - ``list``
     - 362
     - 213
   * - ``numpy``
     - 631
     - 243

.. rubric:: Thermal neutron scattering

114 files, 1540.5 MB; the sample: 9 files, 81.8 MB.

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
     - 114
     - 6.09 s ±1.8 %
     - 253
     - 26.0 s ±1.4 %
     - 63.1
   * - ``EndfParserCpp`` ``list``
     - 114
     - 4.12 s ±2.3 %
     - 374
     - 19.9 s ±1.1 %
     - 82.5
   * - ``EndfParserCpp`` ``numpy``
     - 114
     - 3.76 s ±2.3 %
     - 410
     - 16.3 s ±1.6 %
     - 101
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 9
     - 36.7 s ±1.1 %
     - 2.23
     - 44.5 s ±1.1 %
     - 1.96
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 9
     - 39.1 s ±0.3 %
     - 2.09
     - 1.7 min ±0.4 %
     - 0.86
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 9
     - 39.4 s ±0.5 %
     - 2.07
     - 1.7 min ±0.3 %
     - 0.87

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 129
     - 39
   * - ``list``
     - 188
     - 108
   * - ``numpy``
     - 216
     - 138

.. rubric:: Photonuclear

222 files, 462.8 MB; the sample: 7 files, 9.10 MB.

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
     - 222
     - 1.42 s ±3.2 %
     - 325
     - 3.32 s ±3.0 %
     - 148
   * - ``EndfParserCpp`` ``list``
     - 222
     - 797 ms ±4.4 %
     - 581
     - 3.16 s ±1.8 %
     - 156
   * - ``EndfParserCpp`` ``numpy``
     - 222
     - 510 ms ±2.5 %
     - 908
     - 2.74 s ±1.6 %
     - 180
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 7
     - 6.03 s ±0.8 %
     - 1.51
     - 7.14 s ±0.5 %
     - 1.36
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 7
     - 6.49 s ±0.9 %
     - 1.40
     - 10.4 s ±0.3 %
     - 0.93
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 7
     - 6.64 s ±0.7 %
     - 1.37
     - 10.3 s ±0.5 %
     - 0.94

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 211
     - 103
   * - ``list``
     - 393
     - 161
   * - ``numpy``
     - 625
     - 182

.. rubric:: Decay data

3821 files, 63.9 MB; the sample: 6 files, 0.47 MB.

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
     - 3821
     - 654 ms ±5.1 %
     - 97.8
     - 803 ms ±4.5 %
     - 84.8
   * - ``EndfParserCpp`` ``list``
     - 3821
     - 636 ms ±4.6 %
     - 100
     - 792 ms ±3.4 %
     - 86.0
   * - ``EndfParserCpp`` ``numpy``
     - 3821
     - 644 ms ±4.4 %
     - 99.2
     - 812 ms ±4.7 %
     - 83.9
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 6
     - 699 ms ±1.0 %
     - 0.67
     - 387 ms ±0.7 %
     - 1.29
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 6
     - 709 ms ±0.5 %
     - 0.66
     - 549 ms ±1.1 %
     - 0.91
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 6
     - 713 ms ±0.9 %
     - 0.66
     - 546 ms ±0.9 %
     - 0.92

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 198
     - 61
   * - ``list``
     - 207
     - 88
   * - ``numpy``
     - 211
     - 84

.. rubric:: Photo-atomic

100 files, 84.8 MB; the sample: 6 files, 5.47 MB.

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
     - 100
     - 248 ms ±2.5 %
     - 342
     - 401 ms ±2.3 %
     - 226
   * - ``EndfParserCpp`` ``list``
     - 100
     - 247 ms ±3.1 %
     - 344
     - 401 ms ±2.2 %
     - 225
   * - ``EndfParserCpp`` ``numpy``
     - 100
     - 210 ms ±2.8 %
     - 404
     - 349 ms ±1.9 %
     - 259
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 6
     - 583 ms ±1.5 %
     - 9.38
     - 892 ms ±1.5 %
     - 6.53
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 6
     - 570 ms ±1.5 %
     - 9.59
     - 926 ms ±0.8 %
     - 6.29
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 6
     - 584 ms ±0.5 %
     - 9.36
     - 912 ms ±1.2 %
     - 6.39

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 36
     - 35
   * - ``list``
     - 36
     - 36
   * - ``numpy``
     - 43
     - 41

.. rubric:: Standards

11 files, 62.7 MB; the sample: 10 files, 62.0 MB.

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
     - 11
     - 217 ms ±3.5 %
     - 289
     - 451 ms ±2.9 %
     - 148
   * - ``EndfParserCpp`` ``list``
     - 11
     - 98.5 ms ±2.3 %
     - 636
     - 413 ms ±1.0 %
     - 162
   * - ``EndfParserCpp`` ``numpy``
     - 11
     - 51.4 ms ±7.7 %
     - 1218
     - 350 ms ±2.9 %
     - 191
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 10
     - 39.3 s ±1.4 %
     - 1.58
     - 39.2 s ±1.5 %
     - 1.69
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 10
     - 41.7 s ±0.3 %
     - 1.49
     - 1.1 min ±0.2 %
     - 0.97
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 10
     - 41.7 s ±0.4 %
     - 1.49
     - 1.1 min ±0.3 %
     - 0.97

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 182
     - 88
   * - ``list``
     - 427
     - 167
   * - ``numpy``
     - 823
     - 196

.. rubric:: Protons

49 files, 51.7 MB; the sample: 9 files, 6.12 MB.

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
     - 49
     - 187 ms ±1.7 %
     - 277
     - 444 ms ±2.6 %
     - 124
   * - ``EndfParserCpp`` ``list``
     - 49
     - 112 ms ±2.9 %
     - 463
     - 414 ms ±1.9 %
     - 133
   * - ``EndfParserCpp`` ``numpy``
     - 49
     - 73.3 ms ±3.9 %
     - 706
     - 354 ms ±2.2 %
     - 156
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 9
     - 4.69 s ±1.4 %
     - 1.30
     - 5.42 s ±1.3 %
     - 1.20
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 9
     - 5.07 s ±0.3 %
     - 1.21
     - 7.27 s ±0.3 %
     - 0.90
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 9
     - 5.21 s ±0.3 %
     - 1.17
     - 7.22 s ±0.3 %
     - 0.90

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 208
     - 103
   * - ``list``
     - 371
     - 148
   * - ``numpy``
     - 562
     - 171

.. rubric:: Electro-atomic

100 files, 25.6 MB; the sample: 4 files, 0.87 MB.

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
     - 100
     - 127 ms ±3.0 %
     - 201
     - 197 ms ±2.8 %
     - 139
   * - ``EndfParserCpp`` ``list``
     - 100
     - 99.4 ms ±3.3 %
     - 257
     - 185 ms ±2.7 %
     - 147
   * - ``EndfParserCpp`` ``numpy``
     - 100
     - 82.1 ms ±3.0 %
     - 312
     - 159 ms ±2.2 %
     - 171
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 4
     - 553 ms ±1.8 %
     - 1.57
     - 599 ms ±0.5 %
     - 1.54
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 4
     - 598 ms ±1.8 %
     - 1.45
     - 797 ms ±0.6 %
     - 1.16
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 4
     - 612 ms ±1.3 %
     - 1.42
     - 787 ms ±0.8 %
     - 1.17

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 128
     - 91
   * - ``list``
     - 176
     - 129
   * - ``numpy``
     - 217
     - 147

.. rubric:: Atomic relaxation

100 files, 8.33 MB; the sample: 6 files, 0.58 MB.

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
     - 100
     - 33.2 ms ±6.1 %
     - 251
     - 40.9 ms ±7.5 %
     - 217
   * - ``EndfParserCpp`` ``list``
     - 100
     - 27.5 ms ±5.8 %
     - 303
     - 37.1 ms ±5.1 %
     - 239
   * - ``EndfParserCpp`` ``numpy``
     - 100
     - 26.6 ms ±4.5 %
     - 314
     - 37.5 ms ±3.9 %
     - 237
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 6
     - 243 ms ±1.3 %
     - 2.39
     - 253 ms ±1.2 %
     - 2.44
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 6
     - 252 ms ±1.2 %
     - 2.30
     - 341 ms ±1.3 %
     - 1.81
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 6
     - 248 ms ±2.4 %
     - 2.33
     - 340 ms ±1.1 %
     - 1.82

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 108
     - 90
   * - ``list``
     - 139
     - 134
   * - ``numpy``
     - 143
     - 134

.. rubric:: Neutron-induced fission yields

31 files, 6.66 MB; the sample: 3 files, 0.63 MB.

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
     - 31
     - 18.5 ms ±2.9 %
     - 359
     - 41.7 ms ±1.9 %
     - 170
   * - ``EndfParserCpp`` ``list``
     - 31
     - 10.1 ms ±3.8 %
     - 660
     - 31.5 ms ±1.7 %
     - 225
   * - ``EndfParserCpp`` ``numpy``
     - 31
     - 7.83 ms ±3.1 %
     - 850
     - 32.0 ms ±1.5 %
     - 222
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 3
     - 311 ms ±2.6 %
     - 2.04
     - 337 ms ±1.4 %
     - 2.01
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 3
     - 330 ms ±1.3 %
     - 1.92
     - 654 ms ±0.4 %
     - 1.03
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 3
     - 321 ms ±1.3 %
     - 1.98
     - 655 ms ±1.1 %
     - 1.03

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 176
     - 85
   * - ``list``
     - 342
     - 219
   * - ``numpy``
     - 427
     - 216

.. rubric:: Spontaneous fission yields

9 files, 1.15 MB; the sample: 3 files, 0.38 MB.

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
     - 9
     - 3.17 ms ±3.0 %
     - 365
     - 7.19 ms ±1.5 %
     - 171
   * - ``EndfParserCpp`` ``list``
     - 9
     - 1.95 ms ±8.8 %
     - 593
     - 5.56 ms ±7.7 %
     - 221
   * - ``EndfParserCpp`` ``numpy``
     - 9
     - 1.53 ms ±2.4 %
     - 756
     - 5.66 ms ±1.5 %
     - 217
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 3
     - 201 ms ±1.1 %
     - 1.91
     - 205 ms ±1.7 %
     - 2.00
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 3
     - 209 ms ±0.9 %
     - 1.84
     - 396 ms ±0.6 %
     - 1.03
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 3
     - 203 ms ±1.6 %
     - 1.89
     - 400 ms ±1.3 %
     - 1.02

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 189
     - 85
   * - ``list``
     - 323
     - 215
   * - ``numpy``
     - 405
     - 213

.. rubric:: Light charged particles

The sublibraries ``deuterons``, ``tritons``, ``helium3s``, ``alphas``, as one group.

20 files, 3.01 MB; the sample: 19 files, 2.88 MB.

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
     - 20
     - 11.1 ms ±2.9 %
     - 271
     - 20.4 ms ±2.9 %
     - 157
   * - ``EndfParserCpp`` ``list``
     - 20
     - 7.75 ms ±3.6 %
     - 388
     - 18.8 ms ±2.1 %
     - 171
   * - ``EndfParserCpp`` ``numpy``
     - 20
     - 6.56 ms ±3.7 %
     - 459
     - 17.4 ms ±2.1 %
     - 184
   * - ``EndfParserPy`` ``dict``\ :sup:`*`
     - 19
     - 1.65 s ±1.7 %
     - 1.74
     - 1.88 s ±1.0 %
     - 1.63
   * - ``EndfParserPy`` ``list``\ :sup:`*`
     - 19
     - 1.78 s ±1.7 %
     - 1.62
     - 2.62 s ±0.7 %
     - 1.17
   * - ``EndfParserPy`` ``numpy``\ :sup:`*`
     - 19
     - 1.81 s ±1.6 %
     - 1.59
     - 2.59 s ±0.9 %
     - 1.19

.. list-table:: Time of EndfParserPy over EndfParserCpp, on the sample
   :header-rows: 1

   * - ``array_type``
     - Parse
     - Write
   * - ``dict``
     - 155
     - 96
   * - ``list``
     - 241
     - 146
   * - ``numpy``
     - 292
     - 156
