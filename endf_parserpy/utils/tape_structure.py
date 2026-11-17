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

"""The tape structure of a flavor: how its sections are framed and arranged.

The *tape structure* gives the rules of a flavor for the container of the
sections of a material, as opposed to the content of the sections, which
the recipes give:

- **end records:** whether a SEND record follows a section, and whether a
  FEND record follows the sections of an MF; every material ends with a
  MEND record and the tape with a TEND record;
- **order:** whether the MF numbers of a material, and the MT numbers
  within an MF, are in ascending order or in any order;
- **repetition:** whether a section with the same MF and MT numbers may
  occur more than once in a material;
- **public form:** whether ``parse`` returns a material as the nested
  dictionary ``{MF: {MT: section}}`` or as a list of sections in file
  order (see :func:`to_dict_form` and :func:`to_list_form`);
- **fill of the end records:** whether the columns 1-66 of the SEND, FEND,
  MEND and TEND records that are written hold zeros or blanks.

A tape structure is given as a dictionary of plain values. The empty
dictionary is the structure of ENDF-6, which every flavor except
``gendf`` has. A rule given at the top level is the default of all
sections; it can be overridden for the sections of an MF (key ``"mf"``)
and for one section (key ``"section"``)::

    {
        "mf_order": "free",
        "mt_order": "free",
        "repeat": True,
        "fend": False,
        "mf": {1: {"fend": True}},
        "section": {(1, 451): {"send": False}},
        "material_form": "list",
        "end_record_fill": "blank",
    }

The rule that applies to a section MF/MT is the first one found in this
order: the entry of the section ``(MF, MT)``, the entry of the MF, the
top-level value, the value of ENDF-6. The rules and the levels at which
they may be given:

=================== ============================== ========= ====== =======
rule                values                         ENDF-6    per MF per MT
=================== ============================== ========= ====== =======
``send``            ``True``/``False``             ``True``  yes    yes
``fend``            ``True``/``False``             ``True``  yes    no
``repeat``          ``True``/``False``             ``False`` yes    yes
``mt_order``        ``"ascending"``/``"free"``     ascending yes    no
``mf_order``        ``"ascending"``/``"free"``     ascending no     no
``material_form``   ``"dict"``/``"list"``          ``dict``  no     no
``end_record_fill`` ``"zero"``/``"blank"``         ``zero``  no     no
=================== ============================== ========= ====== =======

A *run* of an MF is a sequence of consecutive sections of this MF in a
material. ``fend`` asks for a FEND record after each run of the MF. With
``mf_order="ascending"`` an MF has a single run, so that a section after
the FEND record of an MF must have a greater MF. With
``mt_order="ascending"``, the MT numbers increase within a run; if the
section may repeat, the copies must follow each other. Copies of a
section that are not separated by any record are read as one section.
The tape head (TPID, MF0/MT0) is outside these rules.

:class:`TapeStructure` is the validated and resolved form of such a
dictionary, which both parsers use.
"""

from collections.abc import Mapping
from dataclasses import dataclass

# the bits of the flags of an MF and of a section
SEND = 1
FEND = 2
REPEAT = 4
MT_ASC = 8
HAS_SECTIONS = 16

_RULES = {
    # rule: (allowed values, levels where allowed: global, mf, section)
    "send": ((True, False), (True, True, True)),
    "fend": ((True, False), (True, True, False)),
    "repeat": ((True, False), (True, True, True)),
    "mt_order": (("ascending", "free"), (True, True, False)),
    "mf_order": (("ascending", "free"), (True, False, False)),
    "material_form": (("dict", "list"), (True, False, False)),
    "end_record_fill": (("zero", "blank"), (True, False, False)),
}

_DEFAULTS = {
    "send": True,
    "fend": True,
    "repeat": False,
    "mt_order": "ascending",
    "mf_order": "ascending",
    "material_form": "dict",
    "end_record_fill": "zero",
}

_LEVEL_NAMES = ("globally", "per MF", "per section")

_NUM_MF = 100


