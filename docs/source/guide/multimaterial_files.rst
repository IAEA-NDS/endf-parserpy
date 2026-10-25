.. _multimaterial_files_sec:

Multi-Material Files
====================

An ENDF-6 file may contain several materials, stored one
after another; such a file is traditionally called a *tape*.
The :ref:`ordinary parser <getting_started_sec>` expects a
single material per file, but ``endf-parserpy`` provides a
dedicated interface for tapes. It also covers the PENDF
tapes produced by :ref:`processing codes <related_software>`,
which repeat the same material at several temperatures.
On this page, we explain how to read, write and navigate
such files.

Reading and writing a tape
--------------------------

The :func:`~endf_parserpy.parse_tape_file` function reads a
multi-material file and returns a list with one entry per
material:

.. code:: Python

   from endf_parserpy import parse_tape_file
   materials = parse_tape_file('tape.endf')  # one entry per material
   len(materials)                            # number of materials

Each tape operation comes as a pair: the ``_file`` variant
works on a file path, the bare name on an ENDF-6 tape held in
a string. :func:`~endf_parserpy.parse_tape_file` reads a file,
:func:`~endf_parserpy.parse_tape` parses a string. Each entry
of the list is an ordinary
dictionary, identical to what the
:func:`~endf_parserpy.EndfParserPy.parsefile` method returns
for a single-material file, and is therefore indexed by MF
and then by MT number:

.. code:: Python

   material = materials[0]      # the first material, a dict
   section = material[3][2]     # its MF=3/MT=2 section, also a dict
   section['AWR']               # a field of that section

As for :func:`~endf_parserpy.EndfParserPy.parsefile`, the
``include`` and ``exclude`` arguments restrict parsing to
parts of each material; sections that are not parsed are
kept as lists of raw strings:

.. code:: Python

   # parse only MF=3 of every material, keep the rest as raw text
   materials = parse_tape_file('tape.endf', include=[3])

Because each material is an ordinary dictionary, modifying the
data before writing it back is a plain assignment. To change,
for instance, the atomic weight ratio in the MF1/MT451 section
of the first material:

.. code:: Python

   materials[0][1][451]['AWR'] = 63.5   # modify a value in place

The :ref:`guide on ENDF-6 file plumbing <endf6_file_plumbing_sec>`
covers modifying, adding and deleting data in more depth; the
same operations apply to every material of a tape.

The reverse operation is the same pair the other way round:
:func:`~endf_parserpy.write_tape` assembles the materials into
an ENDF-6 string, and :func:`~endf_parserpy.write_tape_file`
writes that tape to a file:

.. code:: Python

   from endf_parserpy import write_tape, write_tape_file
   write_tape_file(materials, 'output.endf')   # write to a file
   text = write_tape(materials)                # or obtain the string

If a material cannot be parsed, the ``on_error`` argument
decides what happens. With the default ``'mark'``, the
offending material is returned as a
:class:`~endf_parserpy.FailedMaterial` object instead of a
dictionary. It keeps the raw content of the material, so the
remaining materials are still parsed and the tape can be
written back without loss:

.. code:: Python

   from endf_parserpy import FailedMaterial

   materials = parse_tape_file('tape.endf')  # on_error='mark' is the default
   for material in materials:
       if isinstance(material, FailedMaterial):
           # .mat is the MAT number, .exception the error that
           # occurred and .raw_lines the original text of the material
           print(material.mat, material.exception)
       else:
           ...   # an ordinary material dictionary

With ``on_error='raise'`` the first failure aborts the
operation instead:

.. code:: Python

   materials = parse_tape_file('tape.endf', on_error='raise')

For large tapes, the :func:`~endf_parserpy.iter_parse_tape_file`
function yields one material at a time instead of returning
the complete list, so that the peak memory consumption stays
bounded by the size of the largest material:

.. code:: Python

   from endf_parserpy import iter_parse_tape_file
   for material in iter_parse_tape_file('tape.endf'):
       ...   # one material, a dict or a FailedMaterial

