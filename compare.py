import os
import tokenize
import token
import ast
import sys


def levenstein(str_1, str_2):
    n, m = len(str_1), len(str_2)
    if n > m:
        str_1, str_2 = str_2, str_1
        n, m = m, n

    current_row = range(n + 1)
    for i in range(1, m + 1):
        previous_row, current_row = current_row, [i] + [0] * n
        for j in range(1, n + 1):
            add, delete, change = previous_row[j] + 1, current_row[j - 1] + 1, previous_row[j - 1]
            if str_1[j - 1] != str_2[i - 1]:
                change += 1
            current_row[j] = min(add, delete, change)
        # print(current_row)  # Uncomment to see matrix of computation
    return current_row[n]


def delete_docstrings(fname):
    source = open(fname, errors="ignore")
    mod = open(fname[:-3] + '_done' + '.py', 'w')

    prev_toktype = token.INDENT
    last_lineno = -1
    last_col = 0

    tokgen = tokenize.generate_tokens(source.readline)
    for toktype, ttext, (slineno, scol), (elineno, ecol), ltext in tokgen:
        if slineno > last_lineno:
            last_col = 0
        if scol > last_col:
            mod.write(" " * (scol - last_col))
        if toktype == token.STRING and prev_toktype == token.INDENT:
            mod.write("pass")
        elif toktype == token.COMMENT:
            mod.write('')
        else:
            mod.write(ttext)
        prev_toktype = toktype
        last_col = ecol
        last_lineno = elineno
    mod.close()


# I couldn't fix syntax errors while parsing the code (even with errors="ignore" parameter) in all these files so
# the tree was not built. I made an exception for them. This is sacrifice of 9.2% of all given files
exceptions = ['base.py', 'bn_inception_simple.py', 'cars196.py', 'classification.py',
              'date_flags.py', 'deepar.py', 'eda_utils.py', 'eval-speed.py', 'generator.py',
              'imputation.py', 'iql.py', 'load-metrics.py', 'mixins.py',
              'optuna_example.py', 'plotters.py', 'rnn.py', 'runner.py', 'sac_n.py',
              'sampler.py', 'statistics.py', 'test_add_constant_transform.py',
              'test_autoarima_model.py', 'test_dirac.py', 'test_predictability.py',
              'test_timeflags_transform.py', 'test_voting_ensemble.py', 'trend.py',
              '_workarounds.py']


def type_check(node):
    if type(node) == ast.Attribute:
        return node.attr
    elif type(node) == ast.Constant:
        return node.value
    elif type(node) == ast.Name:
        return node.id
    elif type(node) == ast.Call:
        return type_check(node.func)
    elif type(node) == ast.Tuple or type(node) == ast.List:
        return [type(x) for x in node.elts]
    elif type(node) == ast.Subscript:
        return f'{type_check(node.value)}[{type_check(node.slice)}]'
    elif type(node) == ast.UnaryOp:
        unary_ops = {ast.USub: '-', ast.UAdd: '+', ast.Not: '!', ast.Invert: '~'}
        return f'{unary_ops[type(node.op)]}{type_check(node.operand)}'


# Bugs:
# 1. When return of function is another function call, Node name not "{name} call with {args}", but only {name}.
# 2. Nested structures in the end returns as None, such as "if ast.BinOp && ast.BinOp" will return "if None && None"