def _err(message):
    return ValueError(f"tape_structure: {message}")


def _check_value(rule, value):
    values = _RULES[rule][0]
    if isinstance(values[0], bool):
        if not isinstance(value, bool):
            raise _err(f"{rule!r} must be True or False, not {value!r}")
    elif value not in values:
        choices = " or ".join(f'"{v}"' for v in values)
        raise _err(f"{rule!r} must be {choices}, not {value!r}")


def _check_rules(rules, level, where):
    if not isinstance(rules, Mapping):
        raise TypeError(
            f"tape_structure: the rules {where} must be a dict, not "
            f"{type(rules).__name__}"
        )
    for rule, value in rules.items():
        if rule not in _RULES:
            allowed = ", ".join(r for r in _RULES if _RULES[r][1][level])
            raise _err(f"unknown rule {rule!r} {where} (allowed: {allowed})")
        if not _RULES[rule][1][level]:
            allowed = " and ".join(
                _LEVEL_NAMES[k] for k, ok in enumerate(_RULES[rule][1]) if ok
            )
            raise _err(f"{rule!r} can only be given {allowed}, not {where}")
        _check_value(rule, value)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_mf(mf, what):
    if not _is_int(mf):
        raise TypeError(
            f"tape_structure: the MF number {mf!r} of {what} must be an int"
        )
    if mf == 0:
        raise _err("the MF number 0 is the tape head (TPID) and takes no rules")
    if not 1 <= mf < _NUM_MF:
        raise _err(f"the MF number {mf} of {what} is not between 1 and 99")


def _flags(send, fend, repeat, mt_asc):
    return (
        (SEND if send else 0)
        | (FEND if fend else 0)
        | (REPEAT if repeat else 0)
        | (MT_ASC if mt_asc else 0)
    )


