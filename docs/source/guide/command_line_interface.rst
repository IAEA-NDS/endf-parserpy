.. _command_line_interface:

Command Line Interface
======================

.. note::

   The command line interface is in an early development
   stage and the specific interface may be subject to change
   in the future. However, as it is deemed useful enough in its
   current form, it's been included in the released package.


Advanced operations on ENDF files can be implemented as a Python
script, which is explained in other sections of this guide.
However, common operations, such as retrieving specific data
or the validation of ENDF files, may be performed more
conveniently on the command line. After the installation of
``endf-parserpy``, the command line interface can be
accessed by invoking ``endf-cli`` with various parameters.

Help on the basic use of ``endf-cli`` can be directly
obtained on the command line by executing

.. code-block:: bash

   $ endf-cli --help

which yields

.. code-block:: text

   usage: endf-cli [-h] {compare,validate,replace,show,update-directory,insert-text,explain,match} ...

   Command-line interface to ENDF files

   positional arguments:
     {compare,validate,replace,show,update-directory,insert-text,explain,match}

     options:
       -h, --help            show this help message and exit


Basic help on subcommands, such as ``compare``, can also be obtained on the command line:

.. code-block:: bash

   endf-cli compare --help

However, the returned information is mostly useful
as a reminder of the syntax of the arguments.
Many parameters are related to the initialization
of the :class:`~endf_parserpy.EndfParser` class
and their meaning can be understood by consulting
the associated :ref:`help page <endf_parser_class>`.

Brief explanations of the various functionalities of the
command line interface are given in the following sections.


Comparing
---------

:ref:`Comparisons between ENDF files <guide_file_comparison>` can be performed by invoking

.. code-block:: bash

   endf-cli compare <endf-file1> <endf-file2>

You can also supply the arguments ``--atol`` and ``--rtol`` for specifying the
absolute and relative numerical tolerances, respectively, for the comparison of
:class:`float` numbers, e.g.

.. code-block:: bash

   endf-cli compare --atol 1e-10 --rtol 1e-6 file1.endf file2.endf


Validating
----------

For :ref:`validating the structural correctness of ENDF files <format_validation_sec>`, run

.. code-block:: bash

   endf-cli validate <endf-file1> <endf-file2> ...

The usual wildcards can be used for filenames, e.g. ``endf-cli validate *.endf``.
By default, syntactically valid files need to obey the format description provided
in the `ENDF-6 formats manual <https://doi.org/10.2172/1425114>`_, with some allowed
extensions for a proper parsing of some JENDL files. However,  this default
can be overriden by providing a specific ENDF format flavor as
``--endf_format`` argument. For example, for strict adherence to the ENDF-6 format,
run

.. code-block:: bash

   endf-cli validate --endf_format endf6 <endf-file1> ...

The available format flavors are ``endf6-ext`` (default), ``endf6``, ``pendf``,
and ``jendl``.




By default, the faster C++ parser (:class:`~endf_parserpy.EndfParserCpp`) is used,
which yields less detailed logging output in case of failure. For easier debugging,
you may want to use the ``--no-cpp`` argument, forcing the usage of the Python parser.
Then, also the ``--loglevel`` argument is useful to control the detail of logging output
(higher numbers producing less output). Here is an example invocation:

.. code-block:: bash

   endf-cli validate --no-cpp --loglevel 30 file.endf


Replacing/Inserting
-------------------

:ref:`Replacing/Inserting an MF/MT section <including_mfmt_sec>` from another
ENDF file is also possible on the command line. The syntax is as follows:

.. code-block:: bash

   endf-cli replace <EndfPath> <source-file> <target-file>


The information in the ``<source-file>`` ENDF file at the location
indicated by the :ref:`<EndfPath> <endf_path_class>`
is inserted (or replaced if already there) in the ``<target-file>`` ENDF file.
For instance, inserting MF1/MT451 of one ENDF file into another
one can be done by

.. code-block:: bash

   endf-cli replace /1/451 source.endf target.endf


Noteworthy, this command also works if ``target.endf``
is an empty file. To include a tape id (the first line of
an ENDF file) specify ``/0/0`` as EndfPath. Replacing content
can also be done on a more fine-grained level. As an advanced
example, a specific spingroup in MF2/MT151, can be replaced by

.. code-block:: bash

   endf-cli replace 2/151/isotope/1/range/1/spingroup/1 source.endf target.endf

During this fine-grained replacement, the :ref:`original string representation
of float numbers is preserved <guide_perfect_precision>`.
By default, a backup of the original file will be created with endfing ``.bak``.
If you want to skip the creation of a backup file, supply the ``-n`` argument.

.. note::

   Be aware that the directory in MF1/MT451 is not updated during
   an insertion/replacement procedure. :ref:`See below <updating_directory_cli>`
   how to update it to be in sync with the content of the file.


Showing information
-------------------

The content of an ENDF file can be browsed similar to a file system
via the ``show`` command:

.. code-block:: bash

   endf-cli show <EndfPath> <endf-file>

This command will produce a listing of variables and
their values that can be found under the specified
:ref:`<EndfPath> <endf_path_class>`.
For instance, to list the energy mesh for the total cross section (MF3/MT1),
execute

.. code-block:: bash

   endf-cli show /3/1/xstable/E file.endf

