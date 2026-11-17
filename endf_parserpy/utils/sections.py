############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/11/17
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Addressing the sections of a material.

A material is a sequence of sections. The position of a section is its
identity; its label ``(MF, MT)`` is read from the section and may occur
more than once in a material if the tape structure of the flavor allows
it (e.g. ``gendf``). The functions of this module select a section in
one of three ways, which mirror the selection of a material on a tape
(``MAT``, ``MAT#k``, ``#k``) one level down:

- by its label ``MF/MT``, if no other section of the material has it;
- by the occurrence ``k`` of its label (``MF/MT#k``), counting from 0 in
  the order of the material;
- by its position ``k`` in the material (``#k``), counting from 0.

**The tape head is not counted.** The position ``#0`` is the first
section after the tape head (MF0/MT0), as in :class:`~endf_parserpy.EndfFile`
and :class:`~endf_parserpy.TapeIndex`. On a material in the list form as
returned by ``parse``, whose element 0 is the tape head, the position
``k`` is therefore the list element ``material[k + 1]``. The tape head
itself is selected by its label, ``0/0``. :func:`iter_sections` gives the
position of each section.

The functions work on both forms of a material (see
:func:`~endf_parserpy.to_list_form`):

- **the list form:** a ``list`` of sections in the order of the material;
- **the nested form:** ``{MF: {MT: section}}``, whose order is the
  canonical order (ascending MF, then MT) and in which a label occurs
  at most once.

A section is a parsed section (a mapping with the keys ``MF`` and ``MT``)
or an unparsed one (a list of lines, labelled by the control fields of
its first line). The functions only move references; they never copy a
section.
"""

from collections import namedtuple
from collections.abc import Mapping

from .tape_structure import _line_label

SectionEntry = namedtuple("SectionEntry", "position mf mt occurrence section")
SectionEntry.__doc__ = """A section of a material, as yielded by :func:`iter_sections`.

Attributes
----------
position : int or None
    The position ``#k`` of the section in the material (the tape head
    not counted), or ``None`` for the tape head.
mf, mt : int
    The label of the section.
occurrence : int
    The occurrence ``k`` of the label (``MF/MT#k``), counting from 0.
section : dict or list
    The section itself (not a copy).
"""


def _unwrap(material):
    from .accessories import EndfObject

    if isinstance(material, EndfObject):
        return material.unwrap()
    return material


def _check_material(material):
    if not isinstance(material, (list, Mapping)):
        raise TypeError(
            "a material must be a dict {MF: {MT: section}} or a list of sections, "
            f"not {type(material).__name__}"
        )


def _label(section):
    """The label ``(MF, MT)`` of a section."""
    if isinstance(section, Mapping):
        try:
            return section["MF"], section["MT"]
        except KeyError as exc:
            raise KeyError(
                f"a parsed section must have the keys MF and MT; {exc} is missing"
            ) from None
    if isinstance(section, list):
        if not section:
            raise ValueError("an unparsed section must not be an empty list")
        return _line_label(section[0], 1)[1:]
    raise TypeError(
        "a section must be a dict (parsed) or a list of strings (unparsed), not "
        f"{type(section).__name__}"
    )


def _is_head(section):
    """Whether a section is the tape head (MF0/MT0), without raising."""
    if isinstance(section, Mapping):
        return section.get("MF") == 0 and section.get("MT") == 0
    if isinstance(section, list) and section and isinstance(section[0], str):
        try:
            return _line_label(section[0], 1)[1:] == (0, 0)
        except (TypeError, ValueError):
            return False
    return False


def is_section(obj):
    """Whether ``obj`` looks like a section: a mapping with the keys ``MF``
    and ``MT``, or a non-empty list whose first element is a string (the
    lines of an unparsed section)."""
    if isinstance(obj, Mapping):
        return "MF" in obj and "MT" in obj
    return isinstance(obj, list) and len(obj) > 0 and isinstance(obj[0], str)


def is_section_list(obj):
    """Whether ``obj`` is a material in the list form: a non-empty ``list``
    whose first element is a section (see :func:`is_section`). Only the
    first element is looked at."""
    return isinstance(obj, list) and len(obj) > 0 and is_section(obj[0])


def _head_offset(material):
    """1 if the list ``material`` begins with the tape head, else 0."""
    return 1 if material and _is_head(material[0]) else 0


def _nested_keys(material):
    return [
        (mf, mt) for mf in sorted(material) if mf != 0 for mt in sorted(material[mf])
    ]


def _labels(material):
    """The labels of the sections of a material in its order, the tape
    head not counted."""
    if isinstance(material, list):
        return [_label(s) for s in material[_head_offset(material) :]]
    return _nested_keys(material)


def _count(n, word):
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def _check_index(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an int, not {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must not be negative, not {value}")


def _check_selector(mf, mt, occurrence, position):
    if position is not None:
        if mf is not None or mt is not None or occurrence is not None:
            raise TypeError(
                "a section is selected either by its label (mf, mt and "
                "optionally occurrence) or by its position, not by both"
            )
        _check_index("position", position)
        return
    if mf is None or mt is None:
        raise TypeError("a section is selected by mf and mt, or by position")
    _check_index("mf", mf)
    _check_index("mt", mt)
    if occurrence is not None:
        _check_index("occurrence", occurrence)


def ambiguous_section_error(mf, mt, positions, hint=None):
    """The :class:`~endf_parserpy.tape.AmbiguousSectionError` for a label
    ``MF/MT`` that matches the sections at ``positions``."""
    from ..tape.errors import AmbiguousSectionError

    if hint is None:
        hint = f"{mf}/{mt}#k"
    return AmbiguousSectionError(
        f"MF={mf}/MT={mt} matches {len(positions)} sections at positions "
        f"{positions}; use {hint} to select one",
        mf=mf,
        mt=mt,
        positions=list(positions),
    )


def locate_in_labels(labels, mf, mt, occurrence=None, position=None, hint=None):
    """Resolve a selection against the labels of the sections of a material.

    ``labels`` are the labels ``(MF, MT)`` of the sections in the order of
    the material, the tape head not counted. Returns the position ``#k``
    of the selected section. Used by :func:`locate_section` and by
    :class:`~endf_parserpy.EndfFile`, so that both give the same errors.

    Raises
    ------
    AmbiguousSectionError
        If ``occurrence`` is ``None`` and several sections have the label.
    KeyError
        If no section has the label.
    IndexError
        If the occurrence or the position is out of range.
    """
    if position is not None:
        if position >= len(labels):
            raise IndexError(
                f"section position {position} out of range; the material has "
                f"{_count(len(labels), 'section')}"
            )
        return position
    positions = [k for k, label in enumerate(labels) if label == (mf, mt)]
    if not positions:
        raise KeyError(f"no section MF={mf}/MT={mt} in the material")
    if occurrence is None:
        if len(positions) > 1:
            raise ambiguous_section_error(mf, mt, positions, hint)
        return positions[0]
    if occurrence >= len(positions):
        raise IndexError(
            f"occurrence {occurrence} out of range; MF={mf}/MT={mt} matches "
            f"{_count(len(positions), 'section')}"
        )
    return positions[occurrence]


def _head_slot(material):
    """The container and key of the tape head, or raise KeyError."""
    if isinstance(material, list):
        if _head_offset(material):
            return material, 0
    elif 0 in material and 0 in material[0]:
        return material[0], 0
    raise KeyError("no section MF=0/MT=0 in the material")


def _slot(material, mf, mt, occurrence, position):
    """The container and key of the selected section, and its position
    (``None`` for the tape head)."""
    if position is None and (mf, mt) == (0, 0):
        if occurrence:
            raise IndexError(
                f"occurrence {occurrence} out of range; MF=0/MT=0 matches 1 section"
            )
        container, key = _head_slot(material)
        return container, key, None
    labels = _labels(material)
    k = locate_in_labels(labels, mf, mt, occurrence, position)
    if isinstance(material, list):
        return material, k + _head_offset(material), k
    mf, mt = labels[k]
    return material[mf], mt, k


def _prepare(material, mf, mt, occurrence, position):
    material = _unwrap(material)
    _check_material(material)
    _check_selector(mf, mt, occurrence, position)
    return material


def iter_sections(material, *, head=False):
    """Iterate over the sections of a material.

    Yields a :class:`SectionEntry` ``(position, mf, mt, occurrence,
    section)`` for each section, in the order of the material (the order
    of the list, or the canonical order of the nested form). ``position``
    is the position ``#k`` and ``occurrence`` the ``k`` of ``MF/MT#k``;
    both count from 0. The tape head is skipped, unless ``head`` is true;
    it then comes first, with the position ``None``.

    Example
    -------
    >>> for entry in iter_sections(material):
    ...     print(f"#{entry.position}: {entry.mf}/{entry.mt}#{entry.occurrence}")
    """
    material = _unwrap(material)
    _check_material(material)
    if isinstance(material, list):
        offset = _head_offset(material)
        if head and offset:
            yield SectionEntry(None, 0, 0, 0, material[0])
        sections = material[offset:]
        labels = [_label(s) for s in sections]
    else:
        if head and 0 in material and 0 in material[0]:
            yield SectionEntry(None, 0, 0, 0, material[0][0])
        labels = _nested_keys(material)
        sections = [material[mf][mt] for mf, mt in labels]
    seen = {}
    for k, (label, section) in enumerate(zip(labels, sections)):
        occurrence = seen.get(label, 0)
        seen[label] = occurrence + 1
        yield SectionEntry(k, label[0], label[1], occurrence, section)


def section_positions(material, mf, mt):
    """Return the positions ``#k`` of the sections with the label MF/MT,
    in the order of the material; an empty list if there is none."""
    material = _prepare(material, mf, mt, None, None)
    return [k for k, label in enumerate(_labels(material)) if label == (mf, mt)]


def locate_section(material, mf=None, mt=None, occurrence=None, *, position=None):
    """Return the position ``#k`` of a section of a material.

    The section is selected by its label (``mf`` and ``mt``; with
    ``occurrence``, the ``occurrence``-th section with this label) or by
    its ``position``. The tape head (``mf=0, mt=0``) has no position, so
    ``None`` is returned for it.

    Raises
    ------
    AmbiguousSectionError
        If no ``occurrence`` is given and several sections have the label.
    KeyError
        If no section has the label.
    IndexError
        If the occurrence or the position is out of range.
    """
    material = _prepare(material, mf, mt, occurrence, position)
    return _slot(material, mf, mt, occurrence, position)[2]


def get_section(material, mf=None, mt=None, occurrence=None, *, position=None):
    """Return a section of a material (the object itself, not a copy).

    The section is selected as by :func:`locate_section`, e.g.
    ``get_section(material, 3, 102)``, ``get_section(material, 3, 102, 2)``
    for the third MF3/MT102 section, or ``get_section(material,
    position=0)`` for the first section after the tape head. The errors
    are those of :func:`locate_section`.
    """
    material = _prepare(material, mf, mt, occurrence, position)
    container, key, _ = _slot(material, mf, mt, occurrence, position)
    return container[key]


def insertion_index(labels, label):
    """The position at which a new section with ``label`` is inserted
    among sections with ``labels`` (in their order): directly after the
    last one that is less than or equal to it, or 0 if there is none."""
    position = 0
    for k, other in enumerate(labels):
        if other <= label:
            position = k + 1
    return position


def insertion_position(material, mf, mt):
    """The position ``#k`` at which a new section with the label MF/MT is
    inserted: directly after the last section whose label is less than or
    equal to MF/MT, or at position 0 if there is none."""
    material = _prepare(material, mf, mt, None, None)
    return insertion_index(_labels(material), (mf, mt))


def _insert_head(material, section):
    if isinstance(material, list):
        if _head_offset(material):
            raise ValueError("the material already has a tape head (MF0/MT0)")
        material.insert(0, section)
    else:
        if 0 in material and 0 in material[0]:
            raise ValueError("the material already has a tape head (MF0/MT0)")
        material.setdefault(0, {})[0] = section


def _repeated_in_nested(mf, mt):
    from ..tape.errors import TapeStructureError

    return TapeStructureError(
        f"the material already has a section MF={mf}/MT={mt}; the nested "
        "form {MF: {MT: section}} holds one section per MF/MT; use "
        'material_form="list"'
    )


def insert_section(material, section, position=None):
    """Insert a section into a material and return its position ``#k``.

    In the list form, the section is inserted at ``position`` (0 up to the
    number of sections; the tape head not counted), also if a section with
    the same label exists already; this is how a further copy of a label is
    added. Without ``position``, it is inserted directly after the last
    section whose label is less than or equal to its own, so that an
    ascending list stays ascending and a copy follows the existing copies.

    In the nested form, the label must be new, and the position follows
    from it; ``position`` must not be given.

    A tape head (MF0/MT0) is always inserted first; ``None`` is returned
    for it.

    Raises
    ------
    TapeStructureError
        In the nested form, if the material has a section with the label.
    IndexError
        If ``position`` is out of range.
    """
    material = _unwrap(material)
    _check_material(material)
    mf, mt = _label(section)
    if (mf, mt) == (0, 0):
        if position:
            raise IndexError("the tape head (MF0/MT0) is always the first section")
        _insert_head(material, section)
        return None
    if isinstance(material, list):
        offset = _head_offset(material)
        num = len(material) - offset
        if position is None:
            position = insertion_position(material, mf, mt)
        else:
            _check_index("position", position)
            if position > num:
                raise IndexError(
                    f"section position {position} out of range for an insertion; "
                    f"the material has {_count(num, 'section')}"
                )
        material.insert(position + offset, section)
        return position
    if position is not None:
        raise ValueError(
            "in the nested form the position of a section follows from its "
            "label; insert it without a position"
        )
    if mf in material and mt in material[mf]:
        raise _repeated_in_nested(mf, mt)
    material.setdefault(mf, {})[mt] = section
    return _nested_keys(material).index((mf, mt))


def set_section(material, section, occurrence=None, *, position=None):
    """Replace a section of a material, or insert it; return its position.

    - With ``position``, the section at this position is replaced. In the
      list form the new section may have another label; in the nested
      form it must have the label of the section it replaces.
    - Otherwise the label of ``section`` selects the section to replace:
      the only one with the label, or with ``occurrence`` the
      ``occurrence``-th one. A label that the material does not have is
      inserted as by :func:`insert_section` (only without
      ``occurrence``; copies of a label are added with
      :func:`insert_section`).

    Raises
    ------
    AmbiguousSectionError
        If the label is repeated and no ``occurrence`` is given.
    KeyError
        If ``occurrence`` is given and no section has the label.
    IndexError
        If the occurrence or the position is out of range.
    ValueError
        In the nested form, if the label differs from that of the section
        at ``position``.
    """
    material = _unwrap(material)
    _check_material(material)
    if position is not None:
        if occurrence is not None:
            raise TypeError(
                "a section is selected either by its occurrence or by its "
                "position, not by both"
            )
        _check_index("position", position)
        labels = _labels(material)
        locate_in_labels(labels, None, None, None, position)
        if isinstance(material, list):
            material[position + _head_offset(material)] = section
        else:
            label = _label(section)
            if label != labels[position]:
                raise ValueError(
                    "in the nested form a section set by position keeps its "
                    f"label: position {position} holds MF={labels[position][0]}/"
                    f"MT={labels[position][1]}, the section has MF={label[0]}/"
                    f"MT={label[1]}"
                )
            material[label[0]][label[1]] = section
        return position
    mf, mt = _label(section)
    if occurrence is not None:
        _check_index("occurrence", occurrence)
    if (mf, mt) == (0, 0):
        try:
            container, key = _head_slot(material)
        except KeyError:
            if occurrence:
                raise
            _insert_head(material, section)
            return None
        if occurrence:
            raise IndexError(
                f"occurrence {occurrence} out of range; MF=0/MT=0 matches 1 section"
            )
        container[key] = section
        return None
    labels = _labels(material)
    if occurrence is None and (mf, mt) not in labels:
        return insert_section(material, section)
    k = locate_in_labels(labels, mf, mt, occurrence)
    if isinstance(material, list):
        material[k + _head_offset(material)] = section
    else:
        material[mf][mt] = section
    return k


def remove_section(material, mf=None, mt=None, occurrence=None, *, position=None):
    """Remove a section from a material and return it.

    The section is selected as by :func:`locate_section`. In the nested
    form, an MF whose last section is removed stays as an empty
    dictionary, which the writers accept.
    """
    material = _prepare(material, mf, mt, occurrence, position)
    container, key, _ = _slot(material, mf, mt, occurrence, position)
    section = container[key]
    del container[key]
    return section
