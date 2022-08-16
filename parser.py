from lark import Lark
from lark.indenter import Indenter

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 2

with open('grammar.lark', 'r') as grammar:
    parser = Lark(grammar.read(), parser='lalr', lexer='contextual', postlex=TreeIndenter(), debug=True)
    #parser = Lark(grammar.read(), parser='earley', lexer='basic', postlex=TreeIndenter())

def parse():
    with open('test.zl', 'r') as f:
        parsed = parser.parse(f.read())
    print(parsed.pretty()[:2000])

parse()

