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

.. tip::

   A complete, narrated end-to-end workflow that touches every
   ``endf-cli`` subcommand is provided as the runnable bash script
   ``examples/example-004-cli-workflow.sh`` in the source repository.

Help on the basic use of ``endf-cli`` can be directly
obtained on the command line by executing

.. code-block:: bash

   $ endf-cli --help

which yields

.. code-block:: text

   usage: endf-cli [-h]
                   {compare,convert,validate,replace,show,list-materials,update-directory,insert-text,insert-material,remove-material,explain,match}
                   ...

   Command-line interface to ENDF files

   positional arguments:
     {compare,convert,validate,replace,show,list-materials,update-directory,insert-text,insert-material,remove-material,explain,match}

     options:
       -h, --help            show this help message and exit


Basic help on subcommands, such as ``compare``, can also be obtained on the command line:

.. code-block:: bash

   endf-cli compare --help

However, the returned information is mostly useful
as a reminder of the syntax of the arguments.
Many parameters are related to the initialization
of the :class:`~endf_parserpy.EndfParserPy` class
and their meaning can be understood by consulting
the associated :ref:`help page <endf_parser_class>`.

Brief explanations of the various functionalities of the
command line interface are given in the following sections.


.. _cli_multimaterial:

Working with multi-material files
---------------------------------

An ENDF file (a *tape*) may contain more than one material. Every
``endf-cli`` subcommand handles such :ref:`multi-material files
<multimaterial_files_sec>` transparently. To list the materials on a
tape, run

.. code-block:: bash

   endf-cli list-materials <endf-file>

which prints one line per material, with its tape position, MAT number,
ZA and AWR.

Subcommands that take an :ref:`EndfPath <endf_path_class>` (``show``,
``explain``, ``replace``) accept a *material-qualified* path on a
multi-material tape. Such a path is an ordinary EndfPath prefixed with a
**material selector** and a ``/``. The selector always contains a ``#``,
and that ``#`` is what marks a path as material-qualified:

* ``#k`` selects the material at tape position ``k`` (zero-based), e.g.
  ``#0/3/2/AWR``;
* ``MAT#k`` selects the ``k``-th material carrying that MAT number, e.g.
  ``9237#1/3/2`` (useful for PENDF tapes that repeat a MAT number once
  per temperature). Use ``#0`` for the first — and, on an ordinary tape,
  only — material with that MAT number, e.g. ``2925#0/3/2``.

A bare MAT number *without* a ``#`` is **not** a selector: in a path,
``2925/3/2`` is an ordinary EndfPath (MF=2925/MT=3/...), because the
leading segment of a path is otherwise indistinguishable from an MF
number. Write ``2925#0/3/2`` to select by MAT number.

On a file that holds a single material the selector may be omitted, so
the plain paths described in the following sections keep working
unchanged. On a multi-material tape a selector-less path is rejected
with a listing of the available materials, so you can pick one.


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

When the files are :ref:`multi-material tapes <cli_multimaterial>`, their
materials are paired by MAT number before being compared (a repeated MAT
number is paired by order of appearance, so the ``k``-th occurrence in
one file is matched with the ``k``-th in the other). Each pair is then
compared field by field, and any material that has no counterpart in the
other file is reported as unpaired.


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

Unlike the other subcommands, ``endf-cli validate`` applies strict defaults to the
parsing-leniency flags out of the box. Specifically, ``ignore_number_mismatch``,
``ignore_zero_mismatch``, ``ignore_varspec_mismatch``, ``accept_spaces``,
``ignore_blank_lines``, ``ignore_send_records``, ``ignore_missing_tpid``,
``accept_nan_inf``, ``accept_d_exponent``, and ``accept_non_ascii`` all
default to ``False`` for
``validate``. Run
``endf-cli validate --help`` to see the per-flag defaults. Each flag can still be
relaxed individually on the command line, e.g.

.. code-block:: bash

   endf-cli validate --accept_spaces --ignore_blank_lines file.endf


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


Replacing content can also be done on a more fine-grained level. As an
advanced example, a specific spingroup in MF2/MT151, can be replaced by

.. code-block:: bash

   endf-cli replace 2/151/isotope/1/range/1/spingroup/1 source.endf target.endf

During this fine-grained replacement, the :ref:`original string representation
of float numbers is preserved <guide_perfect_precision>`.
By default, a backup of the original file will be created with ending ``.bak``.
If you want to skip the creation of a backup file, supply the ``-n`` argument.

The path may also address coarser units than a single section. An
``MF`` path replaces a whole MF file (every MT section it contains), and
a material-only path replaces an entire material:

.. code-block:: bash

   endf-cli replace /3 source.endf target.endf      # whole MF3 file
   endf-cli replace '#0' source.endf target.endf    # whole material #0

In both cases the addressed unit of the target is made equal to the
source's: target sections the source does not have are removed.

When the source or target is a :ref:`multi-material tape
<cli_multimaterial>`, prefix the path with a material selector, e.g.
``endf-cli replace '#0/1/451' source.endf target.endf``. By default the
given path is applied to *both* the source and the target, so this form
expects a material at position 0 in each file. When the location in the
source differs from the location in the target -- most commonly when
copying from a single-material reference file into one material of a
tape -- give the source location explicitly with ``--source-path``:

.. code-block:: bash

   endf-cli replace '#1/3/2/AWR' --source-path 3/2/AWR reference.endf tape.endf

Here ``3/2/AWR`` is read from the single-material ``reference.endf`` and
written into material ``#1`` of ``tape.endf``. The source and target
paths must address the same kind of object (both a field, both a
section, both a whole MF file or both a whole material).

.. note::

   Be aware that the directory in MF1/MT451 is not updated during
   an insertion/replacement procedure. :ref:`See below <updating_directory_cli>`
   how to update it to be in sync with the content of the file.


Inserting a material into a tape
--------------------------------

Whereas ``replace`` edits material(s) that already exist, the
``insert-material`` subcommand adds a whole *new* material from one file into a
:ref:`tape <cli_multimaterial>`:

.. code-block:: bash

   endf-cli insert-material --source-path <selector> <source-file> <target-file>

The ``--source-path`` argument is a :ref:`material selector
<cli_multimaterial>` (``#k`` or ``MAT#k``) picking the material to take
from ``<source-file>``; it is mandatory. By default the material is
appended at the end of the target tape. To place it at a specific
position, give ``--after`` with a material selector of the target -- the
new material is inserted right after it:

.. code-block:: bash

   # append the sole material of a single-material file to a tape
   endf-cli insert-material --source-path '#0' material.endf tape.endf

   # insert the 2nd material of one tape right after material #0 of another
   endf-cli insert-material --after '#0' --source-path '#1' source_tape.endf tape.endf

As with ``replace``, a backup of the target is created with suffix
``.bak`` unless the ``-n`` argument is supplied. To add or overwrite an
individual section or a whole MF file rather than a whole material, use
``replace``.


Removing a material from a tape
-------------------------------

The ``remove-material`` subcommand drops a material from a
:ref:`tape <cli_multimaterial>`:

.. code-block:: bash

   endf-cli remove-material <selector> <endf-file> ...

The ``<selector>`` is a :ref:`material selector <cli_multimaterial>`
(``#k`` or ``MAT#k``) identifying the material to remove. Several files
may be given, and the material is removed from each. Removing the only
material of a file leaves a valid, empty tape. A backup with suffix
``.bak`` is created unless ``-n`` is supplied.


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

Or if you just want to know the sections (MF/MT pairs) available in a
file, run

.. code-block:: bash

   endf-cli show / file.endf

Based on the output, you can then interactively explore the file content.
For example, if you see that MF3 is available, you can list the MT
numbers within:

.. code-block:: bash

   endf-cli show /3/ file.endf

On a :ref:`multi-material tape <cli_multimaterial>`, prefix the path with
a material selector, e.g. ``endf-cli show '#0/3/1' file.endf``; a bare
``#0`` lists every section of that material.


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
creation of a backup file.

On a :ref:`multi-material tape <cli_multimaterial>` the material whose
description is to be modified must be selected with the ``-m`` argument,
e.g. ``-m '#0'``, ``-m 2925`` or ``-m '9237#1'``. On a single-material
file the ``-m`` argument may be omitted.


Converting between ENDF and JSON
--------------------------------

:ref:`Converting between the ENDF and JSON format <guide_format_translation>`
can be accomplished with the ``convert`` subcommand.
To convert an ENDF file to JSON, run

.. code-block:: bash

   endf-cli convert --to json <source-endf-file> <target-json-file>

For the opposite direction to convert a JSON file to ENDF, use the command

.. code-block:: bash

   endf-cli convert --to endf <source-json-file> <target-endf-file>


A single-material file is converted to a JSON *object*, whereas a
:ref:`multi-material tape <cli_multimaterial>` is converted to a JSON
*array* with one object per material. The opposite direction recognises
the two cases by the type of the top-level JSON value, so a tape
round-trips through JSON without any extra arguments.

These commands will fail if the target file already exists.
You may want to consider the additional argument ``--array_type=list``,
which will produce a more compact JSON representation. The precise
meaning of this option is explained in :ref:`this section <arrays_as_list_sec>`.
Please note that if you've converted an ENDF file to JSON using this option,
you'll need to use the same option to convert the resulting file back
to the ENDF format. Otherwise, the conversion process will fail.


Explaining symbol names
-----------------------

An experimental (and very incomplete feature) is the
display of explanations of symbol names, which can be
found in an ENDF file. For instance, assume that
you have displayed the content of the MF3/MT1 section
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

This command will list all ENDF materials among the files provided
for which the ``<MATCH-EXPR>`` applies, and also all the variables
and associated values appearing in the ``<MATCH-EXPR>``.
Wildcards in file names are supported, e.g. ``*.endf``.
The exit code follows the ``grep`` convention: ``0`` if at least one
material matched, ``1`` if none did, and ``2`` if a file or material
could not be parsed -- so ``match`` can be used as a test in a script.
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

   endf-cli match --query "/3/*/QM > 0 & /3/*/ZA > 26056" *.endf

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
