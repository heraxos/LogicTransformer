from dataclasses import dataclass, field
from typing import List, Optional
import uuid


def uid():
    return str(uuid.uuid4())[:8]


@dataclass
class Variable:
    def __init__(self, name):
        self.type = 'variable'  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        self.name = name


@dataclass
class Function:
    name: str
    args: list
    id: str = field(default_factory=uid)

    def __post_init__(self):
        self.type = 'function'  # ← ДОБАВИТЬ ЭТУ СТРОКУ

@dataclass
class Predicate:
    def __init__(self, name, args):
        self.type = 'predicate'  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        self.name = name
        self.args = args

@dataclass
class Operation:
    def __init__(self, operator, left, right=None):
        self.type = 'operation'  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        self.operator = operator
        self.left = left
        self.right = right


@dataclass
class Quantifier:
    def __init__(self, quantifier, variable, child):
        self.type = 'quantifier'  # ← ДОБАВИТЬ ЭТУ СТРОКУ
        self.quantifier = quantifier
        self.variable = variable
        self.child = child