############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/11/17
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Per-material state and views for :class:`EndfFile`."""

from ..utils.accessories import EndfPath, _Occurrence, _Position

_KEY_MESSAGE = (
    "a section is addressed by an (MF, MT) pair, e.g. material[3, 2], by "
    "(MF, MT, k) for the k-th section with this label, or by a section path "
    "such as '3/102#1' or '#0'"
)


def _as_mfmt(key):
    """Validate and normalise an ``(MF, MT)`` section key."""
    if not (isinstance(key, tuple) and len(key) == 2):
        raise KeyError(_KEY_MESSAGE)
    mf, mt = key
    return int(mf), int(mt)


def _section_key(key):
    """Split a section key of a :class:`MaterialView` into ``(mf, mt,
    occurrence, position, subpath)``.

    The key is ``(MF, MT)``, ``(MF, MT, k)`` or a section path
    (``"3/102"``, ``"3/102#1"``, ``"#0"``, also followed by a field path).
    """
    if isinstance(key, tuple):
        if len(key) == 3:
            mf, mt = _as_mfmt(key[:2])
            k = key[2]
            if not isinstance(k, int) or isinstance(k, bool) or k < 0:
                raise KeyError(f"the occurrence in {key!r} must be a non-negative int")
            return mf, mt, k, None, None
        mf, mt = _as_mfmt(key)
        return mf, mt, None, None, None
    if isinstance(key, (str, EndfPath)):
        els = EndfPath(key)._path_elements

        def rest(n):
            return EndfPath._from_elements(els[n:]) if len(els) > n else None

        if els and isinstance(els[0], _Position):
            return None, None, None, els[0].k, rest(1)
        if len(els) >= 2 and isinstance(els[0], int):
            if isinstance(els[1], _Occurrence):
                return els[0], els[1].mt, els[1].k, None, rest(2)
            if isinstance(els[1], int):
                return els[0], els[1], None, None, rest(2)
        raise KeyError(
            f"the path {str(key)!r} does not address a section; a section of a "
            "material is addressed by MF/MT, MF/MT#k or #k"
        )
    raise KeyError(_KEY_MESSAGE)


class _MaterialSlot:
    """Mutable per-material state in an :class:`EndfFile`.

    A slot represents one material in the (possibly edited) tape. For a
    material that came from the file ``original_position`` indexes the
    backing :class:`TapeIndex`; for a material added in memory it is
    ``None``. ``overlay`` holds sections that were set or added (keyed
    by ``(MF, MT)``), and ``deleted`` the ``(MF, MT)`` keys removed from
    the original material. ``removed`` is set when the material itself
    is deleted from the tape, which invalidates any :class:`MaterialView`
    bound to the slot.
    """

    # a class attribute, so it defaults to False without per-instance
    # storage and survives unpickling of slots written before it existed
    removed = False

    def __init__(self, original_position=None, mat=None, za=None, awr=None):
        self.original_position = original_position
        self.mat = mat
        self.za = za
        self.awr = awr
        self.overlay = {}
        self.deleted = set()

    @property
    def is_modified(self):
        """Whether the slot differs from its original on-disk material."""
        return bool(self.overlay or self.deleted or self.original_position is None)


class MaterialView:
    """A handle to one material of an :class:`EndfFile`.

    Sections are addressed by an ``(MF, MT)`` pair and parsed lazily on
    access. A section can be read, replaced, added or deleted::

        section = material[3, 2]
        material[3, 2] = edited_section
        del material[3, 2]

    If the tape structure lets a label occur several times in a material
    (e.g. ``gendf``), ``material[3, 102]`` raises an
    :class:`~endf_parserpy.tape.AmbiguousSectionError`; ``material[3, 102, k]``
    selects the ``k``-th section with this label (counting from 0). A key
    can also be a section path, as for an :class:`~endf_parserpy.EndfPath`
    applied to a material: ``material["3/102#1"]``, ``material["#0"]`` (the
    first section; the tape head is not counted) or, reaching into the
    section, ``material["3/102#1/IZAM"]``. Such a section is read-only for
    now: one of several sections with the same label cannot be edited or
    deleted yet.

    Reading a section returns a *view* over the parsed section whose
    mutability follows the file's ``check_edits`` mode -- read-only under
    ``"eager"`` and a live write-through view under ``"deferred"`` (see
    :mod:`endf_parserpy.tape.views`). A section that failed to parse
    raises :class:`~endf_parserpy.tape.SectionParseError` on access.

    The view is bound to the underlying material, so it stays valid if
    the tape is reordered; it becomes invalid only if that material is
    deleted, after which every operation on it raises
    :class:`RuntimeError`.
    """

    def __init__(self, endf_file, slot):
        self._file = endf_file
        self._slot = slot

    def _check_live(self):
        """Raise if the material this view is bound to has been deleted."""
        if self._slot.removed:
            raise RuntimeError("this material has been deleted from the tape")

    @property
    def position(self):
        """The material's current zero-based position on the tape."""
        self._check_live()
        return self._file._position_of(self._slot)

    @property
    def mat(self):
        """ENDF MAT number of the material."""
        self._check_live()
        return self._slot.mat

    @property
    def za(self):
        """ZA identifier of the material, or ``None`` if unknown."""
        self._check_live()
        return self._slot.za

    @property
    def awr(self):
        """Atomic weight ratio of the material, or ``None`` if unknown."""
        self._check_live()
        return self._slot.awr

    @property
    def is_modified(self):
        """Whether this material has been edited."""
        self._check_live()
        return self._slot.is_modified

    def sections(self):
        """Return the list of ``(MF, MT)`` section keys of this material."""
        self._check_live()
        return self._file._slot_section_keys(self._slot)

    def to_tape_dict(self):
        """Return this material as a complete single-material tape dict.

        The result is a ``{MF: {MT: section}}`` mapping that, unlike the
        per-section access of this view, also carries an ``MF=0``/
        ``MT=0`` tape-head (TPID) entry. It therefore forms a complete
        single-material tape and can be handed directly to the ordinary
        parser's ``write`` -- ``parser.write(view.to_tape_dict())``
        yields a tape the ordinary ``parser.parse`` round-trips.

        Untouched sections appear as their raw ENDF-6 lines and edited
        or added ones as parsed mappings; the writer accepts both.

        The result is a standalone copy, like the result of
        ``detach()`` of a section view: it consists of ordinary
        ``dict`` and ``list`` objects (numpy arrays are copied), and
        changing it does not change the tape. To apply a change, assign
        the changed section back, e.g. ``view[mf, mt] = tape_dict[mf][mt]``.
        """
        self._check_live()
        return self._file._assemble(self._slot, detach=True, as_dict=True)

    def _locate(self, key):
        mf, mt, occurrence, position, subpath = _section_key(key)
        mf, mt, k = self._file._locate_slot_section(
            self._slot, mf, mt, occurrence, position
        )
        return mf, mt, k, subpath

    def __getitem__(self, key):
        self._check_live()
        mf, mt, k, subpath = self._locate(key)
        return self._file._located_view(self._slot, mf, mt, k, subpath)

    def __setitem__(self, key, value):
        self._check_live()
        mf, mt, occurrence, position, subpath = _section_key(key)
        if occurrence is not None or position is not None:
            mf, mt, k = self._file._locate_slot_section(
                self._slot, mf, mt, occurrence, position
            )
            self._file._check_not_one_of_repeats(self._slot, mf, mt, k)
        if subpath is None:
            self._file._set_slot_section(self._slot, mf, mt, value)
        else:
            self._file._set_slot_field(self._slot, mf, mt, subpath, value)

    def __delitem__(self, key):
        self._check_live()
        mf, mt, k, subpath = self._locate(key)
        self._file._check_not_one_of_repeats(self._slot, mf, mt, k)
        if subpath is None:
            self._file._delete_slot_section(self._slot, mf, mt)
        else:
            self._file._delete_slot_field(self._slot, mf, mt, subpath)

    def __contains__(self, key):
        """Whether the material has the section, or the field, of ``key``.

        An ``(MF, MT)`` pair tests whether the label occurs in the
        material (as in :meth:`sections`). A selection that is out of range
        answers ``False``; an ambiguous section path (``"3/102"`` for a
        repeated label) raises
        :class:`~endf_parserpy.tape.AmbiguousSectionError`.
        """
        self._check_live()
        if isinstance(key, tuple) and len(key) == 2:
            try:
                mfmt = _as_mfmt(key)
            except (KeyError, TypeError, ValueError):
                return False
            return mfmt in self._file._slot_section_keys(self._slot)
        try:
            mf, mt, k, subpath = self._locate(key)
        except (KeyError, IndexError):
            return False
        return self._file._slot_has(self._slot, mf, mt, k, subpath)

    def __iter__(self):
        self._check_live()
        return iter(self._file._slot_section_keys(self._slot))

    def __len__(self):
        self._check_live()
        return len(self._file._slot_section_keys(self._slot))

    def __repr__(self):
        if self._slot.removed:
            return f"<MaterialView (deleted) MAT={self._slot.mat}>"
        return (
            f"<MaterialView position={self.position} "
            f"MAT={self._slot.mat} ZA={self._slot.za}>"
        )
