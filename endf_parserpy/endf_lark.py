endf_recipe_grammar = \
r"""
%import common.DIGIT
%import common.NEWLINE
%import common.STRING
%import common.CNAME
%import common.INT
%import common.NUMBER
%ignore " "

code_token: (endf_line | for_loop | if_statement | section | COMMENT_LINE | NEWLINE)*
endf_line : list_line | head_line | cont_line | tab1_line
            | text_line | dir_line  | send_line | dummy_line

// section to define namespace for variables
section: section_head section_body section_tail
section_head : "(" extvarname ")"
section_body : code_token*
section_tail : "(/" extvarname ")"

// control numbers
ctrl_spec : MAT_SPEC "," MF_SPEC "," MT_SPEC
MAT_SPEC : "MAT" | INT
MF_SPEC :  "MF" | INT
MT_SPEC : "MT" | INT

// comment line
COMMENT_LINE : "#" /.*/ NEWLINE

// DUMMY record (read but not processed)
dummy_line : "[" ctrl_spec "/" /.*\]/ "DUMMY" NEWLINE*

// TEXT record
text_line : "[" ctrl_spec "/" text_fields "]" "TEXT" NEWLINE*
text_fields : expr

// HEAD record
head_line : "[" ctrl_spec "/" head_fields "]" "HEAD" NEWLINE*
head_fields : expr "," expr "," expr "," expr "," expr "," expr

// CONT record
cont_line : "[" ctrl_spec "/" cont_fields "]" "CONT" NEWLINE*
cont_fields : expr "," expr "," expr "," expr "," expr "," expr

// DIR record
dir_line : "[" ctrl_spec "/" "blank" "," "blank" "," dir_fields "]" "DIR" NEWLINE*
dir_fields :  expr "," expr "," expr "," expr

// TAB1 record
tab1_line : "[" ctrl_spec "/" tab1_fields "]" "TAB1" ("(" table_name ")")? NEWLINE*
tab1_fields : tab1_cont_fields "/" tab1_def
tab1_cont_fields : expr "," expr "," expr "," expr "," expr "," expr
tab1_def : extvarname "/" extvarname
table_name : extvarname

// LIST record
list_line : "[" ctrl_spec "/" list_fields "/"  list_body  "]" "LIST" ("(" list_name ")")? NEWLINE*
list_fields : expr "," expr "," expr "," expr "," expr "," expr
list_body : (expr | list_loop | "," | NEWLINE)+
list_name : extvarname

// LIST loop
list_loop : "{" list_body "}" "{" list_for_head "}"
list_for_head : VARNAME "=" for_start "to" for_stop

// SEND record
send_line : "SEND" NEWLINE*

// FOR loop
for_loop : "for" for_head for_body "endfor"
for_head : VARNAME "=" for_start "to" for_stop ":"
for_body : NEWLINE* code_token* NEWLINE*
for_start :  expr
for_stop :   expr

// IF statement
if_statement : "if" if_head (lookahead_option)? ":" if_body "endif"
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
addpart : multiplication | division | mulpart
mulpart : minusexpr | extvarname | NUMBER | bracketexpr

multiplication : addpart "*" mulpart
division : addpart "/" mulpart
addition : expr "+" addpart
subtraction : expr "-" addpart

minusexpr: "-" mulpart
bracketexpr : "(" expr ")"

// allowed variable names (including indices)
extvarname : VARNAME ("[" INDEXVAR ("," INDEXVAR)* "]")?
VARNAME : CNAME
INDEXVAR : CNAME

// possible field values
CFIELD: CNAME | "0.0"
IFIELD: CNAME | "0"
"""

