.. _create_endf_file_sec:

Creating ENDF-6 Files from Scratch
==================================

You've managed to fit a spline, Pade
approximant or a nuclear physics model nicely to
experimental data. Now you are eager to put
your result into an ENDF-6 file for further
processing with `NJOY <http://www.njoy21.io/>`_
or submit it as a candidate file to
a nuclear data library project.

On this page, we go through the process of creating
an ENDF-6 file that will contain a total cross section
and an associated covariance matrix. Even though
this file will be quite minimal, the steps explained
here can be adjusted to include cross sections and
covariance matrices of more reaction channels.
Once you understand the general process,
you will be able to create hand-tailored ENDF-6 files
for your application needs.


Prerequisites
-------------

In order to create an ENDF-6 file from scratch with
endf-parserpy, you need the following:

- An understanding of the physical quantities defined
  in the `ENDF-6 formats manual <https://doi.org/10.2172/1425114>`_,
  e.g. such as mass number, charge number and cross section.
  You also need the manual to look up the variable names
  associated with those quantities.

- An understanding of how ENDF-6 recipes determine the
  structure of Python dictionaries with ENDF-6 data,
  which was explained :ref:`in this section <endf6_recipe_sec>`.

- The ENDF-6 recipe files corresponding to the
  MF/MT sections you want to create in order to determine
  the variables to be included in the Python dictionary.
  In general, the variable names in the recipes are the same
  as in the ENDF-6 formats manual.


.. note::

   If you just get started with the ENDF-6 format,
   these prerequisites may seem daunting. However,
   with endf-parserpy you can construct the dictionary
   step-by-step. If you forget to include a required
   variable, you will receive a detailed error message
   informing you about the missing variable(s).
   You can work in an interactive Python session to
   construct a complete dictionary by trial and error,
   incrementally including the missing variables.


Creating the dictionary
-----------------------

The Python dictionary we are going to create will include
the following MF/MT sections:

- An **MF1/MT451** section with meta data and a
  general description of the file content (:endf6manshort:`57`).
- An **MF3/MT1** section with tabulated total cross sections as a function of incident energy (:endf6manshort:`122`).
- An **MF33/MT1** section with a covariance matrix to express
  the uncertainty of the total cross section (:endf6manshort:`293`).


Creating the MF1/MT451 section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Section 1.1 in Chapter 1 of the :endf6manpage:`57`
lists all variables that need to be defined for the creation of an
MF1/MT451 section.
The `ENDF-6 recipe for MF1/MT451
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf_recipe_mf1_mt451.py>`_ also contains the required variable names and furthermore we can infer the
:ref:`structure of the Python dictionary <endf6_recipe_sec>` from it.
Because this ENDF-6 recipe is not too long, we also provide it
here for convenient reference:

.. code:: text

    [MAT, 1,451/ ZA, AWR, LRP, LFI, NLIB, NMOD]HEAD
    [MAT, 1,451/ ELIS, STA, LIS, LISO, 0, NFOR]CONT
    [MAT, 1,451/ AWI, EMAX, LREL, 0, NSUB, NVER]CONT
    [MAT, 1,451/ TEMP, 0.0, LDRV, 0, NWD, NXC]CONT

    [MAT, 1,451/ ZSYMAM{11}, ALAB{11}, EDATE{10}, {1}, AUTH{33} ]TEXT
    [MAT, 1,451/ {1}, REF{21}, DDATE{10}, {1},
                 RDATE{10}, {12}, ENDATE{8}, {3} ]TEXT
    for i=1 to 3:
        [MAT, 1,451/ HSUB[i]] TEXT
    endfor
    for i=1 to NWD-5:
        [MAT, 1,451/ DESCRIPTION[i]]TEXT
    endfor
    for i=1 to NXC:
        [MAT, 1,451/ blank, blank, MFx[i], MTx[i], NCx[i], MOD[i]]DIR
    endfor
    SEND

This recipe does not contain any section blocks, hence all variables
in this recipe must be available as keys in the root dictionary associated
with MF=1/MT=451. Let's first instantiate an :ref:`EndfParser <endf_parser_class>`
object:

.. code:: Python

   from endf_parserpy import EndfParser
   parser = EndfParser(explain_missing_variable=True)

Setting ``explain_missing_variable=True`` enables an experimental feature,
which will display the descripton of an omitted but required variable.
To faciliate the creation of the dictionary, we will make use of the
:ref:`EndfDict <endf_dict_class>` class for a more convenient dictionary
building process:

.. code:: Python

   from endf_parserpy.accessories import EndfDict
   endf_dict = EndfDict()

