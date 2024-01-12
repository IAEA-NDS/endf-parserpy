############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/13
# Last modified:   2022/09/13
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################


class ParserException(Exception):
    pass


class StopException(ParserException):
    pass


class UnexpectedControlRecordError(ParserException):
    pass


class InconsistentVariableAssignmentError(ParserException):
    pass


class LoopVariableError(ParserException):
    pass


class NumberMismatchError(ParserException):
    pass


class MoreListElementsExpectedError(ParserException):
    pass


class UnconsumedListElementsError(ParserException):
    pass


class NotSectionEndError(ParserException):
    pass


class UnexpectedEndOfInputError(ParserException):
    pass


class InvalidIntegerError(ParserException):
    pass


class InvalidFloatError(ParserException):
    pass


class InconsistentSectionBracketsError(ParserException):
    pass


class VariableNotFoundError(ParserException):
    pass


class UnavailableIndexError(ParserException):
    pass


class VariableInDenominatorError(ParserException):
    pass


class SeveralUnboundVariablesError(ParserException):
    pass


class AbbreviationNameCollisionError(ParserException):
    pass
