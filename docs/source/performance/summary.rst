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
     - 304 / 145
     - 522 / 155
     - 756 / 180
     - 1.79 / 1.67
     - 1.66 / 0.74
     - 1.66 / 0.75
   * - Thermal neutron scattering
     - 253 / 63.1
     - 374 / 82.5
     - 410 / 101
     - 2.23 / 1.96
     - 2.09 / 0.86
     - 2.07 / 0.87
   * - Photonuclear
     - 325 / 148
     - 581 / 156
     - 908 / 180
     - 1.51 / 1.36
     - 1.40 / 0.93
     - 1.37 / 0.94
   * - Decay data
     - 97.8 / 84.8
     - 100 / 86.0
     - 99.2 / 83.9
     - 0.67 / 1.29
     - 0.66 / 0.91
     - 0.66 / 0.92
   * - Photo-atomic
     - 342 / 226
     - 344 / 225
     - 404 / 259
     - 9.38 / 6.53
     - 9.59 / 6.29
     - 9.36 / 6.39
   * - Standards
     - 289 / 148
     - 636 / 162
     - 1218 / 191
     - 1.58 / 1.69
     - 1.49 / 0.97
     - 1.49 / 0.97
   * - Protons
     - 277 / 124
     - 463 / 133
     - 706 / 156
     - 1.30 / 1.20
     - 1.21 / 0.90
     - 1.17 / 0.90
   * - Electro-atomic
     - 201 / 139
     - 257 / 147
     - 312 / 171
     - 1.57 / 1.54
     - 1.45 / 1.16
     - 1.42 / 1.17
   * - Atomic relaxation
     - 251 / 217
     - 303 / 239
     - 314 / 237
     - 2.39 / 2.44
     - 2.30 / 1.81
     - 2.33 / 1.82
   * - Neutron-induced fission yields
     - 359 / 170
     - 660 / 225
     - 850 / 222
     - 2.04 / 2.01
     - 1.92 / 1.03
     - 1.98 / 1.03
   * - Spontaneous fission yields
     - 365 / 171
     - 593 / 221
     - 756 / 217
     - 1.91 / 2.00
     - 1.84 / 1.03
     - 1.89 / 1.02
   * - Light charged particles\ :sup:`†`
     - 271 / 157
     - 388 / 171
     - 459 / 184
     - 1.74 / 1.63
     - 1.62 / 1.17
     - 1.59 / 1.19
   * - **All**
     - 272 / 93.5
     - 419 / 113
     - 511 / 134
     - 1.85 / 1.76
     - 1.73 / 0.88
     - 1.72 / 0.88

Throughput in MB/s (1 MB = 10\ :sup:`6` bytes), parsing / writing:
the bytes of the files over the time of ``parsefile``, and the bytes
written over the time of ``write``, summed over the files of the
sublibrary.

\ :sup:`*` On the sample of 94 files (see below). \ :sup:`†` Deuterons, tritons, helium-3 and alphas, which have only a few files each, as one group.

Measured on 2026-11-19 with a development version of endf-parserpy after 0.18.0 (v0.18.0-268-g6daa570).
