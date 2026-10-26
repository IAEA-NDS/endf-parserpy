############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2026/10/26
# Last modified:   2026/10/26
# License:         MIT
# Copyright (c) 2026 International Atomic Energy Agency (IAEA)
#
############################################################

"""Recursive-descent parser for the ENDF recipe language.

The language is specified by the EBNF grammar in
:mod:`endf_parserpy.endf_recipes.endf_lark_ebnf`. This module parses
recipes without any third-party dependency and produces parse trees
identical to those obtained with Lark from that grammar, using the
options ``start="endf_recipe"`` and ``keep_all_tokens=True`` and the
default Earley parser with the dynamic lexer:

- every rule of the grammar yields a :class:`Tree` node whose ``data``
  is a ``Token("RULE", <rule name>)``; the helper rules generated for
  ``*``, ``+`` and ``?`` are inlined, so their elements appear directly
  among the children of the enclosing rule;
- all tokens are kept, including punctuation and keywords, with the
  terminal names chosen by Lark (e.g. ``LSQB`` for ``[``, ``FOR`` for
  ``for``, ``__ANON_0`` for ``(/``);
- the left-recursive rules (``expr``, ``addpart``, ``disjunction``,
  ``conjunction``) produce left-nested trees.

Terminals are matched in the context in which the grammar expects them
(as Lark's dynamic lexer does), with the same regular expressions, and
single spaces are ignored between tokens. Keywords are therefore not
required to be separated from adjacent names, e.g. ``fori=1toN:`` is
the head of a for loop.

Where the grammar is ambiguous, the choice Lark's Earley parser makes is
an artifact of its implementation. The cases that follow a regular
pattern have been determined empirically with Lark (1.2) as an oracle
and are reproduced here; they are marked by comments starting with
``Lark:``. In the remaining cases, Lark's choice follows no simple rule
and partly differs between Lark versions; there this parser makes a
fixed choice:

- juxtaposed elements of a LIST record body (elements need not be
  separated by commas): ``x -y`` is always one element (a subtraction);
- a division in the last of the six fields of a LIST record, where the
  slash may also be read as the separator before the body: the last
  field extends as far as possible;
- a name starting with ``PADLINE`` (e.g. ``PADLINE2``) is always a
  variable name.

None of these constructs occurs in the recipes of the package. The
oracle tests in ``tests/test_recipe_parser_oracle.py`` check the
equivalence with Lark.
"""

import re
from bisect import bisect_right
from .tree import Tree, Token


# Regular expressions of the terminals, taken from the patterns Lark
# compiles from the grammar (common.NUMBER etc. expanded).
_NUMBER = (
    r"(?:(?:(?:[0-9])+(?:e|E)(?:(?:\+|\-))?(?:[0-9])+|"
    r"(?:(?:[0-9])+\.(?:(?:[0-9])+)?|\.(?:[0-9])+)"
    r"(?:(?:e|E)(?:(?:\+|\-))?(?:[0-9])+)?)|(?:[0-9])+)"
)
_NUMBER_RE = re.compile(_NUMBER)
_DESIRED_NUMBER_RE = re.compile(_NUMBER + r"\?")
_NEWLINE_RE = re.compile(r"(?:(?:\r)?\n)+")
_COMMENT_RE = re.compile(r"(?s:( *#[^\n]*\r?\n)+)")
_STOP_MESSAGE_RE = re.compile(r'[^"]+')
_TEXTLENGTH_RE = re.compile(r"(?:[0-9])+")
_CONT_SUBTYPE_RE = re.compile(r"(?:CONT|HEAD)")
_IF_RELATION_RE = re.compile(r"(?:!=|==|>=|<=|>|<)")
_VARNAME_RE = re.compile(r"(?:[A-Z]|[a-z])(?:(?:(?:[A-Z]|[a-z])|[0-9]|_))*")
_MAT_SPEC_RE = re.compile(r"(?:(?:[0-9])+|MAT)")
_MF_SPEC_RE = re.compile(r"(?:(?:[0-9])+|MF)")
_MT_SPEC_RE = re.compile(r"(?:(?:[0-9])+|MT)")
_SPACES_RE = re.compile(r" +")

