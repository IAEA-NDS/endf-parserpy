# Design Note — Path-Addressed Access on `EndfFile`

Status: **implemented**
Branch: `feature/multi-material-lazy-tape`
Builds on: `multi_material_lazy_tape.md` (Phases 1–5, implemented)
Target version: additive feature on the still-unreleased tape API.

> **Note (post-implementation):** the tape API was subsequently
> renamed. `EndfFile.save()` was split into `EndfFile.export(path)`
> (write a file) and `EndfFile.to_string()` (return an ENDF-6 string);
> the module functions gained `_file` variants; and `EndfFile.verify()`
> became `EndfFile.invalid_edits()` (it returns the list of
> non-conformant edited sections). Mentions of `save()` and `verify()`
> below predate those renames.

---

## 1. Motivation

`EndfFile` already *reads* by path — `get(path)` resolves an `EndfMaterialPath`
against the tape — but has no path-based *write*: there is no `set`/`remove`/
`exists`, and editing goes through the `MaterialView` mapping protocol.

Two things are unsatisfactory:

* the read/write API is asymmetric — `get` with no `set`;
* the retrieval contract is incoherent. `endf_file[i][mf, mt]` hands back the
  cached parsed section object; mutating it in place is neither persisted
  (`save()` emits the section verbatim from disk, ignoring the change) nor
  inert (the mutation leaks into the cache and is seen by later reads, until
  byte-budget eviction silently drops it). The effect of an in-place edit is
  therefore non-deterministic.

This note adds path-based write / delete / membership (decision **P1**) and
settles two further questions: *when* an edit's recipe-conformity is checked
(**P2**), and *what a retrieved section is* (**P3**).

---

## 2. Settled decisions

| # | Decision |
|---|----------|
| P1 | **`__getitem__`, `__setitem__`, `__delitem__` and `__contains__` are polymorphic.** They accept an integer material position *or* an `EndfMaterialPath` (string or object). No separate `set`/`exists`/`remove` method trio is introduced; `[]`, `[]=`, `del` and `in` carry those roles. The integer form is sugar for the `#k` material selector. |
| P2 | **The recipe-conformity of an edited section is checked by rendering it through the parser's writer** — the engine's only validation mechanism. A `check_edits` constructor argument selects *when* the check runs: `"eager"` (the default) renders on every write and raises at the offending statement; `"deferred"` defers the check to `save()` or `verify()`. |
| P3 | **A retrieved section is a recursive *view* over the canonical cached section, never a defensive copy.** Its mutability follows `check_edits`: `"eager"` yields a recursively read-only (frozen) view; `"deferred"` yields a live write-through view that edits the material's overlay directly. `.detach()` produces a standalone plain mutable copy on demand. numpy arrays are handed out by either view as read-only views of the canonical array (§5.5). |
| P4 | **A section or field view accepts an `EndfPath` string as a key**, not only a plain leaf key. `view["xstable/E"]` reads, and on a live view `view["xstable/E"] = [...]` writes, the same as the chained-`[]` spelling. This mirrors `EndfDict`, so a retrieved view is path-addressable all the way down. Resolution and write-through follow the view's mode (P3); the `EndfPath` reach is *within* a section, the leading material/MF/MT selector stays the job of `EndfMaterialPath`. |

P1 mirrors `EndfDict`, where `d[path]` yields a sub-view or a leaf depending on
the depth the `EndfPath` reaches. `EndfFile` is **not** made a subclass of
`EndfDict` or `MutableMapping`: the two differ structurally (lazy, file-backed,
edit-overlay, material-indexed). `EndfFile` adopts only the *idioms*,
duck-typed — no `isinstance` relationship is claimed.

---

## 3. Addressing — the three path depths

An `EndfMaterialPath` resolves to one of three depths; the depth governs the
behaviour of every `[]` operation.

| depth    | path example            | addresses                       |
|----------|-------------------------|---------------------------------|
| material | `#0`, `2925`, `9237#1`  | a whole material                |
| section  | `#0/3/2`                | an `(MF, MT)` section           |
| field    | `#0/3/2/AWR`            | a field inside a parsed section |

The integer key `endf_file[i]` is exactly `endf_file['#i']` — material depth.
(Integer keys keep Python list semantics, so negative indices are accepted; a
`#k` selector remains non-negative only, as today.)