Next, we create an empty MF=1/MT=451 section and associate it with a
short variable name for reduced typing and perform our first
little variable assignment for the ``MAT`` number (:endf6manshort:`30`).
Let's assume we want to create a file for 26-Fe-54 which corresponds
to ``MAT=2625``.
The code to accomplish the described actions is given by:

.. code:: Python

   endf_dict['1/451'] = {}
   d = endf_dict['1/451']
   d['MAT'] = 2625

Let's see what happens when we attempt to convert the
data of this very empty dictionary into the ENDF-6 format using
the :func:`~endf_parserpy.endf_parser.EndfParser.write` method:

.. code:: Python

   parser.write(endf_dict)

This instruction yields the following error message:

.. code:: pycon

    endf_parserpy.custom_exceptions.VariableNotFoundError:
    Here is the parser record log until failure:
    --------------------------------------------
    Template:  [ MAT , 1 , 451 / ZA , AWR , LRP , LFI , NLIB , NMOD ] HEAD

    Error message: variable ZA not found

    Explanation of missing variable `1/451/ZA`
    ------------------------------------------
    ZA = (1000.0 * Z) + A
    Z ... charge number of material
    A ... mass number of material


This output displays the line in the ENDF-6 recipe that refers to
the missing variable, here ``ZA``.
Furthermore, we obtain the exact location (in :ref:`EndfPath <endf_path_class>` form)
where the missing variable is expected to be.
Based on this information, we can now add the missing variable:

.. code:: Python

   endf_dict['1/451/ZA'] = 1000.0 * 26 + 54  # 26054.0

The alternative assignment  ``p['ZA'] = 26054.0`` would have had the same effect.
One approach to completing the dictionary is calling ``parser.write(endf_dict)``
iteratively and add each time the variable that was reported until
the function doesn't complain anymore.
Probably a faster approach is to consult the explanations of the variables
in the :endf6manpage:`57` and define all of them at once.

Here is a (somewhat messy) example code snippet for defining
all quantities of an MF=1/MT=451 section:

.. code:: Python

    parser = EndfParser(explain_missing_variable=True)
    endf_dict = EndfDict()
    endf_dict['1/451'] = {}
    p = endf_dict['1/451']
    p['MAT'] = 2654;      p['ZA'] = 26*1000. + 54
    p['AWR'] = 53.47625 ; p['LRP'] = 2;      p['LFI'] = 0
    p['NLIB'] = 45;       p['NMOD'] = 1;     p['ELIS'] = 0.0
    p['STA'] = 0;         p['LIS'] = 0;      p['LISO'] = 0
    p['NFOR'] = 6;        p['AWI'] = 1.0;    p['EMAX'] = 2e8
    p['LREL'] = 0;        p['NSUB'] = 10;    p['NVER'] = 1
    p['TEMP'] = 0.0;      p['LDRV'] = 0;     p['NWD'] = 6
    p['NXC'] = 1;         p['ZSYMAM'] = ' 26-FE- 54 '
    p['ALAB'] = 'MyLab'.ljust(11)
    p['EDATE'] = 'EVAL-JAN24'
    p['AUTH'] = 'John Doe'.ljust(33)
    p['REF'] = 'ABC-2023'.ljust(21)
    p['DDATE'] = 'DIST-FEB24'
    p['RDATE'] = 'REV2-MAR24'
    p['ENDATE'] = '20240315'
    p['HSUB/1'] = (f'----LIBPROJ-{p["NVER"]}'.ljust(22) + f'MATERIAL {p["MAT"]}').ljust(66)
    p['HSUB/2'] = '-----INCIDENT NEUTRON DATA'.ljust(66)
    p['HSUB/3'] = '------ENDF-6 FORMAT'.ljust(66)
    p['DESCRIPTION/1'] = 'A new file is born with beautiful data!'.ljust(66)
    p['MFx/1'] = 1;   p['MTx/1'] = 451;  p['NCx/1'] = 5;  p['MOD/1'] = p['NMOD']


For understanding the meaning of a variable and its value, we can use the
:func:`~endf_parserpy.endf_parser.EndfParser.explain` method of the
:class:`~endf_parserpy.endf_parser.EndfParser` class, e.g.
``parser.explain('1/451/STA')``, or look up its description in the :endf6manpage:`57`.
These assignments are also a good opportunity to remind ourselves of how
:ref:`data types <data_types_sec>`
are assigned to variables: The variables in the first two slots of an ENDF record
are of type :class:`float` and the next four of type :class:`int`.

