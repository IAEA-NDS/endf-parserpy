############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/05/15
# Last modified:   2026/10/25
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Per-material state and views for :class:`EndfFile`."""


def _as_mfmt(key):
    """Validate and normalise an ``(MF, MT)`` section key."""
    if not (isinstance(key, tuple) and len(key) == 2):
        raise KeyError(
            "a section is addressed by an (MF, MT) pair, e.g. material[3, 2]"
        )
    mf, mt = key
    return int(mf), int(mt)


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
        return self._file._assemble(self._slot, detach=True)

    def __getitem__(self, key):
        self._check_live()
        mf, mt = _as_mfmt(key)
        section = self._file._get_slot_section(self._slot, mf, mt)
        return self._file._view(self._slot, mf, mt, section)

    def __setitem__(self, key, value):
        self._check_live()
        self._file._set_slot_section(self._slot, *_as_mfmt(key), value)

    def __delitem__(self, key):
        self._check_live()
        self._file._delete_slot_section(self._slot, *_as_mfmt(key))

    def __contains__(self, key):
        self._check_live()
        try:
            mfmt = _as_mfmt(key)
        except KeyError:
            return False
        return mfmt in self._file._slot_section_keys(self._slot)

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