@dataclass(frozen=True)
class TapeStructure:
    """The validated and resolved rules of a tape structure.

    Create it with :meth:`from_spec` from a dictionary (see the module
    documentation); :data:`ENDF6` is the structure of ENDF-6. The object
    is immutable, hashable and can be pickled.

    Attributes
    ----------
    mf_flags : tuple[int, ...]
        The resolved rules of the sections of each MF (index 0 to 99), as
        bits ``SEND``, ``FEND``, ``REPEAT``, ``MT_ASC``, and
        ``HAS_SECTIONS`` if a section of the MF has rules of its own.
    section_flags : tuple[tuple[tuple[int, int], int], ...]
        The resolved rules (bits ``SEND`` and ``REPEAT``) of the sections
        with rules of their own, sorted by MF and MT.
    mf_ascending : bool
        Whether the MF numbers of a material are in ascending order.
    material_form : str
        The public form of a material, ``"dict"`` or ``"list"``.
    end_record_fill : str
        ``"zero"`` or ``"blank"``: the columns 1-66 of the end records
        that are written.
    defaults : tuple[bool, bool, bool, bool]
        The top-level rules ``send``, ``fend``, ``repeat`` and whether
        ``mt_order`` is ascending.
    """

    mf_flags: tuple
    section_flags: tuple
    mf_ascending: bool
    material_form: str
    end_record_fill: str
    defaults: tuple

    @classmethod
    def from_spec(cls, spec):
        """Validate and resolve a tape structure.

        Parameters
        ----------
        spec : None, dict or TapeStructure
            ``None`` is the structure of ENDF-6; a :class:`TapeStructure`
            is returned as it is.

        Raises
        ------
        TypeError, ValueError
            If the dictionary is not a valid tape structure.
        """
        if spec is None:
            return ENDF6
        if isinstance(spec, TapeStructure):
            return spec
        if not isinstance(spec, Mapping):
            raise TypeError(
                "tape_structure must be a dict, a TapeStructure or None, not "
                f"{type(spec).__name__}"
            )
        top = {k: v for k, v in spec.items() if k not in ("mf", "section")}
        _check_rules(top, 0, "at the top level")
        rules = dict(_DEFAULTS)
        rules.update(top)
        by_mf = spec.get("mf", {})
        by_section = spec.get("section", {})
        if not isinstance(by_mf, Mapping):
            raise TypeError("tape_structure: 'mf' must be a dict {MF: {rule: value}}")
        if not isinstance(by_section, Mapping):
            raise TypeError(
                "tape_structure: 'section' must be a dict {(MF, MT): {rule: value}}"
            )
        for mf, mf_rules in by_mf.items():
            _check_mf(mf, "an entry of 'mf'")
            _check_rules(mf_rules, 1, f"for MF={mf}")
        for key, sec_rules in by_section.items():
            if not (
                isinstance(key, tuple)
                and len(key) == 2
                and _is_int(key[0])
                and _is_int(key[1])
            ):
                raise TypeError(
                    "tape_structure: a key of 'section' must be a tuple "
                    f"(MF, MT) of two ints, not {key!r}"
                )
            mf, mt = key
            _check_mf(mf, f"the section {key!r}")
            if not 1 <= mt <= 999:
                raise _err(
                    f"the MT number {mt} of the section {key!r} is not between 1 and 999"
                )
            _check_rules(sec_rules, 2, f"for the section {key!r}")

        defaults = (
            rules["send"],
            rules["fend"],
            rules["repeat"],
            rules["mt_order"] == "ascending",
        )
        mf_flags = []
        mf_resolved = {}
        for mf in range(_NUM_MF):
            r = dict(zip(("send", "fend", "repeat", "mt_order"), defaults))
            r["mt_order"] = rules["mt_order"]
            r.update(by_mf.get(mf, {}))
            mf_resolved[mf] = r
            mf_flags.append(
                _flags(r["send"], r["fend"], r["repeat"], r["mt_order"] == "ascending")
            )
        section_flags = []
        for (mf, mt), sec_rules in sorted(by_section.items()):
            r = mf_resolved[mf]
            send = sec_rules.get("send", r["send"])
            repeat = sec_rules.get("repeat", r["repeat"])
            section_flags.append(((mf, mt), _flags(send, False, repeat, False)))
            mf_flags[mf] |= HAS_SECTIONS
        return cls(
            mf_flags=tuple(mf_flags),
            section_flags=tuple(section_flags),
            mf_ascending=rules["mf_order"] == "ascending",
            material_form=rules["material_form"],
            end_record_fill=rules["end_record_fill"],
            defaults=defaults,
        )

    def __post_init__(self):
        object.__setattr__(self, "_sections", dict(self.section_flags))
        object.__setattr__(
            self,
            "_endf6",
            self.section_flags == ()
            and self.mf_ascending
            and self.material_form == "dict"
            and self.end_record_fill == "zero"
            and self.defaults == (True, True, False, True)
            and all(f == _flags(True, True, False, True) for f in self.mf_flags),
        )

    def __getstate__(self):
        return {name: getattr(self, name) for name in self.__dataclass_fields__}

    def __setstate__(self, state):
        for name, value in state.items():
            object.__setattr__(self, name, value)
        self.__post_init__()

    # -- lookups ---------------------------------------------------------

    @property
    def is_endf6(self):
        """Whether all rules are those of ENDF-6 (the public form
        included)."""
        return self._endf6

    def _section_flags(self, mf, mt):
        if 0 <= mf < _NUM_MF:
            flags = self.mf_flags[mf]
            if flags & HAS_SECTIONS:
                return self._sections.get((mf, mt), flags)
            return flags
        return _flags(*self.defaults)

    def send(self, mf, mt):
        """Whether a SEND record follows the section MF/MT."""
        return bool(self._section_flags(mf, mt) & SEND)

    def repeat(self, mf, mt):
        """Whether the section MF/MT may occur more than once in a
        material."""
        return bool(self._section_flags(mf, mt) & REPEAT)

    def fend(self, mf):
        """Whether a FEND record follows a run of sections of the MF."""
        if 0 <= mf < _NUM_MF:
            return bool(self.mf_flags[mf] & FEND)
        return self.defaults[1]

    def mt_ascending(self, mf):
        """Whether the MT numbers of a run of the MF are in ascending
        order."""
        if 0 <= mf < _NUM_MF:
            return bool(self.mf_flags[mf] & MT_ASC)
        return self.defaults[3]

    # -- other forms -----------------------------------------------------

    def to_spec(self):
        """Return the tape structure as a normalized dictionary, which
        :meth:`from_spec` turns into an equal object; rules equal to
        those of ENDF-6 are left out."""
        send, fend, repeat, mt_asc = self.defaults
        spec = {}
        top = {
            "send": send,
            "fend": fend,
            "repeat": repeat,
            "mt_order": "ascending" if mt_asc else "free",
            "mf_order": "ascending" if self.mf_ascending else "free",
            "material_form": self.material_form,
            "end_record_fill": self.end_record_fill,
        }
        for rule, value in top.items():
            if value != _DEFAULTS[rule]:
                spec[rule] = value
        base = _flags(*self.defaults)
        by_mf = {}
        for mf in range(1, _NUM_MF):
            flags = self.mf_flags[mf] & ~HAS_SECTIONS
            if flags == base:
                continue
            entry = {}
            for rule, bit in (("send", SEND), ("fend", FEND), ("repeat", REPEAT)):
                if bool(flags & bit) != bool(base & bit):
                    entry[rule] = bool(flags & bit)
            if bool(flags & MT_ASC) != bool(base & MT_ASC):
                entry["mt_order"] = "ascending" if flags & MT_ASC else "free"
            by_mf[mf] = entry
        if by_mf:
            spec["mf"] = by_mf
        by_section = {}
        for (mf, mt), flags in self.section_flags:
            mf_flags = self.mf_flags[mf]
            entry = {}
            for rule, bit in (("send", SEND), ("repeat", REPEAT)):
                if bool(flags & bit) != bool(mf_flags & bit):
                    entry[rule] = bool(flags & bit)
            if entry:
                by_section[(mf, mt)] = entry
        if by_section:
            spec["section"] = by_section
        return spec

    def cpp_options(self):
        """Return the form of the rules for the options of the C++
        module: ``(mf_flags, section_flags, mf_ascending, blank_fill)``,
        with ``mf_flags`` as 100 bytes and ``section_flags`` as a tuple of
        ``(1000 * MF + MT, flags)``."""
        cached = self.__dict__.get("_cpp")
        if cached is None:
            cached = (
                bytes(self.mf_flags),
                tuple(
                    (1000 * mf + mt, flags) for (mf, mt), flags in self.section_flags
                ),
                self.mf_ascending,
                self.end_record_fill == "blank",
            )
            object.__setattr__(self, "_cpp", cached)
        return cached

    def __repr__(self):
        return f"TapeStructure.from_spec({self.to_spec()!r})"


