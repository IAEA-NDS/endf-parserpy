from lark import Lark
from tree_utils import is_tree, get_name, get_child, get_child_value
from endf_parsing_utils import map_cont_dic, map_head_dic, map_text_dic, map_dir_dic
from flow_control_utils import cycle_for_loop

from endf_utils import (read_cont, write_cont, get_ctrl,
        write_head, read_head, read_text, write_text,
        read_dir, write_dir)


class BasicEndfParser():

    def __init__(self):
        actions = {}
        actions['head_line'] = self.process_head_line
        actions['cont_line'] = self.process_cont_line
        actions['text_line'] = self.process_text_line
        actions['dir_line'] = self.process_dir_line
        actions['for_loop'] = self.process_for_loop
        self.actions = actions

    def process_text_line(self, tree):
        if self.rwmode == 'read':
            text_dic, self.ofs = read_text(lines, self.ofs, with_ctrl=True)
            map_text_dic(tree, text_dic, self.datadic, self.loop_vars)
        else:
            text_dic = map_text_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            text_dic.update(get_ctrl(self.datadic))
            newlines = write_text(text_dic, with_ctrl=True)
            self.lines += newlines

    def process_head_line(self, tree):
        if self.rwmode == 'read':
            cont_dic, self.ofs = read_head(lines, self.ofs, with_ctrl=True)
            map_head_dic(tree, cont_dic, self.datadic, self.loop_vars)
            self.datadic.update(get_ctrl(cont_dic))
        else:
            head_dic = map_head_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            head_dic.update(get_ctrl(self.datadic))
            newlines = write_head(head_dic, with_ctrl=True)
            self.lines += newlines

    def process_cont_line(self, tree):
        if self.rwmode == 'read':
            cont_dic, self.ofs = read_cont(lines, self.ofs)
            map_cont_dic(tree, cont_dic, self.datadic, self.loop_vars)
        else:
            cont_dic = map_cont_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            cont_dic.update(get_ctrl(self.datadic))
            newlines = write_cont(cont_dic, with_ctrl=True)
            self.lines += newlines

    def process_dir_line(self, tree):
        if self.rwmode == 'read':
            dir_dic, self.ofs = read_dir(lines, self.ofs)
            map_dir_dic(tree, dir_dic, self.datadic, self.loop_vars)
        else:
            dir_dic = map_dir_dic(tree, {}, self.datadic, self.loop_vars, inverse=True)
            dir_dic.update(get_ctrl(self.datadic))
            newlines = write_dir(dir_dic, with_ctrl=True)
            self.lines += newlines

    def process_for_loop(self, tree):
        return cycle_for_loop(tree, self.run_instruction, self.datadic, self.loop_vars)

    def run_instruction(self, t):
        if t.data in self.actions:
            print(t.data)
            self.actions[t.data](t)
        else:
            for child in t.children:
                if is_tree(child):
                    self.run_instruction(child)
                else:
                    print(str(child))

    def parse(self, lines, tree):
        self.loop_vars = {}
        self.datadic = {}
        self.rwmode = 'read'
        self.ofs = 0
        self.run_instruction(tree)
        return self.datadic

    def write(self, endf_dic, tree):
        self.loop_vars = {}
        self.lines = []
        self.rwmode = 'write'
        self.ofs = 0
        self.run_instruction(tree)
        return self.lines


# helpful functions

# some test data for development

with open('endf.lark', 'r') as f:
    mygrammar = f.read()

from testdata.endf_spec import endf_spec_mf1_mt451_wtext_wdir as curspec
#from testdata.endf_snippets import endf_cont_mf1_mt451_wtext_wdir as curcont
with open('testdata/mf1_mt451_test.txt', 'r') as f:
    curcont = f.read()

#curspec = "3 + 7 / (-N+2)"
#curspec = '3*(-N/2+5)*2/5-7'

#myparser = Lark(mygrammar, start='code_token')
myparser = Lark(mygrammar, start='code_token')
tree = myparser.parse(curspec)
print(tree.pretty())

lines = curcont.splitlines()

parser = BasicEndfParser()
datadic = parser.parse(lines, tree)
newlines = parser.write(datadic, tree)
print(datadic)
print('\n'.join(newlines))

print(datadic)