_REGEX_TERMINALS = {
    "NUMBER": _NUMBER_RE,
    "DESIRED_NUMBER": _DESIRED_NUMBER_RE,
    "NEWLINE": _NEWLINE_RE,
    "COMMENT": _COMMENT_RE,
    "STOP_MESSAGE": _STOP_MESSAGE_RE,
    "TEXTLENGTH": _TEXTLENGTH_RE,
    "CONT_SUBTYPE": _CONT_SUBTYPE_RE,
    "IF_RELATION": _IF_RELATION_RE,
    "VARNAME": _VARNAME_RE,
    "MAT_SPEC": _MAT_SPEC_RE,
    "MF_SPEC": _MF_SPEC_RE,
    "MT_SPEC": _MT_SPEC_RE,
}

_NUMBER_START = frozenset(".0123456789")
# characters that can start an arithmetic expression
_EXPR_START = frozenset(
    "-(.0123456789" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "abcdefghijklmnopqrstuvwxyz"
)


class _RuleNames:
    """Rule names as ``Token("RULE", name)``, like Lark's ``Tree.data``."""

    def __getattr__(self, name):
        tok = Token("RULE", name)
        setattr(self, name, tok)
        return tok


_R = _RuleNames()


_BINOPS_ADD = {"+": (_R.addition, "PLUS"), "-": (_R.subtraction, "MINUS")}
_BINOPS_MUL = {
    "*": (_R.multiplication, "STAR"),
    "/": (_R.division, "SLASH"),
    "%": (_R.modulo, "PERCENT"),
}


class RecipeSyntaxError(ValueError):
    """Raised if an ENDF recipe does not conform to the recipe language.

    Attributes
    ----------
    line, column : int
        Position (counted from 1) where the input could not be parsed.
    pos : int
        The corresponding character offset in the recipe string.
    expected : list of str
        Descriptions of the tokens that would have been accepted there.
    """

    def __init__(self, message, line, column, pos, expected):
        super().__init__(message)
        self.line = line
        self.column = column
        self.pos = pos
        self.expected = expected


class _Backtrack(Exception):
    """Internal signal: the current alternative does not match."""


_BACKTRACK = _Backtrack()