ENDF6 = TapeStructure.from_spec({})
"""The tape structure of ENDF-6: all rules at their defaults."""


# -- the forms of a material -----------------------------------------------


def _line_label(line, lineno=None, what="the section given as a list of lines"):
    from ..interpreter.endf_utils import ctrl_field_value

    if isinstance(line, bytes):
        line = line.decode("latin-1")
    if not isinstance(line, str):
        raise TypeError(f"a line of {what} must be a str, not {type(line).__name__}")
    text = line.rstrip("\r\n")[66:75].ljust(9)
    values = []
    for name, start, length in (("MAT", 0, 4), ("MF", 4, 2), ("MT", 6, 3)):
        field = text[start : start + length]
        value = ctrl_field_value(field)
        if value is None:
            where = f" of line {lineno}" if lineno is not None else ""
            raise ValueError(
                f'invalid {name} number field: "{field}" (columns '
                f"{67 + start}-{66 + start + length}){where} of {what}"
            )
        values.append(value)
    return tuple(values)


def section_label(section):
    """Return the label ``(MAT, MF, MT)`` of a section.

    A parsed section (a mapping) gives its keys ``MAT``, ``MF`` and
    ``MT``; an unparsed section (a list of lines) gives the control
    fields (columns 67-75) of its first line. For the tape head (MF0/MT0),
    the MAT field is the tape number.
    """
    if isinstance(section, Mapping):
        try:
            return (section["MAT"], section["MF"], section["MT"])
        except KeyError as exc:
            raise KeyError(
                f"a parsed section must have the keys MAT, MF and MT; {exc} is missing"
            ) from None
    if isinstance(section, list):
        if not section:
            raise ValueError("an unparsed section must not be an empty list")
        return _line_label(section[0], 1)
    raise TypeError(
        "a section must be a dict (parsed) or a list of strings (unparsed), not "
        f"{type(section).__name__}"
    )


