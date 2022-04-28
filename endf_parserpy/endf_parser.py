from copy import deepcopy
from lark import Lark
from .tree_utils import is_tree, get_name, get_child, get_child_value
from .endf_mappings import (map_cont_dic, map_head_dic, map_text_dic,
        map_dir_dic, map_tab1_dic, map_list_dic)
from .flow_control_utils import cycle_for_loop, evaluate_if_statement, should_proceed

from .endf_utils import (read_cont, write_cont, read_ctrl, get_ctrl,
        write_head, read_head, read_text, write_text,
        read_dir, write_dir, read_tab1, write_tab1,
        read_send, write_send, write_fend, write_mend, write_tend,
        read_list, write_list, split_sections)


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
        endf_actions['list_line'] = self.process_list_line
        endf_actions['send_line'] = self.process_send_line
        self.endf_actions = endf_actions
        # program flow
        flow_actions = {}
        flow_actions['for_loop'] = self.process_for_loop
        flow_actions['if_statement'] = self.process_if_statement
        self.flow_actions = flow_actions

    def process_text_line(self, tree):
        if self.rwmode == 'read':
            text_dic, self.ofs = read_text(self.lines, self.ofs, with_ctrl=True)
            map_text_dic(tree, text_dic, self.datadic, self.loop_vars)
        else:
            text_dic = map_text_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            text_dic.update(get_ctrl(self.datadic))
            newlines = write_text(text_dic, with_ctrl=True)
            self.lines += newlines

    def process_head_line(self, tree):
        if self.rwmode == 'read':
            cont_dic, self.ofs = read_head(self.lines, self.ofs, with_ctrl=True)
            map_head_dic(tree, cont_dic, self.datadic, self.loop_vars)
            self.datadic.update(get_ctrl(cont_dic))
        else:
            head_dic = map_head_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            head_dic.update(get_ctrl(self.datadic))
            newlines = write_head(head_dic, with_ctrl=True)
            self.lines += newlines

    def process_cont_line(self, tree):
        if self.rwmode == 'read':
            cont_dic, self.ofs = read_cont(self.lines, self.ofs)
            map_cont_dic(tree, cont_dic, self.datadic, self.loop_vars)
        else:
            cont_dic = map_cont_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            cont_dic.update(get_ctrl(self.datadic))
            newlines = write_cont(cont_dic, with_ctrl=True)
            self.lines += newlines

    def process_dir_line(self, tree):
        if self.rwmode == 'read':
            dir_dic, self.ofs = read_dir(self.lines, self.ofs)
            map_dir_dic(tree, dir_dic, self.datadic, self.loop_vars)
        else:
            dir_dic = map_dir_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            dir_dic.update(get_ctrl(self.datadic))
            newlines = write_dir(dir_dic, with_ctrl=True)
            self.lines += newlines

    def process_tab1_line(self, tree):
        if self.rwmode == 'read':
            tab1_dic, self.ofs = read_tab1(self.lines, self.ofs)
            map_tab1_dic(tree, tab1_dic, self.datadic, self.loop_vars)
        else:
            tab1_dic = map_tab1_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            tab1_dic.update(get_ctrl(self.datadic))
            newlines = write_tab1(tab1_dic, with_ctrl=True)
            self.lines += newlines

    def process_list_line(self, tree):
        if self.rwmode == 'read':
            list_dic, self.ofs = read_list(self.lines, self.ofs)
            map_list_dic(tree, list_dic, self.datadic, self.loop_vars)
            # TODO: remove
            self.ofs += 1
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
        self.datadic = datadic
        self.lines = lines
        self.rwmode = rwmode
        self.ofs = 0

    def dump_parser_state(self):
        return {'loop_vars': deepcopy(self.loop_vars),
                'datadic' : deepcopy(self.datadic),
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

    def parse(self, lines):
        tree_dic = self.tree_dic
        mfmt_dic = split_sections(lines)
        for mf in mfmt_dic:
            for mt in mfmt_dic[mf]:
                print(f'working on MF {mf} and MT {mt}\n')
                curlines = mfmt_dic[mf][mt]
                cur_tree = self.get_responsible_tree(tree_dic, mf, mt)
                if cur_tree is not None:
                    self.reset_parser_state(rwmode='read', lines=curlines)
                    self.run_instruction(cur_tree)
                    mfmt_dic[mf][mt] = self.datadic
        return mfmt_dic

    def write(self, endf_dic, mf_list=None, mt_list=None):
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
                    # add the NS number
                    curlines = [l + str(i).rjust(5)
                                for i, l in enumerate(self.lines, 1)]
                    lines.extend(curlines)
                else:
                    # nothing is parsed here, but in the spirit of
                    # defensive coding, we reset the parser nevertheless
                    self.reset_parser_state(rwmode='write')
                    # if no recipe is available to parse a
                    # MF/MT section, it will be preserved as a
                    # list of strings in the parse step
                    # and we output that unchanged
                    curlines = endf_dic[mf][mt]
                    lines.extend(endf_dic[mf][mt])
                    # update the MAT, MF, MT number
                    self.datadic = read_ctrl(lines[-1])

                # add the SEND record in between the MT subections
                lines.extend(write_send(self.datadic, with_ctrl=True, with_ns=True))
            lines.extend(write_fend(self.datadic, with_ctrl=True, with_ns=True))

        lines.extend(write_mend(with_ctrl=True, with_ns=True))
        lines.extend(write_tend(with_ctrl=True, with_ns=True))
        return lines