Lazy access with EndfFile
-------------------------

When only some materials or sections of a large tape are
relevant, parsing the complete file is wasteful. The
:class:`~endf_parserpy.EndfFile` class indexes the file on
construction and reads and parses an individual section from
disk only when it is accessed:

.. code:: Python

   from endf_parserpy import EndfFile
   endf_file = EndfFile('tape.endf')
   len(endf_file)                # number of materials on the tape

A material is addressed by its zero-based position on the
tape. Indexing an :class:`~endf_parserpy.EndfFile` returns a
:class:`~endf_parserpy.tape.MaterialView`, a lightweight
handle to one material; iterating over the file yields
these handles in turn:

.. code:: Python

   material = endf_file[0]            # a MaterialView
   for material in endf_file:         # iterate over all materials
       print(material.position, material.mat, material.za)

Besides ``position``, ``mat``, ``za`` and ``awr``, a
:class:`~endf_parserpy.tape.MaterialView` reports the
sections the material contains:

.. code:: Python

   material.sections()        # list of the (MF, MT) pairs present

A section is addressed on a material by an ``(MF, MT)`` pair.
Accessing it parses that section and returns it as a
dictionary; a section for which no recipe exists is returned
as a list of raw strings instead:

.. code:: Python

   section = endf_file[0][3, 2]       # parsed MF=3/MT=2 section, a dict

A whole material can also be lifted out of the tape as an
ordinary single-material tape dictionary with the
:meth:`~endf_parserpy.tape.MaterialView.to_tape_dict` method.
The result is a ``{MF: {MT: section}}`` mapping, the same
form a single-material parse produces and complete with its
``MF=0``/``MT=0`` tape head, so it can be handed straight to
the parser's writer or to :func:`~endf_parserpy.write_tape`:

.. code:: Python

   material_dict = endf_file[0].to_tape_dict()   # one material as a tape dict
   text = parser.write(material_dict)            # render it on its own

Because the same material number (``MAT``) may occur several
times on a tape (a PENDF tape repeats it for every
temperature), materials are identified by position rather
than by ``MAT``. The :meth:`~endf_parserpy.EndfFile.by_mat`,
:meth:`~endf_parserpy.EndfFile.by_za` and
:meth:`~endf_parserpy.EndfFile.find` methods look materials
up by their identifiers:

.. code:: Python

   material = endf_file.by_mat(2925)     # the single material with MAT 2925
   materials = endf_file.by_za(29063)    # a list of materials with that ZA
   materials = endf_file.find(mat=2925)  # a list matching every criterion

:meth:`~endf_parserpy.EndfFile.by_mat` returns a single
:class:`~endf_parserpy.tape.MaterialView`, whereas
:meth:`~endf_parserpy.EndfFile.by_za` and
:meth:`~endf_parserpy.EndfFile.find` return a list of them.
If the ``MAT`` number is not unique,
:meth:`~endf_parserpy.EndfFile.by_mat` raises
:class:`~endf_parserpy.tape.AmbiguousMaterialError`, and the
copy of interest must then be selected with the
``occurrence`` argument:

.. code:: Python

   material = endf_file.by_mat(2925, occurrence=0)   # the first such material

The sections of a material can be replaced, added or
deleted, and whole materials can be deleted, appended or
reordered. Every edit is kept in memory until the tape is
written back:

.. code:: Python

   endf_file[0][3, 2] = section          # replace (or add) a section
   del endf_file[0][3, 18]               # delete a section
   del endf_file[1]                      # delete the second material

A new material (an ordinary ``{MF: {MT: section}}`` mapping,
such as one entry of a :func:`~endf_parserpy.parse_tape_file`
result) is appended with
:meth:`~endf_parserpy.EndfFile.append_material`, which
returns a :class:`~endf_parserpy.tape.MaterialView` of the
added material:

.. code:: Python

   donor = parse_tape_file('other.endf')[0]            # a material dictionary
   mat = donor[1][451]['MAT']                          # the MAT it carries
   new_material = endf_file.append_material(donor, mat=mat)

The ``mat`` argument must equal the MAT number the material
carries in its own records; it is rejected otherwise, since the
records, not the argument, are what gets written to the tape.

The materials can be reordered by passing a permutation of
their positions to :meth:`~endf_parserpy.EndfFile.reorder`:

.. code:: Python

   endf_file.reorder([1, 0])             # swap the first two materials

Finally, :meth:`~endf_parserpy.EndfFile.export` writes the
edited tape to a file and :meth:`~endf_parserpy.EndfFile.to_string`
returns it as an ENDF-6 string, the same memory/file pairing
as the module functions. Sections that were not edited keep
their data records verbatim from disk; the SEND/FEND/MEND
framing and the column 76-80 sequence numbers are regenerated
either way. Every data field is therefore preserved byte for
byte, but the tape as a whole is not necessarily byte-identical
to the original:

.. code:: Python

   endf_file.export('edited.endf')               # write to a new file
   text = endf_file.to_string()                  # or obtain the string

Exporting onto the very file the :class:`~endf_parserpy.EndfFile`
was opened from is allowed, but it leaves the in-memory index
out of step with the rewritten file. The object is therefore
*invalidated*: any further use raises
:class:`~endf_parserpy.tape.StaleSourceError`, and the file
must be re-opened to continue working with it.

.. code:: Python

   endf_file.export('tape.endf', overwrite=True)  # overwrites the source
   endf_file = EndfFile('tape.endf')              # re-open to continue

.. note::

   The structural index that :class:`~endf_parserpy.EndfFile`
   builds on construction is faster to compute when
   `NumPy <https://numpy.org/>`_ is available. Installing the
   package with the ``fast`` extra pulls in this optional
   dependency; without it a pure-Python fallback is used.

Selecting a material by its content
-----------------------------------

On a tape that repeats the same material, the position is
often not the most convenient way to pick a particular copy.
A PENDF tape, for example, stores the same material at a
series of temperatures, and one usually wants the copy at a
specific temperature. The :meth:`~endf_parserpy.EndfFile.query`
method selects materials by the value of a field in one of
their sections and returns the matches as a list of
:class:`~endf_parserpy.tape.MaterialView` objects:

.. code:: Python

   from endf_parserpy import EndfParserCpp, EndfFile

   parser = EndfParserCpp(endf_format='pendf')
   endf_file = EndfFile('file.pendf', parser=parser)

   # the materials whose MF1/MT451 temperature is 293.6 K
   room_temp = endf_file.query('1/451/TEMP', 293.6, tol=1.0)
   xs = room_temp[0][3, 1]      # MF=3/MT=1 of the first match

The first argument is a path into an MF/MT section (here the
``TEMP`` field of the MF1/MT451 section), and the second the
value to match; the ``tol`` argument allows for a numerical
tolerance. Instead of a value, a ``predicate`` callable can
be supplied to match on an arbitrary condition:

.. code:: Python

   hot = endf_file.query('1/451/TEMP', predicate=lambda t: t > 1000.0)

If the same lookup is needed repeatedly, the
:meth:`~endf_parserpy.EndfFile.build_index` method parses the
section once per material and returns a dictionary that maps
each field value to the list of material positions carrying
it:

.. code:: Python

   temperatures = endf_file.build_index('1/451/TEMP')
   # e.g. {293.6: [0, 3], 600.0: [1, 4], ...}
   positions = temperatures[293.6]

Passing a list of section paths instead of a single one builds a
*composite* index: the key becomes the tuple of the values at the
given paths, in order. The paths may address fields in different
sections, and a material that lacks any of them is left out:

.. code:: Python

   index = endf_file.build_index(['1/451/ZA', '1/451/TEMP'])
   # e.g. {(29063.0, 293.6): [0], (30064.0, 293.6): [1], ...}
   positions = index[(29063.0, 293.6)]