class Node:
    bin_operations = {ast.Eq: '==', ast.Gt: '>', ast.Lt: '<', ast.GtE: '>=', ast.LtE: '<=', ast.NotEq: '!=',
                      ast.And: '&&', ast.Or: '||', ast.Not: 'not', ast.IsNot: 'is not', ast.Add: '+', ast.Div: '/',
                      ast.Mult: '*', ast.Sub: '-', ast.Pow: '**', ast.Is: 'is', ast.In: 'in', ast.NotIn: 'not in',
                      ast.FloorDiv: '//', ast.BitAnd: '&', ast.BitOr: '|'}

    def __init__(self, name, source=None):
        self.name = name
        self.children = []
        if source:
            if type(source) == list:
                fields = source
            else:
                fields = source.body
            for field in fields:
                if type(field) == ast.Import or type(field) == ast.ImportFrom:
                    self.children.append(Node(f'import {field.names[0].name}'))
                elif type(field) == ast.ClassDef:
                    self.children.append(Node(f'class {field.name}', field))
                elif type(field) == ast.FunctionDef:
                    self.children.append(Node(f'func {field.name}', field))
                elif type(field) == ast.If:
                    if type(field.test) == ast.Attribute:
                        self.children.append(Node(f'if {field.test.attr}', field))
                    elif type(field.test) == ast.Compare:
                        operation = f'{type_check(field.test.left)} ' \
                                    f'{self.bin_operations[type(field.test.ops[0])]} ' \
                                    f'{type_check(field.test.comparators[0])}'
                        self.children.append(Node(f'if {operation}', field))
                    elif type(field.test) == ast.BoolOp:
                        operation = f'{type_check(field.test.values[0])} ' \
                                    f'{self.bin_operations[type(field.test.op)]} ' \
                                    f'{type_check(field.test.values[1])}'
                        self.children.append(Node(f'if {operation}', field))
                    elif type(field.test) == ast.Subscript:
                        self.children.append(Node(f'if {type_check(field.test.value)}[{type_check(field.test.slice)}]', field))
                    elif type(field.test) == ast.Call:
                        self.children.append(Node(f'if {type_check(field.test)} call with {[type(x) for x in field.test.args]}', field))
                    if field.orelse:
                        self.children.append(Node('else', field.orelse))
                elif type(field) == ast.For:
                    self.children.append(Node(f"for {type_check(field.target)} in {type_check(field.iter)}", field))
                elif type(field) == ast.Assign:
                    self.children.append(Node(f"{type_check(field.targets[0])} assign"))
                elif type(field) == ast.AugAssign:
                    self.children.append(Node(f"{type_check(field.target)} {self.bin_operations[type(field.op)]}="))
                elif type(field) == ast.Return:
                    self.children.append(Node(f"return {type_check(field.value)}"))
                elif type(field) == ast.Expr:
                    self.children.append(Node('expr', [field.value]))
                elif type(field) == ast.Call:
                    self.children.append(Node(f'{type_check(field.func)} call with {[type(x) for x in field.args]}'))
                elif type(field) == ast.Raise:
                    self.children.append(Node(f'raise {type_check(field.exc)}'))
        self.children_sorted = sorted(self.children, key=lambda x: x.name)


def compare_not_sort(node1: Node, node2: Node, deep=0):
    global cost_not_sort
    global length_not_sort
    # print(' ' * deep, node1.name, ' ' * deep, node2.name)  # Uncomment to see two trees compared
    leva = levenstein(node1.name, node2.name)
    cost_not_sort += leva
    length_not_sort += len(node1.name)
    deep += 4
    for child1, child2 in zip(node1.children, node2.children):
        compare_not_sort(child1, child2, deep)


def compare_sort(node1: Node, node2: Node, deep=0):
    global cost_sort
    global length_sort
    # print(' ' * deep, node1.name, ' ' * deep, node2.name)  # Uncomment to see two trees compared
    leva = levenstein(node1.name, node2.name)
    length_sort += len(node1.name)
    cost_sort += leva
    deep += 4
    for child1, child2 in zip(node1.children_sorted, node2.children_sorted):
        compare_sort(child1, child2, deep)


with open(sys.argv[1], 'r') as f:
    plagiat1 = []
    plagiat2 = []
    for line in f.readlines():
        plagiat1.append(line.split()[0])
        plagiat2.append(line.split()[1])

# In docstrings we have meaningless symbols so we just get rid out of them
# All files will be renamed to {previous_filename}_done.py
for f in range(len(plagiat1)):
    delete_docstrings(plagiat1[f])
    os.remove(plagiat1[f])
    plagiat1[f] = plagiat1[f][:-3] + '_done.py'
for f in range(len(plagiat2)):
    delete_docstrings(plagiat2[f])
    os.remove(plagiat2[f])
    plagiat2[f] = plagiat2[f][:-3] + '_done.py'

for file1, file2 in zip(plagiat1, plagiat2):
    with open(file1, "r") as f:
        tree1 = Node('body', ast.parse(f.read()))
    with open(file2, "r") as f:
        tree2 = Node('body', ast.parse(f.read()))
    cost_sort = 0
    length_sort = 0
    compare_sort(tree1, tree2)
    eval_sort = (length_sort - cost_sort) / length_sort

    cost_not_sort = 0
    length_not_sort = 0
    compare_not_sort(tree1, tree2)
    eval_not_sort = (length_not_sort - cost_not_sort) / length_not_sort
    with open(sys.argv[2], 'a') as f:
        f.write(str(round(0.3 * eval_not_sort + 0.7 * eval_sort, 2)) + '\n')
