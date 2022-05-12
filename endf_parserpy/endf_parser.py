from .logging_utils import logging, write_info
from copy import deepcopy
from lark import Lark
from .tree_utils import is_tree, get_name, get_child, get_child_value
from .endf_mappings import (map_cont_dic, map_head_dic, map_text_dic,
        map_dir_dic, map_tab1_dic, map_tab2_dic, map_list_dic)
from .endf_mapping_utils import get_varname, get_indexvars, open_section, close_section
from .flow_control_utils import cycle_for_loop, evaluate_if_statement, should_proceed

from .endf_utils import (read_cont, write_cont, read_ctrl, get_ctrl,
        write_head, read_head, read_text, write_text,
        read_dir, write_dir, read_tab1, write_tab1, read_tab2, write_tab2,
        read_send, write_send, write_fend, write_mend, write_tend,
        read_list, write_list, split_sections)

logging.basicConfig(level=logging.INFO)


class BasicEndfParser():

    def __init__(self):
        # obtain the parsing tree for the language
        # in which ENDF reading recipes are formulated
        from .endf_lark import endf_recipe_grammar
        from .endf_spec import spec_dic
        endf_recipe_grammar_parser= Lark(endf_recipe_grammar, start='code_token')
        tree_dic = {}
        for mf in spec_dic:
            tree_dic.setdefault(mf, {})
            if isinstance(spec_dic[mf], str):
                tree_dic[mf] = endf_recipe_grammar_parser.parse(spec_dic[mf])
            else:
                for mt in spec_dic[mf]:
                    tree_dic[mf][mt] = endf_recipe_grammar_parser.parse(spec_dic[mf][mt])
        self.tree_dic = tree_dic
        # endf record treatment
        endf_actions = {}
        endf_actions['head_line'] = self.process_head_line
        endf_actions['cont_line'] = self.process_cont_line
        endf_actions['text_line'] = self.process_text_line
        endf_actions['dir_line'] = self.process_dir_line
        endf_actions['tab1_line'] = self.process_tab1_line
        endf_actions['tab2_line'] = self.process_tab2_line
        endf_actions['list_line'] = self.process_list_line
        endf_actions['send_line'] = self.process_send_line
        self.endf_actions = endf_actions
        # program flow
        flow_actions = {}
        flow_actions['for_loop'] = self.process_for_loop
        flow_actions['if_statement'] = self.process_if_statement
        flow_actions['section'] = self.process_section
        self.flow_actions = flow_actions

    def process_text_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            # write_info('Reading a TEXT record', self.ofs)
            text_dic, self.ofs = read_text(self.lines, self.ofs, with_ctrl=True)
            map_text_dic(tree, text_dic, self.datadic, self.loop_vars)
        else:
            text_dic = map_text_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            text_dic.update(get_ctrl(self.datadic))
            newlines = write_text(text_dic, with_ctrl=True)
            self.lines += newlines

    def process_head_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a HEAD record', self.ofs)
            cont_dic, self.ofs = read_head(self.lines, self.ofs, with_ctrl=True)
            write_info('Content of the HEAD record: ' + str(cont_dic), self.ofs)
            map_head_dic(tree, cont_dic, self.datadic, self.loop_vars)
            self.datadic.update(get_ctrl(cont_dic))
        else:
            head_dic = map_head_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            head_dic.update(get_ctrl(self.datadic))
            newlines = write_head(head_dic, with_ctrl=True)
            self.lines += newlines

    def process_cont_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a CONT record', self.ofs)
            cont_dic, self.ofs = read_cont(self.lines, self.ofs)
            write_info('Content of the CONT record: ' + str(cont_dic))
            map_cont_dic(tree, cont_dic, self.datadic, self.loop_vars)
        else:
            cont_dic = map_cont_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            cont_dic.update(get_ctrl(self.datadic))
            newlines = write_cont(cont_dic, with_ctrl=True)
            self.lines += newlines

    def process_dir_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            dir_dic, self.ofs = read_dir(self.lines, self.ofs)
            map_dir_dic(tree, dir_dic, self.datadic, self.loop_vars)
        else:
            dir_dic = map_dir_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            dir_dic.update(get_ctrl(self.datadic))
            newlines = write_dir(dir_dic, with_ctrl=True)
            self.lines += newlines

    def process_tab1_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a TAB1 record', self.ofs)
            tab1_dic, self.ofs = read_tab1(self.lines, self.ofs)
            map_tab1_dic(tree, tab1_dic, self.datadic, self.loop_vars)
        else:
            tab1_dic = map_tab1_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            tab1_dic.update(get_ctrl(self.datadic))
            newlines = write_tab1(tab1_dic, with_ctrl=True)
            self.lines += newlines

    def process_tab2_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a TAB2 record', self.ofs)
            tab2_dic, self.ofs = read_tab2(self.lines, self.ofs)
            map_tab2_dic(tree, tab2_dic, self.datadic, self.loop_vars)
        else:
            tab2_dic = map_tab2_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            tab2_dic.update(get_ctrl(self.datadic))
            newlines = write_tab2(tab2_dic, with_ctrl=True)
            self.lines += newlines

    def process_list_line(self, tree):
        if self.rwmode == 'read':
            self.loop_vars['__ofs'] = self.ofs
            write_info('Reading a LIST record', self.ofs)
            list_dic, self.ofs = read_list(self.lines, self.ofs)
            map_list_dic(tree, list_dic, self.datadic, self.loop_vars)
        else:
            list_dic = map_list_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            list_dic.update(get_ctrl(self.datadic))
            newlines = write_list(list_dic, with_ctrl=True)
            self.lines += newlines

    def process_send_line(self, tree):
        if self.rwmode == 'read':
            read_send(self.lines, self.ofs)
        else:
            newlines = write_send(self.datadic, with_ctrl=True)
            self.lines += newlines

    def process_section(self, tree):
        self.loop_vars['__ofs'] = self.ofs
        section_head = get_child(tree, 'section_head')
        section_tail = get_child(tree, 'section_tail')
        varname = get_varname(section_head)
        varname2 = get_varname(section_tail)
        if varname != varname2:
            raise ValueError('The section name in the tail does not correspond to the one in the head')

        self.datadic = open_section(section_head, self.datadic, self.loop_vars)
        section_body = get_child(tree, 'section_body')
        self.run_instruction(section_body)
        self.datadic = close_section(section_head, self.datadic)

    def process_for_loop(self, tree):
        return cycle_for_loop(tree, self.run_instruction, self.datadic, self.loop_vars)

    def process_if_statement(self, tree):
        evaluate_if_statement(tree, self.run_instruction,
                              self.datadic, self.loop_vars,
                              dump_state = self.dump_parser_state,
                              restore_state = self.restore_parser_state)

    def run_instruction(self, tree):
        if tree.data in self.endf_actions:
            if should_proceed(tree, self.datadic, self.loop_vars,
                                         action_type='endf_action'):
                self.endf_actions[tree.data](tree)
        elif tree.data in self.flow_actions:
            if should_proceed(tree, self.datadic, self.loop_vars,
                                          action_type='flow_action'):
                self.flow_actions[tree.data](tree)
        else:
            for child in tree.children:
                if is_tree(child):
                    self.run_instruction(child)

    def reset_parser_state(self, rwmode='read', lines=None, datadic=None):
        self.loop_vars = {}
        # NOTE: default argument datadic={} does not work because
        #       Python's default arguments are evaluated once when
        #       the function is defined, not each time the function
        #       is called, and then changes of a mutable object in the
        #       function are preserved across function evaluations.
        # For a nice explanation and further details see:
        # https://medium.com/nerd-for-tech/how-default-parameters-could-cause-havoc-python-e6cb3d8fefb8
        # TO CHECK: mutable default arguments have been used elsewhere.
        #           Better to replace to avoid problems during future
        #           development.
        datadic = datadic if datadic is not None else {}
        lines = lines if lines is not None else []
        self.loop_vars = {'__ofs': 0}
        self.datadic = datadic
        self.lines = lines
        self.rwmode = rwmode
        self.ofs = 0

    def dump_parser_state(self):
        # NOTE: We have to protect the __up
        # pointer against deepcopy to ensure
        # that we can go back to the enclosing
        # dictionary and not a copy thereof
        # which is problematic for the if statement
        # with lookahead.
        if '__up' in self.datadic:
            updic = self.datadic['__up']
            del self.datadic['__up']
            datadic_copy = deepcopy(self.datadic)
            datadic_copy['__up'] = updic
        else:
            datadic_copy = deepcopy(self.datadic)

        return {'loop_vars': deepcopy(self.loop_vars),
                'datadic' : datadic_copy,
                'lines' : deepcopy(self.lines),
                'rwmode' : self.rwmode,
                'ofs' : self.ofs}

    def restore_parser_state(self, dump):
        self.loop_vars.clear()
        self.loop_vars.update(dump['loop_vars'])
        self.datadic.clear()
        self.datadic.update(dump['datadic'])
        self.lines.clear()
        self.lines.extend(dump['lines'])
        self.rwmode = dump['rwmode']
        self.ofs = dump['ofs']

    def get_responsible_tree(self, dic, mf, mt):
        tree_dic = self.tree_dic
        if mf in tree_dic:
            if is_tree(tree_dic[mf]):
                return tree_dic[mf]
            elif mt in tree_dic[mf] and is_tree(tree_dic[mf][mt]):
                return tree_dic[mf][mt]
        else:
            return None

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

    def parse(self, lines, exclude=None, include=None):
        # lines should be a list of lines.
        # if it is a string, we assume that the
        # string indicates a file name.
        if isinstance(lines, str):
            with open(lines, 'r') as f:
                lines = f.readlines()
        tree_dic = self.tree_dic
        mfmt_dic = split_sections(lines)
        for mf in mfmt_dic:
            write_info(f'Parsing section MF{mf}')
            for mt in mfmt_dic[mf]:
                curmat = read_ctrl(mfmt_dic[mf][mt][0])
                write_info(f'Parsing subsection MF/MT {mf}/{mt}')
                curlines = mfmt_dic[mf][mt]
                cur_tree = self.get_responsible_tree(tree_dic, mf, mt)
                should_skip = self.should_skip_section(mf, mt, exclude, include)
                if cur_tree is not None and not should_skip:
                    # we add the SEND line so that parsing fails
                    # if the MT section cannot be completely parsed
                    curlines += write_send(curmat, with_ctrl=True)
                    self.reset_parser_state(rwmode='read', lines=curlines)
                    self.run_instruction(cur_tree)
                    mfmt_dic[mf][mt] = self.datadic
        return mfmt_dic

    def write(self, endf_dic, mf_list=None, mt_list=None):
        self.reset_parser_state(rwmode='write', datadic={})
        tree_dic = self.tree_dic
        lines = []
        for mf in sorted(endf_dic):
            for mt in sorted(endf_dic[mf]):
                if ((mf_list is not None and mf not in mf_list) or
                    (mt_list is not None and mt not in mt_list)):
                    continue
                cur_tree = self.get_responsible_tree(tree_dic, mf, mt)
                if cur_tree is not None:
                    datadic = endf_dic[mf][mt]
                    self.reset_parser_state(rwmode='write', datadic=datadic)
                    self.run_instruction(cur_tree)
                    # the NS number is already part of the last line
                    curline_send = self.lines[-1]
                    # add the NS number to the other lines
                    curlines = [l + str(i).rjust(5)
                                for i, l in enumerate(self.lines[:-1], 1)]
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
                    self.datadic = read_ctrl(lines[-1])
                    # add the SEND record in between the MT subections
                    lines.extend(write_send(self.datadic, with_ctrl=True, with_ns=True))
            lines.extend(write_fend(self.datadic, with_ctrl=True, with_ns=True))

        lines.extend(write_mend(with_ctrl=True, with_ns=True))
        lines.extend(write_tend(with_ctrl=True, with_ns=True))
        return lines