A single value can also be retrieved directly with the
:meth:`~endf_parserpy.EndfFile.get` method and a
material-qualified path. Such a path, described by the
:class:`~endf_parserpy.EndfMaterialPath` class, extends an
ordinary :class:`~endf_parserpy.EndfPath` with a leading
material selector — a ``MAT`` number, ``MAT#k`` for the
``k``-th material carrying that ``MAT`` number, or ``#k``
for the material at position ``k``:

.. code:: Python

   endf_file.get('#0/1/451/AWR')        # AWR of the material at position 0
   endf_file.get('2925#0/3/2')          # MF=3/MT=2 of the 1st MAT-2925 material
   endf_file.get('2925#1/1/451/TEMP')   # a field of the 2nd MAT-2925 material

A bare ``MAT`` number with no ``#k`` selector picks the material
with that ``MAT`` only when it is unique on the tape; if the
``MAT`` number repeats, as it does on a PENDF tape, it must be
qualified with ``#k`` or the lookup raises
:class:`~endf_parserpy.tape.AmbiguousMaterialError`.

The path may stop at a section, in which case the whole
section is returned, or continue into it to address a single
field.

Path-addressed access and editing
---------------------------------

The :meth:`~endf_parserpy.EndfFile.get` method has a shorter
spelling: an :class:`~endf_parserpy.EndfFile` can be indexed
directly with an :class:`~endf_parserpy.EndfMaterialPath`. The
``[]``, ``[]=``, ``del`` and ``in`` operators all accept such a
path (a string or an :class:`~endf_parserpy.EndfMaterialPath`
object) in addition to an integer material position, so a tape
reads and edits like a path-addressable mapping:

.. code:: Python

   awr = endf_file['9237#1/3/2/AWR']     # read a field
   endf_file['9237#1/3/2/AWR'] = 63.5    # write a field
   section = endf_file['#0/3/2']         # read a whole section
   del endf_file['#0/3/18']              # delete a section
   del endf_file['#1']                   # delete a material
   present = '#0/1/451/TEMP' in endf_file  # test for presence

Every such edit, whether a field write, a section or material
deletion, an :meth:`~endf_parserpy.EndfFile.append_material` or a
:meth:`~endf_parserpy.EndfFile.reorder`, only changes the
in-memory tape. The file on disk is never touched until the tape
is written out explicitly with
:meth:`~endf_parserpy.EndfFile.export` (or
:meth:`~endf_parserpy.EndfFile.to_string`); without that call the
edits are discarded when the :class:`~endf_parserpy.EndfFile`
object goes away.

``endf_file.get(path)`` is the explicit-method synonym of
``endf_file[path]``; both return the same thing: a
:class:`~endf_parserpy.tape.MaterialView` for a material-depth
path, a section for an ``MF/MT`` path, and the value at the
field for a deeper path.

A retrieved section is not a plain dictionary but a *view* over
the tape, and what that view permits is governed by the
``check_edits`` argument of the :class:`~endf_parserpy.EndfFile`
constructor:

.. code:: Python

   from endf_parserpy import EndfFile

   strict = EndfFile('tape.endf')                          # check_edits='eager'
   relaxed = EndfFile('tape.endf', check_edits='deferred')

With ``check_edits='eager'`` (the default) every edit is rendered
through the parser's writer immediately, so a change that breaks
the ENDF recipe raises :class:`~endf_parserpy.tape.SectionRenderError`
at the offending assignment. A section retrieved in this mode is
a *read-only* view; to edit it, take a standalone copy with its
``detach()`` method, change the copy and assign it back:

.. code:: Python

   section = strict['#0/3/2'].detach()   # a plain, mutable dict
   section['QI'] = 0.0
   strict['#0/3/2'] = section            # rendered and checked here