def is_list_form(material):
    """Whether ``material`` is a material in the list form (a list of
    sections), as opposed to the nested form (a mapping)."""
    return isinstance(material, list)


def to_list_form(material):
    """Return a material in the list form.

    A material in the nested form ``{MF: {MT: section}}`` becomes the
    list of its sections in canonical order: the tape head (MF0/MT0)
    first, then ascending MF and, within an MF, ascending MT. A parsed
    section without the keys ``MF`` and ``MT`` gets them from its keys in
    the dictionary; a section whose ``MF`` or ``MT`` differs from them is
    an error. A list is returned as it is. Only references are moved.
    """
    if isinstance(material, list):
        return material
    if not isinstance(material, Mapping):
        raise TypeError(
            "a material must be a dict {MF: {MT: section}} or a list of sections, "
            f"not {type(material).__name__}"
        )
    from ..interpreter.custom_exceptions import UnexpectedControlRecordError

    result = []
    for mf in sorted(material):
        mtdic = material[mf]
        for mt in sorted(mtdic):
            section = mtdic[mt]
            if isinstance(section, Mapping):
                section.setdefault("MF", mf)
                if section["MF"] != mf:
                    raise UnexpectedControlRecordError(
                        f"expected MF={mf} but found MF={section['MF']}"
                    )
                section.setdefault("MT", mt)
                if section["MT"] != mt:
                    raise UnexpectedControlRecordError(
                        f"expected MT={mt} but found MT={section['MT']}"
                    )
            result.append(section)
    return result


def _positions(positions):
    positions = [str(p) for p in positions]
    if len(positions) == 1:
        return positions[0]
    return ", ".join(positions[:-1]) + " and " + positions[-1]


def to_dict_form(material):
    """Return a material in the nested form ``{MF: {MT: section}}``.

    A list of sections becomes the nested dictionary by their labels (see
    :func:`section_label`); a mapping is returned as it is. Only
    references are moved. The order of the sections is not kept.

    Raises
    ------
    TapeStructureError
        If two sections have the same MF and MT numbers, which the
        nested form cannot hold.
    """
    if not isinstance(material, list):
        return material
    result = {}
    seen = {}
    repeated = None
    for pos, section in enumerate(material):
        _, mf, mt = section_label(section)
        mtdic = result.setdefault(mf, {})
        if mt in mtdic:
            seen[(mf, mt)].append(pos)
            if repeated is None:
                repeated = (mf, mt)
            continue
        seen[(mf, mt)] = [pos]
        mtdic[mt] = section
    if repeated is not None:
        from ..tape.errors import TapeStructureError

        mf, mt = repeated
        positions = seen[repeated]
        raise TapeStructureError(
            f"the material has {len(positions)} sections MF={mf}/MT={mt} "
            f"(at positions {_positions(positions)} of the list); the nested "
            "form {MF: {MT: section}} holds one section per MF/MT; use "
            'material_form="list"'
        )
    return result


def recipe_ends_with_send(recipe):
    """Whether the text of a recipe ends with a SEND record (its last
    instruction, comments left out)."""
    for line in reversed(recipe.splitlines()):
        code = line.split("#", 1)[0].strip()
        if code:
            return code == "SEND"
    return False