---

## 4. Edit-checking modes

A write can produce a recipe-non-conformant section. This is obvious for a
section-depth assignment of a malformed section, but it is equally true of a
field-depth write: the assigned value may be a wrongly-shaped nested
structure, or even a correctly-typed scalar that breaks a *consistency*
constraint — a count field (`NW`, `NP`, …) that no longer matches the array it
counts. endf-parserpy has no standalone section validator; the only check for
"is this section well-formed" is whether the parser's writer can render it.

The `check_edits` constructor argument selects *when* that render-check runs
and, as a coupled consequence, *what kind of view* retrieval returns (§5). It
governs **every** edit spelling — `endf_file[path] =`, `material[mf, mt] =`,
in-place mutation of a retrieved view and every `del` — and is orthogonal to
`on_error`, which concerns read/parse failures, not edits.

**`check_edits="eager"` (default).** Every write renders the affected section
immediately (by handing `{MF: {MT: section}}` to the parser's `write`); a
render failure raises at the offending assignment. A field-depth `del` raises
outright. The benefit is *error locality* — the failure names the exact
statement rather than surfacing at a distant `save()`. Retrieval returns a
frozen view (§5.1).

A consequence worth documenting: eager mode requires *every intermediate
state* to be valid. A change that legitimately needs two coordinated field
edits (resize an array *and* its count) fails on the first edit. The remedy is
to assign the whole section in one go (`endf_file['#0/3/2'] = edited_section`),
or to use deferred mode. Eager mode therefore means "each edit must
independently be valid". This is also why eager mode cannot offer a live
write-through view — it would render on every keystroke and fire on every
transient inconsistency.

**`check_edits="deferred"`.** Any write and any delete — including a
field-depth `del` — is accepted; the section is merely marked dirty.
Recipe-conformity is checked only at `save()` or via an explicit `verify()`.
This supports transactional editing: intermediate states may violate
constraints as long as the section is consistent before it is saved.
Retrieval returns a live write-through view (§5.2).

**`verify()`** renders every *dirty* section (untouched sections are written
verbatim and need no check) and returns a report — a list of
`(position, MF, MT, exception)` tuples, empty when all dirty sections are
conformant. In deferred mode `save()` renders the dirty sections anyway, so it
*is* the implicit verify; `verify()` is "`save()` without writing". In eager
mode `verify()` is a near-no-op, since every dirty section was checked at
write time, but it remains harmless to call.

The render-check applies only to sections that are mappings. A recipe-less
section held as a `list[str]` is written verbatim and has no recipe to
violate, so it is never render-checked.

`check_edits` is fixed at construction for v1 (see §14).

---

## 5. Retrieved sections — frozen and write-through views

Retrieval never takes a defensive copy. `endf_file[i][mf, mt]`,
`endf_file[section_path]` and `get` return a lazy **view** over the canonical
cached section: a `Mapping` / `Sequence` wrapper that, on `__getitem__`,
returns a wrapper of the same kind for a nested `dict` / `list` and the bare
value for a scalar. The cost is one small wrapper allocation per *container*
crossed during navigation — never an upfront copy, and scalars (including
`EndfFloat`) are never wrapped. Parsed sections contain nested `dict`s,
`list`s and scalars, so these two wrapper kinds suffice, plus, with
`array_type="numpy"`, numpy arrays, which follow the rule of §5.5.

The kind of view follows `check_edits`.

### 5.1 `check_edits="eager"` — frozen view

The view is recursively **read-only**. A `__setitem__` / `__delitem__` at any
depth raises `TypeError` (the `Mapping` / `Sequence` ABCs define no mutators;
the wrappers override them only to raise a message naming the remedy). The
canonical cached section cannot be corrupted by a caller.

To edit, obtain a detached copy with `.detach()` (§5.3), change it and assign
it back, or use the path-based write of §7.

### 5.2 `check_edits="deferred"` — live write-through view

The view is recursively **mutable**, and `EndfFile` behaves, in this mode,
like a storage-backed `EndfDict`:

    endf_file[0][3, 2]['AWR'] = 99.0       # writes through to the tape

A write at any depth follows the **no-copy-on-write** model:

* the write mutates the canonical cached section *in place*;
* the *first* write to a section also installs that very object into the
  material's edit overlay — `slot.overlay[(mf, mt)] = section` — marking it
  dirty.

Four consequences make this correct, not merely convenient:

* no second copy and no copy-on-write, hence no stale-nested-handle identity
  bug;
* the canonical object and the overlay entry are the *same* object, so the
  parsed-section cache and the overlay can never disagree;
* **a read never installs anything into the overlay** — an un-written section
  stays "untouched" and is emitted verbatim from disk by `save()`, so the
  byte-exact round-trip contract (`multi_material_lazy_tape.md` §6) is
  preserved;
* two live views of one section share the one canonical object, so aliasing
  is consistent.

The nested wrappers of a live view share a `_touch()` callback — idempotent,
"ensure this section is in the overlay" — invoked on any mutation. Conformity
is *not* checked at write time in this mode; it is checked at `save()` /
`verify()` (§4).

### 5.3 `detach()`

`.detach()`, available on either view, returns a standalone, plain, mutable
deep copy of the section as ordinary `dict`s and `list`s, disconnected from
the `EndfFile`. It is the *only* place a deep copy is taken — on explicit
caller intent.

* On a frozen view it is *the* way to obtain an editable section: detach,
  edit, assign back.
* On a live view it yields a detached snapshot whose edits do **not** write
  through — useful to experiment without touching the tape.

numpy arrays are deep-copied as well (`a.copy()`, same dtype and shape), so a
detached section shares no data with the cache.

`MaterialView.to_tape_dict()` returns a whole material in the same detached
form: an ordinary `{MF: {MT: section}}` dict for the parser's writer, whose
edited sections are copies of the overlay (untouched sections are the raw
lines read from disk, new lists in any case). A view would not do here, as
the writer takes `dict`s and `list`s; and since a change to the result would
not reach the tape, the result must not share containers with it ("nothing
looks writable whose write would be lost").

### 5.4 Type

A view is a `Mapping` / `Sequence`, not a `dict` / `list`, so
`isinstance(section, dict)` is no longer true for a retrieved section. The
tape API is unreleased, so this breaks nothing; internal code and the
parser's writer only ever see the canonical section or a caller-supplied
mapping, never a view.

### 5.5 numpy arrays

A section parsed with `array_type="numpy"` holds numpy arrays, which are
mutable in place without going through any wrapper. A bare array handed out
by a view would break both modes: in a frozen view an in-place edit would
corrupt the cached section, and in a live view it would change the cache
without `_touch()`, so `save()` would emit the untouched disk text and the
edit would be lost silently. Wrapping arrays in a third view kind would hide
the numpy API, and copying them would contradict "never a defensive copy".

* **Read.** Both view kinds return a numpy array as a *read-only view of the
  canonical array*: `a.view()` with `flags.writeable = False`. No data is
  copied, and the result is a real `ndarray` (slicing, arithmetic, ufuncs all
  work). An in-place change (`arr[0] = x`, `arr *= 2`) raises numpy's own
  `ValueError: assignment destination is read-only`; its message cannot be
  customised, which is accepted. Nothing therefore looks writable whose write
  would be lost, and a read still never touches the overlay.
* **Write, live view.** A write goes through the view, so `_touch()` fires:
  either a path ending at an element (`view['xstable/xs/0'] = 1.5`, or
  `view['b/2/1/1'] = 0.5` for an element of a 2-D block, resolved to the
  canonical array by `_navigate`) or the assignment of a whole array
  (`view['xstable/xs'] = new_array`). An assigned read-only array — as handed
  out by a view — is copied, like an assigned view is detached, so a section
  never holds read-only data shared with another section.
* **Write, frozen view.** As for any field: `endf_file[path] = value` with a
  path to an element or to the whole array, rendered and checked (§7).
* **Detach** copies the arrays (§5.3).
* **Equality.** `==` / `!=` on views use the numpy-aware
  `recursive_equality_check` of `utils.accessories` (the comparison of
  `EndfDict`), so views of numpy sections compare element by element with
  dicts, views and list-mode data.

numpy stays optional: the views detect arrays through `sys.modules` and never
import numpy.

---

## 6. Read — `endf_file[key]`

The resolution of `key` is independent of `check_edits`; only the *kind* of
section view returned depends on it (§5). Return value by path depth — the
same as `get` (§10):

* **material** → a `MaterialView`.
* **section** → a section view (frozen or live per mode) — a `Mapping` view of
  a parsed section, or a `Sequence` view of the raw lines of a recipe-less
  section.
* **field** → the value at the sub-path: a scalar, or, if the sub-path stops
  at a nested container, a view of that container.

A section or field view is itself path-addressable (decision **P4**): a string
key is interpreted as an `EndfPath` *relative to the view*, so
`endf_file["#0/3/2"]["xstable/E"]` and `endf_file["#0/3/2/xstable/E"]` reach the
same leaf. A plain (single-component) key still works unchanged — a one-element
`EndfPath` is just that key — so the addition is transparent to callers that
index a view with a bare field name or list position.

---

## 7. Write

A section can be written in two ways.

**Assignment** — `endf_file[key] = value`, in either mode:

* **material depth** → rejected with `ValueError`. A material's identity
  (MAT, ZA) cannot be inferred from the value; adding a material stays the job
  of `append_material`.
* **section depth** → set, replace or add the section. `value` is any mapping
  (a parsed section, an `EndfDict`, a detached view, …) or a `list[str]` (a
  raw section). The target material must already exist — there is **no
  autovivification** of materials.
* **field depth** → read-modify-write: the canonical section is copied, the
  field at the sub-path is set on the copy, and the copy is stored in the
  material's edit overlay. The section must already exist.

Under `check_edits="eager"` the resulting section is render-checked
immediately and a malformed result raises at the assignment; under
`"deferred"` it is stored dirty and checked at `save()` / `verify()`.

**In-place mutation of a retrieved view** — meaningful only under
`check_edits="deferred"`, where the live view writes through (§5.2). The
target may be a plain key or an `EndfPath` string (decision **P4**):

    endf_file[0][3, 2]['AWR'] = 99.0
    endf_file['#0/3/2']['xstable/E'] = [1, 2, 3, 4]   # path-addressed write

Under `check_edits="eager"` the retrieved view is frozen, so in-place mutation
raises `TypeError` whatever the key spelling; assignment or `detach()` is the
route, and a deep eager edit goes through the top-level path write
`endf_file['#0/3/2/xstable/E'] = ...`.

---

## 8. Delete — `del endf_file[key]`

* **material depth** → delete the material, in either mode.
* **section depth** → delete the section, in either mode.
* **field depth** — `del endf_file['#0/3/2/AWR']`, or `del view['AWR']` on a
  deferred-mode live view:
  * under `"eager"` → **rejected** with `ValueError`: a section's fields are
    mandated by its ENDF recipe, so removing one yields a section the writer
    cannot render;
  * under `"deferred"` → **accepted**: the section is marked dirty and will
    fail at `save()` / `verify()` unless the field is restored beforehand.
    This permits the transient inconsistency of a multi-step edit.

---

## 9. Membership — `key in endf_file`

`path in endf_file` is the `exists` check: it reports whether the path
resolves to a present material, section or field. A cleanly-absent target
yields `False`. A malformed path or an ambiguous bare-`MAT` selector
propagates `ValueError` / `AmbiguousMaterialError` respectively — the
membership question is genuinely ill-posed there, so it is not silently
answered `False`.

---

## 10. Relationship to the existing API

* **`get`** is kept as the explicit-method synonym of `[]` for reads, and is
  *relaxed*: `get(material_path)` returns a `MaterialView` instead of raising
  `ValueError`. After this change `get(path)` and `endf_file[path]` are exact
  synonyms at every depth, and `get` returns the mode-dependent view.
* **`MaterialView`** keeps its `material[mf, mt]` mapping protocol; it now
  returns the mode-dependent section view, and its writes follow the
  `check_edits` mode. `endf_file[0][3, 2]` and `endf_file['#0/3/2']` remain
  equivalent.
* The integer material API (`endf_file[i]`, `del endf_file[i]`, `len`,
  iteration) is unchanged.
* `check_edits` is orthogonal to `on_error`: the former concerns the validity
  of edits, the latter the handling of read/parse failures.

---

## 11. Error surface

| condition                                            | result                   |
|-------------------------------------------------------|--------------------------|
| key is not `int` / `str` / `EndfMaterialPath`         | `TypeError`              |
| malformed path string                                 | `ValueError`             |
| bare `MAT` selector, not unique                        | `AmbiguousMaterialError` |
| `MAT` not present on the tape                           | `KeyError`               |
| material position out of range                          | `IndexError`             |
| read of an absent section                              | `KeyError`               |
| read of a section that failed to parse                  | `SectionParseError`      |
| read of an absent field within a section                | `KeyError`               |
| assignment at material depth                             | `ValueError`             |
| field assignment into a recipe-less (raw) section        | `TypeError`              |
| field assignment into an absent section                  | `KeyError`               |
| write yields a non-conformant section (eager mode)       | `SectionRenderError`     |
| `del` at field depth (eager mode)                        | `ValueError`             |
| mutating a frozen (eager-mode) view, at any depth        | `TypeError`              |

`__contains__` swallows `KeyError` / `IndexError` (→ `False`) but lets
`ValueError` / `AmbiguousMaterialError` propagate (§9).

---

## 12. Implementation sketch

All the addressing machinery exists; the work is dispatch, the section views
and the render-check.

* A private `_resolve_key(key)` returning `(position, mf, mt, subpath)`:
  * `int` → `(key, None, None, None)` with Python list indexing;
  * `str` / `EndfMaterialPath` → build an `EndfMaterialPath`, call
    `resolve_material(_CurrentMaterials(self._materials))` for the position,
    take `mf` / `mt` / `subpath` from it.
* **Section views** — a small `_SectionView` base implementing the recursive
  `__getitem__` wrapping, with two pairs of leaves:
  * `_FrozenMapping` / `_FrozenSequence` — read-only; mutators raise
    `TypeError` with a remedy message;
  * `_LiveMapping` / `_LiveSequence` — mutable; `__setitem__` / `__delitem__`
    call a shared `_touch()` then mutate the underlying object. `_touch()`
    does `slot.overlay[(mf, mt)] = section` under the `EndfFile` lock.
  Both expose `detach()`, returning a recursively unwrapped plain
  `dict` / `list` deep copy.
  * **`EndfPath` keys (P4)** — `_SectionView.__getitem__`/`__setitem__`/
    `__delitem__`/`__contains__` first normalise the key: a `str` is turned
    into an `EndfPath`. A single-component path resolves to the plain key and
    takes the fast leaf path; a multi-component path is walked with
    `EndfPath.get` / `.set` / `.exists` on the wrapped target and the result
    re-wrapped. On a frozen view a multi-component `__setitem__` raises
    `TypeError` like any other mutation; on a live view it walks to the parent
    container, mutates it and calls `_touch()`.
* A `_view(slot, mf, mt, section)` helper wraps a canonical section in the
  mode's view type. It is applied by the public accessors
  (`EndfFile.__getitem__`, `MaterialView.__getitem__`, `get`) and **skipped**
  by the internal read-and-discard paths (`query`, `build_index`), which
  operate on the canonical section directly and pay no wrapping cost; only a
  field handed to a user `predicate` of `query` is wrapped as a frozen view
  hands it out (a `dict` / `list` as a frozen view, a numpy array read-only,
  §5.5), and `query(..., value)` compares numpy fields element by element.
* `__getitem__` — dispatch on depth: material → `MaterialView`; section →
  `_view(...)`; field → `_view(...)` of, or the bare value at,
  `walk_section`. A `FailedSection` raises `SectionParseError`.
* `__setitem__` — material → `ValueError`; section → `_set_slot_section`;
  field → fetch + copy the canonical section, `subpath.set(copy, value)`,
  `_set_slot_section`. In eager mode `_set_slot_section` calls the
  render-check.
* `__delitem__` — material → drop the slot; section → `_delete_slot_section`;
  field → `ValueError` in eager mode, a dirty field-delete in deferred mode.
* `__contains__` — resolve and probe, per §9.
* `get` — relax the current `mf is None` guard to return `self[position]`.
* **Render-check** — `_check_section(mf, mt, section)` renders a mapping
  section through `self._parser.write(...)`; any writer failure (a section
  that does not conform to its ENDF recipe makes the writer raise — often a
  bare `KeyError` for a missing field) is wrapped in a `SectionRenderError`
  (a `TapeError`) with the writer's exception kept as its cause, so the eager
  failure surface is a single typed, catchable error. Eager `_set_slot_section`
  calls it; `verify()` calls it for every dirty section and collects the
  `SectionRenderError`s into the report; deferred `save()` runs `verify()`
  first and raises before writing anything if the report is non-empty.
* The mode is stored as `self._check_edits` (validated against
  `("eager", "deferred")`, default `"eager"`).

The reusable pieces (`EndfMaterialPath.resolve_material`, `_CurrentMaterials`,
`walk_section`, `section_has`, `_get/_set/_delete_slot_section`,
`EndfPath.set`) are already in place from Phases 4–5.

---

## 13. Testing

Add to `tests/test_tape_query.py` (reads) and `tests/test_tape_editing.py`
(writes/deletes):

* read at each depth via `[]`, equivalence with `get` and with the
  `MaterialView` spelling; `get` relaxed to material depth;
* `__setitem__` at section depth (replace and add) and field depth
  (read-modify-write), then a `save` round-trip;
* `__delitem__` at section and material depth;
* `in` for present / absent / ambiguous paths;
* every row of the §11 error table;
* **eager mode** (default): a frozen view rejects mutation at top *and*
  nested depth; a write that breaks a section raises at the assignment; a
  field-depth `del` raises; `detach()` yields an independent mutable copy;
* **deferred mode**: a live view writes through at top and nested depth and
  marks the section dirty; a *pure read* through a live view leaves the
  section untouched, so an unedited tape still saves byte-exact; field-depth
  `del` is accepted; `verify()` reports a malformed dirty section and `save()`
  fails on it; two live views of one section observe each other's writes;
* `detach()` on a live view yields a snapshot whose edits do not write
  through;
* **`EndfPath` keys on a view** (P4): a multi-component string key reads the
  same leaf as the chained-`[]` and the top-level path spellings; a bare key
  still resolves unchanged; a path write through a live view writes through and
  is rejected (`TypeError`) on a frozen view; a path read of an absent leaf
  raises `KeyError`.

---

## 14. Open questions (not blocking)

* Should `check_edits` be switchable at runtime? Deferred for v1: switching
  `"deferred"` → `"eager"` would beg the question of re-validating sections
  already made dirty. A `verify()` call covers that need explicitly.
* Should `get` gain a `default=` parameter for true `dict.get` semantics
  (return a default instead of raising)? Out of scope here; the `[]` form
  always raises, like `dict.__getitem__`.
* Slicing (`endf_file[1:3]`) is intentionally **not** added; `[]` accepts an
  `int` or a path only.
* MF-level access (`endf_file["9237/3"]` yielding a `{MT: section}` handle) is
  **not** added in v1. Unlike a section view, which wraps an already-parsed
  in-memory object, an MF-level handle would have to lazily parse each MT from
  disk — it is a slot-backed lazy view, closer to a `MaterialView` narrowed to
  one MF than to the `_SectionView` wrappers. Deferred as a separate follow-up;
  the depth table of §3 stays material / section / field.

---

## 15. CHANGELOG

Under `[Unreleased] / Added`: notes that `EndfFile` supports
`EndfMaterialPath`-based item access — `endf_file[path]`, `endf_file[path] =
value`, `del endf_file[path]` and `path in endf_file` — so a tape can be
navigated and edited like a path-addressable mapping; and that the
`check_edits` argument (`"eager"` by default, or `"deferred"`) selects both
whether an edit's recipe-conformity is verified immediately or only at
`save()` / `verify()`, and whether a retrieved section is a read-only view or
a live write-through view. A retrieved section is a recursive view over the
tape and is itself path-addressable — a string key is read as an `EndfPath`
relative to the view — so a tape is navigable and editable as a path-addressed
mapping all the way down; `.detach()` returns a standalone editable copy. A new
`SectionRenderError` (a `TapeError`) reports an edit that does not render to
valid ENDF-6 text, and `EndfFile.verify()` renders every edited section and
returns the non-conformant ones.
