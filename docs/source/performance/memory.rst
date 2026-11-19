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
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Neutrons
     - 100 kB – 1 MB
     - 1.2
     - 0.8
     - 0.8
     - 0.7
     - 0.7
     - 0.7
   * - Neutrons
     - 1 MB – 10 MB
     - 2.9
     - 1.3
     - 1.2
     - 2.9
     - 1.7
     - 1.6
   * - Neutrons
     - ≥ 10 MB
     - 8.0
     - 4.1
     - 2.3
     - 8.1
     - 8.2
     - 7.8
   * - Thermal neutron scattering
     - 100 kB – 1 MB
     - 1.6
     - 1.3
     - 1.1
     - 0.3
     - 1.7
     - 1.7
   * - Thermal neutron scattering
     - 1 MB – 10 MB
     - 3.1
     - 2.9
     - 3.9
     - 1.8
     - 1.5
     - 2.3
   * - Thermal neutron scattering
     - ≥ 10 MB
     - 3.8
     - 3.0
     - 4.0
     - 1.7
     - 1.6
     - 2.6
   * - Photonuclear
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Photonuclear
     - 100 kB – 1 MB
     - 2.4
     - 0.8
     - 0.8
     - 0.7
     - 1.9
     - 1.5
   * - Photonuclear
     - 1 MB – 10 MB
     - 2.7
     - 1.3
     - 1.5
     - 2.0
     - 1.9
     - 1.8
   * - Decay data
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Decay data
     - 100 kB – 1 MB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Photo-atomic
     - 100 kB – 1 MB
     - 2.3
     - 2.1
     - 2.3
     - 2.5
     - 2.2
     - 2.8
   * - Photo-atomic
     - 1 MB – 10 MB
     - 2.3
     - 2.0
     - 2.3
     - 2.5
     - 2.3
     - 2.9
   * - Standards
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Standards
     - 100 kB – 1 MB
     - 3.1
     - 1.5
     - 1.5
     - 2.2
     - 1.5
     - 2.5
   * - Standards
     - 1 MB – 10 MB
     - 4.4
     - 2.6
     - 2.4
     - 6.1
     - 3.6
     - 6.1
   * - Standards
     - ≥ 10 MB
     - 7.6
     - 3.6
     - 1.6
     - 4.7
     - 3.4
     - 2.5
   * - Protons
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Protons
     - 100 kB – 1 MB
     - 2.6
     - 0.9
     - 0.9
     - 1.7
     - 1.7
     - 1.7
   * - Protons
     - 1 MB – 10 MB
     - 3.3
     - 1.1
     - 1.1
     - 0.4
     - 1.8
     - 2.3
   * - Electro-atomic
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Electro-atomic
     - 100 kB – 1 MB
     - 2.5
     - 0.8
     - 0.8
     - 0.8
     - 0.0
     - 0.0
   * - Atomic relaxation
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Atomic relaxation
     - 100 kB – 1 MB
     - 3.1
     - 1.1
     - 1.3
     - 0.0
     - 1.3
     - 1.3
   * - Neutron-induced fission yields
     - 100 kB – 1 MB
     - 4.1
     - 2.1
     - 2.1
     - 4.1
     - 2.0
     - 4.1
   * - Spontaneous fission yields
     - 100 kB – 1 MB
     - 2.1
     - 2.1
     - 2.1
     - 4.1
     - 2.1
     - 4.1
   * - Light charged particles
     - < 100 kB
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
     - 0.0
   * - Light charged particles
     - 100 kB – 1 MB
     - 2.6
     - 0.9
     - 0.4
     - 0.0
     - 1.6
     - 1.6

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
     - n-008_O_016.endf (42.5 MB)
     - 421.8 MB
     - 216.3 MB
     - 121.1 MB
     - —
     - —
     - —
   * - Thermal neutron scattering
     - tsl-CinC8H8.endf (92.8 MB)
     - 863.4 MB
     - 565.5 MB
     - 399.0 MB
     - —
     - —
     - —
   * - Photonuclear
     - g-073_Ta_181.endf (9.20 MB)
     - 82.2 MB
     - 36.8 MB
     - 13.2 MB
     - —
     - —
     - —
   * - Decay data
     - dec-071_Lu_170.endf (0.33 MB)
     - 0.81 MB
     - 0.54 MB
     - 0.54 MB
     - —
     - —
     - —
   * - Photo-atomic
     - photoat-093_Np_000.endf (1.34 MB)
     - 2.70 MB
     - 2.70 MB
     - 2.70 MB
     - —
     - —
     - —
   * - Standards
     - std-092_U_235.endf (36.9 MB)
     - 296.3 MB
     - 145.7 MB
     - 63.5 MB
     - 297.3 MB
     - 212.2 MB
     - 143.0 MB
   * - Protons
     - p-029_Cu_063.endf (1.55 MB)
     - 5.40 MB
     - 1.62 MB
     - 1.62 MB
     - —
     - —
     - —
   * - Electro-atomic
     - e-091_Pa_000.endf (0.39 MB)
     - 1.08 MB
     - 0.27 MB
     - 0.27 MB
     - —
     - —
     - —
   * - Atomic relaxation
     - atom-093_Np_000.endf (0.23 MB)
     - 0.81 MB
     - 0.27 MB
     - 0.54 MB
     - —
     - —
     - —
   * - Neutron-induced fission yields
     - nfy-094_Pu_239.endf (0.51 MB)
     - 1.89 MB
     - 1.08 MB
     - 1.08 MB
     - —
     - —
     - —
   * - Spontaneous fission yields
     - sfy-092_U_238.endf (0.13 MB)
     - 0.54 MB
     - 0.27 MB
     - 0.27 MB
     - —
     - —
     - —
   * - Light charged particles
     - h-002_He_003.endf (0.46 MB)
     - 1.89 MB
     - 0.81 MB
     - 0.81 MB
     - 0.81 MB
     - 1.35 MB
     - 1.35 MB

The increase of the peak resident memory while parsing the largest
file of each sublibrary (— if it is not in the sample).
