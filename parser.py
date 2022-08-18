import lark
from lark import Lark
from lark.indenter import Indenter

import argparse
import urllib.parse

argparser = argparse.ArgumentParser()
argparser.add_argument('path', help='Input file for the zeal processor; can be relative or absolute but should generally end with .zl')
argparser.add_argument('--to', help='Output format; one of md/markdown, tree')

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

    def matches(self, p):
        if isinstance(p, type): return isinstance(self, p)
        elif callable(p): return p(self)

    def __str__(self):
        return f'Token <{self.type}, {self.line}:{self.column}> {self.value}'

class Node:
    def __init__(self, source=None, parent=None, children=None, depth=0, root=None):
        self.parent = parent
        self.children = children
        self.root = root if root else self
        self.children = []
        self.source = source
        self.head = self.children[0] if self.children else None

        if self.source:
            self.meta = self.source.meta
            self.type = self.source.data
        else:
            self.meta = None
            self.type = 'synthetic'

        self.depth = depth
        if self.source:
            for c in self.source.children:
                if isinstance(c, lark.Tree):
                    subclass = Node
                    types = [Pair, Multiline, Info, Tree, Command, Keyword]
                    names = list(map(lambda t: t.__name__.lower(), types))
                    #print(names)
                    if c.data in names: subclass = types[names.index(c.data)]
                    self.children.append(subclass(
                        source=c, parent=self,
                        depth=self.depth+1,
                        root=self.root if self.root else self))
                elif c is None: self.children.append(c)
                else:
                    assert isinstance(c, lark.Token), c
                    self.children.append(Token(c))

            for n in self.filter(Pair, Tree).filter(lambda x: x.head):
                attr = n.head.text()
                if not hasattr(self, attr):
                    setattr(self, attr, n)

        self.tags = []

    #def pair_attr():

    def matches(self, p):
        if isinstance(p, type): return isinstance(self, p)
        #elif callable(p): return p(self)

    def filter(self, *p):
        return Node(children=list(filter(
            lambda x: any(x.matches(y) for y in p), self.children)))

    def markdown(self, *args, **kwargs) -> str:
        if self.type in ['word', 'wordlike', 'quote', 'url']: return ''.join(c.markdown() for c in self.children)
        elif self.type == 'text': return ' '.join(c.markdown() for c in self.children)
        else: return '\n'.join(c.markdown() for c in self.children)

    def text(self):
        return ''.join(c.text() for c in self.children)

    def __str__(self):
        return f'{type(self).__name__} <{self.type}> ({self.depth})' + \
            '\n' + '\n'.join('  '*self.depth + str(n) for n in self.children)

    def __getitem__(self, key): return self.children[key]
    def __getattr__(self, name): return None

class Keyword(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def canonical(self): return '`'+self.text()+'`'
    def source(self): pass

class Tree(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self, aslist=False, **kwargs) -> str:
        if self.children and self[0].text() in ['items']: return ''
        result = ''.join(c.markdown(aslist) for c in self.children)
        if self.info: result += self.info.markdown()
        if self.items: result += ''.join(x.markdown(True) for x in self.items[1:]) + '\n'
        if aslist: result = '  '*(self.depth-3) + '- ' + result
        return result+('\n' if not aslist else '')

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


# Generate a new Node subclass with specified attributes and methods
def NodeType(name: str, *properties, **methods):
    class NewType(Node):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            for i, p in enumerate(properties):
                setattr(self, p, self[i])
    NewType.__name__ = name
    for n, m in methods.items(): setattr(NewType, n, m)
    return NewType


def command_markdown(self, *args, **kwargs) -> str:
    result = self.content.markdown()
    #print("Processing command")
    if self.symbol.text() == '%':
        result = f'[{result}](https://en.wikipedia.org/wiki/{urllib.parse.quote(result)})'
    return result
Command = NodeType('Command', 'symbol', 'content', markdown=command_markdown)

def m_markdown(self, *args, **kwargs):
    return ' '.join(c.markdown() for c in self.children)
Multiline = NodeType('Multiline', markdown=m_markdown)

def pair_markdown(self, *args, **kwargs) -> str:
    if self.key.text() in ['info', 'format', 'filters', 'repo', 'keywords']:
        return ''
    if self.parent.parent.format:
        r = self.parent.parent.format.text()
        for a in ['key', 'value']:
            r = r.replace('.' + a, getattr(self, a).markdown())
        return r + '\n'
    return f'{self.key.markdown()}: {self.value.markdown()}\n'
Pair = NodeType('Pair', 'key', 'value', markdown=pair_markdown)


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

