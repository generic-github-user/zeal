import lark
from lark import Lark
from lark.indenter import Indenter

import argparse
import urllib.parse

argparser = argparse.ArgumentParser()
argparser.add_argument('path')
argparser.add_argument('--to')

class TreeIndenter(Indenter):
    NL_type = '_NL'
    OPEN_PAREN_types = []
    CLOSE_PAREN_types = []
    INDENT_type = '_INDENT'
    DEDENT_type = '_DEDENT'
    tab_len = 2

class Token:
    def __init__(self, source, parent=None):
        self.parent = parent
        self.source = source
        for attr in 'type value line column'.split():
            setattr(self, attr, getattr(self.source, attr))
            self.length = len(self.source)

    def markdown(self) -> str: return self.value
    def text(self): return self.value

    def __str__(self):
        return f'Token <{self.type}, {self.line}:{self.column}> {self.value}'

class Node:
    def __init__(self, source, parent=None, depth=0, root=None):
        self.parent = parent
        self.root = root if root else self
        self.children = []
        self.source = source

        self.meta = self.source.meta
        self.type = self.source.data
        self.depth = depth
        for c in self.source.children:
            if isinstance(c, lark.Tree):
                subclass = Node
                match c.data:
                    case 'pair': subclass = Pair
                    case 'multiline': subclass = Multiline
                    case 'info': subclass = Info
                    case 'tree': subclass = Tree
                    case 'command': subclass = Command
                self.children.append(subclass(
                    c, self, self.depth+1, root=self.root if self.root else self))
            elif c is None: self.children.append(c)
            else:
                assert isinstance(c, lark.Token), c
                self.children.append(Token(c))

        items = list(filter(lambda x:
                (x.type == 'pair' and x.text() == 'items') or
                (x.type == 'tree' and x.children and x[0].text() == 'items'), self.children))
        self.items = items[0] if items else None

        info = list(filter(lambda x: x.type == 'pair' and x.key.text() == 'info', self.children))
        self.info = info[0].value if info else None
        
        self.tags = []

    def markdown(self) -> str:
        if self.type in ['word', 'wordlike']: return ''.join(c.markdown() for c in self.children)
        elif self.type == 'text': return ' '.join(c.markdown() for c in self.children)
        else: return '\n'.join(c.markdown() for c in self.children)

    def text(self):
        return ''.join(c.text() for c in self.children)

    def __str__(self):
        return f'{type(self).__name__} <{self.type}> ({self.depth})' + '\n' + '\n'.join('  '*self.depth + str(n) for n in self.children)

    def __getitem__(self, key): return self.children[key]

class Tree(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self, aslist=False) -> str:
        if self.children and self[0].text() in ['items']: return ''
        result = '\n'.join(c.markdown(aslist) for c in self.children)
        if self.info: result += self.info.markdown()
        if self.items: result += '\n'.join(x.markdown(True) for x in self.items[1:]) + '\n'
        if aslist: result = '  '*(self.depth-3) + '- ' + result
        return result

class Info(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self, *args, **kwargs) -> str:
        result = ''
        if 1 < self.depth < 4 and self.parent.type == 'tree':
            result += '#'*(self.depth-1)+' '
            self.tags.append('header')
        result += ''.join(c.markdown() for c in self.children)
        if 'header' in self.tags: result += '\n'
        return result

class Pair(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key, self.value = self.children

    def markdown(self, *args, **kwargs) -> str: return ''

class Multiline(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self, *args, **kwargs) -> str:
        return ' '.join(c.markdown() for c in self.children)

class Command(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            self.symbol, self.content = self.children
        except ValueError as E:
            print(E)
            print(self)

    def markdown(self, *args, **kwargs) -> str:
        result = self.content.markdown()
        if self.symbol.text() == '%':
            result = f'[{result}](https://en.wikipedia.org/wiki/{urllib.parse.quote(result)})'
        return result


with open('grammar.lark', 'r') as grammar:
    parser = Lark(grammar.read(), parser='lalr', lexer='contextual', postlex=TreeIndenter(), debug=True)
    #parser = Lark(grammar.read(), parser='earley', lexer='basic', postlex=TreeIndenter())

def parse(path):
    with open(path, 'r') as f:
        parsed = parser.parse(f.read())
    tree = Node(parsed)
    return tree
    #print(parsed.pretty()[:2000])

# P = parse('test.zl')
# print(P)
# print(P.markdown())

args = argparser.parse_args()
P = parse(args.path)
if args.to in ['md', 'markdown']:
    print(P.markdown())
elif args.to == 'tree':
    print(P)

