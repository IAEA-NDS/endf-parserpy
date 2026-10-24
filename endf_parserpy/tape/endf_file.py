############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/10/24
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Lazy, memory-bounded, editable access to a multi-material ENDF file.

:class:`EndfFile` indexes a tape on construction and reads and parses
individual sections from disk only when they are accessed, keeping the
results in bounded caches (see :mod:`endf_parserpy.tape.cache`). A
single section is parsed by wrapping its records in a minimal
single-material tape and handing that to an ordinary parser, so the
parsing engine is used unchanged.

Each material is represented by a :class:`_MaterialSlot` that carries an
edit overlay. Sections can be replaced, added or deleted and materials
can be deleted, appended or reordered; :meth:`EndfFile.export` writes
the edited tape back out and :meth:`EndfFile.to_string` returns it as
text. Untouched sections keep their data records verbatim from disk;
the SEND/FEND/MEND framing and the column 76-80 sequence numbers are
regenerated, so an unedited round trip preserves every data field
byte-for-byte but is not necessarily byte-identical overall -- the same
guarantee the ordinary writer gives.
"""

import os
from contextlib import contextmanager
from collections.abc import Mapping

from ..endf_parser_factory import EndfParserFactory
from ..endf_parser_base import EndfParserBase
from .address import (
    EndfMaterialPath,
    parse_index_spec,
    parse_section_path,
    section_has,
    walk_section,
)
from .cache import _RawCache, _SectionCache, _Section
from .errors import (
    AmbiguousMaterialError,
    SectionParseError,
    SectionRenderError,
    StaleSourceError,
    TapeStructureError,
)
from .index import TapeIndex
from .material import MaterialView, _MaterialSlot
from .operations import write_tape, write_tape_file, _VALID_ON_ERROR, _FailedUnit
from .records import _control_numbers, _control_line, _strip_send, TEND_LINE
from .views import (
    _FrozenMapping,
    _FrozenSequence,
    _LiveMapping,
    _LiveSequence,
    _SectionView,
    _navigate,
    _plain,
)


_VALID_MODES = ("index", "load_raw", "parse_all")
_VALID_CHECK_EDITS = ("eager", "deferred")
# _VALID_ON_ERROR is shared with operations.py -- the on_error policy is
# the same concept for EndfFile and for the parse_tape functions.

# sentinel distinguishing "no value given" from an explicit value of None
_UNSET = object()


def _value_match(field, value, tol):
    if tol and isinstance(field, (int, float)) and isinstance(value, (int, float)):
        return abs(field - value) <= tol
    return field == value


class _CurrentMaterials:
    """Adapter over the current slot list for material-selector resolution.

    Exposes the ``__len__`` and ``by_mat`` that
    :meth:`EndfMaterialPath.resolve_material` needs, so a material
    selector resolves against the *current* (possibly edited) material
    order rather than the on-disk index.
    """

    def __init__(self, slots):
        self._slots = slots

    def __len__(self):
        return len(self._slots)

    def by_mat(self, mat):
        return [i for i, s in enumerate(self._slots) if s.mat == mat]


class FailedSection(_FailedUnit):
    """Internal placeholder for a section that could not be parsed.

    When the :class:`EndfFile` was opened with ``on_error="mark"`` a
    section that fails to parse is kept as a :class:`FailedSection` so
    that the bulk operations (:meth:`~EndfFile.query`,
    :meth:`~EndfFile.build_index`, :meth:`~EndfFile.export`) can skip it
    or write it back verbatim instead of aborting. Accessing such a
    section directly (``endf_file[path]`` or ``material[mf, mt]``)
    raises :class:`SectionParseError`, with this object's
    :attr:`exception` kept as the cause; a :class:`FailedSection` is
    therefore never handed back to the caller.

    Attributes
    ----------
    exception : Exception
        The exception raised while parsing the section.
    raw_lines : list[str]
        The raw text of the section.
    position : int
        Position of the material the section belongs to.
    mf, mt : int
        The MF/MT numbers of the section.
    """

    def __init__(self, exception, raw_lines, position, mf, mt):
        super().__init__(exception, raw_lines)
        self.position = position
        self.mf = mf
        self.mt = mt

    def __repr__(self):
        return (
            f"FailedSection(position={self.position}, MF={self.mf}, "
            f"MT={self.mt}, exception={self.exception!r})"
        )


class EndfFile:
    """Lazy, memory-bounded, editable view of a multi-material ENDF file.

    The file is indexed on construction (see :class:`TapeIndex`).
    Section data is read from disk and parsed only on access and is then
    held in bounded caches. Materials are addressed by zero-based
    position::

        with EndfFile("tape.endf") as endf_file:
            material = endf_file[0]         # a MaterialView
            section = material[3, 2]        # parsed MF=3/MT=2 section
            material[3, 2] = section        # edit it back in
            endf_file.export("edited.endf")

    Parameters
    ----------
    filename : str or os.PathLike
        Path to the ENDF file.
    parser : EndfParserBase, optional
        Engine used to parse and write sections. Defaults to
        ``EndfParserFactory.create(select="fastest")``.
    mode : {"index", "load_raw", "parse_all"}
        ``"index"`` (default) only builds the index. ``"load_raw"`` also
        pre-reads section text into the raw cache; ``"parse_all"`` also
        parses every section. The cache budgets still apply, so these
        modes pre-warm the caches rather than guarantee residency.
    parsed_cache_bytes, raw_cache_bytes : int
        Budgets, in raw-text-equivalent bytes, for the parsed-section
        and raw-text caches.
    on_error : {"raise", "mark"}
        Whether a section that fails to parse raises
        :class:`SectionParseError` or is returned as a
        :class:`FailedSection`.
    check_edits : {"eager", "deferred"}
        When the recipe-conformity of an edited section is checked.
        ``"eager"`` (the default) renders every edited section through
        the parser's writer immediately, so a malformed edit raises at
        the offending assignment, and a retrieved section is a read-only
        (frozen) view. ``"deferred"`` accepts every edit, marking the
        section dirty, and checks conformity only at :meth:`export` /
        :meth:`to_string` or :meth:`invalid_edits`; a retrieved section
        is then a live write-through view.
    verify_source : bool
        If true, the file's size and mtime are checked against the
        index before every disk read; a change raises
        :class:`StaleSourceError`.

    Notes
    -----
    An :class:`EndfFile` is not safe for concurrent use from several
    threads: its caches, material list and edit overlays are plain,
    unguarded state, so any access racing with another is undefined.
    Use one :class:`EndfFile` per thread.
    """

    def __init__(
        self,
        filename,
        *,
        parser=None,
        mode="index",
        parsed_cache_bytes=64 << 20,
        raw_cache_bytes=64 << 20,
        on_error="mark",
        check_edits="eager",
        verify_source=False,
    ):
        if mode not in _VALID_MODES:
            raise ValueError(f"mode must be one of {_VALID_MODES}, got {mode!r}")
        if on_error not in _VALID_ON_ERROR:
            raise ValueError(
                f"on_error must be one of {_VALID_ON_ERROR}, got {on_error!r}"
            )
        if check_edits not in _VALID_CHECK_EDITS:
            raise ValueError(
                f"check_edits must be one of {_VALID_CHECK_EDITS}, got "
                f"{check_edits!r}"
            )
        self._path = os.fspath(filename)
        self._parser = parser or EndfParserFactory.create(select="fastest")
        if not isinstance(self._parser, EndfParserBase):
            raise TypeError(
                f"parser must be an EndfParserBase instance (as created by "
                f"EndfParserFactory.create()), got {type(self._parser).__name__}"
            )
        self._on_error = on_error
        self._check_edits = check_edits
        self._verify_source = verify_source
        self._index = TapeIndex.from_file(self._path)
        self._materials = [
            _MaterialSlot(e.position, e.mat, e.za, e.awr) for e in self._index
        ]
        self._raw_cache = _RawCache(raw_cache_bytes)
        self._section_cache = _SectionCache(parsed_cache_bytes)
        self._material_views = {}
        self._secondary_indexes = {}
        self._read_fh = None
        self._invalidated = False
        if mode == "load_raw":
            self._preload(parse=False)
        elif mode == "parse_all":
            self._preload(parse=True)

    def _ensure_valid(self):
        """Raise if the object was invalidated by an export onto its source.

        After :meth:`export` overwrites the file the :class:`EndfFile`
        was opened from, the structural index no longer matches the
        bytes on disk, so lazily reading any untouched section would
        return garbage. The object is therefore invalidated; every data
        operation raises until the file is re-opened.
        """
        if self._invalidated:
            raise StaleSourceError(
                f"this EndfFile was invalidated when export() overwrote its "
                f"source file {self._path!r}; its structural index no longer "
                f"matches the file on disk -- re-open it with "
                f"EndfFile({self._path!r})"
            )

    def _preload(self, parse):
        # a whole-tape operation: read every section through a single
        # held file handle instead of reopening the file per section
        with self._read_session():
            for entry in self._index:
                for mf, mt in list(entry.sections):
                    if parse:
                        self._get_section(entry.position, mf, mt)
                    else:
                        self._get_raw(entry.position, mf, mt, entry.sections[(mf, mt)])

    # -- polymorphic item protocol -------------------------------------
    #
    # ``[]``, ``[]=``, ``del`` and ``in`` accept either an integer
    # material position or an EndfMaterialPath (string or object). The
    # path may stop at a material, a section or a field; see the design
    # note docs/design/endf_file_path_addressing.md.

    def __len__(self):
        self._ensure_valid()
        return len(self._materials)

    def _material_view(self, slot):
        """Return the (cached) :class:`MaterialView` of a slot."""
        view = self._material_views.get(slot)
        if view is None:
            view = MaterialView(self, slot)
            self._material_views[slot] = view
        return view

    def _remove_material(self, position):
        """Delete the material at ``position`` and drop its cached view.

        Dropping the :class:`MaterialView` keeps ``_material_views`` from
        accumulating entries for materials that no longer exist; an
        external reference to the view stays valid as an *invalid* view
        (its :attr:`~MaterialView.position` then raises). The named
        secondary indexes are dropped too -- see :meth:`_invalidate_indexes`.
        """
        slot = self._materials.pop(position)
        slot.removed = True
        self._material_views.pop(slot, None)
        self._invalidate_indexes()

    def _invalidate_indexes(self):
        """Drop the cached secondary indexes after a structural edit.

        :meth:`build_index` keys its result by tape position, so adding,
        removing or reordering materials would silently leave a stored
        index pointing at the wrong materials. Rather than let it go
        stale, any structural edit clears it; rebuild it afterwards.
        """
        self._secondary_indexes.clear()

    def _resolve_key(self, key):
        """Resolve a path key to ``(position, mf, mt, subpath)``.

        ``mf`` is ``None`` for a material-depth path; ``subpath`` is
        ``None`` unless the path reaches into a section.
        """
        mp = key if isinstance(key, EndfMaterialPath) else EndfMaterialPath(key)
        if mp.mf is not None and mp.mt is None:
            raise ValueError(
                f"{mp!r} addresses a whole MF file; MF-level addressing is "
                "not supported -- address a section as material/MF/MT"
            )
        position = mp.resolve_material(_CurrentMaterials(self._materials))
        return position, mp.mf, mp.mt, mp.subpath

    def __getitem__(self, key):
        """Return the material, section or field addressed by ``key``.

        ``key`` is an integer material position or an
        :class:`EndfMaterialPath` (string or object). A material-depth
        path yields a :class:`MaterialView`, a section-depth path a
        section view and a field-depth path the value at that field.
        """
        self._ensure_valid()
        if isinstance(key, int):
            return self._material_view(self._materials[key])
        if not isinstance(key, (str, EndfMaterialPath)):
            raise TypeError(
                "EndfFile is indexed by an integer material position or an "
                "EndfMaterialPath (string or object); use by_mat() or "
                "by_za() for other lookups"
            )
        position, mf, mt, subpath = self._resolve_key(key)
        slot = self._materials[position]
        if mf is None:
            return self._material_view(slot)
        section = self._get_slot_section(slot, mf, mt)
        return self._view(slot, mf, mt, section, subpath)

    def __setitem__(self, key, value):
        """Assign the section or field addressed by an :class:`EndfMaterialPath`.

        A section-depth path replaces or adds a whole section; a
        field-depth path edits one field within it. Whole materials
        cannot be assigned -- use :meth:`append_material`.
        """
        self._ensure_valid()
        if isinstance(key, int):
            raise ValueError(
                "a whole material cannot be assigned by position; use "
                "append_material() to add a material"
            )
        if not isinstance(key, (str, EndfMaterialPath)):
            raise TypeError(
                "EndfFile is indexed by an integer material position or an "
                "EndfMaterialPath (string or object)"
            )
        position, mf, mt, subpath = self._resolve_key(key)
        slot = self._materials[position]
        if mf is None:
            raise ValueError(
                "a whole material cannot be assigned; use append_material() "
                "to add a material"
            )
        if subpath is None:
            self._set_slot_section(slot, mf, mt, value)
        else:
            self._set_slot_field(slot, mf, mt, subpath, value)

    def __delitem__(self, key):
        """Delete the material, section or field addressed by ``key``."""
        self._ensure_valid()
        if isinstance(key, int):
            self._remove_material(key)
            return
        if not isinstance(key, (str, EndfMaterialPath)):
            raise TypeError(
                "EndfFile is indexed by an integer material position or an "
                "EndfMaterialPath (string or object)"
            )
        position, mf, mt, subpath = self._resolve_key(key)
        slot = self._materials[position]
        if mf is None:
            self._remove_material(position)
        elif subpath is None:
            self._delete_slot_section(slot, mf, mt)
        else:
            self._delete_slot_field(slot, mf, mt, subpath)

    def __contains__(self, key):
        """Whether ``key`` resolves to a present material/section/field.

        An ``int`` is tested as a material position. A malformed path or
        an ambiguous bare-MAT selector is genuinely ill-posed and
        propagates its :class:`ValueError` / :class:`AmbiguousMaterialError`
        rather than being answered ``False``. A field-depth path whose
        section cannot be parsed answers ``False`` -- the field is not
        reachable -- regardless of the ``on_error`` mode.
        """
        self._ensure_valid()
        if isinstance(key, int):
            return -len(self._materials) <= key < len(self._materials)
        if not isinstance(key, (str, EndfMaterialPath)):
            return False
        try:
            position, mf, mt, subpath = self._resolve_key(key)
        except (KeyError, IndexError):
            return False
        slot = self._materials[position]
        if mf is None:
            return True
        if (mf, mt) not in self._slot_section_keys_set(slot):
            return False
        if subpath is None:
            return True
        try:
            section = self._get_slot_section(slot, mf, mt)
        except (KeyError, SectionParseError):
            return False
        if not isinstance(section, Mapping):
            return False  # an unparsable (FailedSection) or raw section
        return section_has(section, subpath)

    def __iter__(self):
        """Iterate over the materials as :class:`MaterialView` objects."""
        self._ensure_valid()
        for position in range(len(self._materials)):
            yield self._material_view(self._materials[position])

    def materials(self):
        """Return all materials as a list of :class:`MaterialView` objects."""
        return list(self)

    def _position_of(self, slot):
        try:
            return self._materials.index(slot)
        except ValueError:
            raise RuntimeError("this material has been deleted from the tape") from None

    # -- editing -------------------------------------------------------

    def append_material(self, material, *, mat, za=None, awr=None):
        """Append a new material to the tape.

        Parameters
        ----------
        material : Mapping
            A nested ``{MF: {MT: section}}`` mapping, as returned by an
            ordinary ``parsefile``. The ``MF=0`` tape-head entry, if
            present, is ignored.
        mat : int
            ENDF MAT number of the new material.
        za, awr : optional
            Identifiers, used by :meth:`by_za` and the index.

        Returns
        -------
        MaterialView
            A view of the appended material.

        Notes
        -----
        Under ``check_edits="eager"`` every section of the appended
        material is render-checked immediately, exactly as a section
        assignment is, so a malformed section is rejected here rather
        than at :meth:`export` time.

        The ``mat`` argument must agree with the MAT number the
        material carries in its own records (the ``'MAT'`` key of a
        parsed section, or the control field of a raw section's first
        line); a mismatch is rejected, since the records, not the
        argument, are what gets written to the tape.
        """
        self._ensure_valid()
        mat = int(mat)
        slot = _MaterialSlot(
            original_position=None,
            mat=mat,
            za=None if za is None else int(za),
            awr=None if awr is None else float(awr),
        )
        for mf, mtdic in material.items():
            mf_i = int(mf)
            if mf_i == 0:
                continue  # the MF=0 tape-head entry, if present, is ignored
            for mt, section in mtdic.items():
                mf_mt = (mf_i, int(mt))
                self._check_section_key(*mf_mt)
                if isinstance(section, _SectionView):
                    section = section.detach()
                if not isinstance(section, (Mapping, list)):
                    raise TypeError(
                        f"section MF={mf_mt[0]}/MT={mf_mt[1]} of the appended "
                        "material must be a mapping (parsed) or a list of "
                        "strings (raw)"
                    )
                section_mat = self._section_mat(section)
                if section_mat is not None and section_mat != mat:
                    raise ValueError(
                        f"mat={mat} was given, but section MF={mf_mt[0]}/"
                        f"MT={mf_mt[1]} of the material carries MAT="
                        f"{section_mat}; the two must agree"
                    )
                if self._check_edits == "eager":
                    self._check_section(*mf_mt, section)
                slot.overlay[mf_mt] = section
        self._materials.append(slot)
        self._invalidate_indexes()
        return self[len(self._materials) - 1]

    def reorder(self, order):
        """Reorder the materials of the tape.

        ``order`` is a permutation of ``range(len(self))``: the material
        currently at ``order[i]`` moves to position ``i``.
        """
        self._ensure_valid()
        order = list(order)
        if sorted(order) != list(range(len(self._materials))):
            raise ValueError("order must be a permutation of range(len(self))")
        self._materials = [self._materials[i] for i in order]
        self._invalidate_indexes()

    # -- secondary lookups ---------------------------------------------

    def _positions(self, *, mat=_UNSET, za=_UNSET):
        """Tape positions of the materials matching every given criterion.

        A criterion left as ``_UNSET`` is not applied; ``None`` is
        treated as an ordinary value to match, so ``by_za(None)``
        selects the materials whose ZA is unknown. This is the single
        structural-filter loop behind :meth:`by_mat`, :meth:`by_za` and
        :meth:`find`.
        """
        return [
            i
            for i, s in enumerate(self._materials)
            if (mat is _UNSET or s.mat == mat) and (za is _UNSET or s.za == za)
        ]

    def by_mat(self, mat, *, occurrence=None):
        """Return the material with the given MAT number.

        ``occurrence`` (zero-based) selects among several materials that
        share a MAT number, as on a PENDF tape. Without it, a MAT number
        that is not unique raises :class:`AmbiguousMaterialError`.
        """
        self._ensure_valid()
        positions = self._positions(mat=mat)
        if not positions:
            raise KeyError(f"no material with MAT={mat}")
        if occurrence is not None:
            return self[positions[occurrence]]
        if len(positions) > 1:
            raise AmbiguousMaterialError(
                f"MAT={mat} matches {len(positions)} materials at positions "
                f"{positions}; pass occurrence=0..{len(positions) - 1}"
            )
        return self[positions[0]]

    def by_za(self, za):
        """Return a list of materials with the given ZA identifier."""
        self._ensure_valid()
        return [self[i] for i in self._positions(za=za)]

    def find(self, *, mat=None, za=None):
        """Return a list of materials matching every given criterion.

        This is the structural lookup; a criterion left as ``None`` is
        not applied. For lookups by a parsed section field, see
        :meth:`query`.
        """
        self._ensure_valid()
        criteria = {}
        if mat is not None:
            criteria["mat"] = mat
        if za is not None:
            criteria["za"] = za
        return [self[i] for i in self._positions(**criteria)]

    # -- path-based queries --------------------------------------------

    def get(self, path):
        """Return the material, section or field addressed by ``path``.

        ``path`` is an :class:`EndfMaterialPath` or a string of the form
        ``material[/MF/MT[/field...]]``. This is the explicit-method
        synonym of ``endf_file[path]``: a material-depth path yields a
        :class:`MaterialView`, a section-depth path a section view (see
        :mod:`endf_parserpy.tape.views`) and a field-depth path the value
        at that field. If the addressed section cannot be parsed a
        :class:`SectionParseError` is raised regardless of ``on_error``.
        """
        return self[path]

    def build_index(self, section_path, *, name=None):
        """Build a secondary index over one or several section fields.

        With a single section path -- a string ``"MF/MT[/field...]"`` --
        this parses that section of every material that has it, reads
        the value at the field path and returns a dict
        ``{value: [positions]}``.

        With a list (or tuple) of section paths it builds a *composite*
        index instead: the key is the tuple of the values at the
        respective paths, in the order given, so the result is a dict
        ``{(value0, value1, ...): [positions]}``. A material is indexed
        only if *every* path resolves for it; one that lacks any of the
        addressed sections or fields is skipped. Paths that share an
        ``MF/MT`` section have it parsed only once per material. The key
        shape follows the *argument type*: a one-element list still
        yields one-element-tuple keys.

        One section is parsed per material per distinct ``MF/MT``, so
        the cost grows with the number of materials. With ``name`` the
        result is also stored and reachable via
        :attr:`secondary_indexes`; because the index is keyed by tape
        position, a stored index is dropped whenever a material is
        appended, removed or reordered, and must then be rebuilt.
        """
        self._ensure_valid()
        specs, is_multi = parse_index_spec(section_path)
        mapping = {}
        for position, slot in enumerate(self._materials):
            values = self._collect_index_values(slot, specs)
            if values is None:
                continue
            key = tuple(values) if is_multi else values[0]
            try:
                mapping.setdefault(key, []).append(position)
            except TypeError:
                raise ValueError(
                    f"section path {section_path!r} resolves to a "
                    "non-hashable value; build_index needs scalar field(s)"
                ) from None
        if name is not None:
            self._secondary_indexes[name] = mapping
        return mapping

    def _resolve_query_field(self, slot, mf, mt, subpath):
        """Resolve one section field of a material for the bulk lookups.

        Returns ``(True, value)`` for a field that is present, and
        ``(False, None)`` when the material lacks the section or the
        field, or the section failed to parse under ``on_error="mark"``
        (under ``on_error="raise"`` the failing parse propagates). The
        section is read through the cache, so addressing the same
        ``MF/MT`` more than once does not re-parse it. Shared by
        :meth:`query` and :meth:`build_index`.
        """
        if (mf, mt) not in self._slot_section_keys_set(slot):
            return False, None
        section = self._get_slot_section(slot, mf, mt)
        if isinstance(section, FailedSection):
            return False, None
        if not section_has(section, subpath):
            return False, None
        return True, walk_section(section, subpath)

    def _collect_index_values(self, slot, specs):
        """Return the field values for ``build_index``, or ``None`` to skip.

        ``specs`` is a list of ``(mf, mt, subpath)``. The material is
        skipped (``None`` is returned) when it lacks any of the
        addressed sections or fields, or when a needed section failed to
        parse under ``on_error="mark"``.
        """
        values = []
        for mf, mt, subpath in specs:
            found, value = self._resolve_query_field(slot, mf, mt, subpath)
            if not found:
                return None
            values.append(value)
        return values

    def query(self, section_path, value=_UNSET, *, predicate=None, tol=0.0):
        """Return the materials whose section field matches.

        Pass exactly one of ``value`` (equality, within ``tol`` for
        numbers) or ``predicate`` (a callable applied to the field).
        Returns a list of :class:`MaterialView`.
        """
        self._ensure_valid()
        if (value is _UNSET) == (predicate is None):
            raise ValueError("pass exactly one of value or predicate")
        mf, mt, subpath = parse_section_path(section_path)
        matches = []
        for position, slot in enumerate(self._materials):
            found, field = self._resolve_query_field(slot, mf, mt, subpath)
            if not found:
                continue
            if predicate is not None:
                matched = bool(predicate(field))
            else:
                matched = _value_match(field, value, tol)
            if matched:
                matches.append(self[position])
        return matches

    @property
    def secondary_indexes(self):
        """The named secondary indexes built by :meth:`build_index`.

        Emptied whenever a material is appended, removed or reordered,
        since the indexes are keyed by tape position.
        """
        return self._secondary_indexes

    # -- per-material section access (slot-aware) ----------------------

    def _slot_section_keys_set(self, slot):
        if slot.original_position is not None:
            keys = set(self._index[slot.original_position].sections)
        else:
            keys = set()
        keys -= slot.deleted
        keys |= set(slot.overlay)
        return keys

    def _slot_section_keys(self, slot):
        return sorted(self._slot_section_keys_set(slot))

    def _get_slot_section(self, slot, mf, mt):
        self._ensure_valid()
        key = (mf, mt)
        if key in slot.overlay:
            return slot.overlay[key]
        if key in slot.deleted:
            raise KeyError(f"this material has no MF={mf}/MT={mt} section")
        if (
            slot.original_position is None
            or key not in self._index[slot.original_position].sections
        ):
            raise KeyError(f"this material has no MF={mf}/MT={mt} section")
        return self._get_section(slot.original_position, mf, mt)

    @staticmethod
    def _check_section_key(mf, mt):
        """Reject an ``(MF, MT)`` that cannot name a material section.

        A material section has ``MF >= 1`` and ``MT >= 1``; ``MF 0`` is
        the tape-head slot and ``MT 0`` marks a SEND record, so assigning
        a section to either would corrupt the written tape.
        """
        if mf < 1 or mt < 1:
            raise ValueError(
                f"MF={mf}/MT={mt} is not a valid section key; a material "
                "section has MF >= 1 and MT >= 1"
            )

    @staticmethod
    def _section_mat(section):
        """The MAT number a material section carries, or ``None``.

        A parsed section is a mapping with a ``'MAT'`` key; a raw
        section is a list of ENDF lines whose first line names the MAT
        in its control field. ``None`` is returned when neither yields
        a usable (positive) value.
        """
        if isinstance(section, Mapping):
            mat = section.get("MAT")
            return None if mat is None else int(mat)
        if isinstance(section, list) and section:
            mat = _control_numbers(section[0])[0]
            return mat if mat > 0 else None
        return None

    def _set_slot_section(self, slot, mf, mt, value):
        self._ensure_valid()
        self._check_section_key(mf, mt)
        if isinstance(value, _SectionView):
            value = value.detach()
        if not isinstance(value, (Mapping, list)):
            raise TypeError(
                "a section must be a mapping (parsed) or a list of strings (raw)"
            )
        if self._check_edits == "eager":
            self._check_section(mf, mt, value)
        slot.overlay[(mf, mt)] = value
        slot.deleted.discard((mf, mt))

    def _set_slot_field(self, slot, mf, mt, subpath, value):
        """Read-modify-write a single field within a section.

        Under ``check_edits="eager"`` a deep copy of the section is
        edited and render-checked before it is committed, so a malformed
        result leaves the canonical section untouched. Under
        ``"deferred"`` the canonical section is edited in place and
        marked dirty.
        """
        if isinstance(value, _SectionView):
            value = value.detach()
        section = self._get_slot_section(slot, mf, mt)
        self._require_mapping_section(section, mf, mt)
        if self._check_edits == "eager":
            work = _plain(section)
            self._set_at(work, subpath, value)
            self._check_section(mf, mt, work)
            slot.overlay[(mf, mt)] = work
            slot.deleted.discard((mf, mt))
        else:
            self._set_at(section, subpath, value)
            slot.overlay[(mf, mt)] = section
            slot.deleted.discard((mf, mt))

    def _delete_slot_section(self, slot, mf, mt):
        self._ensure_valid()
        if (mf, mt) not in self._slot_section_keys_set(slot):
            raise KeyError(f"this material has no MF={mf}/MT={mt} section")
        slot.overlay.pop((mf, mt), None)
        if (
            slot.original_position is not None
            and (mf, mt) in self._index[slot.original_position].sections
        ):
            slot.deleted.add((mf, mt))

    def _delete_slot_field(self, slot, mf, mt, subpath):
        """Delete a single field within a section (deferred mode only)."""
        if self._check_edits == "eager":
            raise ValueError(
                "deleting a section field is rejected in check_edits='eager' "
                "mode because the resulting section no longer conforms to "
                "its ENDF recipe; open the EndfFile with "
                "check_edits='deferred', or assign a whole edited section"
            )
        section = self._get_slot_section(slot, mf, mt)
        self._require_mapping_section(section, mf, mt)
        self._del_at(section, subpath)
        slot.overlay[(mf, mt)] = section
        slot.deleted.discard((mf, mt))

    def _require_mapping_section(self, section, mf, mt):
        """Raise unless ``section`` is a parsed (mapping) section."""
        if isinstance(section, FailedSection):
            raise SectionParseError(
                f"MF={mf}/MT={mt} of the material at position "
                f"{section.position} failed to parse"
            ) from section.exception
        if not isinstance(section, Mapping):
            raise TypeError(
                f"MF={mf}/MT={mt} is a recipe-less (raw) section; it has no "
                "addressable fields"
            )

    @staticmethod
    def _set_at(container, subpath, value):
        parent, last = _navigate(container, subpath)
        parent[last] = value

    @staticmethod
    def _del_at(container, subpath):
        parent, last = _navigate(container, subpath)
        del parent[last]

    def _view(self, slot, mf, mt, section, subpath=None):
        """Wrap a canonical section in the mode-dependent view.

        ``check_edits="eager"`` yields a frozen (read-only) view,
        ``"deferred"`` a live write-through view. A
        :class:`FailedSection` raises :class:`SectionParseError`. With a
        ``subpath`` the view is navigated to that field, returning a
        nested view or a bare scalar.
        """
        if isinstance(section, FailedSection):
            raise SectionParseError(
                f"MF={mf}/MT={mt} of the material at position "
                f"{section.position} failed to parse"
            ) from section.exception
        if self._check_edits == "deferred":

            def touch(_slot=slot, _mf=mf, _mt=mt, _section=section):
                _slot.overlay[(_mf, _mt)] = _section
                _slot.deleted.discard((_mf, _mt))

            if isinstance(section, Mapping):
                view = _LiveMapping(section, touch)
            else:
                view = _LiveSequence(section, touch)
        else:
            if isinstance(section, Mapping):
                view = _FrozenMapping(section)
            else:
                view = _FrozenSequence(section)
        if subpath is None:
            return view
        return view[subpath]

    def _check_section(self, mf, mt, section):
        """Render a section through the writer to check recipe conformity.

        A render failure -- the section does not conform to its ENDF
        recipe -- propagates. Only mapping sections are checked; a
        recipe-less raw section is written verbatim and has no recipe to
        violate.
        """
        if not isinstance(section, Mapping):
            return
        try:
            self._parser.write({0: {0: [self._index.tpid_line]}, mf: {mt: section}})
        except Exception as exc:
            raise SectionRenderError(
                f"the edited MF={mf}/MT={mt} section does not render to "
                f"valid ENDF-6 text: {exc}"
            ) from exc

    def invalid_edits(self):
        """Return the edited sections that do not conform to their recipe.

        Renders every edited section through the parser's writer and
        returns a list of ``(position, MF, MT, exception)`` tuples, one
        per edited section that fails to render; an empty list means
        every edit is conformant, so ``if not endf_file.invalid_edits()``
        reads as "every edit is valid". Untouched sections are written
        verbatim and are not checked.

        Under ``check_edits="deferred"`` this is the explicit conformity
        check that :meth:`export` and :meth:`to_string` perform
        implicitly; under ``"eager"`` every edit was already checked at
        write time, so it is a near no-op but remains harmless to call.
        """
        report = []
        for position, slot in enumerate(self._materials):
            for (mf, mt), section in list(slot.overlay.items()):
                if not isinstance(section, Mapping):
                    continue
                try:
                    self._check_section(mf, mt, section)
                except SectionRenderError as exc:
                    report.append((position, mf, mt, exc))
        return report

    # -- the lazy access path ------------------------------------------

    def _get_raw(self, position, mf, mt, sec_entry):
        key = (position, mf, mt)
        cached = self._raw_cache.get(key)
        if cached is not None:
            return cached
        raw = self._read_span(sec_entry.offset, sec_entry.length)
        self._raw_cache.put(key, raw, sec_entry.length)
        return raw

    def _get_section(self, position, mf, mt):
        key = (position, mf, mt)
        cached = self._section_cache.get(key)
        if cached is not None:
            return cached
        entry = self._index[position]
        sec_entry = entry.sections.get((mf, mt))
        if sec_entry is None:
            raise KeyError(
                f"material at position {position} (MAT={entry.mat}) has "
                f"no MF={mf}/MT={mt} section"
            )
        raw = self._get_raw(position, mf, mt, sec_entry)
        section = self._parse_section(entry, mf, mt, raw)
        self._section_cache.put(key, section, sec_entry.length)
        return section

    def _parse_section(self, entry, mf, mt, raw_lines):
        # wrap the section in a minimal single-material tape so the
        # ordinary parser can be used unchanged
        mini_tape = (
            [self._index.tpid_line]
            + list(raw_lines)
            + [
                _control_line(entry.mat, 0, 0),  # FEND
                _control_line(0, 0, 0),  # MEND
                TEND_LINE,  # TEND
            ]
        )
        try:
            result = self._parser.parse(mini_tape)
            section = result[mf][mt]
        except Exception as exc:
            if self._on_error == "raise":
                raise SectionParseError(
                    f"failed to parse MF={mf}/MT={mt} of the material at "
                    f"position {entry.position} (MAT={entry.mat})"
                ) from exc
            return FailedSection(exc, raw_lines, entry.position, mf, mt)
        if isinstance(section, Mapping):
            return _Section(section)
        return section  # a section without a recipe stays a list of strings

    @contextmanager
    def _read_session(self):
        """Hold one file handle open for the duration of the block.

        Disk reads performed inside the block reuse a single handle
        instead of reopening the file per section. Used for whole-tape
        operations; outside such a block every read opens and closes the
        file on its own, which keeps interactive use simple and never
        pins the file open.
        """
        with open(self._path, "rb") as fh:
            self._read_fh = fh
            try:
                yield
            finally:
                self._read_fh = None

    def _read_span(self, offset, length):
        if self._verify_source:
            self._check_source()
        fh = self._read_fh
        if fh is None:
            with open(self._path, "rb") as fh:
                fh.seek(offset)
                data = fh.read(length)
        else:
            fh.seek(offset)
            data = fh.read(length)
        return data.decode("latin-1").splitlines()

    def _check_source(self):
        stat = os.stat(self._path)
        if (
            stat.st_size != self._index.source_size
            or stat.st_mtime_ns != self._index.source_mtime_ns
        ):
            raise StaleSourceError(
                f"the source file {self._path!r} changed after it was indexed"
            )

    # -- write-back ----------------------------------------------------

    def _assemble(self, slot):
        """Build a ``{MF: {MT: section}}`` dict ready for the writer.

        Untouched sections are taken verbatim from disk; edited or added
        sections come from the overlay.
        """
        material = {0: {0: [self._index.tpid_line]}}
        for mf, mt in self._slot_section_keys(slot):
            if (mf, mt) in slot.overlay:
                section = slot.overlay[(mf, mt)]
                # an overlay section is always a parsed mapping or a raw
                # list of lines; a raw list is stripped of any trailing
                # SEND so the writer can re-emit it
                if isinstance(section, list):
                    section = _strip_send(section)
            else:
                sec_entry = self._index[slot.original_position].sections[(mf, mt)]
                raw = self._get_raw(slot.original_position, mf, mt, sec_entry)
                section = _strip_send(raw)
            material.setdefault(mf, {})[mt] = section
        return material

    def _check_deferred_edits(self):
        """Render-check the edits before output (deferred mode only).

        Under ``check_edits="deferred"`` a non-conformant edited section
        raises :class:`SectionRenderError` here, before any output is
        produced; under ``"eager"`` every edit was already checked when
        it was made, so this is a no-op.
        """
        if self._check_edits != "deferred":
            return
        report = self.invalid_edits()
        if report:
            position, mf, mt, exc = report[0]
            raise SectionRenderError(
                f"the edited MF={mf}/MT={mt} section of the material at "
                f"position {position} does not render to valid ENDF-6 text "
                f"({len(report)} edited section(s) failed to render); call "
                "invalid_edits() for the full report"
            ) from exc.__cause__

    def _check_materials_have_sections(self):
        """Reject, before output, a material left with no sections.

        A sectionless material is a legal *transient* state -- e.g.
        while every section is deleted to rebuild a material -- but it
        is not valid ENDF: on re-indexing such a material is silently
        dropped. It is therefore rejected at :meth:`export` /
        :meth:`to_string` time, naming the offending position.
        """
        for position, slot in enumerate(self._materials):
            if not self._slot_section_keys_set(slot):
                raise TapeStructureError(
                    f"the material at position {position} has no sections; "
                    "a material must have at least one section to be "
                    "written -- use 'del endf_file[position]' to remove a "
                    "material entirely"
                )

    def _empty_tape_text(self):
        """The ENDF-6 text of this tape once every material is removed.

        A tape with no materials is just its tape head (TPID) followed
        by the tape end (TEND). The original TPID is kept, so an
        emptied tape retains its identity.
        """
        return self._index.tpid_line + "\n" + TEND_LINE + "\n"

    def _output_materials(self):
        """Yield each material assembled and ready for :func:`write_tape`.

        Each material is produced as a ``{MF: {MT: section}}`` dict, one
        at a time, so a streaming consumer (:func:`write_tape_file`)
        never holds the whole tape in memory. An untouched section is
        assembled from its raw on-disk text -- it is not parsed -- so
        only sections that were actually edited were ever parsed.
        """
        for slot in self._materials:
            yield self._assemble(slot)

    def to_string(self):
        """Return the (possibly edited) tape as an ENDF-6 formatted string.

        Untouched sections keep their data records verbatim from disk
        and edited or added sections are rendered by the parser; in both
        cases the SEND/FEND/MEND framing and the column 76-80 sequence
        numbers are regenerated, so every data field is preserved
        byte-for-byte but the tape is not necessarily byte-identical to
        the input. The result ends with a newline; use
        :meth:`str.splitlines` if a list of lines is needed. A tape from
        which every material has been deleted is written as its tape
        head (TPID) followed by the tape end (TEND).

        This necessarily builds the whole tape in memory; for a large
        tape, write it to a file with :meth:`export`, which is
        memory-bounded.
        """
        self._ensure_valid()
        self._check_deferred_edits()
        self._check_materials_have_sections()
        if not self._materials:
            return self._empty_tape_text()
        with self._read_session():
            return write_tape(self._output_materials(), parser=self._parser)

    def export(self, path, *, overwrite=False):
        """Write the (possibly edited) tape to a file.

        The tape is written one material at a time via a temporary file
        and an atomic replace, so peak memory stays bounded by a single
        material regardless of the tape size. Untouched sections keep
        their data records verbatim from disk (they are not parsed) and
        edited or added sections are rendered by the parser; the
        SEND/FEND/MEND framing and the column 76-80 sequence numbers are
        regenerated either way, preserving every data field byte-for-byte
        without making the tape byte-identical. An existing file is only
        overwritten when ``overwrite=True``. A tape from which every
        material has been deleted is written as its tape head (TPID)
        followed by the tape end (TEND).

        Exporting onto the file the :class:`EndfFile` was opened from is
        permitted, but it leaves the in-memory structural index stale
        (the byte offsets of untouched sections have moved). The object
        is therefore *invalidated*: every subsequent operation raises
        :class:`StaleSourceError`, and the file must be re-opened with a
        new :class:`EndfFile` to continue. Exporting to any other path
        leaves the object usable.
        """
        self._ensure_valid()
        self._check_deferred_edits()
        self._check_materials_have_sections()
        path = os.fspath(path)
        if os.path.exists(path) and not overwrite:
            raise FileExistsError(
                f"file {path} already exists; pass overwrite=True to replace it"
            )
        onto_source = os.path.realpath(path) == os.path.realpath(self._path)
        tmp = path + ".endfparserpy-tmp"
        try:
            if self._materials:
                with self._read_session():
                    write_tape_file(
                        self._output_materials(),
                        tmp,
                        parser=self._parser,
                        overwrite=True,
                    )
            else:
                # every material was deleted: a valid TPID + TEND tape
                # (newline="" keeps the LF terminators verbatim on Windows)
                with open(tmp, "w", newline="", encoding="latin-1") as fh:
                    fh.write(self._empty_tape_text())
            os.replace(tmp, path)
        except BaseException:
            # a failed or interrupted write must not leave the temporary
            # file behind (os.replace has consumed it on success); a
            # cleanup failure must not mask the original error
            try:
                os.remove(tmp)
            except OSError:
                pass
            raise
        if onto_source:
            # the file the index describes has just been rewritten; the
            # offsets of untouched sections no longer match -- this object
            # can no longer read from disk safely (see _ensure_valid)
            self._invalidated = True

    # -- memory management ---------------------------------------------

    def unload(self, position=None):
        """Drop cached raw text and parsed sections.

        Edits held in the material overlays are not affected. With no
        argument the whole cache is cleared; given a material position,
        only that material's cached data is dropped.
        """
        if position is None:
            self._raw_cache.clear()
            self._section_cache.clear()
            return
        original = self._materials[position].original_position
        if original is not None:
            self._raw_cache.drop_material(original)
            self._section_cache.drop_material(original)

    @property
    def cache_nbytes(self):
        """The current ``(raw, parsed)`` cache sizes in bytes."""
        return self._raw_cache.nbytes, self._section_cache.nbytes

    @property
    def index(self):
        """The underlying :class:`TapeIndex` (describes the file on disk)."""
        return self._index

    @property
    def parser(self):
        """The parser engine used for sections."""
        return self._parser

    # -- context manager -----------------------------------------------

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.unload()
        return False

    def __repr__(self):
        state = " (invalidated)" if self._invalidated else ""
        return f"<EndfFile {self._path!r}: {len(self._materials)} " f"materials{state}>"

    # -- pickling ------------------------------------------------------
    #
    # The index, the material slots (which carry any edits) and the
    # parser are pickled; the caches and named secondary indexes are
    # not. The parser pickles by recipe (see EndfParserBase), so its
    # construction options are preserved across pickling. Any secondary
    # indexes must be rebuilt with build_index() afterwards.

    def __getstate__(self):
        return {
            "path": self._path,
            "parser": self._parser,
            "on_error": self._on_error,
            "check_edits": self._check_edits,
            "invalidated": self._invalidated,
            "verify_source": self._verify_source,
            "raw_cache_bytes": self._raw_cache.max_bytes,
            "parsed_cache_bytes": self._section_cache.max_bytes,
            "index": self._index,
            "materials": self._materials,
        }

    def __setstate__(self, state):
        self._path = state["path"]
        self._parser = state["parser"]
        self._on_error = state["on_error"]
        self._check_edits = state.get("check_edits", "eager")
        self._invalidated = state.get("invalidated", False)
        self._verify_source = state["verify_source"]
        self._index = state["index"]
        self._materials = state["materials"]
        self._raw_cache = _RawCache(state["raw_cache_bytes"])
        self._section_cache = _SectionCache(state["parsed_cache_bytes"])
        self._material_views = {}
        self._secondary_indexes = {}
        self._read_fh = None