def _recipe_keys(recipes):
    """Yield ``(MF, MT, text)`` of the recipes of a recipe dictionary;
    ``MT`` is ``None`` for a recipe of all sections of an MF (also for
    the key -1)."""
    for mf, entry in recipes.items():
        if isinstance(entry, str):
            yield mf, None, entry
        elif isinstance(entry, Mapping):
            for mt, text in entry.items():
                if isinstance(text, str):
                    yield mf, (None if mt == -1 else mt), text


def check_recipes(recipes, tape_structure):
    """Check that the recipes and the tape structure agree on the SEND
    records.

    For a section with a recipe, the recipe decides whether a SEND record
    is read and written; the tape structure must give the same rule for
    every section the recipe can serve. The recipe of the tape head
    (MF0/MT0) is not checked.

    Raises
    ------
    ValueError
        At the first recipe that disagrees with the tape structure.
    """
    ts = TapeStructure.from_spec(tape_structure)
    for mf, mt, text in _recipe_keys(recipes):
        if not _is_int(mf) or mf == 0:
            continue
        has_send = recipe_ends_with_send(text)
        if mt is not None:
            labels = [(mt, "section")]
        else:
            labels = [(None, "MF")]
            labels += [(m, "section") for (f, m), _ in ts.section_flags if f == mf]
        for m, level in labels:
            expected = ts.send(mf, -1 if m is None else m)
            if expected == has_send:
                continue
            what = f"MF={mf}/MT={m}" if m is not None else f"MF={mf}"
            recipe = f"MF={mf}/MT={mt}" if mt is not None else f"MF={mf}"
            if (mf, m) in ts._sections:
                rule = f"rule of the section ({mf}, {m})"
            elif (ts.mf_flags[mf] & ~HAS_SECTIONS) != _flags(*ts.defaults):
                rule = f"rule of MF={mf}"
            else:
                rule = "global rule"
            if has_send:
                raise ValueError(
                    f"the recipe for {recipe} ends with a SEND record, but the "
                    f"tape structure has no SEND record after the sections of "
                    f"{what} ({rule}); remove SEND from the recipe or set "
                    '"send": True'
                )
            raise ValueError(
                f"the recipe for {recipe} does not end with a SEND record, but "
                f"the tape structure expects one after the sections of {what} "
                f"({rule})"
            )


def _lenient_label(section):
    """The label of a section, with ``None`` for the numbers that cannot
    be determined (they are reported where the section is written)."""
    if isinstance(section, Mapping):
        return section.get("MAT"), section.get("MF"), section.get("MT")
    if isinstance(section, list) and section:
        try:
            return _line_label(section[0], 1)
        except (TypeError, ValueError):
            return None, None, None
    return None, None, None


def dict_form_keys(material):
    """The keys ``(MF, MT)`` of a material in the nested form, in the
    order of :func:`to_list_form`."""
    return [(mf, mt) for mf in sorted(material) for mt in sorted(material[mf])]


