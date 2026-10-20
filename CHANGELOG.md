# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- MF5 recipe: energy-dependent Watt spectrum (LF=11). The recipe previously stopped with an error for this representation; the fractional probability p(E) and the energy-dependent parameters a(E) and b(E) are now read into the tables `p_table`, `a_table` and `b_table` of the corresponding `contribution[k]`
- MF14 recipe: anisotropic photon angular distributions in tabular form (LI=0, LTT=2). The recipe previously stopped with an error for this representation. As for the Legendre representation (LTT=1), the NI isotropic photons are read first; for each anisotropic photon k, the probability distribution p(mu,E) at the incident energy `E[k,l]` is stored in the table `angtable[k,l]`
- `accept_d_exponent` option of `EndfParserPy` and `EndfParserCpp` (default `True`): accept numbers with a Fortran double-precision exponent introduced by `D` or `d`, e.g. `5.438673D-4`. Such numbers do not conform to the ENDF-6 format but occur in evaluated data files, e.g. in the MF1/MT451 section of all files of the ENDF/B-VIII.0 electro-atomic sublibrary, which could therefore not be read. With `False`, these numbers raise an error as before. The numbers are written in the usual ENDF-6 notation unless their original strings are preserved with `preserve_value_strings=True`. The option is also available in `EndfParserFactory.create` and as a flag of `endf-cli`, where `validate` sets it to `False` by default like the other leniency flags. `TapeIndex` accepts such numbers in the ZA and AWR fields of HEAD records

### Changed

- Arithmetic in ENDF recipe expressions is now exact in both `EndfParserPy` and `EndfParserCpp`. Integers and decimal literals are exact numbers (a decimal literal such as `0.1` denotes exactly 1/10), and a division of exact numbers gives an exact fraction, e.g. 13/6; only where an integer is needed (an integer field, a loop bound, an index) must the value of an expression be an integer. Values of float fields are floats, and arithmetic with a float gives a float. Previously, `EndfParserPy` required every division of two integers to be exact, so that e.g. `2*(N/4)` could not be evaluated for N=6, and it could not solve a field for an unknown inside a division, e.g. `2*N/3`, even if the solution is an integer. `EndfParserCpp` used the C++ operators, which truncate an integer division (13/6 gave 2), so it read and wrote data that `EndfParserPy` rejects. Both parsers now give the same results; for valid data of the recipes of the package, the results do not change
- `EndfParserCpp` converts number fields to floats faster when reading: a decimal number with at most 15 significant digits and a power of ten up to 10^22 in magnitude, i.e. most numbers in ENDF-6 files, is converted with a single correctly rounded multiplication or division, as both operands are exactly representable; all other numbers are still converted with `std::strtod`. The results are identical
- `EndfParserCpp` reads and writes faster thanks to fewer redundant operations in the C++ helpers: a value of the Python dictionary is looked up once instead of several times when writing, arguments are passed by reference instead of being copied, and the nested containers holding parsed arrays are moved instead of copied. The results are identical
- `EndfParserCpp` writes faster: numbers are formatted into a character buffer instead of using one to three `std::ostringstream` objects per field. The decimal digits of a float are computed with exact double arithmetic where this provably gives the correctly rounded result, and with `std::snprintf` otherwise. The output is identical
- `EndfParserCpp` writes faster: the generated writing code retrieves the value of each field from the Python dictionary once instead of twice. The output is identical
- `EndfParserCpp` reads number fields faster: integer and float fields of the common form (blanks, sign, digits, decimal point, exponent) are converted in a single pass over the 11 characters of the field; all other fields still go through the previous conversion, so values and error messages are unchanged
- `EndfParserCpp` parses files faster, in particular files with many short sections such as decay data: `parsefile` reads the complete file into memory and parses it from there, so that repositioning in the data (at the start of each section and in lookaheads) only moves a pointer instead of discarding and re-reading the buffer of the file stream. This needs additional memory of the size of the file during parsing; the new option `load_file_into_memory=False` of `EndfParserCpp` restores reading through the file stream. `parse` now parses a string in place instead of copying it into a string stream. The results are identical
- `EndfParserCpp` reads TAB1 and TAB2 records faster: the interpolation table and the pairs of values are read directly into their final containers, which are reserved from the counts in the record and moved instead of copied. The results are identical
- `EndfParserCpp` parses faster with `preserve_value_strings=True`: Python's cyclic garbage collector is paused while a parse function builds its result, so that it no longer repeatedly traverses the growing result, and its previous state is restored afterwards. The results are identical
- `EndfParserCpp` reads lines faster: a line is located in the buffer of the input stream and appended as a whole instead of character by character, and the memory of the line is reused for the next line. The results are identical
- `EndfParserCpp` converts `EndfFloat` objects faster (with `preserve_value_strings=True`): it creates them and reads their value and original string directly instead of calling the Python class and its methods for every value. A check at first use falls back to the previous conversion if the class `EndfFloat` no longer matches. The results are identical

### Removed

