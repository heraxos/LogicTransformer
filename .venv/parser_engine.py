import re
from ast_nodes import *

class LogicParser:

    def parse(self, text: str):

        text = text.replace(' ', '')

        return self._parse_formula(text)

    def _parse_formula(self, s):

        s = self._strip_outer(s)

        idx = self._main_operator(s, '→')
        if idx != -1:
            return Operation(
                'implies',
                self._parse_formula(s[:idx]),
                self._parse_formula(s[idx + 1:])
            )

        idx = self._main_operator(s, '∨')
        if idx != -1:
            return Operation(
                'or',
                self._parse_formula(s[:idx]),
                self._parse_formula(s[idx + 1:])
            )

        idx = self._main_operator(s, '∧')
        if idx != -1:
            return Operation(
                'and',
                self._parse_formula(s[:idx]),
                self._parse_formula(s[idx + 1:])
            )

        if s.startswith('¬'):
            return Operation('not', self._parse_formula(s[1:]))

        if s.startswith('∀'):
            var = Variable(s[1])
            return Quantifier('forall', var, self._parse_formula(s[2:]))

        if s.startswith('∃'):
            var = Variable(s[1])
            return Quantifier('exists', var, self._parse_formula(s[2:]))

        pred = re.match(r'([A-Z][A-Za-z0-9_]*)\((.*)\)', s)
        if pred:
            name = pred.group(1)
            args = pred.group(2)
            parsed_args = []
            for a in self._split_args(args):
                parsed_args.append(self._parse_formula(a))
            return Predicate(name, parsed_args)

        if len(s) == 1 and s.islower():
            return Variable(s)

        if len(s) == 1 and s.isupper():
            return Predicate(s, [])

        raise ValueError(f'Ошибка парсинга: {s}')

    def _split_args(self, s):

        args = []
        cur = ''
        depth = 0

        for ch in s:

            if ch == ',' and depth == 0:
                args.append(cur)
                cur = ''
                continue

            if ch == '(':
                depth += 1

            if ch == ')':
                depth -= 1

            cur += ch

        if cur:
            args.append(cur)
        return args

    def _strip_outer(self, s):

        if not (s.startswith('(') and s.endswith(')')):
            return s

        depth = 0

        for i, ch in enumerate(s):

            if ch == '(':
                depth += 1

            elif ch == ')':
                depth -= 1

            if depth == 0 and i < len(s) - 1:
                return s

        return s[1:-1]

    def _main_operator(self, s, op):

        depth = 0

        for i in range(len(s) - 1, -1, -1):

            if s[i] == ')':
                depth += 1

            elif s[i] == '(':
                depth -= 1

            elif depth == 0 and s[i] == op:
                return i
        return -1