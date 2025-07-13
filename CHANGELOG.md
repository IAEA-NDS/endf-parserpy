# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.14.2]

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

### Changed

- Replaced deprecated dependency `appdirs` by `platformdirs` package
- Default value of `fuzzy_matching` Python parser argument to `False`
- Expose `include_linenum` argument in command-line interface
- Disabled zero padding of list bodies in Python parser (same behavior now as C++ parser)

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
