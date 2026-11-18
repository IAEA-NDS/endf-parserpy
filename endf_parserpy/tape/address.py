############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/18
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Material-qualified addressing for multi-material ENDF files.

An :class:`EndfMaterialPath` extends an :class:`EndfPath` with a leading
*material selector* so that a location can be addressed across a whole
tape. The two grammars are kept separate (design decision D13):
``EndfPath`` is unchanged and still addresses a location within one
material's parsed data; ``EndfMaterialPath`` prepends a material
selector to it.

Material selector grammar -- ``#`` selects the zero-based k-th member of
the candidate set to its left:

* ``MAT``    -- the unique material with that MAT number
* ``MAT#k``  -- the k-th material with that MAT number (PENDF tapes
                repeat a MAT number, once per temperature)
* ``#k``     -- the material at tape position k

The selector is followed by an ordinary ``EndfPath``, so
``9237#1/3/2/xstable`` selects the second material with MAT 9237 and the
``xstable`` field of its MF=3/MT=2 section. The section is selected as by
an ``EndfPath`` applied to a material: ``MF/MT``, ``MF/MT#k`` (the
``k``-th section with this label) or ``#k`` (the section at position
``k``, the tape head not counted), e.g. ``9543#0/3/102#2/IZAM``.
"""

from ..utils.accessories import EndfPath, _Occurrence, _parse_selector_token
from .errors import AmbiguousMaterialError


class EndfMaterialPath:
    """A material selector followed by an :class:`EndfPath`.

    A material-qualified path has the form ``material/MF/MT/field...``.
    The leading *material selector* picks one material of a tape, and
    the remaining ``/MF/MT/field...`` part is an ordinary
    :class:`EndfPath` addressing data within that material. That part
    may be truncated: a path may stop at the material, at a section
    (``material/MF/MT``), or reach down to an individual field.

    The section that follows the material selector is selected in one of
    three ways, as by an :class:`EndfPath` applied to a material:

    - ``MF/MT`` selects the section with this label, which must be unique
      in the material (else an
      :class:`~endf_parserpy.tape.AmbiguousSectionError` is raised);
    - ``MF/MT#k`` selects the ``k``-th section with this label, e.g.
      ``9543/3/102#2``, for a label that occurs several times;
    - ``#k`` selects the section at position ``k`` of the material, e.g.
      ``#0/#1``; the tape head (MF0/MT0) is not counted.

    The material selector takes one of three forms:

    - ``MAT`` selects the material with the given MAT number, e.g.
      ``2925``. Resolving this form fails with an
      :class:`~endf_parserpy.tape.AmbiguousMaterialError` when the MAT
      number is not unique, as it is on a PENDF tape.
    - ``MAT#k`` selects the ``k``-th material carrying that MAT number,
      e.g. ``9237#1``. This disambiguates a repeated MAT number; the
      index ``k`` is zero-based, so ``9237#0`` is the first occurrence.
    - ``#k`` selects the material at tape position ``k``, e.g. ``#0``
      for the first material on the tape. The index ``k`` is zero-based.

    Parameters
    ----------
    pathspec : str or EndfMaterialPath
        The path. For example, ``"9237#1/1/451/TEMP"`` addresses the
        ``TEMP`` field (the temperature) of the MF=1/MT=451 section of
        the second material with MAT 9237, ``"#0/1/451"`` the whole MF=1/MT=451 section of
        the first material on the tape, and ``"2925/3/1"`` the
        MF=3/MT=1 section of the material with MAT 2925.

    Attributes
    ----------
    depth : str
        ``"material"``, ``"mf"``, ``"section"`` or ``"field"``: where the
        path stops.
    mf, mt : int or None
        The label of the section addressed by the path, or ``None`` if the
        path stops at material level or selects the section by its
        position (``#k``). ``mt`` is ``None`` for a path that stops at an
        MF.
    section_occurrence : int or None
        The ``k`` of ``MF/MT#k``, or ``None``.
    section_position : int or None
        The ``k`` of ``#k``, or ``None``.
    subpath : EndfPath or None
        The path *within* the parsed section, or ``None`` for the whole
        section.
    """

    def __init__(self, pathspec):
        if isinstance(pathspec, EndfMaterialPath):
            self.__dict__.update(pathspec.__dict__)
            return
        self._spec = str(pathspec).strip()
        parts = self._spec.strip("/").split("/")
        if parts == [""]:
            raise ValueError("an EndfMaterialPath must not be empty")
        self._parse_material(parts[0])
        rest = [part.strip() for part in parts[1:]]
        self.mf = None
        self.mt = None
        self.section_occurrence = None
        self.section_position = None
        if rest and rest[0].startswith("#"):
            self.section_position = _parse_selector_token(rest[0]).k
            nsel = 1
        else:
            nsel = min(len(rest), 2)
            mt_token = rest[1] if len(rest) >= 2 else None
            if mt_token is not None and "#" in mt_token:
                token = _parse_selector_token(mt_token)
                if not isinstance(token, _Occurrence):
                    raise ValueError(
                        f"invalid material path {self._spec!r}: the section "
                        f"selector {mt_token!r} must be the first element "
                        "after the material selector"
                    )
                self.section_occurrence = token.k
                mt_token = str(token.mt)
            try:
                self.mf = int(rest[0]) if len(rest) >= 1 else None
                self.mt = int(mt_token) if mt_token is not None else None
            except ValueError:
                raise ValueError(
                    f"invalid material path {self._spec!r}: MF and MT must be integers"
                ) from None
        self.subpath = EndfPath("/".join(rest[nsel:])) if len(rest) > nsel else None
        if self.subpath is not None and self.subpath._has_tokens:
            raise ValueError(
                f"invalid material path {self._spec!r}: a section selector can "
                "only follow the material selector"
            )
        if not rest:
            self.depth = "material"
        elif self.section_position is None and self.mt is None:
            self.depth = "mf"
        elif self.subpath is None:
            self.depth = "section"
        else:
            self.depth = "field"

    def _parse_material(self, token):
        try:
            if token.startswith("#"):
                self._kind = "position"
                self._position = int(token[1:])
                self._mat = None
                self._occurrence = None
                if self._position < 0:
                    raise ValueError
            elif "#" in token:
                mat_str, occ_str = token.split("#", 1)
                self._kind = "mat"
                self._mat = int(mat_str)
                self._occurrence = int(occ_str)
                self._position = None
                if self._occurrence < 0:
                    raise ValueError
            else:
                self._kind = "mat"
                self._mat = int(token)
                self._occurrence = None
                self._position = None
        except ValueError:
            raise ValueError(
                f"invalid material selector {token!r}; expected MAT, MAT#k "
                "or #k with non-negative integers"
            ) from None

    def resolve_material(self, index):
        """Resolve the material selector against a :class:`~endf_parserpy.TapeIndex`.

        Returns the zero-based position of the selected material.
        """
        if self._kind == "position":
            if not 0 <= self._position < len(index):
                raise IndexError(
                    f"material position {self._position} out of range; the "
                    f"tape has {len(index)} materials"
                )
            return self._position
        positions = index.by_mat(self._mat)
        if not positions:
            raise KeyError(f"no material with MAT={self._mat}")
        if self._occurrence is None:
            if len(positions) > 1:
                raise AmbiguousMaterialError(
                    f"MAT={self._mat} matches {len(positions)} materials at "
                    f"positions {positions}; use MAT#k to select one"
                )
            return positions[0]
        if not 0 <= self._occurrence < len(positions):
            raise IndexError(
                f"occurrence {self._occurrence} out of range; MAT={self._mat} "
                f"matches {len(positions)} materials"
            )
        return positions[self._occurrence]

    def __repr__(self):
        return f"EndfMaterialPath({self._spec!r})"

    def __eq__(self, other):
        if isinstance(other, EndfMaterialPath):
            return self._spec == other._spec
        return NotImplemented

    def __hash__(self):
        return hash(self._spec)


def parse_section_path(spec):
    """Parse a section-relative path ``"MF/MT[/field...]"``.

    Returns ``(mf, mt, subpath)`` where ``subpath`` is an
    :class:`EndfPath` or ``None`` (meaning the whole section). Used by
    the bulk query operations, which apply the same section path to
    every material.
    """
    parts = str(spec).strip().strip("/").split("/")
    if len(parts) < 2 or parts[0] == "":
        raise ValueError(
            f"section path {spec!r} must have at least MF/MT, e.g. '1/451'"
        )
    try:
        mf = int(parts[0])
        mt = int(parts[1])
    except ValueError:
        raise ValueError(f"section path {spec!r}: MF and MT must be integers") from None
    subpath = EndfPath("/".join(parts[2:])) if len(parts) > 2 else None
    return mf, mt, subpath


def parse_index_spec(spec):
    """Parse a :meth:`EndfFile.build_index` path specification.

    ``spec`` is either a single section path string (the single-field
    index) or a list/tuple of them (a composite index). Returns
    ``(specs, is_multi)`` where ``specs`` is a list of ``(mf, mt,
    subpath)`` triples -- as produced by :func:`parse_section_path` --
    and ``is_multi`` records whether a composite, tuple-keyed index was
    requested. The distinction is by argument *type*, so a one-element
    list still counts as multi.
    """
    if isinstance(spec, str):
        return [parse_section_path(spec)], False
    paths = list(spec)
    if not paths:
        raise ValueError("build_index needs at least one section path")
    return [parse_section_path(p) for p in paths], True


def section_has(section, subpath):
    """Return whether ``subpath`` is present within a parsed section."""
    if subpath is None:
        return True
    return subpath.exists(section)


def walk_section(section, subpath):
    """Return the value at ``subpath`` within a parsed section.

    ``subpath`` is an :class:`EndfPath`, or ``None`` for the whole
    section.
    """
    if subpath is None:
        return section
    return subpath.get(section)
