############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/09/13
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2022-2026 International Atomic Energy Agency (IAEA)
#
############################################################


from ..errors import EndfParserpyError


class ParserException(EndfParserpyError):
    pass


class StopException(ParserException):
    pass


class UnexpectedControlRecordError(ParserException):
    pass


class BlankLineError(ParserException):
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


class InvalidCharacterError(ParserException):
    """A character that cannot be read or written.

    Raised for characters above U+00FF in strings to be parsed or
    written, which do not correspond to a byte of an ENDF-6 file.
    """

    pass


class VariableNotFoundError(ParserException):
    def __init__(self, message, varname=""):
        super().__init__(message)
        self.varname = varname

    def to_index_error(self):
        return IndexVariableNotFoundError(*self.args, varname=self.varname)


class IndexVariableNotFoundError(VariableNotFoundError):
    pass


class UnavailableIndexError(ParserException):
    pass


class VariableInDenominatorError(ParserException):
    pass


class SeveralUnboundVariablesError(ParserException):
    pass


class AbbreviationNameCollisionError(ParserException):
    pass


class SizeMismatchError(ParserException):
    pass


class MissingSectionError(ParserException):
    def __init__(self, message, section_name="", section_type=""):
        super().__init__(message)
        self.section_name = section_name
        self.section_type = section_type


# not a ParserException: raised while annotating a recipe parse tree for
# the list modes (see numpy_annotation), not while parsing data, and it
# must not be absorbed by the handlers that catch ParserException
class RecipeAnnotationError(EndfParserpyError):
    pass