Importantly, we need to keep in mind that the ``NWD`` variable counts
the number of all TEXT records in MF1/MT451. The first five of these
records have a specific structure and only the subsequent TEXT records
(associated with the ``DESCRIPTION[i]`` array) can be filled with free-form text.
This means that the number of elements in the ``DESCRIPTION`` array
is ``NWD-5``. The preparation of the text fields in this section is still
a bit cumbersome.
Convenience functions may be added in the future to make the
handling of variables associated with strings easier so that the user
doesn't need to be concerned anymore about the alignment of strings in
text fields or the number of dashes preceding certain words.

Also note that the MF1/MT451
dictionary contains a directory (:endf6manshort:`57`) represented by
the arrays ``MFx[i]``, ``MTx[i]``, ``NCx[i]`` and ``MOD[i]``, which keeps
track of MF/MT sections included in the file and the number of ENDF records stored
in each of them.
We will synchronize this directory with the full file using
the :func:`~endf_parserpy.endf6_plumbing.update_directory` function once
we've added all required information to the dictionary.

Regarding the process, there are a lot of variables and it takes time
to understand their meaning and associate them with the right values.
On the positive side, issues regarding formatting, reading and writing
are completely decoupled from the specification of the data. In effect,
this approach emphasizes an *information-oriented* perspective
over a *processing-oriented* one. The user can focus on
the correct definition of variables and doesn't need to be concerned anymore
with the technical details of how the data is organized in an ENDF-6 file.

.. _creating_mf3mt1_sec:

Creating the MF3/MT1 section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The creation of the MF3/MT1 section (described on :endf6manshort:`122`)
with cross sections as a function of incident energy is straightforward.
The associated
`ENDF-6 recipe
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf_recipe_mf3.py>`_
is given by:

.. code:: text

    [MAT, 3, MT/ ZA, AWR, 0, 0, 0, 0] HEAD
    [MAT, 3, MT/ QM, QI, 0, LR, NR, NP / E / xs]TAB1 (xstable)
    SEND

We have encountered the variables ``ZA`` and ``AWR`` already in the creation
of the MF1/MT451 section above. The mass-difference Q-value for the
total cross section is zero, i.e. ``QM = 0.0``, and the same holds true
for the reaction Q-value, i.e. ``QI =  0.0``. Also the breakup flag is
given by ``LR = 0``.
For the total cross section, these values will be stored in an ``MT=1``
section. For the association between reaction channels and MT numbers
consult the :endf6manpage:`348`.

As discussed in the section about the :ref:`particularities of the TAB1 record
<particularities_tab1_tab2_record>`, the ``NR`` and ``NP`` variable are
ignored because their values can be inferred from the length of the
:class:`list` stored under the ``NBT`` and ``E`` variables.
Because of the presence of a `table body section
<https://arxiv.org/pdf/2312.08249.pdf#page=14>`_ named ``xstable``, the
variables ``NBT``, ``INT``, ``E`` and ``xs`` are supposed to be
in that section. Here we will use some dummy data for the excitation
function in the construction of the dictionary. We augment the dictionary
``endf_dict`` (being an :class:`~endf_parserpy.accessories.EndfDict` object)
introduced above (which already includes the MF1/MT451 section):


.. code:: Python

    endf_dict['3/1/MAT'] = endf_dict['1/451/MAT']
    endf_dict['3/1/AWR'] = endf_dict['1/451/AWR']
    endf_dict['3/1/ZA'] = endf_dict['1/451/ZA']
    endf_dict['3/1/QM'] = 0.0
    endf_dict['3/1/QI'] = 0.0
    endf_dict['3/1/LR'] = 0
    endf_dict['3/1/xstable/NBT'] = [5]
    endf_dict['3/1/xstable/INT'] = [2]
    endf_dict['3/1/xstable/E'] = [1.0, 2.0, 3.0, 4.0, 5.0]
    endf_dict['3/1/xstable/xs'] = [10.0, 11.0, 12.0, 13.0, 14.0]


We can rely on the description in the :endf6manpage:`122`,
the ENDF-6 recipe shown above and also the iterative approach based
on calls to ``parser.write(endf_dict)`` to learn about the missing
variables.
In the example code snippet here,
we worked with the original ``endf_dict`` instance.
Equally possible, we could have used an abbreviation,
such as ``p = endf_dict['3/1']`` for more concise specifications, e.g.
``p['QM'] = 0``.
Choosing ``NBT`` to be a list with a single entry given by the number of
elements in ``E`` (or ``xs``) means that we are using a single interpolation region.
The choice of ``INT = [2]`` specifies linear interpolation for that region.
For details on the available interpolation schemes, see
the :endf6manpage:`43`.

