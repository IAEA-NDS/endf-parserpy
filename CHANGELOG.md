# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- MF7/MT4 recipe (incoherent inelastic thermal scattering) failed for materials without a principal scattering atom (B(1)=0.0), whose scattering law is completely described by the analytic functions of the non-principal atoms: the recipe always expected the tabulated S(alpha,beta), which is omitted in this case. The TAB2 record and the TAB1/LIST records of S(alpha,beta) are now only read if B(1) is non-zero

## [0.17.0]

### Added

- Multi-material ENDF tape support via the new functions `parse_tape`, `iter_parse_tape` and `write_tape`, each paired with a `_file` variant (`parse_tape_file`, `iter_parse_tape_file`, `write_tape_file`). These parse and write ENDF files that contain several materials, including PENDF tapes that repeat the same material at different temperatures. Mirroring the `parse`/`parsefile` naming of the single-material parser, the bare name works on an in-memory ENDF-6 string and the `_file` variant on a file path. A tape is split lexically into single-material chunks that are handed to the ordinary single-material parser, which is used unchanged. `iter_parse_tape`/`iter_parse_tape_file` stream one material at a time so peak memory stays bounded by the largest single material. The `on_error` option (`"raise"` or `"mark"`) selects whether a material that fails to parse aborts the operation or is returned as a `FailedMaterial` (which round-trips verbatim through `write_tape`). `write_tape_file` consumes its `materials` argument lazily and writes one material at a time, so passing it a generator keeps peak memory bounded by a single material rather than by the whole tape; a material supplied as a plain `list` of ENDF lines (not only a `FailedMaterial`) is written verbatim, with no intermediate parse or render. This removes the long-standing limitation that only a single material per file was supported
- `TapeIndex`: a structural index over the materials of an ENDF tape, built with `TapeIndex.from_file()` or `TapeIndex.from_lines()`. A single linear scan records, for every material, its MAT number, the ZA/AWR identifiers, the byte range it occupies and the byte range of every (MF, MT) section. The scan is recipe-free (it inspects only the MAT/MF/MT control fields and the universal HEAD-record layout) and therefore independent of the parsing engine. Materials are addressed by zero-based position; `by_mat()` and `by_za()` provide secondary lookups that return all matching positions (PENDF tapes repeat a MAT number). The index is picklable and records the source file size and mtime for staleness checks
- `EndfFile`: lazy, memory-bounded access to a multi-material ENDF file. The file is indexed on construction; individual sections are read from disk and parsed (by wrapping them in a minimal single-material tape handed to the ordinary parser) only on access, then held in two byte-budgeted caches. Materials are addressed by zero-based position via the mapping protocol (`endf_file[i]` yields a `MaterialView`, `material[mf, mt]` yields the parsed section); `by_mat()`, `by_za()` and `find()` are secondary lookups. The parsed-section cache keeps strong references within its budget and weak references beyond it, so a section the caller still holds keeps its identity across eviction. `EndfFile` is a context manager, is picklable (the index travels with it; the caches do not) for use with `ProcessPoolExecutor`, supports `on_error` (`"raise"`/`"mark"` with `FailedSection`), and can verify that the source file has not changed since indexing
- `EndfMaterialPath` and the `EndfFile` query layer. `EndfMaterialPath` extends an `EndfPath` with a leading material selector (`MAT`, `MAT#k` for the k-th material with that MAT number on a PENDF tape, or `#k` for tape position k); `EndfPath` itself is unchanged, so existing code is unaffected. `EndfFile.get(path)` resolves a material-qualified path to a single value, parsing only the one section it refers to. `EndfFile.build_index(section_path, name=...)` parses one section of every material to build a `{value: [positions]}` secondary index — passing a list of section paths instead builds a composite index keyed on the tuple of their values, parsing each shared section only once — and `EndfFile.query(section_path, value/predicate, tol=...)` returns the materials whose section field matches. This makes semantic lookups (e.g. by temperature) a matter of supplying a path, with no temperature-specific knowledge baked into the library
- In-memory editing of an `EndfFile` and write-back. Sections can be replaced, added or deleted (`material[mf, mt] = section`, `del material[mf, mt]`), and materials can be deleted (`del endf_file[i]`), appended (`append_material(material, mat=...)`) or reordered (`reorder(order)`). Each material carries an edit overlay; the structural index is untouched and still describes the file on disk, so editing never invalidates it. `MaterialView` is bound to its material, so it survives a reorder. `EndfFile.export(path, overwrite=False)` writes the edited tape to a file and `EndfFile.to_string()` returns it as an ENDF-6 string — untouched sections keep their data records verbatim from disk and edited ones are rendered by the parser, while the SEND/FEND/MEND framing and the column 76-80 sequence numbers are regenerated either way, so every data field is preserved byte-for-byte (the same guarantee the ordinary writer gives) without the tape being byte-identical; `export` uses a temporary file and an atomic replace, and writes the tape one material at a time so its peak memory is bounded by a single material regardless of the tape size. Exporting onto the file the `EndfFile` was opened from is permitted, but it leaves the in-memory structural index stale, so the object is invalidated: any further operation raises `StaleSourceError` until the file is re-opened. Exporting to any other path leaves the object usable. `MaterialView.to_tape_dict()` returns the material as a complete single-material `{MF: {MT: section}}` tape dict — including the `MF=0`/`MT=0` tape head that per-section access omits — so it can be handed straight to the ordinary parser's `write`. `append_material` rejects a `mat` argument that disagrees with the MAT number the supplied material carries in its own records
- `EndfParserpyError`: a package-wide base exception. Every exception raised by endf-parserpy now derives from it—the parsing engine's `ParserException`, the recipe compiler's `EquationSolveError` and the tape interface's `TapeError`—so `except EndfParserpyError` catches any library-specific error regardless of the subsystem that raised it. `AmbiguousMaterialError` additionally derives from the built-in `LookupError`, since it reports a failed lookup. The change is backward compatible: existing `except` clauses for the individual exception classes are unaffected
- Path-addressed item access on `EndfFile`. The `[]`, `[]=`, `del` and `in` operators are now polymorphic: besides an integer material position they accept an `EndfMaterialPath` (string or object), so a tape can be navigated and edited like a path-addressable mapping — `endf_file["9237#1/3/2/AWR"]` reads a field, `endf_file[path] = value` writes one, `del endf_file[path]` removes a material, section or field, and `path in endf_file` tests for presence. `get(path)` is now the explicit-method synonym of `endf_file[path]` and is relaxed to also accept a material-depth path (returning a `MaterialView`)
- `check_edits` argument on `EndfFile` (`"eager"` by default, or `"deferred"`). It selects both *when* an edited section's recipe-conformity is verified — immediately, raising `SectionRenderError` at the offending assignment, or only at `export()` / `to_string()` / the new `invalid_edits()` method — and *what a retrieved section is*: under `"eager"` a recursively read-only (frozen) view, under `"deferred"` a live write-through view that edits the tape in place. A retrieved section is therefore a recursive view, never a defensive copy; it is itself path-addressable (a string key is read as an `EndfPath` relative to the view), and its `.detach()` method returns a standalone, plain, mutable copy. `EndfFile.invalid_edits()` renders every edited section and returns the non-conformant ones (an empty list meaning every edit is valid); `SectionRenderError` is the new tape exception for an edit that does not render to valid ENDF-6 text
- `EndfParserPy` and `EndfParserCpp` are now picklable. A parser is pickled *by recipe* — the arguments it was constructed with — and rebuilt by re-running its constructor on unpickling. Previously `EndfParserCpp` could not be pickled at all (it wraps an unpicklable compiled extension) and `EndfParserPy` pickled its full, heavy live state; both now round-trip as a small construction recipe. As a result a pickled `EndfFile` carries its parser with it, so an `EndfFile` sent to a `ProcessPoolExecutor` worker keeps the exact parser options it was opened with instead of being rebuilt with parser defaults
- `endf-cli` now handles multi-material ENDF tapes throughout. Every subcommand reads files via `EndfFile`, so single- and multi-material files are treated uniformly. A new `list-materials` subcommand enumerates the materials of a tape (tape position, MAT, ZA, AWR). Subcommands that take an `EndfPath` (`show`, `explain`, `replace`) accept a material-qualified path with a leading material selector — `#k` for tape position k, or `MAT#k` for the k-th material with that MAT number (use `#0` for the first/only one). The selector always contains a `#`, and that `#` is what marks a path as material-qualified; a bare MAT number without a `#` stays an ordinary `EndfPath`. On a single-material file the selector may be omitted, so existing invocations keep working; on a multi-material tape a selector-less path is rejected with a listing of the available materials. `validate` checks every section of every material; `match` evaluates its query against each material and reports the matching ones individually; `compare` pairs the materials of the two files by MAT number (a repeated MAT number paired by order of appearance) and reports any unpaired material; `convert` writes a single-material file as a JSON object and a multi-material tape as a JSON array of material objects, recognising the two cases on the way back; `insert-text` gained a `-m/--material` option to choose which material to modify. `replace` accepts not only a section or field path but also an MF-depth path (swapping a whole MF file) or a material-depth path (swapping a whole material), making the addressed unit of the target equal to the source's; its new `--source-path` option addresses the object in the source file independently of the target path, which is needed whenever the two locations differ — most commonly when copying from a single-material reference file into one material of a tape. A section or a whole MF file must be copied to the same MF/MT it came from — a section carries its own MF/MT in its records — so `replace` rejects a source/target MF/MT mismatch instead of silently misplacing the data. A new `insert-material` subcommand adds a whole material from one file into a tape — appended at the end by default, or placed right after a chosen material with `--after` — and a new `remove-material` subcommand drops a material from a tape; together with `list-materials` they are the material-level counterparts of the section-level `replace` (which keeps its general, unsuffixed name). Files are written back via `EndfFile.export`, which terminates the tape with a trailing newline