Or if you just want to know the available MF sections in a file, run

.. code-block:: bash

   endf-cli show / file.endf

Based on the output, you can then interactively explore the file content.
For example, if you see that MF3 is available, you can show all the available
MT numbers within:

.. code-block:: bash

   endf-cli show /3/ file.endf


.. _updating_directory_cli:

Updating the MF1/MT451 directory
--------------------------------

The directory listing in MF1/MT451 of an ENDF file (see :endf6manshort:`57`)
can be updated to be in sync with the file content
by running

.. code-block:: bash

   endf-cli update-directory <endf-file>

If you want to suppress the creation of a backup file
(with suffix ``.bak``), also pass the ``-n`` argument:

.. code-block:: bash

   endf-cli update-directory -n <endf-file>


Inserting free-form text
------------------------

Free-form text can be added to the descriptive
text in MF1/MT451 with the ``insert-text``
subcommand. Here is an example of how it can be used
on Linux and MacOS:

.. code-block:: bash

   endf-cli insert-text -l 0 file.endf <<EOF
   Text inserted at the beginning
   EOF

The text provided via standard input is inserted
after the line indicated via the ``-l`` argument.
Supply the ``-n`` switch if you want to suppress the
creation o a backup file.


Explaining symbol names
-----------------------

An experimental (and very incomplete feature) is the
display of explanations of symbol names, which can be
found in an ENDF file. For instance, assume that
you have displayed the content of the MF1/MT1 section
via ``endf-cli show 3/1 file.endf`` and are interested
in the meaning of the ``QM`` variable. You can run

.. code-block:: bash

   endf-cli explain 3/1/QM file.endf

This command will display the description on standard output.
Again, this feature is very incomplete and won't return information
for most symbol names existing in an ENDF file yet.


Matching ENDF files
-------------------

ENDF files can be matched according to values of variables
stored within them. The syntax is as follows:

.. code-block:: bash

   endf-cli match --query <MATCH-EXPR> <endf-file1> ...

This command will list all ENDF files among the ones provided
for which the ``<MATCH-EXPR>`` applies, and also all the variables
and associated values appearing in the ``<MATCH-EXPR>``.
Wildcards in file names are supported, e.g. ``*.endf``.
The ``<MATCH-EXPR>`` is composed of order relations between
symbol names (provided as EndfPath) and numbers, e.g.
``/3/1/ZA >= 26056`` that are potentially connected by logical
operators, e.g. ``/3/1/ZA <= 25056 & /1/451/LRP == 1``.

.. note::

   Please be aware that all :ref:`EndfPaths <endf_path_class>`
   must start with a ``/`` character, e.g. ``/3/1/ZA``. Otherwise,
   omitting the slash will yield an error message.


In more detail, the order relations ``==``, ``!=``, ``>``, ``>=``, ``<``, ``<=``
are supported. Regarding the logical operators, the unary ``not`` operator is
implemented by prefixing a relation by ``!``, e.g. ``! /3/1/ZA == 0``.
In addition, the following binary logical operators are supported:
logical-and ``&`` and logical-or ``|``. Brackets to group logical
expressions are also implemented. An example, showcasing the explained capabilities is given by

.. code-block:: bash

   endf-cli match --query "! /1/451/ZA == 0 & (/3/1/AWR <= 1000 | /3/1/ZA > 0)" *.endf

An advanced feature is the asterik wildcard ``*`` in an EndfPath, useful
for finding matches within arrays of values or subsections. For instance,
to match files whose energy mesh for the total cross section covers energies
larger than 1 MeV, execute

.. code-block:: bash

   endf-cli match --query "/3/1/xstable/E/* >= 1e6" *.endf

The asterisk can appear at any position in the EndfPath.
For instance, to match MF3/MT sections with a q-value
greater than zero, run

.. code-block:: bash

   endf-cli match --query "/3/*/QM > 0" *.endf


Regarding the use of the asterisk, be aware that a command, such as

.. code-block:: bash

   endf-cli match --query "/3/*/QM > 0 & /3/*/ZA > 26056

will also produce a match for a file if the individual comparisons
match for different sections, e.g. ``QM > 0`` for ``/3/1`` and
``ZA > 26056`` for ``/3/2``.

However, sometimes the desired behavior is to find a section where
both comparison relations are satisfied at the same time. This can
be accomplished with **EndfPath prefixes**:

.. code-block:: bash

   endf-cli match --query "/3/*( /QM > 0 & /ZA > 26056 )" *.endf

As can be seen, if a bracket is prefixed with an EndfPath, all
paths within the bracket will be relative to the outer path.
Therefore, this example invocation will only return MF3/MT sections
were both conditions are satisfied at the same time.
*As an important reminder, every EndfPath (and also the EndfPath prefix)
must start with a slash.*

EndfPath prefixes can also be nested, e.g.

.. code-block:: bash

   endf-cli match --query "/2/151( /AWR < 1000 | /isotope/*( /ZAI > 2000 ))" *.endf

Example output of this command may look like this:

.. code-block::

   match: n_2925_29-Cu-63_2.endf
     2/151/AWR = 62.389
     2/151/isotope/1/ZAI = 29063.0
   match: n_2925_29-Cu-63.endf
     2/151/AWR = 62.389
     2/151/isotope/1/ZAI = 29063.0