.. note::

    The parser doesn't check whether the values provided
    are physically meaningful. For instance, negative cross section
    values in ``xs`` or negative incident energies in ``E`` will be written
    by the :func:`~endf_parserpy.endf_parser.EndfParser.writefile` method to an ENDF-6 file as
    they are, without any warnings.


.. _creating_mf33_mt1_sec:

Creating the MF33/MT1 section
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Any measurement without knowledge of its uncertainty is meaningless
<https://youtu.be/GtOGurrUPmQ?t=263>`_.
Also evaluated nuclear data derived from a statistical analysis of
experimental data need to be given with uncertainty information.
The purpose of the MF33 section is the storage of covariance matrices
for the cross section data included in the MF3 section
(see :endf6manshort:`293`). There is an overwhelming number of options
and ways for storing these matrices. The aim of this section
is to walk you through the process for one specific and commonly
used approach.

We assume that you have a covariance matrix prepared as a
`numpy <https://numpy.org/>`_ array that contains
the relative uncertainties in the cross section values.
We've introduced five cross section points in the definition of
the MF3/MT1 dictionary discussed earlier. For simplicity, let's introduce a
covariance matrix associated with the same energy mesh as for
the cross sections, i.e. ``endf_dict['3/1/xstable/E']``.

.. note ::

   Cross sections stored under MF3 are defined at specific energies
   and linear interpolation (or other interpolation schemes)
   needs to be used to determine their values at
   intermediate energies. To refer to this approach, people often
   say that cross sections are stored *point-wise*. In contrast,
   a covariance matrix in an MF33 section is defined *group-wise*.
   This means that the energy mesh provides the boundaries between distinct groups and
   uncertainty information is provided for each energy group. Consult the
   :endf6manpage:`274` for more details. To keep this section manageable,
   we don't discuss this aspect further.

An example covariance matrix can be created with the following code snippet:

.. code:: python

   import numpy as np
   covmat = np.diag([0.04, 0.09, 0.16, 0.25])

With this specification including four elements together with the
adopted energies (``endf_dict['3/1/xstable/E']``), the uncertainty
is specified as 20% (square root of 0.04) between one and two eV,
30% between two and three electronvolt, etc. The numbers in
``endf_dict['3/1/xstable/E']`` were specified in the code snippet
introduced above :ref:`in the section about MF3/MT1 <creating_mf3mt1_sec>`.

.. _ENDF-6 recipe for MF33: https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf_recipe_mf33.py

The `ENDF-6 recipe for MF33`_ sections
is more complex and we don't include it in full here.
Instead, we consider the relevant parts in a step-by-step approach
for instructional purposes.
As before, we will use the ``endf_dict`` dictionary that already includes
the MF1/MT451 and MF3/MT1 sections. The goal of this last part of the
tutorial is to properly set up an MF33/MT1 section with the covariance
matrix for the total cross section.

The first line of the MF33 recipe is given by:

.. code:: text

   [MAT, 33, MT/ ZA, AWR, 0, MTL, 0, NL] HEAD

We've already encountered ``MAT``, ``ZA`` and ``AWR`` before.
The variable ``MTL`` indicates whether the covariance matrix
defined in this section is given by a sum of covariance matrices
from other MT sections in MF33. Here we directly provide our
covariance matrix, so ``MTL=0``.

Let's set up these variables:

.. code:: python

   endf_dict['33/1/MAT'] = endf_dict['1/451/MAT']
   endf_dict['33/1/ZA'] = endf_dict['1/451/ZA']
   endf_dict['33/1/AWR'] = endf_dict['1/451/AWR']
   endf_dict['33/1/MTL'] = 0

The ``NL`` variable defines the number of subsections.
The relevant part of the recipe looks like this:

.. code:: text

    if MTL == 0:
        for n=1 to NL:
        (subsection[n])
           ...
        (/subsection[n])
        endfor

Because of ``MTL = 0`` in our case, the part inside the if-block
is active. The integer stored in ``NL`` determines how
many ``subsection`` should be present in the dictionary.
Each subsection contains the covariance matrix
between the cross section data associated with this
MF33 section (here MF3/MT1) and another cross section
channel (determined by another MAT, MF, MT number
combination). In this guide, we only want to
include a single section that contains the covariance
matrix for MF33/MT1, hence ``NL = 1``.
Let's establish this assignment and create an empty ``subsection``:

.. code:: python

   endf_dict['33/1/NL'] = 1
   endf_dict['33/1/subsection[1]'] = {}

We could have also used the equivalent
:ref:`EndfPath notation <endf_path_class>` ``33/1/subsection/1``.

We descend further into the nested recipe structure to
determine which additional variables we still need to define:

.. code:: text

    for n=1 to NL:
        (subsection[n])
            [MAT,33,MT/ XMF1, XLFS1, MAT1, MT1, NC, NI]CONT
            ...
        (/subsection[n])
    endfor

