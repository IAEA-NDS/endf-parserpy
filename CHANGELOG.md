# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Removed

- Option `blank\_as\_zero` from `EndfParser` constructor---now blank numeric fields are always interpreted as zero.

### Fixed

- Avoid check of MAT/MF/MT consistency if `ignore_send_records` option is active

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
