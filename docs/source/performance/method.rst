The files are the 5135 ENDF files of ENDF/B-VIII.1 that every cell
parses and writes;
0 files that fail in a cell are excluded from all cells and listed
with the errors in the results file
(:download:`results.json <performance/results.json>`, key ``excluded``).
Each file is measured in
5 rounds; a time is the sum of the medians per
file, its spread (±) half the difference of the sums of the maxima
and minima, relative to it.
``EndfParserPy`` is measured on a sample of 94 files: per
sublibrary and size group, up to
3 files at fixed quantiles of the
file size, chosen without randomness; ``EndfParserCpp`` is measured
on all files, and so also on the sample.