class _Parser:

    def __init__(self, text):
        self.text = text
        self.n = len(text)
        # end position of the last consumed token
        self.pos = 0
        # furthest position at which a match failed, for error messages
        self.fail_pos = -1
        self.fail_expected = set()
        self.line_starts = None
        # memo of the last parse of record fields: (start, limit, result)
        self._fields_memo = (None, None, None)

    # ---------------------------------------------------------------
    # position information
    # ---------------------------------------------------------------

    def _line_starts(self):
        starts = [0]
        find = self.text.find
        i = find("\n")
        while i != -1:
            starts.append(i + 1)
            i = find("\n", i + 1)
        self.line_starts = starts
        return starts

    def _linecol(self, pos):
        starts = self.line_starts or self._line_starts()
        idx = bisect_right(starts, pos) - 1
        return idx + 1, pos - starts[idx] + 1

    def _tok(self, ttype, value, start, end):
        starts = self.line_starts or self._line_starts()
        idx = bisect_right(starts, start)
        col = start - starts[idx - 1] + 1
        if "\n" in value:
            end_line, end_col = self._linecol(end)
        else:
            end_line, end_col = idx, col + (end - start)
        return Token(ttype, value, start, idx, col, end_line, end_col, end)

    # ---------------------------------------------------------------
    # terminal matching
    # ---------------------------------------------------------------

    def _skip(self, pos):
        # %ignore " ": spaces are allowed between any two tokens
        if pos < self.n and self.text[pos] == " ":
            return _SPACES_RE.match(self.text, pos).end()
        return pos

    def _expect(self, pos, what):
        if pos > self.fail_pos:
            self.fail_pos = pos
            self.fail_expected = {what}
        elif pos == self.fail_pos:
            self.fail_expected.add(what)

    def _peek(self, lit):
        p = self._skip(self.pos)
        if self.text.startswith(lit, p):
            return True
        self._expect(p, repr(lit))
        return False

    def _lit(self, lit, ttype):
        p = self._skip(self.pos)
        if self.text.startswith(lit, p):
            end = p + len(lit)
            self.pos = end
            return self._tok(ttype, lit, p, end)
        self._expect(p, repr(lit))
        raise _BACKTRACK

    def _re(self, ttype, noskip=False):
        p = self.pos if noskip else self._skip(self.pos)
        m = _REGEX_TERMINALS[ttype].match(self.text, p)
        if m is None:
            self._expect(p, ttype)
            raise _BACKTRACK
        end = m.end()
        self.pos = end
        return self._tok(ttype, m.group(), p, end)

    def _opt_newline(self):
        p = self._skip(self.pos)
        m = _NEWLINE_RE.match(self.text, p)
        if m is None:
            self._expect(p, "NEWLINE")
            return None
        end = m.end()
        self.pos = end
        return self._tok("NEWLINE", m.group(), p, end)

    def _newline(self):
        tok = self._opt_newline()
        if tok is None:
            raise _BACKTRACK
        return tok

    # ---------------------------------------------------------------
    # top level and statement sequences
    # ---------------------------------------------------------------

    def parse(self):
        children = self._statements()
        p = self._skip(self.pos)
        if p != self.n:
            self._expect(p, "end of input")
            self._raise_error()
        return Tree(_R.endf_recipe, children)

    def _statements(self):
        # (code_token | NEWLINE)*  in endf_recipe, section_body,
        # for_body, repeat_body and if_body
        children = []
        append = children.append
        while True:
            nl = self._opt_newline()
            if nl is not None:
                append(nl)
                continue
            start = self.pos
            try:
                node = self._code_token()
            except _Backtrack:
                self.pos = start
                break
            append(Tree(_R.code_token, [node]))
        if not children:
            # Lark: code_token has an empty alternative; an empty sequence
            # is represented by a single empty code_token rather than by
            # the empty alternative of the enclosing rule.
            children.append(Tree(_R.code_token, []))
        return children

    def _code_token(self):
        text = self.text
        # Lark: a comment block absorbs the spaces preceding the `#`
        # (the COMMENT pattern starts with ` *`), i.e. it is matched
        # directly at the end of the previous token.
        m = _COMMENT_RE.match(text, self.pos)
        if m is not None:
            start, end = m.span()
            self.pos = end
            tok = self._tok("COMMENT", m.group(), start, end)
            return Tree(_R.comment_block, [tok])
        p = self._skip(self.pos)
        self._expect(p, "COMMENT")
        if text.startswith("[", p):
            node = self._record_line()
            return Tree(_R.endf_line, [node, self._newline()])
        # An abbreviation is recognized by the `:=` after the name, which
        # also distinguishes it from statements starting with a keyword.
        # A keyword ending a block (e.g. `endif`) immediately followed by
        # an abbreviation (`endifM := 3`) is read as one abbreviation;
        # Lark backtracks and also accepts the other reading.
        m = _VARNAME_RE.match(text, p)
        if m is not None:
            q = self._skip(m.end())
            if text.startswith(":=", q):
                return self._abbreviation()
        else:
            self._expect(p, "VARNAME")
        if text.startswith("for", p):
            return self._for_loop()
        if text.startswith("if", p):
            return self._if_clause()
        if text.startswith("repeat", p):
            return self._repeat_loop()
        if text.startswith("stop", p):
            node = self._stop_line()
            return Tree(_R.endf_line, [node, self._newline()])
        if text.startswith("SEND", p):
            node = Tree(_R.send_line, [self._lit("SEND", "SEND")])
            return Tree(_R.endf_line, [node, self._newline()])
        if text.startswith("(", p):
            return self._section()
        for what in ("'['", "'for'", "'if'", "'repeat'", "'stop'", "'SEND'", "'('"):
            self._expect(p, what)
        raise _BACKTRACK

    def _abbreviation(self):
        var = self._re("VARNAME")
        assign = self._lit(":=", "__ANON_1")
        expr = self._expr()
        return Tree(_R.abbreviation, [var, assign, expr, self._newline()])

    def _section(self):
        lpar = self._lit("(", "LPAR")
        name = self._extvarname()
        rpar = self._lit(")", "RPAR")
        head = Tree(_R.section_head, [lpar, name, rpar, self._newline()])
        body = Tree(_R.section_body, self._statements())
        tlpar = self._lit("(/", "__ANON_0")
        tname = self._extvarname()
        trpar = self._lit(")", "RPAR")
        tail = Tree(_R.section_tail, [tlpar, tname, trpar, self._newline()])
        return Tree(_R.section, [head, body, tail])

    def _for_loop(self):
        children = [
            self._lit("for", "FOR"),
            self._re("VARNAME"),
            self._lit("=", "EQUAL"),
            Tree(_R.for_start, [self._expr()]),
            self._lit("to", "TO"),
            Tree(_R.for_stop, [self._expr()]),
            self._lit(":", "COLON"),
        ]
        head = Tree(_R.for_head, children)
        body = Tree(_R.for_body, self._statements())
        endfor = self._lit("endfor", "ENDFOR")
        return Tree(_R.for_loop, [head, body, endfor, self._newline()])

    def _repeat_loop(self):
        children = [self._lit("repeat", "REPEAT")]
        if self._peek("["):
            lsqb = self._lit("[", "LSQB")
            var = self._re("VARNAME")
            eq = self._lit("=", "EQUAL")
            assign = Tree(_R.repeat_varassign, [var, eq, self._expr()])
            children.extend((lsqb, assign, self._lit("]", "RSQB")))
        children.append(self._lit(":", "COLON"))
        head = Tree(_R.repeat_head, children)
        body = Tree(_R.repeat_body, self._statements())
        until = self._lit("until", "UNTIL")
        tail = Tree(_R.repeat_tail, [until, self._if_head()])
        return Tree(_R.repeat_loop, [head, body, tail, self._newline()])

    def _if_clause(self):
        children = [self._if_statement("if", "IF", _R.if_statement)]
        while self._peek("elif"):
            children.append(self._if_statement("elif", "ELIF", _R.elif_statement))
        if self._peek("else:"):
            tok = self._lit("else:", "__ANON_2")
            body = Tree(_R.if_body, self._statements())
            children.append(Tree(_R.else_statement, [tok, body]))
        children.append(self._lit("endif", "ENDIF"))
        return Tree(_R.if_clause, children)

    def _if_statement(self, keyword, ttype, rule):
        children = [self._lit(keyword, ttype), self._if_head()]
        if self._peek("["):
            lsqb = self._lit("[", "LSQB")
            look = self._lit("lookahead", "LOOKAHEAD")
            eq = self._lit("=", "EQUAL")
            expr = self._expr()
            rsqb = self._lit("]", "RSQB")
            children.append(Tree(_R.lookahead_option, [lsqb, look, eq, expr, rsqb]))
        children.append(self._lit(":", "COLON"))
        children.append(Tree(_R.if_body, self._statements()))
        return Tree(rule, children)

    def _stop_line(self):
        children = [self._lit("stop", "STOP"), self._lit("(", "LPAR")]
        if self._peek('"'):
            q1 = self._lit('"', "DBLQUOTE")
            # Lark: like COMMENT, the message keeps its leading spaces
            msg = self._re("STOP_MESSAGE", noskip=True)
            q2 = self._lit('"', "DBLQUOTE")
            children.append(Tree(_R.escaped_stop_message, [q1, msg, q2]))
        children.append(self._lit(")", "RPAR"))
        return Tree(_R.stop_line, children)

    # ---------------------------------------------------------------
    # conditions
    # ---------------------------------------------------------------

    def _if_head(self):
        return Tree(_R.if_head, [self._disjunction()])

    def _disjunction(self):
        node = Tree(_R.disjunction, [self._conjunction()])
        while self._peek("or"):
            save = self.pos
            op = self._lit("or", "IF_OR")
            try:
                rhs = self._conjunction()
            except _Backtrack:
                self.pos = save
                break
            node = Tree(_R.disjunction, [node, op, rhs])
        return node

    def _conjunction(self):
        node = Tree(_R.conjunction, [self._comparison()])
        while self._peek("and"):
            save = self.pos
            op = self._lit("and", "IF_AND")
            try:
                rhs = self._comparison()
            except _Backtrack:
                self.pos = save
                break
            node = Tree(_R.conjunction, [node, op, rhs])
        return node

    def _comparison(self):
        start = self.pos
        try:
            lhs = self._expr()
            rel = self._re("IF_RELATION")
            rhs = self._expr()
            return Tree(_R.comparison, [Tree(_R.if_condition, [lhs, rel, rhs])])
        except _Backtrack:
            self.pos = start
        lpar = self._lit("(", "LPAR")
        disj = self._disjunction()
        rpar = self._lit(")", "RPAR")
        return Tree(_R.comparison, [lpar, disj, rpar])

    # ---------------------------------------------------------------
    # arithmetic expressions
    # ---------------------------------------------------------------

    def _expr(self, limit=None):
        """Parse the longest expression starting at the current position.

        If ``limit`` is given, at most ``limit`` binary operators outside
        of brackets are consumed. The number of such operators consumed
        is stored in ``self.expr_nops``.
        """
        count = [0, limit]
        node = Tree(_R.expr, [self._addpart(count)])
        text = self.text
        while limit is None or count[0] < limit:
            p = self._skip(self.pos)
            op = _BINOPS_ADD.get(text[p : p + 1])
            if op is None:
                self._expect(p, "operator")
                break
            save = self.pos
            self.pos = p + 1
            optok = self._tok(op[1], text[p], p, p + 1)
            count[0] += 1
            try:
                rhs = self._addpart(count)
            except _Backtrack:
                count[0] -= 1
                self.pos = save
                break
            node = Tree(_R.expr, [Tree(op[0], [node, optok, rhs])])
        self.expr_nops = count[0]
        return node

    def _addpart(self, count):
        node = Tree(_R.addpart, [self._mulpart()])
        text = self.text
        limit = count[1]
        while limit is None or count[0] < limit:
            p = self._skip(self.pos)
            op = _BINOPS_MUL.get(text[p : p + 1])
            if op is None:
                self._expect(p, "operator")
                break
            save = self.pos
            self.pos = p + 1
            optok = self._tok(op[1], text[p], p, p + 1)
            try:
                rhs = self._mulpart()
            except _Backtrack:
                self.pos = save
                break
            count[0] += 1
            node = Tree(_R.addpart, [Tree(op[0], [node, optok, rhs])])
        return node

    def _mulpart(self):
        text = self.text
        p = self._skip(self.pos)
        c = text[p : p + 1]
        if c == "-":
            minus = self._lit("-", "MINUS")
            node = Tree(_R.minusexpr, [minus, self._mulpart()])
        elif c == "(":
            lpar = self._lit("(", "LPAR")
            expr = self._expr()
            rpar = self._lit(")", "RPAR")
            node = Tree(_R.bracketexpr, [lpar, expr, rpar])
        elif c and c in _NUMBER_START:
            m = _DESIRED_NUMBER_RE.match(text, p) or _NUMBER_RE.match(text, p)
            if m is None:
                self._expect(p, "NUMBER")
                raise _BACKTRACK
            end = m.end()
            ttype = "DESIRED_NUMBER" if text[end - 1] == "?" else "NUMBER"
            self.pos = end
            node = self._tok(ttype, m.group(), p, end)
        elif c and c in _EXPR_START:
            node = self._extvarname()
            if self._peek("?"):
                qmark = self._lit("?", "QMARK")
                node = Tree(_R.inconsistent_varspec, [node, qmark])
        else:
            for what in ("NUMBER", "VARNAME", "'-'", "'('"):
                self._expect(p, what)
            raise _BACKTRACK
        return Tree(_R.mulpart, [node])

    def _extvarname(self):
        var = self._re("VARNAME")
        if self._peek("["):
            # Lark: the index is optional; if it cannot be parsed, the
            # bracket belongs to what follows (e.g. a lookahead option)
            save = self.pos
            try:
                children = [var, self._lit("[", "LSQB")]
                children.append(Tree(_R.indexquant, [self._expr()]))
                while self._peek(","):
                    children.append(self._lit(",", "COMMA"))
                    children.append(Tree(_R.indexquant, [self._expr()]))
                children.append(self._lit("]", "RSQB"))
                return Tree(_R.extvarname, children)
            except _Backtrack:
                self.pos = save
        return Tree(_R.extvarname, [var])

    def _exprs(self, num):
        children = [self._expr()]
        for _ in range(num - 1):
            children.append(self._lit(",", "COMMA"))
            children.append(self._expr())
        return children

    # ---------------------------------------------------------------
    # ENDF records
    # ---------------------------------------------------------------

    def _record_line(self):
        lsqb = self._lit("[", "LSQB")
        ctrl = Tree(
            _R.ctrl_spec,
            [
                self._re("MAT_SPEC"),
                self._lit(",", "COMMA"),
                self._re("MF_SPEC"),
                self._lit(",", "COMMA"),
                self._re("MT_SPEC"),
            ],
        )
        slash = self._lit("/", "SLASH")
        prefix = [lsqb, ctrl, slash]
        start = self.pos
        for alternative in (
            self._head_or_cont_line,
            self._list_line,
            self._tab1_line,
            self._tab2_line,
            self._text_line,
            self._intg_line,
            self._dir_line,
        ):
            self.pos = start
            try:
                return alternative(prefix)
            except _Backtrack:
                pass
        raise _BACKTRACK

    def _record_fields(self, limit=None):
        # memoized, as the alternatives of _record_line parse the same
        # fields again after backtracking
        start = self.pos
        memo_start, memo_limit, memo_result = self._fields_memo
        if memo_start == start and memo_limit == limit:
            fields, nops, end = memo_result
            self.pos = end
            return fields, nops
        children = self._exprs(5)
        children.append(self._lit(",", "COMMA"))
        children.append(self._expr(limit))
        fields = Tree(_R.record_fields, children)
        nops = self.expr_nops
        self._fields_memo = (start, limit, (fields, nops, self.pos))
        return fields, nops

    def _with_record_fields(self, prefix, finish):
        # Records whose six fields are followed by a slash (TAB1, TAB2,
        # LIST). As the slash is also the division operator, the last
        # field may end before any of its top-level slashes.
        # Lark: of the possible splits, the longest last field wins.
        start = self.pos
        limit = None
        while True:
            self.pos = start
            fields, nops = self._record_fields(limit)
            try:
                return finish(prefix, fields)
            except _Backtrack:
                if nops == 0:
                    raise
                limit = nops - 1

    def _head_or_cont_line(self, prefix):
        fields, _ = self._record_fields()
        rsqb = self._lit("]", "RSQB")
        subtype = self._re("CONT_SUBTYPE")
        return Tree(_R.head_or_cont_line, prefix + [fields, rsqb, subtype])

    def _tab1_line(self, prefix):
        return self._with_record_fields(prefix, self._finish_tab1_line)

    def _finish_tab1_line(self, prefix, fields):
        slash = self._lit("/", "SLASH")
        xname = self._extvarname()
        slash2 = self._lit("/", "SLASH")
        yname = self._extvarname()
        tab1_def = Tree(_R.tab1_def, [xname, slash2, yname])
        tab1_fields = Tree(_R.tab1_fields, [fields, slash, tab1_def])
        children = prefix + [tab1_fields, self._lit("]", "RSQB")]
        children.append(self._lit("TAB1", "TAB1"))
        self._opt_name(children, _R.table_name)
        return Tree(_R.tab1_line, children)

    def _tab2_line(self, prefix):
        return self._with_record_fields(prefix, self._finish_tab2_line)

    def _finish_tab2_line(self, prefix, fields):
        slash = self._lit("/", "SLASH")
        tab2_def = Tree(_R.tab2_def, [self._extvarname()])
        tab2_fields = Tree(_R.tab2_fields, [fields, slash, tab2_def])
        children = prefix + [tab2_fields, self._lit("]", "RSQB")]
        children.append(self._lit("TAB2", "TAB2"))
        self._opt_name(children, _R.table_name)
        return Tree(_R.tab2_line, children)

    def _list_line(self, prefix):
        return self._with_record_fields(prefix, self._finish_list_line)

    def _finish_list_line(self, prefix, fields):
        slash = self._lit("/", "SLASH")
        body = self._list_body(toplevel=True)
        children = prefix + [fields, slash, body, self._lit("]", "RSQB")]
        children.append(self._lit("LIST", "LIST"))
        self._opt_name(children, _R.list_name)
        return Tree(_R.list_line, children)

    def _opt_name(self, children, rule):
        # ("(" table_name ")")?  or  ("(" list_name ")")?
        if self._peek("("):
            lpar = self._lit("(", "LPAR")
            name = Tree(rule, [self._extvarname()])
            children.extend((lpar, name, self._lit(")", "RPAR")))

    def _text_line(self, prefix):
        fields = self._text_fields()
        rsqb = self._lit("]", "RSQB")
        return Tree(_R.text_line, prefix + [fields, rsqb, self._lit("TEXT", "TEXT")])

    def _intg_line(self, prefix):
        fields = Tree(_R.intg_fields, self._exprs(3))
        lbrace = self._lit("{", "LBRACE")
        ndigit = Tree(_R.ndigit_expr, [self._expr()])
        rbrace = self._lit("}", "RBRACE")
        rsqb = self._lit("]", "RSQB")
        intg = self._lit("INTG", "INTG")
        children = prefix + [fields, lbrace, ndigit, rbrace, rsqb, intg]
        return Tree(_R.intg_line, children)

    def _dir_line(self, prefix):
        children = prefix + [
            self._lit("blank", "BLANK"),
            self._lit(",", "COMMA"),
            self._lit("blank", "BLANK"),
            self._lit(",", "COMMA"),
            Tree(_R.dir_fields, self._exprs(4)),
            self._lit("]", "RSQB"),
            self._lit("DIR", "DIR"),
        ]
        return Tree(_R.dir_line, children)

    # ---------------------------------------------------------------
    # TEXT record fields
    # ---------------------------------------------------------------

    def _text_fields(self):
        children = [self._textplaceholder()]
        nl = self._opt_newline()
        if nl is not None:
            children.append(nl)
        while self._peek(","):
            children.append(self._lit(",", "COMMA"))
            nl1 = self._opt_newline()
            placeholder = self._textplaceholder()
            nl2 = self._opt_newline()
            if nl1 is not None and nl2 is None and not placeholder.children:
                # Lark: a newline between a comma and an empty
                # placeholder is attributed to the slot after the
                # placeholder (`"," textplaceholder NEWLINE`)
                nl1, nl2 = None, nl1
            if nl1 is not None:
                children.append(nl1)
            children.append(placeholder)
            if nl2 is not None:
                children.append(nl2)
        return Tree(_R.text_fields, children)

    def _textplaceholder(self):
        children = []
        p = self._skip(self.pos)
        if _VARNAME_RE.match(self.text, p) is not None:
            children.append(self._extvarname())
        else:
            self._expect(p, "VARNAME")
        if self._peek("{"):
            children.append(self._lit("{", "LBRACE"))
            children.append(self._re("TEXTLENGTH"))
            while True:
                p = self._skip(self.pos)
                if _TEXTLENGTH_RE.match(self.text, p) is None:
                    self._expect(p, "TEXTLENGTH")
                    break
                children.append(self._re("TEXTLENGTH"))
            children.append(self._lit("}", "RBRACE"))
        return Tree(_R.textplaceholder, children)

    # ---------------------------------------------------------------
    # LIST record body
    # ---------------------------------------------------------------

    def _list_body(self, toplevel=False):
        # (expr | list_loop | LINEPADDING | "," | NEWLINE)*
        text = self.text
        children = []
        append = children.append
        while True:
            p = self._skip(self.pos)
            c = text[p : p + 1]
            if c == ",":
                append(self._lit(",", "COMMA"))
            elif c == "{":
                append(self._list_loop())
            elif c == "\n" or c == "\r" and text.startswith("\r\n", p):
                append(self._newline())
            elif c and c in _EXPR_START:
                if toplevel and not children and text.startswith("PADLINE", p):
                    tok = self._linepadding(p)
                    if tok is not None:
                        append(tok)
                        continue
                # Elements need not be separated by commas, so `x -y`
                # can be one element (a subtraction) or two. The
                # expression is always maximal here. Lark makes the same
                # choice for the first element and in most other cases,
                # but in some it splits the text into two elements,
                # depending on the order in which Earley processes the
                # ambiguous derivations (e.g. `x, y -z*w` gives the
                # elements `x`, `y`, `-z*w`).
                append(self._expr())
            else:
                for what in ("','", "'{'", "NEWLINE", "expression"):
                    self._expect(p, what)
                break
        return Tree(_R.list_body, children)

    def _linepadding(self, p):
        # Lark: the text `PADLINE` matches both LINEPADDING and VARNAME.
        # As the first element of the body of a LIST record, the bare
        # word `PADLINE` is LINEPADDING, unless it begins a longer
        # expression (e.g. `PADLINE-1`, `PADLINE[1]`, `PADLINE?`).
        # Anywhere else (later elements, elements of list loops), Lark
        # chooses the variable name `PADLINE`.
        # Lark splits a longer name such as `PADLINE2` or `PADLINEx` in
        # some positions into LINEPADDING and the remainder, as an
        # artifact of the order in which Earley processes ambiguous
        # derivations; here such a name is always a variable name.
        end = p + 7
        if _VARNAME_RE.match(self.text, p).end() != end:
            return None
        save = self.pos
        self._expr()
        longer = self.pos != end
        self.pos = save
        if longer:
            return None
        self.pos = end
        return self._tok("LINEPADDING", "PADLINE", p, end)

    def _list_loop(self):
        lbrace = self._lit("{", "LBRACE")
        body = self._list_body()
        rbrace = self._lit("}", "RBRACE")
        lbrace2 = self._lit("{", "LBRACE")
        head = Tree(
            _R.list_for_head,
            [
                self._re("VARNAME"),
                self._lit("=", "EQUAL"),
                Tree(_R.for_start, [self._expr()]),
                self._lit("to", "TO"),
                Tree(_R.for_stop, [self._expr()]),
            ],
        )
        rbrace2 = self._lit("}", "RBRACE")
        return Tree(_R.list_loop, [lbrace, body, rbrace, lbrace2, head, rbrace2])

    # ---------------------------------------------------------------
    # error reporting
    # ---------------------------------------------------------------

    def _raise_error(self):
        pos = max(self.fail_pos, 0)
        line, col = self._linecol(pos)
        text = self.text
        if pos >= self.n:
            found = "end of input"
        else:
            m = re.compile(r"[A-Za-z0-9_.]+|\r?\n|.").match(text, pos)
            found = repr(m.group())
        expected = sorted(self.fail_expected)
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        if line_end == -1:
            line_end = self.n
        src_line = text[line_start:line_end]
        msg = (
            f"Invalid ENDF recipe: unexpected {found} at line {line}, "
            f"column {col}.\nExpected one of: {', '.join(expected)}\n"
            f"\n    {src_line}\n    {' ' * (col - 1)}^"
        )
        raise RecipeSyntaxError(msg, line, col, pos, expected)


def parse_recipe(recipe):
    """Parse an ENDF recipe into a parse tree.

    Parameters
    ----------
    recipe : str
        The recipe in the ENDF recipe language.

    Returns
    -------
    Tree
        The parse tree, identical to the one Lark produces from the
        grammar in :mod:`endf_parserpy.endf_recipes.endf_lark_ebnf`
        with ``start="endf_recipe"`` and ``keep_all_tokens=True``.

    Raises
    ------
    RecipeSyntaxError
        If the recipe cannot be parsed. The message states the line and
        column and the tokens that were expected.
    """
    parser = _Parser(recipe)
    try:
        return parser.parse()
    except _Backtrack:
        parser._raise_error()


class RecipeParser:
    """Recipe parser with the ``parse`` method of a ``lark.Lark`` object."""

    def parse(self, recipe):
        return parse_recipe(recipe)


_RECIPE_PARSER = RecipeParser()


def get_recipe_parser():
    """Return a (shared) :class:`RecipeParser` instance."""
    return _RECIPE_PARSER
