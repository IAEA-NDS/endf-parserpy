.. _guide_format_extension:

Extending the ENDF-6 Format
===========================

endf-parserpy leverages
:ref:`ENDF-6 recipe files <endf6_recipe_sec>`
for reading and writing ENDF-6 files.
These recipe files are written in a
formal language described in
detail in `this ArXiv preprint
<https://arxiv.org/abs/2312.08249>`_.
This approach enables the addition of support
for format extensions by
updating these recipe files.
The Python source code of endf-parserpy
doesn't need to be touched.

In this tutorial, we want to demonstrate
this approach by including a format
extension to enable the storage
of covariance matrices relying on the
decomposition ``C = S A S^T``.
Therefore, we want to extend the format
to support the storage of two matrices
``S`` and ``A`` in an MF33 section.

As a first step, we retrieve all
ENDF-6 recipes used by endf-parserpy:

.. code:: python

    from endf_parserpy.endf_recipes import endf_recipe_dictionary

The variable ``endf_recipe_dictionary`` contains a dictionary
with all the available recipes.
If a recipe applies to all MT sections of an MF section, it
is directly stored under an integer key given by the MF number.
This is the case for the MF33 section, so we can print the corresponding
`MF33 recipe <https://github.com/IAEA-NDS/endf-parserpy/blob/main/endf_parserpy/endf_recipes/endf6/endf_recipe_mf33.py>`_:

.. code:: python

   print(endf_recipe_dictionary[33])


We reproduce the output for the part of the recipe
that is concerned with the different representations
of covariance matrices within an *NI-type subsection*,
see :endf6manpage:`301`:

.. code:: text

	if LB>=0 and LB<=4 [lookahead=1]:
		[MAT,33,MT/ 0.0, 0.0, LT, LB, 2*NP, NP/
			{Ek[k] , Fk[k]}{k=1 to (NP-LT)}
			{El[k] , Fl[k]}{k=1 to LT} ]LIST

	elif LB==5 and LS==0 [lookahead=1]:

		 ...

	elif LB==5 and LS==1 [lookahead=1]:

		 ...

	elif LB==6 [lookahead=1]:

		 ...

	elif (LB==8 or LB==9) and LT==0 [lookahead=1]:

		 ...

	endif


We can assign our format extension to a new ``LB`` number
and include the associated ENDF record specifications
in an additional if-branch. Choosing ``LB=10``, here
is a possible form of the additional branch:

.. code:: python

    format_extension = """

    elif LB==10 [lookahead=1]:
        numel := NE + (NE-1)*M + M*M
        [MAT, 33, MT / 0.0, 0.0, NE, LB, numel, M /
            { E[i] }{ i=1 to NE},
            {{ S[i,j] }{ i=1 to NE-1 }}{ j=1 to M },
            {{ A[i,j] }{ i=1 to M  }}{ j=1 to M }
        ] LIST

    """

The notation ``numel := ...``` introduces a
name for an expression that can be used
as an abbreviation in record specifications.

We can now include this additional representation
option into the ENDF-6 recipe dictionary:

.. code:: python

    from copy import deepcopy
    import re
    import numpy as np
    mf33_recipe = endf_recipe_dictionary[33]
    m = re.search(r'elif.*LB==8(.|\n)*?endif', mf33_recipe, re.MULTILINE)
    inspos = m.span()[1] - len('endif')
    new_mf33_recipe = mf33_recipe[:inspos] + format_extension + mf33_recipe[inspos:]
    new_recipe_dictionary = deepcopy(endf_recipe_dictionary)
    new_recipe_dictionary[33] = new_mf33_recipe

This code snippet finds the last ``elif ... endfif`` part
by regular expression matching and then introduces the
string with the format extension just before the word ``endif``.
We could have achieved the same by copy-pasting the
complete recipe specification into a text editor and
insert the format extension manually at the correct location.

To make :class:`~endf_parserpy.EndfParser` aware
of the format extension, we need to pass the ``recipes`` argument
with the updated ENDF recipe dictionary to its constructor:

.. code:: python

   parser = EndfParser(recipes=new_recipe_dictionary)


For the sake of illustration, let's create an
MF33/MT1 section making use of the format extension.
We can adopt a large of part of the set up from the
tutorial that covered the creation of an ENDF-6 file,
more precisely the :ref:`section that covered the
creation of MF33/MT1 <creating_mf33_mt1_sec>`.

The following code snippet sets up the generic part
specifying that we want to have one *NI-type subsection*:

.. code:: python

    endf_dict = EndfDict()
    endf_dict['33/1'] = {}
    endf_dict['33/1/MAT'] = 2625
    endf_dict['33/1/ZA'] = 26054
    endf_dict['33/1/AWR'] = 53.47625
    endf_dict['33/1/MTL'] = 0
    endf_dict['33/1/NL'] = 1
    endf_dict['33/1/subsection[1]'] = {}
    endf_dict['33/1/subsection[1]/XMF1'] = 0.0
    endf_dict['33/1/subsection[1]/XLFS1'] = 0.0
    endf_dict['33/1/subsection[1]/MAT1'] = 2625
    endf_dict['33/1/subsection[1]/MT1'] = 1
    endf_dict['33/1/subsection[1]/NC'] = 0
    endf_dict['33/1/subsection[1]/NI'] = 1


The next part is concerned with the representation
of the covariance matrix and we use here our
newly introduced ``LB=10`` option with some
dummy data for the energies ``E`` and the two
matrices ``S`` and ``A``:

.. code:: python

    energies = np.linspace(1, 10, 5)
    NE = len(energies)
    M = 2
    myS = np.full((NE-1, M), 1.)
    myA = np.full((M, M), 2.)

    endf_dict['33/1/subsection[1]/ni_subsection[1]/LB'] = 10
    endf_dict['33/1/subsection[1]/ni_subsection[1]/NE'] = NE
    endf_dict['33/1/subsection[1]/ni_subsection[1]/M'] = M

    endf_dict['33/1/subsection[1]/ni_subsection[1]/E'] = \
       {k: v for k, v in enumerate(energies, start=1)}

    endf_dict['33/1/subsection[1]/ni_subsection[1]/S'] = {}
    S = endf_dict['33/1/subsection[1]/ni_subsection[1]/S']
    for k in range(1, NE):
        for kp in range(1, M+1):
            S[k, kp] = float(myS[k-1, kp-1])

    endf_dict['33/1/subsection[1]/ni_subsection[1]/A'] = {}
    A = endf_dict['33/1/subsection[1]/ni_subsection[1]/A']
    for k in range(1, M+1):
        for kp in range(1, M+1):
            A[k, kp] = float(myA[k-1, kp-1])


Finally, we can output the data in the ENDF-6 format:

.. code:: python

   parser.writefile('output.endf', endf_dict)


Once you understand the `formal ENDF format description language
<https://arxiv.org/abs/2312.08249>`_.
you can quickly bend the format in any way you want to
test your ENDF-6 format extension proposals.
