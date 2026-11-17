The files are the 4 ENDF files of ENDF/B-VIII.1 that every cell
parses and writes;
1 file that fails in a cell is excluded from all cells and listed
with the errors in the results file
(:download:`results.json <performance/results.json>`, key ``excluded``).
Each file is measured in
3 rounds; a time is the sum of the medians per
file, its spread (±) half the difference of the sums of the maxima
and minima, relative to it.
``EndfParserPy`` is measured on a sample of 4 files: per
sublibrary and size group, up to
3 files at fixed quantiles of the
file size, chosen without randomness; ``EndfParserCpp`` is measured
on all files, and so also on the sample.
