############################################################
#
# Author(s):       Georg Schnabel
# Email:           g.schnabel@iaea.org
# Creation date:   2022/05/30
# Last modified:   2022/05/30
# License:         MIT
# Copyright (c) 2022 International Atomic Energy Agency (IAEA)
#
############################################################

from collections.abc import Mapping
from .logging_utils import write_info, RingBuffer
from appdirs import user_cache_dir
from os.path import exists as file_exists
from .tree_utils import (is_tree, get_child, get_child_value,
        retrieve_value)
from .endf_mappings import (map_cont_dic, map_head_dic, map_text_dic,
        map_dir_dic, map_intg_dic, map_tab1_dic, map_tab2_dic, map_list_dic)
from .endf_mapping_utils import eval_expr_without_unknown_var, get_varname
from .meta_control_utils import (cycle_for_loop, evaluate_if_clause,
        open_section, close_section, should_proceed,
        initialize_abbreviations, introduce_abbreviation, finalize_abbreviations)
from .endf_utils import (read_cont, write_cont, read_ctrl, get_ctrl,
        write_head, read_head, read_text, write_text, read_intg, write_intg,
        read_dir, write_dir, read_tab1, write_tab1, read_tab2, write_tab2,
        read_send, write_send, write_fend, write_mend, write_tend,
        read_list, write_list, split_sections, skip_blank_lines)
from .custom_exceptions import (
        InconsistentSectionBracketsError,
        StopException,
        ParserException
    )
from .endf_recipe_utils import (
        get_recipe_parsetree_dic,
        get_responsible_recipe_parsetree,
)
from .endf_recipes import endf_recipe_dictionary