- Unused module `endf_parserpy/endf_recipes/endf6/endf_recipe_mf31.py`, an incomplete draft of the spontaneous fission formats of MF31 that was not registered for any MF/MT section. MF31 sections are read by the recipe derived from MF33 (`endf_recipe_mf31_mt452_455_456.py`), which also covers the spontaneous fission formats of ENDF-102, Section 31.2, as special cases of the particle-induced fission formats; this is now documented in the recipe and covered by tests

### Fixed

- MF26 recipe (electro-atomic interaction data) failed on any section whose product subsections differ in ZAP, AWI or LAW: the yield TAB1 record that opens each subsection was read outside of the `subsection[i]` block, so all subsections shared one set of variables and the second subsection raised a `NumberMismatchError`. This broke, for instance, the bremsstrahlung section (MT=527) of every file in the ENDF/B-VIII.0 electro-atomic sublibrary. The yield record is now part of its subsection. As a consequence, `ZAP`, `AWI`, `LAW` and `yields` are now found under `subsection[i]` rather than at the top level of an MF26 section, also for sections with a single subsection
- MF1/MT455 recipe (delayed neutron data) failed for energy-dependent decay constants combined with a polynomial representation of the delayed neutron yield (LDG=1, LNU=1) whenever more than one incident energy was given: the energy of each LIST record of decay constants was read into a scalar `E1` instead of the array element `E[k]`, so the second energy raised a `NumberMismatchError`. The energies are now stored in the array `E`, as in the LDG=1, LNU=2 branch. In addition, the TAB2 record with the interpolation scheme for the incident energies of both LDG=1 branches had no table name, so its `NBT` and `INT` arrays shared the section-level keys of the TAB1 record of the tabulated delayed neutron yield (LNU=2); the TAB1 record then raised a mismatch in `EndfParserPy` unless both interpolation tables coincided, and `EndfParserCpp` failed with "Both the expected and actual value are vectors". The TAB2 interpolation table is now stored under `E_interpol`
- MF8/MT457 recipe (radioactive decay data) could not read the covariance matrix of a discrete spectrum (LCOV=2,3): the LB=5 LIST record contains NERP=NER+1 energies followed by the upper triangle of the NER x NER relative covariance matrix of the discrete intensities, but the recipe let the matrix indices run only to NERP-2, dropping one row and column and failing with an `UnconsumedListElementsError`. Fixed in the ENDF-6 recipe and in the JENDL flavor, which carries its own copy of the recipe
- MF2/MT151 recipe could not read the background R-matrix of the R-Matrix Limited format (LRU=1, LRF=7, KBK>0): for the tabulated option (LBK=1) the introductory `[LCH, LBK]` CONT record was read twice, so that the first TAB1 record was mistaken for a CONT record, and the channel index LCH, the option LBK and the LBK-dependent quantities were stored in scalars shared by all channels of a spin group, so background R-matrices for more than one channel raised a `NumberMismatchError`. The data of each channel is now kept in its own `background[n]` section of the spin group (`j_group[k]`). For the same reason the tabulated phase shifts (KPS>0) of each channel are now kept in a `phase_shift[n]` section, replacing the `real_part[n]`/`imag_part[n]` tables and the scalar `LPS` at the spin-group level
- MF32/MT151 recipe could not read the uncertainties of the scattering radii (ISR>0) in the covariance formats for the R-Matrix Limited formalism (LRU=1, LRF=7). The sixth field of the LIST record holding the DAP values is the number of lines they occupy, 1+(NJCH-1)/6 with Fortran integer division; the recipe used this expression literally, but `EndfParserPy` requires divisions of integers in recipes to be exact, so for LCOMP=2 it failed unless NJCH-1 was a multiple of six (the code generated for `EndfParserCpp` truncates and was not affected). The integer division is now expressed exactly with the modulo operator. For LCOMP=1 the recipe additionally depended on the number of channels NCH, which is not known at this point, so `EndfParserPy` could not read the record and `EndfParserCpp` derived a spurious NCH from the line count, failing for values spanning more than one line; the DAP values are now stored in the order given in the one-dimensional array `DAP[m]`, m=1..JCH, interpreting the record in the same way as for LCOMP=2
- `EndfParserCpp` evaluated if-conditions with lookahead incorrectly when writing data if a variable in the condition was absent from the dictionary. The generated code substitutes absent variables by placeholder values in the lookahead but still marked them as read, so a comparison such as `JENDL_LIST_NPL != 6` was true and the writer entered a branch whose data did not exist, failing with a `KeyError`. As a consequence, `EndfParserCpp` with the `jendl` flavor and the default `endf6-ext` flavor could not write ENDF-6 conformant MF8/MT457 sections of stable nuclides, e.g. 245 of the 3821 files of the ENDF/B-VIII.0 decay sublibrary. A variable absent from the dictionary is no longer considered read in the lookahead, so comparisons involving it are false, matching the behavior of `EndfParserPy`. In the same vein, an error raised while evaluating the records of a lookahead in write mode, e.g. an expression involving an absent variable that cannot be solved, no longer aborts writing but means that the branch does not apply
- `EndfParserCpp`: the result of a modulo operation in a recipe expression had the sign of the dividend instead of the sign of the divisor, e.g. (5-7)%6 gave -2 instead of 4. This affects the number of padding zeros `(5-NCH)%6` in the resonance parameter records of the R-Matrix Limited format (MF2 and MF32, LRF=7) for spin groups with more than five channels, which no ENDF/B-VIII.0 or ENDF/B-VIII.1 evaluation contains
- The C++ code generator dropped the operator of binary operations (`+`, `-`, `*`, `/`, `%`) in if-conditions, producing code that did not compile; no recipe of the package uses such conditions
- Arithmetic with the value of a float field in a recipe expression: `EndfParserPy` raised a `TypeError` with `preserve_value_strings=True`, the code generated for `EndfParserCpp` did not compile, and solving a float field for a variable through an expression gave code that did not compile (variable `cpp_float_val` declared twice). No recipe of the package contains such expressions
- `EndfParserPy` wrote the value of an expression with an inexact division of integers into a float field (e.g. 1.5 for `N/4` with N=6) but rejected the same value when reading
- `EndfParserCpp` checked only the variables on the left-hand side of a comparison in an if-condition for having been read. `EndfParserPy` treats a comparison involving a variable that has not been read as false, whichever side the variable is on. In the code generated for `EndfParserCpp`, a comparison with an unread variable on the right-hand side used an undefined value, so the wrong branch could be read or written, and a comparison with a constant on the left-hand side, such as `2 != NX`, gave code that did not compile. The variables on both sides are now checked. The recipes of the package contain six comparisons with a variable on the right-hand side; in all of them, the variable has been read when the comparison is evaluated during parsing
- The C++ code generator recursed endlessly (`RecursionError`) on a record field containing a sum of numbers, e.g. `(1+1)*N`, because factoring the number 1 out of `1+1` gives `1*(1+1)` again. The same happened for a field in which the unknown variable appears more than once, e.g. `N+N`, while other such fields, e.g. `2*N-N`, were solved by `EndfParserCpp` but are rejected by `EndfParserPy`. The number 1 is no longer factored out, and a field in which the unknown appears more than once is no longer solved for it, as in `EndfParserPy`: the generated code raises an error if no other field provides the value of the variable. No recipe of the package contains such a field; the code generated for them does not change
- Writing negative zero (`-0.0`): `EndfParserCpp` wrote ` -0.00000+0` (a leading space in addition to the minus sign, with one digit less) and, with `prefer_noexp=True`, `-0`, whereas `EndfParserPy` wrote `-0.000000+0` and `0`, respectively. Both writers now write negative zero as zero (` 0.000000+0`, or `0` with `prefer_noexp=True`). With `preserve_value_strings=True`, the original string of a field read from a file is still written verbatim
- Formatting of floats when a carry in the rounding changes the length of the exponent: `EndfParserPy` wrote one significant digit less than fits into the field with `keep_E=True` (e.g. `1.0000e-9` for 9.99999949e-10), `EndfParserCpp` failed with a field of 10 characters ("wrong size10") with `abuse_signpos=True` (e.g. for 9.9999995e-10), and both wrote `1.000000+10` for 9999999500 with `abuse_signpos=True`, where the exact `9.9999995+9` fits. Both writers now use the largest precision for which a number fits into the field, and produce identical output for all combinations of the formatting options (checked for 40000 values). With the default options, the output of neither writer changes
- MF7/MT451 recipe (generalized information file for thermal scattering data) failed for materials composed of several elements with a different number of atoms per molecule or unit cell (e.g. SiO2): the LIST record describing each element carries its own NAS value, but the recipe stored it in a single scalar, so the second element raised a `NumberMismatchError`. For several elements (NA>1), NAS is now an array indexed by element, `NAS[i]`; for a single element (NA=1), `NAS` remains a scalar, so the dictionary layout of existing files is unchanged
- MF7/MT4 recipe (incoherent inelastic thermal scattering) failed for materials without a principal scattering atom (B(1)=0.0), whose scattering law is completely described by the analytic functions of the non-principal atoms: the recipe always expected the tabulated S(alpha,beta), which is omitted in this case, together with the TAB1 record of the effective temperature of the principal atom (Teff0). The TAB2 record and the TAB1/LIST records of S(alpha,beta) as well as the Teff0 record are now only read if B(1) is non-zero
- `EndfParserCpp` failed with `std::out_of_range` ("stod: out of range") when writing a subnormal number (absolute value below about 2.2e-308, e.g. `4.3709-320` in the tails of S(alpha,beta) tables), or a slightly larger number that is rounded to a subnormal one, with `prefer_noexp=True`, as `std::stod` was used to convert the two candidate representations back to numbers. It now uses `std::strtod` and selects the representation that reproduces the value more closely by the same comparison as `EndfParserPy`, so both writers produce the same output; for numbers that could be written before, the output does not change
- `EndfParserCpp` wrote the original string of an `EndfFloat` value only if the writing parser was also created with `preserve_value_strings=True`, and formatted the number otherwise, whereas `EndfParserPy` always wrote the original string, as documented (the option only determines whether the strings are recorded during parsing). `EndfParserCpp` now also writes the original string of an `EndfFloat` value irrespective of the option, e.g. for data parsed by a different parser or for custom string representations assigned by the user

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