The variables ``XMF1``, ``XLFS1```, ``MAT1`` and ``MT1``
specify to which other material/cross section combination
we want to define the covariance matrix, see also
:endf6manshort:`295`.
Because we are in the MF=33/MT=1 section for a covariance
matrix to a total cross section and we only provide the
matrix for that channel, by the convention laid out in
the manual, we have ``XMF1=0.0``, ``XLFS1=0.0``, ``MAT1=2625``
and ``MT1=1``:

.. code:: python

   endf_dict['33/1/subsection[1]/XMF1'] = 0.0
   endf_dict['33/1/subsection[1]/XLFS1'] = 0.0
   endf_dict['33/1/subsection[1]/MAT1'] = endf_dict['1/451/MAT']
   endf_dict['33/1/subsection[1]/MT1'] = 1

The complete covariance matrix can be composed of summing up several
covariance matrix, perhaps containg contributions associated
with different sources of uncertainty. Each of these contributions
is stored in its own sub-subsection. There are two types of sub-subsections
referred to as NI-type and NC-type. The variables ``NC`` and ``NI``
indicate the number of sub-subsection of the respective type.
We only want to include a single NI-type sub-subsection, so we have
the specification:

.. code:: python

   endf_dict['33/1/subsection[1]/NC'] = 0
   endf_dict['33/1/subsection[1]/NI'] = 1

There are different ways of storing the covariance matrix in
a sub-subsection. We will use the one indicated by
the variable assignment ``LB=5``. Furthermore, due to our
covariance matrix being symmetric, we can use the flag ``LS=1``
to indicate this situation and store only half of the elements.
These variables are described in the :endf6manpage:`301`.
We include here an abridged version of the relevant recipe part:

.. code:: text

    for m=1 to NI:
        (ni_subsection[m])
            if LB>=0 and LB<=4 [lookahead=1]:

                ...

            if LB==5 and LS==1 [lookahead=1]:

                ...

            endif

        (/ni_subsection[m])
    endfor

The ``lookahead=1`` specification informs the parser that
the variable names used in the logical expression may
be only defined within a certain number of ENDF records
(here 1) inside the if-branch, which is the
the case for the ``LB`` and ``LS`` variable.

To use the representation associated with ``LB=5`` and
``LS=1`` (:endf6manshort:`303`), we need to introduce the corresponding variables
in our dictionary:

.. code:: python

   endf_dict['33/1/subsection[1]/ni_subsection[1]/LB'] = 5
   endf_dict['33/1/subsection[1]/ni_subsection[1]/LS'] = 1


The ENDF record specifications inside the ``LB=5``, ``LS=1``
branch of the if-block tell us how the covariance matrix
should be stored:

.. code:: text

    NT := NE*(NE+1)/2
    [MAT,33,MT/ 0.0, 0.0, LS, LB, NT, NE/
      { E[k] }{ k=1 to NE }
      { {F[k,kp] }{ kp=k to NE-1} }{ k=1 to NE-1 } ]LIST

The variables ``LB`` and ``LS`` have already been defined above.
The variable ``NE`` contains the number of energy mesh points
for the covariance matrix. We use the same mesh as for
MF3/MT1 with five mesh points  (``endf_dict['3/1/xstable/E']``),
so ``NE=5``.


``NT`` is a placeholder variable whose value is defined in terms
of other variables, in our example ``NE``. We can ignore this variable
as any definition of this variable in the dictionary would be ignored
by the parser.
The energy mesh of the covariance matrix is stored in the array
``E[k]``. Importantly, ``E`` is a Python dictionary with contiguous
integer keys covering the range from 1 to ``NE``. We can
set up this dictionary with this code snippet:

.. code:: python

   energies = endf_dict['3/1/xstable/E']
   endf_dict['33/1/subsection[1]/ni_subsection[1]/NE'] = len(energies)
   endf_dict['33/1/subsection[1]/ni_subsection[1]/E'] = \
       {k: v for k, v in enumerate(energies, start=1)}

The first instruction retrieves the energies
from MF3/MT1 (given as a ``list`` object).
The second instruction assigns the correct value to ``NE``.
In the assignment accomplished by the third instruction,
the energies :class:`list` is converted to a :class:`dict` data type.
As the integer keys start at 1 (as can be inferred from
``{E[k]}{k=1 to NE}`` in the recipe snippet above, we need
to specify the argument ``start=1`` in the call to the
:func:`enumerate` function.
You may also consider :ref:`the section that elaborated on
the modification of arrays <modifying_arrays_sec>`

Finally (yes, we are almost done!), we need to put the covariance
matrix into the two-dimensional array ``F`` (again a repurposed
nested Python dictionary). The following code snippet achieves
this task:

.. code:: python

    NE = endf_dict['33/1/subsection[1]/ni_subsection[1]/NE']
	endf_dict['33/1/subsection[1]/ni_subsection[1]/F'] = {}
	F = endf_dict['33/1/subsection[1]/ni_subsection[1]/F']
	for k in range(1, NE):
		for kp in range(k, NE):
			F[k, kp] = float(covmat[k-1, kp-1])

The variable ``covmat`` was set up at the very beginning
of this section.
The structure of the two nested for-loops exactly reflects
the structure in the ENDF-6 recipe definition
(``{ {F[k,kp] }{ kp=k to NE-1} }{ k=1 to NE-1 }``).
Please note the notation ``F[k, kp]`` to set elements in
the nested dictionary is only possible because
``F`` is an :class:`~endf_parserpy.accessories.EndfDict` object.

After this quite lengthy explanation with all the pointers
to the ENDF-6 formats manual and also linking the building process of
the dictionary to the relevant parts in the ENDF-6
recipe, here is the Python code that assembles all the
code snippets introduced in this section in a single
script:

.. code:: python

    import numpy as np
    covmat = np.diag([0.1, 0.2, 0.3, 0.4])

    endf_dict['33/1'] = {}
    endf_dict['33/1/MAT'] = endf_dict['1/451/MAT']
    endf_dict['33/1/ZA'] = endf_dict['1/451/ZA']
    endf_dict['33/1/AWR'] = endf_dict['1/451/AWR']
    endf_dict['33/1/MTL'] = 0
    endf_dict['33/1/NL'] = 1
    endf_dict['33/1/subsection[1]'] = {}
    endf_dict['33/1/subsection[1]/XMF1'] = 0.0
    endf_dict['33/1/subsection[1]/XLFS1'] = 0.0
    endf_dict['33/1/subsection[1]/MAT1'] = endf_dict['1/451/MAT']
    endf_dict['33/1/subsection[1]/MT1'] = 1
    endf_dict['33/1/subsection[1]/NC'] = 0
    endf_dict['33/1/subsection[1]/NI'] = 1
    endf_dict['33/1/subsection[1]/ni_subsection[1]/LB'] = 5
    endf_dict['33/1/subsection[1]/ni_subsection[1]/LS'] = 1
    energies = endf_dict['3/1/xstable/E']
    endf_dict['33/1/subsection[1]/ni_subsection[1]/NE'] = len(energies)
    endf_dict['33/1/subsection[1]/ni_subsection[1]/E'] = \
       {k: v for k, v in enumerate(energies, start=1)}
    NE = endf_dict['33/1/subsection[1]/ni_subsection[1]/NE']
    endf_dict['33/1/subsection[1]/ni_subsection[1]/F'] = {}
    F = endf_dict['33/1/subsection[1]/ni_subsection[1]/F']
    for k in range(1, NE):
        for kp in range(k, NE):
            F[k, kp] = float(covmat[k-1, kp-1])


Adding the TPID record
~~~~~~~~~~~~~~~~~~~~~~

Complete ENDF-6 files also contain a TPID record at the very beginning
of the file (see :endf6manshort:`52`). It is a TEXT record whose text
field is ignored and hence may be used for version control information.
The MAT number is given by a *tape number* NTAPE, which we can set
to one. The MF and MT numbers in the control record must be zero.
Also the TPID record is defined in an `ENDF-6 recipe file
<https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf_recipe_mf0_mt0.py>`_
and we can add this record to our dictionary using the following assignments:

.. code:: python

   endf_dict['0/0/MAT'] = 1
   endf_dict['0/0/TAPEDESCR'] = 'some ignored description in the TPID record'


Updating the ENDF directory
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Being (hopefully) statisfied with our data, we need to wrap
it up by updating the directory in MF1/MT451.
The information we have at present in the directory is
given by:

.. code:: pycon

    >>> endf_dict['1/451/MFx']
    {1: 1}
    >>> endf_dict['1/451/MTx']
    {1: 451}
    >>> endf_dict['1/451/NCx']
    {1: 5}
    >>> endf_dict['1/451/MOD']
    {1: 1}

In words: During the construction of the MF1/MT451 we've included
a directory that accounted only for this section. As we have
added an MF3/MT1 and also MF33/MT1 section, this information
is outdated. We can update it using the
:func:`~endf_parserpy.endf6_plumbing.update_directory` function:

.. code:: python

   from endf_parserpy.end6_plumbing import update_directory
   update_directory(endf_dict, parser)


Let's check the udpated values:

.. code:: pycon

    >>> endf_dict['1/451/MFx']
    {1: 1, 2: 3, 3: 33}
    >>> endf_dict['1/451/MTx']
    {1: 451, 2: 1, 3: 1}
    >>> endf_dict['1/451/NCx']
    {1: 13, 2: 5, 3: 6}
    >>> endf_dict['1/451/MOD']
    {1: 1, 2: 0, 3: 0}

The result of the first two instructions indicate the MF/MT sections present
and the third instruction the number of ENDF records associated with each of these
sections, so we have:

- MF1/MT451: 13 ENDF records
- MF3/MT1: 5 ENDF records
- MF33/MT1: 6 ENDF records

To check whether the :func:`~endf_parserpy.endf6_plumbing.update_directory` function
has done a good job,
let's convert the data in ``endf_dict`` into the ENDF-6 format and print it:

.. code:: python

   lines = parser.write(endf_dict)
   print('\n'.join(lines))


This yields the following output:

.. code:: text

     2.605400+4 5.347625+1          2          0         45          12654 1451    1
     0.000000+0 0.000000+0          0          0          0          62654 1451    2
     1.000000+0 2.000000+8          0          0         10          12654 1451    3
     0.000000+0 0.000000+0          0          0          6          32654 1451    4
     26-FE- 54 MyLab      EVAL-JAN24 John Doe                         2654 1451    5
     ABC-2023             DIST-FEB24 REV2-MAR24            20240315   2654 1451    6
    ----LIBPROJ-1         MATERIAL 2654                               2654 1451    7
    -----INCIDENT NEUTRON DATA                                        2654 1451    8
    ------ENDF-6 FORMAT                                               2654 1451    9
    A new file is born!                                               2654 1451   10
                                    1        451         13          12654 1451   11
                                    3          1          5          02654 1451   12
                                   33          1          6          02654 1451   13
     0.000000+0 0.000000+0          0          0          0          02654 1  099999
     0.000000+0 0.000000+0          0          0          0          02654 0  0    0
     2.605400+4 5.347625+1          0          0          0          02654 3  1    1
     0.000000+0 0.000000+0          0          0          1          52654 3  1    2
              5          2                                            2654 3  1    3
     1.000000+0 1.000000+1 2.000000+0 1.100000+1 3.000000+0 1.200000+12654 3  1    4
     4.000000+0 1.300000+1 5.000000+0 1.400000+1                      2654 3  1    5
     0.000000+0 0.000000+0          0          0          0          02654 3  099999
     0.000000+0 0.000000+0          0          0          0          02654 0  0    0
     2.605400+4 5.347625+1          0          0          0          1265433  1    1
     0.000000+0 0.000000+0       2654          1          0          1265433  1    2
     0.000000+0 0.000000+0          1          5         15          5265433  1    3
     1.000000+0 2.000000+0 3.000000+0 4.000000+0 5.000000+0 1.000000-1265433  1    4
     0.000000+0 0.000000+0 0.000000+0 2.000000-1 0.000000+0 0.000000+0265433  1    5
     3.000000-1 0.000000+0 4.000000-1 0.000000+0 0.000000+0 0.000000+0265433  1    6
     0.000000+0 0.000000+0          0          0          0          0265433  099999
     0.000000+0 0.000000+0          0          0          0          02654 0  0    0
     0.000000+0 0.000000+0          0          0          0          0   0 0  0    0
     0.000000+0 0.000000+0          0          0          0          0  -1 0  0    0


Taking into account that the ``SEND`` (=Section end) records are not considered
for the counting,
we see that :func:`~endf_parserpy.endf6_plumbing.update_directory`
has indeed determined the correct number of ENDF records of each MF/MT section.

Summary
~~~~~~~

If you have followed along until here, you have a Python dictionary with
a general description, (dummy) total cross section data, and a
covariance matrix associated with the total cross section.
Congratulations! You can produce your awesome ENDF-6 file
with the :func:`~endf_parserpy.endf_parser.EndfParser.writefile` method:

.. code:: python

   parser.writefile('output.endf', endf_dict)


The Python code that has been introduced in this tutorial
in a step-by-step manner is listed in its full form
in the following Python script:

.. code:: python

    from endf_parserpy import EndfParser
    from endf_parserpy.accessories import EndfDict
    from endf_parserpy.endf6_plumbing import update_directory
    import numpy as np

    parser = EndfParser()

    endf_dict = EndfDict()

    # definition of MF1/MT451
    endf_dict['1/451'] = {}
    p = endf_dict['1/451']
    p['MAT'] = 2654;      p['ZA'] = 26*1000. + 54
    p['AWR'] = 53.47625 ; p['LRP'] = 2;      p['LFI'] = 0
    p['NLIB'] = 45;       p['NMOD'] = 1;     p['ELIS'] = 0.0
    p['STA'] = 0;         p['LIS'] = 0;      p['LISO'] = 0
    p['NFOR'] = 6;        p['AWI'] = 1.0;    p['EMAX'] = 2e8
    p['LREL'] = 0;        p['NSUB'] = 10;    p['NVER'] = 1
    p['TEMP'] = 0.0;      p['LDRV'] = 0;     p['NWD'] = 6
    p['NXC'] = 1;         p['ZSYMAM'] = ' 26-FE- 54 '
    p['ALAB'] = 'MyLab'.ljust(11)
    p['EDATE'] = 'EVAL-JAN24'
    p['AUTH'] = 'John Doe'.ljust(33)
    p['REF'] = 'ABC-2023'.ljust(21)
    p['DDATE'] = 'DIST-FEB24'
    p['RDATE'] = 'REV2-MAR24'
    p['ENDATE'] = '20240315'
    p['HSUB/1'] = (f'----LIBPROJ-{p["NVER"]}'.ljust(22) + f'MATERIAL {p["MAT"]}').ljust(66)
    p['HSUB/2'] = '-----INCIDENT NEUTRON DATA'.ljust(66)
    p['HSUB/3'] = '------ENDF-6 FORMAT'.ljust(66)
    p['DESCRIPTION/1'] = 'A new file is born!'.ljust(66)
    p['MFx/1'] = 1;   p['MTx/1'] = 451;  p['NCx/1'] = 5;  p['MOD/1'] = p['NMOD']

    # definition of MF3/MT1
    endf_dict['3/1/MAT'] = endf_dict['1/451/MAT']
    endf_dict['3/1/AWR'] = endf_dict['1/451/AWR']
    endf_dict['3/1/ZA'] = endf_dict['1/451/ZA']
    endf_dict['3/1/QM'] = 0.0
    endf_dict['3/1/QI'] = 0.0
    endf_dict['3/1/LR'] = 0
    endf_dict['3/1/xstable/NBT'] = [5]
    endf_dict['3/1/xstable/INT'] = [2]
    endf_dict['3/1/xstable/E'] = [1.0, 2.0, 3.0, 4.0, 5.0]
    endf_dict['3/1/xstable/xs'] = [10.0, 11.0, 12.0, 13.0, 14.0]

    # definition of MF33/MT1

    covmat = np.diag([0.1, 0.2, 0.3, 0.4])

    endf_dict['33/1'] = {}
    endf_dict['33/1/MAT'] = endf_dict['1/451/MAT']
    endf_dict['33/1/ZA'] = endf_dict['1/451/ZA']
    endf_dict['33/1/AWR'] = endf_dict['1/451/AWR']
    endf_dict['33/1/MTL'] = 0
    endf_dict['33/1/NL'] = 1
    endf_dict['33/1/subsection[1]'] = {}
    endf_dict['33/1/subsection[1]/XMF1'] = 0.0
    endf_dict['33/1/subsection[1]/XLFS1'] = 0.0
    endf_dict['33/1/subsection[1]/MAT1'] = endf_dict['1/451/MAT']
    endf_dict['33/1/subsection[1]/MT1'] = 1
    endf_dict['33/1/subsection[1]/NC'] = 0
    endf_dict['33/1/subsection[1]/NI'] = 1
    endf_dict['33/1/subsection[1]/ni_subsection[1]/LB'] = 5
    endf_dict['33/1/subsection[1]/ni_subsection[1]/LS'] = 1
    energies = endf_dict['3/1/xstable/E']
    endf_dict['33/1/subsection[1]/ni_subsection[1]/NE'] = len(energies)
    endf_dict['33/1/subsection[1]/ni_subsection[1]/E'] = \
       {k: v for k, v in enumerate(energies, start=1)}
    NE = endf_dict['33/1/subsection[1]/ni_subsection[1]/NE']
    endf_dict['33/1/subsection[1]/ni_subsection[1]/F'] = {}
    F = endf_dict['33/1/subsection[1]/ni_subsection[1]/F']
    for k in range(1, NE):
        for kp in range(k, NE):
            F[k, kp] = float(covmat[k-1, kp-1])

    # add the TPID record
    endf_dict['0/0/MAT'] = 1
    endf_dict['0/0/TAPEDESCR'] = 'some ignored description in the TPID record'

    # update the directory in MF1/MT451
    update_directory(endf_dict, parser)

    # output as a file
    parser.writefile('output.endf', endf_dict)