### Changed

- `endf-cli match` now reports its result through grep-like exit codes: `0` when at least one material matched the query, `1` when none did, and `2` when a file or material could not be parsed. Previously it exited `0` regardless of whether anything matched, so `match` could not be used as a scriptable test

### Fixed

- `EndfParserCpp` mishandled a LIST record with zero elements (`NPL=0`): the generated C++ unconditionally read a body line even when the LIST had no body, consuming the following record (typically the SEND) and desynchronizing the parser, which then failed with a misleading `Material End (MEND) and Tape End (TEND) records missing` error at end of file. The first body line is now read only when `NPL > 0`. This affected, for instance, the MF8/MT457 section of stable nuclides (242 of the JENDL-5 decay sublibrary files); `EndfParserPy` was not affected
- `EndfParserCpp` mismatch error messages now print enough significant digits to reveal a small difference between two close values; previously the default 6-digit formatting could render the expected and actual value identically (e.g. `Expected AWR=11.8969 but found AWR=11.8969`)
- C++ extension build could compile and link stale shared translation units. The deduplicated functions are emitted into either a single `_shared.cpp` or several `_shared_part_NN.cpp` chunks depending on the `INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS` setting; a build with a different layout than a previous one left the old shared files in place, and the build step discovered shared sources by scanning the directory, so both the stale and the current files were compiled and linked, causing duplicate-symbol link errors. The code generator now removes shared translation units from a previous build before writing the new ones, and the build step compiles exactly the shared files the generator reports rather than whatever is found on disk
- `endf-cli explain` exited with status code 1 even when it succeeded: its action handler never called `sys.exit(0)`, so control fell through to a trailing `sys.exit(1)` in the dispatcher. It now exits 0 on success
- `endf-cli match` printed its `parsing failed: <file>` diagnostic to standard output; it is now written to standard error, where diagnostics belong, leaving standard output for match results only
- `endf-cli validate` and `endf-cli match` silently exited `0` when a file argument did not exist, or when a glob pattern matched nothing — the unchecked glob expansion dropped the path. Such an argument is now carried through and reported (a failed file for `validate`, a parse failure for `match`), yielding a non-zero exit code
- `endf-cli compare` aborted with an uncaught `FileNotFoundError` traceback when a file could not be read; it now prints a clean error and exits with status `2`
- ENDF files written on Windows carried CRLF (`\r\n`) line terminators instead of LF: the Python writers (`EndfParserPy.writefile`, `write_tape`/`write_tape_file`, `EndfFile.export`) opened the output file in text mode, leaving the line terminator to the platform. They now open the file with newline translation disabled and write LF on every platform, matching the C++ parser's writer, which already wrote in binary mode

