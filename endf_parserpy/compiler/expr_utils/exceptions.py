############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2024/04/23
# Last modified:   2024/04/23
# License:         MIT
# Copyright (c) 2024 International Atomic Energy Agency (IAEA)
#
############################################################


class EquationSolveError(Exception):
    pass


class VariableMissingError(EquationSolveError):
    pass


class MultipleVariableOccurrenceError(EquationSolveError):
    pass


class ModuloEquationError(EquationSolveError):
    pass


class SeveralUnknownVariablesError(EquationSolveError):
    pass