With ``check_edits='deferred'`` a retrieved section is instead a
*live* view: assigning into it writes straight through to the
tape, exactly as for an :class:`~endf_parserpy.EndfDict`.
Recipe-conformity is then checked only when the tape is written
out, or on demand via :meth:`~endf_parserpy.EndfFile.invalid_edits`,
which returns the edited sections that fail to render:

.. code:: Python

   relaxed['#0/3/2']['QI'] = 0.0         # writes through to the tape
   if not relaxed.invalid_edits():       # empty list -> every edit is valid
       ...

A view — frozen or live — is itself path-addressable: a string
key is read as an :class:`~endf_parserpy.EndfPath` relative to
the view, so ``relaxed['#0/3/2']['xstable/E']`` and
``relaxed['#0/3/2/xstable/E']`` reach the same data.

With a parser created with ``array_type='numpy'``, the arrays of a
section are numpy arrays. A view, frozen or live, returns such an
array as a *read-only* numpy array that shares its data with the
tape's copy of the section (no data is copied). Changing it in
place, e.g. ``section['xstable/xs'][0] = 1.5`` or
``section['xstable/xs'] *= 2``, therefore raises numpy's
``ValueError: assignment destination is read-only`` in both modes,
rather than silently changing data that would not be written out.
To change an array, use one of the following:

.. code:: Python

   # a path ending at the element (2-D blocks: one index per dimension)
   relaxed['#0/3/2']['xstable/xs/0'] = 1.5
   strict['#0/3/2/xstable/xs/0'] = 1.5            # rendered and checked
   # assignment of a whole array
   section = relaxed['#0/3/2']
   section['xstable/xs'] = section['xstable/xs'] * 2
   # a detached copy, whose arrays are ordinary writable copies
   section = strict['#0/3/2'].detach()
   section['xstable']['xs'][0] = 1.5
   strict['#0/3/2'] = section

A read-only array obtained from a view is copied when it is assigned
into a section. Views compare element by element with dictionaries,
other views and data parsed with ``array_type='list'``.

Bounded memory and parallel processing
--------------------------------------

Because :class:`~endf_parserpy.EndfFile` parses sections lazily,
it can open a tape far larger than the available memory. Parsed
and raw sections are kept in two caches of a fixed byte budget,
set by the ``parsed_cache_bytes`` and ``raw_cache_bytes``
constructor arguments; once a budget is exhausted the
least-recently-used entries are evicted and re-read on the next
access:

.. code:: Python

   # 16 MiB for each cache tier instead of the 64 MiB default
   endf_file = EndfFile('huge.endf', parsed_cache_bytes=16 << 20,
                        raw_cache_bytes=16 << 20)

The :attr:`~endf_parserpy.EndfFile.cache_nbytes` property reports
the current ``(raw, parsed)`` cache occupancy, and the
:meth:`~endf_parserpy.EndfFile.unload` method drops the cached
sections of one material (or, with no argument, of the whole
tape) without discarding any pending edits.

The parser objects are picklable, so a configured parser can be
shipped to a pool of worker processes. Together with the fast,
index-only construction of :class:`~endf_parserpy.EndfFile`, this
makes it straightforward to scan or parse a whole library of
files in parallel:

.. code:: Python

   from concurrent.futures import ProcessPoolExecutor
   from functools import partial
   from endf_parserpy import EndfParserFactory, EndfFile

   parser = EndfParserFactory.create(select='fastest')

   def material_count(path, parser):
       return path, len(EndfFile(path, parser=parser))

   with ProcessPoolExecutor() as pool:
       worker = partial(material_count, parser=parser)  # parser is pickled
       counts = dict(pool.map(worker, library_files))

.. tip::

   Two runnable scripts in the source repository exercise this
   interface end to end: ``examples/example-002-multimaterial-tapes.py``
   builds, explores and edits a multi-material tape, and
   ``examples/example-003-bounded-memory.py`` demonstrates opening,
   editing and exporting a tape larger than the available memory with a
   bounded memory footprint.
