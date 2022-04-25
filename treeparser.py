from copy import deepcopy
from lark import Lark
from tree_utils import is_tree, get_name, get_child, get_child_value
from endf_parsing_utils import (map_cont_dic, map_head_dic, map_text_dic,
        map_dir_dic, map_tab1_dic)
from flow_control_utils import cycle_for_loop, evaluate_if_statement, should_proceed

from endf_utils import (read_cont, write_cont, read_ctrl, get_ctrl,
        write_head, read_head, read_text, write_text,
        read_dir, write_dir, read_tab1, write_tab1,
        read_send, write_send, split_sections)


class BasicEndfParser():

    def __init__(self):
        # endf record treatment
        endf_actions = {}
        endf_actions['head_line'] = self.process_head_line
        endf_actions['cont_line'] = self.process_cont_line
        endf_actions['text_line'] = self.process_text_line
        endf_actions['dir_line'] = self.process_dir_line
        endf_actions['tab1_line'] = self.process_tab1_line
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

    def run_instruction(self, t):
        if t.data in self.endf_actions:
            if should_proceed(tree, self.datadic, self.loop_vars,
                                         action_type='endf_action'):
                self.endf_actions[t.data](t)
        elif t.data in self.flow_actions:
            if should_proceed(tree, self.datadic, self.loop_vars,
                                          action_type='flow_action'):
                self.flow_actions[t.data](t)
        else:
            for child in t.children:
                if is_tree(child):
                    self.run_instruction(child)

    def reset_parser_state(self, rwmode='read', lines=[], datadic={}):
        self.loop_vars = {}
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

    def parse(self, lines, tree_dic):
        mfmt_dic = split_sections(lines)
        for mf in mfmt_dic:
            for mt in mfmt_dic[mf]:
                curlines = mfmt_dic[mf][mt]
                if mf in tree_dic and mt in tree_dic[mf]:
                    self.reset_parser_state(rwmode='read', lines=curlines)
                    self.run_instruction(tree)
                    mfmt_dic[mf][mt] = self.datadic
        return mfmt_dic

    def write(self, endf_dic, tree_dic):
        lines = []
        for mf in sorted(endf_dic):
            for mt in sorted(endf_dic[mf]):
                if mf in tree_dic and mt in tree_dic[mf]:
                    datadic = endf_dic[mf][mt]
                    self.reset_parser_state(rwmode='write', datadic=datadic)
                    self.run_instruction(tree)
                    lines.extend(self.lines)
                else:
                    # if no recipe is available to parse a
                    # section, it will be preserved as a
                    # string in the parse step
                    # and we output it unchanged
                    lines.extend(endf_dic[mf][mt])
        return lines


# helpful functions

# some test data for development

with open('endf.lark', 'r') as f:
    mygrammar = f.read()

from testdata.endf_spec import endf_spec_mf1_mt451_wtext_wdir as curspec
#from testdata.endf_snippets import endf_cont_mf1_mt451_wtext_wdir as curcont

with open('n_2925_29-Cu-63.endf', 'r') as f:
    curcont = f.read()

#from testdata.endf_spec import endf_spec_mf3_mt as curspec
#from testdata.endf_snippets import endf_cont_mf3_mt16 as curcont

#from testdata.endf_spec import endf_spec_several_mfmt as curspec
#from testdata.endf_snippets import endf_cont_mf1_mt451_wtext_wdir as curcont

#from testdata.endf_spec import endf_spec_mf1_mt451 as curspec
#from testdata.endf_snippets import endf_cont_mf1_mt451 as curcont

myparser = Lark(mygrammar, start='code_token')
tree = myparser.parse(curspec)

tree_dic = {1: {451: tree}}
#print(tree.pretty())

xlines = curcont.splitlines()

parser = BasicEndfParser()
datadic = parser.parse(xlines, tree_dic)

parser = BasicEndfParser()
newlines = parser.write(datadic, tree_dic)
#
#print('#####################')
#print('\n'.join(xlines))
#print('---------------------')
#print('\n'.join(newlines))
#print('#####################')
#
print(datadic[3][16])