## [0.16.1]

### Changed

- C++ extension build time reduced by roughly 5x on multi-core machines (measured: 6:44 → 1:18 on a 4-physical / 8-logical i7-1165G7) by combining three changes: (a) parallel compilation across the six flavor extensions, (b) hash-based deduplication of recipe-derived parse/write functions so identical functions across flavors are now emitted once into a shared translation unit, and (c) splitting that shared translation unit into N pieces so it itself compiles in parallel. Mitigates the long install times observed by downstream CI users (#42)
- Two new environment variables control the build parallelism: `INSTALL_ENDF_PARSERPY_NUM_BUILD_JOBS` (worker count, default `os.cpu_count()`) and `INSTALL_ENDF_PARSERPY_NUM_SHARED_CHUNKS` (number of shared-TU chunks, default `min(os.cpu_count(), 8)`)

### Fixed

- Docstring of `EndfParserCpp` now documents the `validate_control_records` parameter

## [0.16.0]

### Added

- ENDF recipe for MF26 (electroatomic interaction data)
- ENDF recipe for MF28 (atomic relaxation data)
- ENDF recipe for MF30/MT1 (directory of model-parameter covariances) and MF30/MT2 (covariance matrix)
- `accept_nan_inf` option on `EndfParserPy` and `EndfParserCpp` (default `True`): allow non-finite floats (`NaN`, `+inf`, `-inf`) in ENDF fields; with `False` such values raise. The writer also gained the ability to emit non-finite floats as the textual tokens `NaN` / `Inf` / `-Inf` right-aligned in the 11-character field
- Optional `defaults` parameter on `add_common_cmd_parser_args` to override argparse-level defaults for individual subcommands and surface those overrides in `--help`

### Fixed

- C++ parser: number parsing now uses `std::strtod` instead of `std::stod`, which avoids spurious exceptions on subnormal values produced by some evaluations (770 affected files in JEFF-4.0/tsl)
- C++ parser: `cpp_read_vec` no longer consumes a line when `numel == 0`, fixing 59 spurious SEND-record failures in TENDL-2025/he3 metastables
- C++ codegen: the `?` (inconsistent variable) marker is now propagated through `:=` placeholder expansions, so recipes like `NX := ...; NX?` are honored under `ignore_varspec_mismatch=True`. This unblocks parsing of JEFF-4.0/n Gd-155, Gd-157 and O-16 with the C++ parser (#53, #55)
- `endf-cli validate`: strict defaults are now reflected at argparse level and shown in `--help`; an `accept_nan_inf=False` strict default was added so non-finite floats are rejected by default during validation; an override-after-parse code path was retired as redundant (#56)
- C++ parser: SEND/FEND/MEND/TEND completeness is now checked at EOF. Tapes truncated before MEND/TEND no longer parse silently; this matches the long-standing Python behavior (#57)
- C++ parser: integer-field parsing is now strict. `std::atoi`-based silent truncation of float-shaped strings (`"0.000000+0" -> 0`, `"4.000000-6" -> 4`, etc.) has been replaced with a `std::strtol`-based path that rejects anything Python's `int()` would reject. A blank field still reads as zero per ENDF convention (#58)

### Changed

- `endf-cli validate` is now strict-by-default across `ignore_number_mismatch`, `ignore_zero_mismatch`, `ignore_varspec_mismatch`, `accept_spaces`, `ignore_blank_lines`, `ignore_send_records`, `ignore_missing_tpid`, and `accept_nan_inf`. Each flag can still be overridden individually on the command line
- C++ parser is stricter by default in two ways that previously masked malformed files: it now rejects tapes truncated before MEND/TEND, and it now rejects float-shaped strings in integer fields. Both behaviors match the Python parser. Files that relied on the old silent acceptance can opt back in with `ignore_send_records=True` and, for integer fields, must be repaired (no opt-in flag is provided)

## [0.15.0]

### Added

- Adler-Adler formalism in MF2/MT151 ENDF recipe (#43)
- Comprehensive description in MF2/MT151 and MF32 recipe (#43 and #45)

### Fixed

- Some edge cases in the MF2/MT151 and MF32 recipe (#43)
- Issue with `endf-cli match` command for variable names with underscore (#49)
- Issue with `ignore_blank_lines` option of C++ parser (#51)

### Changed

- Consistent names in MF2/MT151 and MF32/MT151 ENDF recipes
- Default C++ optimization level for faster package installation (#52)
- GitHub workflow to enable native compilation on ARM architecture

## [0.14.3]

### Deprecated

- The `EndfParser` class has been renamed to `EndfParserPy` and the old name should not be used anymore

### Added

- Support of `repat...until` syntax in formal recipe language
- Support of `stop` instruction to C++ parser generator
- `EndfParserFactory` class for automatic selection between Python and C++ parser
- Abstract base class `EndfParserBase` serving as parent class for `EndfParserCpp` and `EndfParserPy`
- Recipe flavor ``errorr`` to support parsing and writing NJOY ERRORR output files
- Support of array values as indices in ENDF recipes
- Possibility to control C++ optimization level via `INSTALL_ENDF_PARSERPY_CPP_OPTIM` environment variable
- Tests to verify character by character equivalence of Python and C++ parser output

### Fixed

- Python parser now always inject MAT, MF, MT numbers before parsing
- Inject MF, MT if missing before writing via `EndfParserCpp`
- Deal gracefully with `UnavailableIndexError` in if-lookahead
- Ensure character by character equivalence of `EndfParserPy` and `EndfParserCpp` output
- C++ parser now accepts blank lines after TEND record (irrespective of `ignore_blank_lines` option)
- Division-by-zero issue in arithmetic expressions generated by C++ parser code generator

### Changed

- Replaced deprecated dependency `appdirs` by `platformdirs` package
- Default value of `fuzzy_matching` Python parser argument to `False`
- Expose `include_linenum` argument in command-line interface
- Disabled zero padding of list bodies in Python parser (same behavior now as C++ parser)
- Interaction with `importlib.resources` API to avoid deprecation warnings

## [0.13.1]

### Fixed

- Enable conversion from Python `int` to `EndfFloatCpp` object in C++ code

### Changed

- More descriptive error message for blank line error in generated C++ parser code

## [0.13.0]

### Added

- Conversion between ENDF and JSON format via command-line interface

### Fixed

- ENDF recipe for MF1/MT460
- `EndfParser` `write` method to deal with `EndfDict` object as input
- Some mistakes in the documentation
- Invalid escape sequence in doc string (#10)

## [0.12.0]

### Added

- `EndfFloat` class for storing float numbers with associated original string
- Support of PENDF files produced by NJOY
- Argument `preserve_value_strings` to `EndfParser` and `EndfParserCpp` class
- `matching` module for matching ENDF files according to logical expressions
- Argument `array_type` to `EndfParser` and `EndfParserCpp` to support representing ENDF arrays as Python `list`

### Removed

- Option `blank\_as\_zero` from `EndfParser` constructor---now blank numeric fields are always interpreted as zero.

### Fixed

- SEND record treatment in cpp parser for sections read verbatim
- `EndfParserCpp` on Windows 11 by using binary mode for reading/writing
- Output of integers instead of float numbers in SEND records
- Avoid check of MAT/MF/MT consistency if `ignore_send_records` option is active
- Add forgotten newline character while joining list of strings in `EndfParserCpp.parse` method.
- Do not remove last line when writing verbatim MF/MT section with `EndfParser`

### Changed

- Options for reading and writing are now passed as dictionaries (`read_opts` and `write_opts`) to functions.
- Redesigned and extended command-line interface

## [0.11.0]

### Added

- Argument `include_linenum` to `EndfParser` class constructor [#6](https://github.com/IAEA-NDS/endf-parserpy/issues/6)
- Argument `include_linenum` to `EndfParserCpp` and C++ parsers [#6](https://github.com/IAEA-NDS/endf-parserpy/issues/6)
- Variable `__version__` in package namespace [#5](https://github.com/IAEA-NDS/endf-parserpy/issues/5)

### Fixed

- Sequence number is reset to 1 if it exceeds 99999 [#6](https://github.com/IAEA-NDS/endf-parserpy/issues/6)

## [0.10.3]

### Added

- First version for reference in this changelog
