from sly import Lexer, Parser

class TruthTableLexer(Lexer):
    tokens = {
        NOT,
        AND,
        OR,
        CONDITIONAL,
        BICONDITIONAL,
        LESS,
        GREATER,
        LESS_EQ,
        GREATER_EQ,
        XOR,
        NOT_EQ,
        LEFT_PAR,
        RIGHT_PAR,
        IDENTIFIER
    }

    ignore = ' '
    
    LEFT_PAR = r'(\(|\[|\{)'
    RIGHT_PAR = r'(\)|\]|\})'
    NOT = r'(~|!|not)'
    OR = r'(\∨|V|or|\|)'
    AND = r'(\⋀|A|and|\&)'
    CONDITIONAL = r'(→|->)'
    LESS_EQ = r'<='
    GREATER_EQ = r'>='
    NOT_EQ = r'!='
    LESS = r'<'
    GREATER = r'>'
    BICONDITIONAL = r'(↔|<->|=)'
    XOR = r'(⊕|\^|xor)'
    IDENTIFIER = r'[a-zA-Z_][a-zA-Z0-9_]*'

#class TruthTableParser(Parser):
#    tokens = TruthTableLexer.tokens

#    precedence = (
#        ('left', AND, OR)
#    )
