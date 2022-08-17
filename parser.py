import lark
from lark import Lark
from lark.indenter import Indenter

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

    def markdown(self): return self.value
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
                self.children.append(subclass(
                    c, self, self.depth+1, root=self.root if self.root else self))
            elif c is None: self.children.append(c)
            else:
                assert isinstance(c, lark.Token), c
                self.children.append(Token(c))

        items = list(filter(lambda x: x.type == 'pair' and x.text() == 'items', self.children))
        self.items = items[0] if items else None
        info = list(filter(lambda x: x.type == 'pair' and x.key.text() == 'info', self.children))
        self.info = info[0].value if info else None

    def markdown(self):
        return '\n'.join(c.markdown() for c in self.children)

    def text(self):
        return ''.join(c.text() for c in self.children)

    def __str__(self):
        return f'{type(self).__name__} <{self.type}> ({self.depth})' + '\n' + '\n'.join('  '*self.depth + str(n) for n in self.children)

class Tree(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self):
        result = '\n'.join(c.markdown() for c in self.children)
        if self.info: result += self.info.markdown()
        if self.items: result += '\n'.join(f'- {x}' for x in self)
        return result

class Info(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self):
        result = ('# ' if self.depth == 2 and self.parent.type == 'tree' else '')\
            + ('## ' if self.depth == 3 and self.parent.type == 'tree' else '')\
            + '\n'.join(c.markdown() for c in self.children)
        return result

class Pair(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key, self.value = self.children

    def markdown(self): return ''

class Multiline(Node):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def markdown(self):
        return ' '.join(c.markdown() for c in self.children)


with open('grammar.lark', 'r') as grammar:
    parser = Lark(grammar.read(), parser='lalr', lexer='contextual', postlex=TreeIndenter(), debug=True)
    #parser = Lark(grammar.read(), parser='earley', lexer='basic', postlex=TreeIndenter())

def parse():
    with open('test.zl', 'r') as f:
        parsed = parser.parse(f.read())
    tree = Node(parsed)
    return tree
    #print(parsed.pretty()[:2000])

P = parse()
print(P)
print(P.markdown())

