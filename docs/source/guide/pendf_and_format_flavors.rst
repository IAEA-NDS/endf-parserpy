.. _pendf_and_format_flavors:

PENDF and Format Flavors
========================

Pointwise Evaluated Nuclear Data Files (PENDF)
can be produced by :ref:`processing codes <related_software>`,
such as NJOY2016. Compared to ENDF-6 files, PENDF files
contain data in representations tailored for use in application codes,
such as Monte Carlo transport and inventory codes.
For example, cross sections reconstructed from the resonance
parameter representation in MF2/MT151 (see :endf6manshort:`78`)
may be already included in MF3 sections (see :endf6manshort:`122`).
Another example are probability tables in the *Unresolved Resonance
Range*, which are also required in application codes.

While PENDF files do not strictly follow the ENDF-6 format,
their structure can still be well described by
:ref:`ENDF recipes <endf6_recipe_sec>` and considered as a
specific *ENDF format flavor*.
Support of PENDF files has therefore been implemented in ``endf-parserpy``.
The ENDF format flavor can be selected during initialization of the
:class:`~endf_parserpy.EndfParserPy` class using the ``endf_format`` argument.
To parse PENDF files, use the following initialization:

.. code:: python

   from endf_parserpy import EndfParserPy
   parser = EndfParserPy(endf_format='pendf')

Available ENDF flavors can be queried by

.. code:: python

   from endf_parserpy.endf_recipes import list_endf_flavors
   list_endf_flavors()
   # ('endf6-ext', 'endf6', 'jendl', 'pendf', 'errorr')

The default is ``endf6-ext``, which is a syntactical superset
of the ``endf6`` and ``jendl`` flavor. The ``errorr`` flavor
can be used to read files produced by the NJOY2016 ERRORR module
and, as for all other flavors, to modify and create them.

Using the ``pendf`` flavor, PENDF files produced by NJOY2016
can be parsed and also modified in the same way as explained
in :ref:`the section on ENDF-6 file plumbing <endf6_file_plumbing_sec>`.

.. note::

   Compared to ENDF-6 files, processed PENDF files can be
   significantly larger and therefore the time needed to
   parse them substantially increased. It is recommended
   to use the :class:`~endf_parserpy.EndfParserCpp` class
   for a more convenient user experience, i.e.
   ``parser = EndfParserCpp(endf_format='pendf')``


Plotting point-wise cross sections
----------------------------------

We provide example code that demonstrates
how point-wise cross sections can be plotted from a
PENDF file using the `matplotlib <https://matplotlib.org/>`_
Python package. Please note that for the time being only a single
material section in a PENDF file is supported. For inspiration how
to work around this limitation, consider the practical solution
explained in the :ref:`guide on working with legacy formats <working_with_legacy_formats_sec>`.

Plotting the total cross sections can be achieved by this code snippet:

.. code:: python

   import matplotlib.pyplot as plt
   from endf_parserpy import EndfParserPy
   parser = EndfParserPy(endf_format='pendf')
   endf_dict = parser.parsefile('file.pendf')
   energies = endf_dict[3][1]['xstable']['E']
   xsarr = endf_dict[3][1]['xstable']['xs']
   plt.plot(energies, xsarr)
   plt.show()


Probability tables
------------------

Probability tables are essential for calculating
self-shielded cross sections in the Unresolved Resonance Range (URR).
We provide an example code demonstrating how self-shielded cross sections
can be (approximately) calculated based on the information in an appropriately
prepared PENDF file. We provide the code without additional explanations,
hoping that it will be nevertheless sufficient inspiration for people
who are confronted with this advanced use case. Here is the code:

.. code:: python

    from endf_parserpy import EndfParserCpp
    from endf_parserpy.utils.user_tools import show_content
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt

    parser = EndfParserCpp(endf_format="pendf", array_type="list")
    # endf_dict = parser.parsefile("92U_235_stripped.pendf")
    endf_dict = parser.parsefile("92U_235_stripped.pendf")
    show_content(endf_dict[2][153])
    endf_dict[2][153].keys()

    sec = endf_dict[2][153]
    for en_idx, en in enumerate(sec["EUNR"]):
        colnames = ("PROB", "TOTL", "ELAS", "FISS", "CAPT", "HEAT")
        cols = {}
        for cname in colnames:
            cols[cname] = sec[cname][en_idx]
        dt = pd.DataFrame(cols)
        print(f"\n\n--- ENERGY: {en}")
        print(dt)
        print(f"sum of prob: {sum(dt['PROB'])}")


    sec152 = endf_dict[2][152]
    columns = ('SIGZ', 'STOT', 'SELAS', 'SFIS', 'SCAP', 'STRN')
    dt_list = []
    for en_idx, en in enumerate(sec152['EUNR']):
        print(f'--- energy: {en}')
        cols = {}
        for cname in columns:
            if cname != 'SIGZ':
                cols[cname] = sec152[cname][en_idx]
            else:
                cols[cname] = sec152[cname]
        # dt['EN'] = en
        dt = pd.DataFrame(cols)
        dt['EN'] = en
        dt_list.append(dt)

    xs_dt = pd.concat(dt_list, ignore_index=True)


    sigma0_mesh = np.logspace(np.log10(0.001), np.log10(100), 1000)
    xsname = "ELAS"
    en_idx = 0
    xsb_values = []

    for i, sigma0 in enumerate(sigma0_mesh):
        prob = np.array(sec['PROB'][en_idx])
        totl = np.array(sec['TOTL'][en_idx])
        xs = sec[xsname][en_idx]
        r1 = sum((prob * xs) / (sigma0 + totl))
        r2 = sum(prob / (sigma0 + totl))
        xsb = r1 / r2
        xsb_values.append(xsb)
        print(f'sigma0: {sigma0} --- xsb: {xsb}')

    plt.title(f"energy: {sec['EUNR'][en_idx]} --- {xsname}")
    plt.plot(sigma0_mesh, xsb_values)
    plt.show()


    xsname = "TOTL"
    sigma0_mesh = (1, 10, 100, 10**10)
    mapcol = {'TOTL': 'STOT', 'ELAS': 'SELAS', 'FISS': 'SFIS', 'CAPT': 'SCAP'}
    for sigma0 in sigma0_mesh:
        en_mesh = []
        xsb_values = []
        for en_idx, en in enumerate(sec['EUNR']):
            prob = np.array(sec['PROB'][en_idx])
            totl = np.array(sec['TOTL'][en_idx])
            xs = sec[xsname][en_idx]
            r1 = sum((prob * xs) / (sigma0 + totl))
            r2 = sum(prob / (sigma0 + totl))
            xsb = r1 / r2
            # infinite dilution cross section
            xs_infdil = xs_dt.loc[(xs_dt['SIGZ'] == 10**10) & (xs_dt['EN'] == en), mapcol[xsname]].iloc[0]
            en_mesh.append(en)
            xsb_values.append(xsb * xs_infdil)
        plt.plot(en_mesh, xsb_values)


    plt.title(f'{xsname}')
    plt.xscale('log')
    plt.yscale('log')
    # plt.ylim(10, 50)
    plt.show()