class BasicEndfParser():

    def __init__(self, ignore_number_mismatch=False, ignore_zero_mismatch=True,
                       ignore_varspec_mismatch=False, fuzzy_matching=True,
                       blank_as_zero=True, abuse_signpos=False,
                       skip_intzero=False, prefer_noexp=False,
                       accept_spaces=True, keep_E=False, width=11,
                       cache_dir=None, print_cache_info=True, recipes=None):
        # obtain the parsing tree for the language
        # in which ENDF reading recipes are formulated
        if cache_dir is None:
            cache_dir = user_cache_dir('endf_parserpy', 'gschnabel')
            if print_cache_info:
                print(
                    f'Compiled ENDF recipes are cached in {cache_dir}\n' +
                    'Specify `cache_dir=False` to disable the creation ' +
                    'and use of a cache directory.\n' +
                    'Alternatively, pass a path as `cache_dir` argument.\n' +
                    'To suppress this message, specify `print_cache_info=False`.'
                )

        if recipes is None:
            recipes = endf_recipe_dictionary
        self.tree_dic = get_recipe_parsetree_dic(recipes, cache_dir)
        # endf record treatment
        endf_actions = {}
        endf_actions['head_or_cont_line'] = self.process_head_or_cont_line
        endf_actions['text_line'] = self.process_text_line
        endf_actions['dir_line'] = self.process_dir_line
        endf_actions['intg_line'] = self.process_intg_line
        endf_actions['tab1_line'] = self.process_tab1_line
        endf_actions['tab2_line'] = self.process_tab2_line
        endf_actions['list_line'] = self.process_list_line
        endf_actions['send_line'] = self.process_send_line
        endf_actions['stop_line'] = self.process_stop_line
        self.endf_actions = endf_actions
        # program flow
        meta_actions = {}
        meta_actions['for_loop'] = self.process_for_loop
        meta_actions['if_clause'] = self.process_if_clause
        meta_actions['section'] = self.process_section
        meta_actions['abbreviation'] = self.process_abbreviation
        self.meta_actions = meta_actions

        self.parse_opts = {
                'ignore_zero_mismatch': ignore_zero_mismatch,
                'ignore_number_mismatch': ignore_number_mismatch,
                'ignore_varspec_mismatch': ignore_varspec_mismatch,
                'fuzzy_matching': fuzzy_matching,
                'blank_as_zero': blank_as_zero
            }
        self.write_opts = {
                'abuse_signpos': abuse_signpos,
                'skip_intzero': skip_intzero,
                'prefer_noexp': prefer_noexp,
                'keep_E': keep_E,
                'width': width
            }
        self.read_opts = {
                'accept_spaces': accept_spaces,
                'width': width
            }

    def process_stop_line(self, tree):
        stop_message = retrieve_value(tree, 'STOP_MESSAGE')
        stop_message = stop_message if stop_message is not None else "stop instruction"
        raise StopException(stop_message)

    def process_text_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            write_info('Reading a TEXT record', self.ofs)
            text_dic, self.ofs = read_text(self.lines, self.ofs, with_ctrl=True, **self.read_opts)
            text_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_text_dic(tree, text_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            # this line adds MAT, MF, MT to the dictionary.
            # this line is introduced here to deal with the tape head (mf=0, mt=0)
            # which does not contain a head record as first item, which is the
            # only other place that adds this information.
            self.datadic.update(get_ctrl(text_dic))
        else:
            text_dic = map_text_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            text_dic.update(get_ctrl(self.datadic))
            newlines = write_text(text_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_head_or_cont_line(self, tree):
        line_type = get_child_value(tree, 'CONT_SUBTYPE')
        if line_type == 'HEAD':
            self.process_head_line(tree)
        elif line_type == 'CONT':
            self.process_cont_line(tree)
        else:
            raise TypeError('parser code / grammar mismatch')

    def process_head_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a HEAD record', self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            cont_dic, self.ofs = read_head(self.lines, self.ofs, with_ctrl=True,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            cont_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            write_info('Content of the HEAD record: ' + str(cont_dic), self.ofs)
            map_head_dic(tree, cont_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            self.datadic.update(get_ctrl(cont_dic))
        else:
            head_dic = map_head_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            head_dic.update(get_ctrl(self.datadic))
            newlines = write_head(head_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_cont_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a CONT record', self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            cont_dic, self.ofs = read_cont(self.lines, self.ofs,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            cont_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            write_info('Content of the CONT record: ' + str(cont_dic))
            map_cont_dic(tree, cont_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            cont_dic = map_cont_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            cont_dic.update(get_ctrl(self.datadic))
            newlines = write_cont(cont_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_dir_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            dir_dic, self.ofs = read_dir(self.lines, self.ofs,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            dir_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_dir_dic(tree, dir_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            dir_dic = map_dir_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            dir_dic.update(get_ctrl(self.datadic))
            newlines = write_dir(dir_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_intg_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            ndigit = eval_expr_without_unknown_var(get_child(tree, 'ndigit_expr'), self.datadic, self.loop_vars)
            intg_dic, self.ofs = read_intg(self.lines, self.ofs, ndigit=ndigit,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            intg_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_intg_dic(tree, intg_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            intg_dic = map_intg_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            intg_dic.update(get_ctrl(self.datadic))
            ndigit = eval_expr_without_unknown_var(get_child(tree, 'ndigit_expr'), self.datadic, self.loop_vars)
            newlines = write_intg(intg_dic, with_ctrl=True, ndigit=ndigit, **self.write_opts)
            self.lines += newlines

    def process_tab1_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a TAB1 record', self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            tab1_dic, self.ofs = read_tab1(self.lines, self.ofs,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            tab1_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_tab1_dic(tree, tab1_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            tab1_dic = map_tab1_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            tab1_dic.update(get_ctrl(self.datadic))
            newlines = write_tab1(tab1_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_tab2_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a TAB2 record', self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            tab2_dic, self.ofs = read_tab2(self.lines, self.ofs,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            tab2_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_tab2_dic(tree, tab2_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            tab2_dic = map_tab2_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            tab2_dic.update(get_ctrl(self.datadic))
            newlines = write_tab2(tab2_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_list_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a LIST record', self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            list_dic, self.ofs = read_list(self.lines, self.ofs,
                    blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
            list_dic.update(self.logbuffer.get_last_entry(key_prefix='__'))
            map_list_dic(tree, list_dic, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
        else:
            list_dic = map_list_dic(tree, {}, self.datadic, self.loop_vars, self.rwmode, parse_opts=self.parse_opts)
            list_dic.update(get_ctrl(self.datadic))
            newlines = write_list(list_dic, with_ctrl=True, **self.write_opts)
            self.lines += newlines

    def process_send_line(self, tree):
        if self.rwmode == 'read':
            self.ofs = skip_blank_lines(self.lines, self.ofs)
            self.logbuffer.save_record_log(self.ofs, self.lines[self.ofs], tree)
            read_send(self.lines, self.ofs,
                      blank_as_zero=self.parse_opts['blank_as_zero'], **self.read_opts)
        else:
            newlines = write_send(self.datadic, with_ctrl=True,
                                  zero_as_blank=self.zero_as_blank,
                                  **self.write_opts)
            self.lines += newlines

    def process_section(self, tree):
        self.loop_vars['__ofs'] = self.ofs
        section_head = get_child(tree, 'section_head')
        section_tail = get_child(tree, 'section_tail')
        varname = get_varname(section_head)
        varname2 = get_varname(section_tail)
        if varname != varname2:
            raise InconsistentSectionBracketsError(
                    'The section name in the tail does not correspond to ' +
                    f'the one in the head (`{varname}` vs `{varname2}`)')

        create_missing = (self.rwmode == 'read')
        self.datadic = open_section(section_head, self.datadic,
                                    self.loop_vars, create_missing)
        section_body = get_child(tree, 'section_body')
        initialize_abbreviations(self.datadic)
        self.run_instruction(section_body)
        finalize_abbreviations(self.datadic)
        self.datadic = close_section(section_head, self.datadic)

    def process_for_loop(self, tree):
        return cycle_for_loop(tree, self.run_instruction, self.datadic, self.loop_vars)

    def process_if_clause(self, tree):
        evaluate_if_clause(tree,
                           self.datadic, self.loop_vars,
                           self.run_instruction,
                           set_parser_state=self.set_parser_state,
                           get_parser_state=self.get_parser_state)

    def process_abbreviation(self, tree):
        introduce_abbreviation(tree, self.datadic)

    def run_instruction(self, tree):
        if tree.data in self.endf_actions:
            if should_proceed(self.datadic, self.loop_vars,
                                         action_type='endf_action'):
                self.endf_actions[tree.data](tree)
        elif tree.data in self.meta_actions:
            if should_proceed(self.datadic, self.loop_vars,
                                          action_type='meta_action'):
                self.meta_actions[tree.data](tree)
        else:
            for child in tree.children:
                if is_tree(child):
                    if should_proceed(self.datadic,
                                      self.loop_vars,
                                      action_type='unspecified'):
                        self.run_instruction(child)
                    else:
                        break

    def reset_parser_state(self, rwmode='read', lines=None, datadic=None):
        self.loop_vars = {}
        datadic = datadic if datadic is not None else {}
        lines = lines if lines is not None else []
        self.loop_vars = {'__ofs': 0}
        self.datadic = datadic
        self.lines = lines
        self.rwmode = rwmode
        self.ofs = 0
        self.logbuffer = RingBuffer(capacity=20)

    def get_parser_state(self):
        return {'loop_vars': self.loop_vars,
                'datadic': self.datadic,
                'lines': self.lines,
                'rwmode': self.rwmode,
                'ofs': self.ofs,
                'logbuffer_state': self.logbuffer.dump_state(),
                'parse_opts': self.parse_opts}

    def set_parser_state(self, parser_state):
        self.loop_vars = parser_state['loop_vars']
        self.datadic = parser_state['datadic']
        self.lines = parser_state['lines']
        self.rwmode = parser_state['rwmode']
        self.ofs = parser_state['ofs']
        self.logbuffer.load_state(parser_state['logbuffer_state'])
        self.parse_opts = parser_state['parse_opts']

    def should_skip_section(self, mf, mt, exclude=None, include=None):
        if exclude is None:
            if include is not None:
                if (mf not in include and
                    (mf, mt) not in include):
                    return True
        # exclude not None
        else:
            if mf in exclude:
                return True
            elif (mf, mt) in exclude:
                return True
        return False

    def parse(self, lines, exclude=None, include=None, nofail=False):
        if isinstance(lines, str):
            lines = lines.split('\n')
        tree_dic = self.tree_dic
        mfmt_dic = split_sections(lines, **self.read_opts)
        for mf in mfmt_dic:
            write_info(f'Parsing section MF{mf}')
            for mt in mfmt_dic[mf]:
                curmat = read_ctrl(mfmt_dic[mf][mt][0], **self.read_opts)
                write_info(f'Parsing subsection MF/MT {mf}/{mt}')
                curlines = mfmt_dic[mf][mt]
                cur_tree = get_responsible_recipe_parsetree(tree_dic, mf, mt)
                should_skip = self.should_skip_section(mf, mt, exclude, include)
                if cur_tree is not None and not should_skip:
                    # we add the SEND line so that parsing fails
                    # if the MT section cannot be completely parsed
                    curlines += write_send(curmat, with_ctrl=True, **self.write_opts)
                    self.reset_parser_state(rwmode='read', lines=curlines)
                    try:
                        initialize_abbreviations(self.datadic)
                        self.run_instruction(cur_tree)
                        finalize_abbreviations(self.datadic)
                        mfmt_dic[mf][mt] = self.datadic
                    except ParserException as exc:
                        if not nofail:
                            logstr = self.logbuffer.display_record_logs()
                            raise ParserException(
                                    '\nHere is the parser record log until failure:\n\n' +
                                    logstr + 'Error message: ' + str(exc))
        return mfmt_dic

    def write(self, endf_dic, exclude=None, include=None, zero_as_blank=False):
        self.zero_as_blank = zero_as_blank
        self.reset_parser_state(rwmode='write', datadic={})
        tree_dic = self.tree_dic
        lines = []
        for mf in sorted(endf_dic):
            some_mf_output = False
            for mt in sorted(endf_dic[mf]):
                should_skip = self.should_skip_section(mf, mt, exclude, include)
                if should_skip:
                    continue
                cur_tree = get_responsible_recipe_parsetree(tree_dic, mf, mt)
                is_parsed = isinstance(endf_dic[mf][mt], Mapping)
                if cur_tree is not None and is_parsed:
                    datadic = endf_dic[mf][mt]
                    self.reset_parser_state(rwmode='write', datadic=datadic)
                    initialize_abbreviations(self.datadic)
                    self.run_instruction(cur_tree)
                    finalize_abbreviations(self.datadic)
                    # add the NS number to the lines except last one
                    # because the SEND (=section end) record already
                    # contains it
                    curlines = [l + str(i).rjust(5)
                                for i, l in enumerate(self.lines[:-1], 1)]
                    # prepare the SEND (=section end) line
                    curline_send = self.lines[-1]
                    # in the case of tape head, which only is one line
                    # curline_send contains the tape head line and
                    # we need to append NS=0
                    if mf == 0:
                        curline_send += '0'.rjust(5)
                    # add the send line to the output
                    curlines.append(curline_send)
                    lines.extend(curlines)
                    # NOTE: the SEND record is part of the recipe
                    # and therefore will be added by the parser in
                    # process_send_line method. Hence there is no
                    # need to add it here, in contrast to the
                    # branch of the if-statement below to deal
                    # with non-parsable MF/MF sections.
                else:
                    # nothing is parsed here, but in the spirit of
                    # defensive coding, we reset the parser nevertheless
                    self.reset_parser_state(rwmode='write')
                    # if no recipe is available to parse a
                    # MF/MT section, it will be preserved as a
                    # list of strings in the parse step
                    # and we output that unchanged
                    curlines = endf_dic[mf][mt].copy()
                    # except that we remove newlines that screw it up
                    curlines = [t.replace('\n','').replace('\r','') for t in curlines]
                    lines.extend(curlines)
                    # update the MAT, MF, MT number
                    self.datadic = read_ctrl(lines[-1], **self.read_opts)
                    # add the SEND record in between the MT subections
                    # if it was not a tape head record (mf=0)
                    if mf != 0:
                        lines.extend(write_send(self.datadic, with_ctrl=True, with_ns=True,
                                                zero_as_blank=zero_as_blank))
                some_mf_output = True
            # we output the file end (fend) record only if something has been written
            # to this mf section and it is not the tape head (mf=0)
            if some_mf_output and mf != 0 :
                lines.extend(write_fend(self.datadic, with_ctrl=True, with_ns=True,
                                        zero_as_blank=zero_as_blank, **self.write_opts))

        lines.extend(write_mend(with_ctrl=True, with_ns=True,
                                zero_as_blank=zero_as_blank, **self.write_opts))
        lines.extend(write_tend(with_ctrl=True, with_ns=True,
                                zero_as_blank=zero_as_blank, **self.write_opts))
        del self.zero_as_blank
        return lines

    def parsefile(self, filename, exclude=None, include=None, nofail=False):
        with open(filename, 'r') as fin:
            lines = fin.readlines()
        return self.parse(lines, exclude, include, nofail=nofail)

    def writefile(self, filename, endf_dic, exclude=None, include=None,
                        zero_as_blank=False, overwrite=False):
        if file_exists(filename) and not overwrite:
            raise FileExistsError(f'file {filename} already exists. '
                                   'Change overwrite option to True if you '
                                   'really want to overwrite this file.')
        else:
            lines = self.write(endf_dic, exclude, include, zero_as_blank)
            with open(filename, 'w') as fout:
                fout.write('\n'.join(lines))
