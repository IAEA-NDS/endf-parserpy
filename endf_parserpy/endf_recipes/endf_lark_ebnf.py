############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2025/06/03
# License:         MIT
# Copyright (c) 2022-2025 International Atomic Energy Agency (IAEA)
#
############################################################

endf_recipe_grammar = r"""
%import common.DIGIT
%import common.LETTER
%import common.NEWLINE
%import common.STRING
%import common.CNAME
%import common.INT
%import common.NUMBER
%import common.ESCAPED_STRING
%ignore " "

endf_recipe : (code_token | NEWLINE)*
code_token: (endf_line | for_loop | repeat_loop | if_clause | section |
            | abbreviation | comment_block)
endf_line : (list_line | head_or_cont_line | tab1_line | tab2_line
            | text_line | dir_line | intg_line | send_line | stop_line) NEWLINE

// section to define namespace for variables
section: section_head section_body section_tail
section_head : "(" extvarname ")" NEWLINE
section_body : (code_token | NEWLINE)*
section_tail : "(/" extvarname ")" NEWLINE

// control numbers
ctrl_spec : MAT_SPEC "," MF_SPEC "," MT_SPEC
MAT_SPEC : "MAT" | INT
MF_SPEC :  "MF" | INT
MT_SPEC : "MT" | INT

// generic record body
record_fields : expr "," expr "," expr "," expr "," expr "," expr

// comment block
comment_block : COMMENT
COMMENT : /( *#[^\n]*\r?\n)+/s

// stop instruction to quit parsing
stop_line : "stop" "(" escaped_stop_message? ")"
escaped_stop_message : "\"" STOP_MESSAGE "\""
STOP_MESSAGE : /[^"]+/

// abbreviations of expressions to avoid cluttered ENDF record specifications
abbreviation : VARNAME ":=" expr NEWLINE

// TEXT record
text_line : "[" ctrl_spec "/" text_fields "]" "TEXT"
text_fields : textplaceholder NEWLINE? ("," NEWLINE? textplaceholder NEWLINE?)*
textplaceholder : extvarname? ("{" TEXTLENGTH+ "}")?
TEXTLENGTH : DIGIT+

// HEAD and CONT record
head_or_cont_line : "[" ctrl_spec "/" record_fields "]" CONT_SUBTYPE
CONT_SUBTYPE : "CONT" | "HEAD"

// DIR record
dir_line : "[" ctrl_spec "/" "blank" "," "blank" "," dir_fields "]" "DIR"
dir_fields :  expr "," expr "," expr "," expr

// INTG record
intg_line : "[" ctrl_spec "/" intg_fields "{" ndigit_expr "}" "]" "INTG"
intg_fields : expr "," expr "," expr
ndigit_expr : expr

// TAB1 record
tab1_line : "[" ctrl_spec "/" tab1_fields "]" "TAB1" ("(" table_name ")")?
tab1_fields : record_fields "/" tab1_def
tab1_def : extvarname "/" extvarname
table_name : extvarname

// TAB2 record
tab2_line : "[" ctrl_spec "/" tab2_fields "]" "TAB2" ("(" table_name ")")?
tab2_fields : record_fields "/" tab2_def
tab2_def : extvarname

// LIST record
list_line : "[" ctrl_spec "/" record_fields "/"  list_body  "]" "LIST" ("(" list_name ")")?
list_body : (expr | list_loop | LINEPADDING | "," | NEWLINE)*
list_name : extvarname
LINEPADDING : "PADLINE"

// LIST loop
list_loop : "{" list_body "}" "{" list_for_head "}"
list_for_head : VARNAME "=" for_start "to" for_stop

// SEND record
send_line : "SEND"

// FOR loop
for_loop : for_head for_body "endfor" NEWLINE
for_head : "for" VARNAME "=" for_start "to" for_stop ":"
for_body : (code_token | NEWLINE)*
for_start :  expr
for_stop :   expr

// REPEAT .. UNTIL loop
repeat_loop : repeat_head repeat_body repeat_tail NEWLINE
repeat_head : "repeat" ( "[" repeat_varassign "]" )? ":"
repeat_varassign : VARNAME "=" expr
repeat_body : (code_token | NEWLINE)*
repeat_tail : "until" if_head

// IF statement
if_clause : if_statement elif_statement* else_statement? "endif"
if_statement : "if" if_head (lookahead_option)? ":" if_body
elif_statement : "elif" if_head (lookahead_option)? ":" if_body
else_statement : "else:" if_body

lookahead_option : "[" "lookahead" "=" expr "]"
if_head : disjunction
if_condition : expr IF_RELATION expr
IF_RELATION  : ">" | "<" | "!=" | "==" | ">=" | "<="
IF_AND : "and"
IF_OR : "or"
if_body : (code_token | NEWLINE)*
// the solution in the answer at https://stackoverflow.com/questions/63493679/backus-naur-form-with-boolean-algebra-problem-with-brackets-and-parse-tree
// was helpful and modified to treat conjunction, disjunction and bracketed expressions
disjunction : disjunction "or" conjunction | conjunction
conjunction : conjunction "and" comparison | comparison
comparison : if_condition | "(" disjunction ")"

// arithmetic expression
// adopted from: http://marvin.cs.uidaho.edu/Teaching/CS445/grammar.pdf (3.3)
expr : addition | subtraction | addpart
addpart : multiplication | division | modulo | mulpart
mulpart : minusexpr | extvarname | inconsistent_varspec | NUMBER | DESIRED_NUMBER | bracketexpr

multiplication : addpart "*" mulpart
division : addpart "/" mulpart
modulo : addpart "%" mulpart
addition : expr "+" addpart
subtraction : expr "-" addpart

minusexpr: "-" mulpart
bracketexpr : "(" expr ")"

// allowed variable names (including indices)
extvarname : VARNAME ("[" indexquant ("," indexquant)* "]")?
VARNAME : LETTER (LETTER | DIGIT | "_")*
indexquant : expr

// special number symbol indicating that
// a specific number is expected but it may be different in practice
DESIRED_NUMBER : NUMBER "?"

// special variable symbol indicating
// that if the value of the variable in the current record
// is permitted to be inconsistent with a previously read value
inconsistent_varspec : extvarname "?"
"""