def check_material(material, tape_structure, given_as_list=True, keys=None):
    """Check a material in the list form before it is written.

    The checks of the writers of both parsers:

    - every section is a mapping (parsed) or a list of lines (unparsed)
      with the labels ``MF`` and ``MT``, and the tape head (MF0/MT0), if
      present, is the first section;
    - all sections except the tape head have the same MAT number;
    - the order and the repetition of the sections follow the rules of
      the tape structure (only for a material given as a list; the
      conversion of the nested form gives the canonical order).

    For a material given in the nested form, ``keys`` are its keys
    ``(MF, MT)`` (see :func:`dict_form_keys`), which label the sections;
    a MAT number that cannot be read (e.g. a missing key or an invalid
    field) is left to the writer, which reports it as before. A section of
    a list must have readable labels.

    Returns
    -------
    list[tuple]
        The labels ``(MAT, MF, MT)`` of the sections.

    Raises
    ------
    TypeError, ValueError
        At the first section that breaks a rule.
    """
    ts = TapeStructure.from_spec(tape_structure)
    labels = []
    material_mat = None
    prev = None
    seen = set()
    for pos, section in enumerate(material):
        if given_as_list:
            if not isinstance(section, (Mapping, list)):
                raise TypeError(
                    "a section must be a dict (parsed) or a list of strings "
                    f"(unparsed), got {type(section).__name__} at position {pos} "
                    "of the list"
                )
            if isinstance(section, Mapping) and (
                section.get("MF") is None or section.get("MT") is None
            ):
                raise ValueError(
                    f"the parsed section at position {pos} of the list has no "
                    "MF or MT key"
                )
        if keys is not None:
            mf, mt = keys[pos]
            mat = _lenient_label(section)[0]
        elif isinstance(section, list) and section:
            mat, mf, mt = _line_label(section[0], 1, f"the section at position {pos}")
        else:
            mat, mf, mt = _lenient_label(section)
        labels.append((mat, mf, mt))
        if mf == 0 and mt == 0:
            if pos != 0 and given_as_list:
                raise ValueError(
                    "the tape head (MF=0/MT=0) must be the first section of the "
                    f"list, found at position {pos}"
                )
            continue
        if mat is not None:
            if material_mat is None:
                material_mat = (mat, mf, mt)
            elif mat != material_mat[0]:
                raise ValueError(
                    f"section MF={mf}/MT={mt} at position {pos} of the list has "
                    f"MAT={mat}, but the material has MAT={material_mat[0]} (from "
                    f"the section MF={material_mat[1]}/MT={material_mat[2]}); all "
                    "sections of a material must have the same MAT number (the "
                    "tape head MF=0/MT=0 is not counted)"
                )
        if not given_as_list:
            continue
        where = (
            f"cannot write the section MF={mf}/MT={mt} at position {pos} of the list"
        )
        if prev is not None:
            pmf, pmt = prev
            if ts.mf_ascending and mf < pmf:
                raise ValueError(
                    f"{where} after MF={pmf}/MT={pmt}: the tape structure requires "
                    "ascending MF"
                )
            if mf == pmf and ts.mt_ascending(mf):
                if mt < pmt or (mt == pmt and not ts.repeat(mf, mt)):
                    raise ValueError(
                        f"{where} after MF={pmf}/MT={pmt}: the tape structure "
                        "requires ascending MT within an MF"
                    )
            if ts.mf_ascending and mf != pmf and mf in {m for m, _ in seen}:
                raise ValueError(
                    f"{where} after MF={pmf}/MT={pmt}: the tape structure requires "
                    "ascending MF"
                )
        if (mf, mt) in seen and not ts.repeat(mf, mt):
            first = next(k for k, l in enumerate(labels[:-1]) if l[1:] == (mf, mt))
            raise ValueError(
                f"{where}: MF={mf}/MT={mt} already occurs at position {first}, and "
                "the tape structure does not allow a repeated section"
            )
        seen.add((mf, mt))
        prev = (mf, mt)
    return labels


def check_verbatim_labels(lines, mf, mt):
    """Check that all lines of an unparsed section have the MAT, MF and MT
    numbers of its first line (lines whose numbers cannot be read are left
    to the writer)."""
    if not lines:
        return
    first = lines[0]
    if isinstance(first, bytes):
        first = first.decode("latin-1")
    if not isinstance(first, str):
        return
    first_cols = first.rstrip("\r\n")[66:75]
    expected = None
    for k, line in enumerate(lines[1:], start=2):
        if isinstance(line, bytes):
            line = line.decode("latin-1")
        if not isinstance(line, str):
            continue
        cols = line.rstrip("\r\n")[66:75]
        if cols == first_cols or cols.strip() == "":
            # (a short line without control fields is written as it is)
            continue
        try:
            if expected is None:
                expected = _line_label(first, 1)
            found = _line_label(line, k)
        except ValueError:
            continue
        if found != expected:
            raise ValueError(
                f"line {k} of the section MF={mf}/MT={mt} given as a list of lines "
                f"has MAT/MF/MT {'/'.join(map(str, found))}, which differ from "
                f"{'/'.join(map(str, expected))} of its first line"
            )
