import copy
from ast_nodes import *

def rename_conflicting_vars(node):
    used_names = set()
    return _rename_vars(node, used_names)

def _rename_vars(node, used_names):
    if node is None:
        return node, used_names

    if isinstance(node, Quantifier):
        old_name = node.variable.name

        if old_name in used_names:
            counter = 1
            new_name = f"{old_name}_{counter}"
            while new_name in used_names:
                counter += 1
                new_name = f"{old_name}_{counter}"
            node.variable.name = new_name

        new_used = used_names | {node.variable.name}
        node.child, _ = _rename_vars(node.child, new_used)
        return node, used_names

    if isinstance(node, Operation):
        if node.left:
            node.left, _ = _rename_vars(node.left, used_names)
        if node.right:
            node.right, _ = _rename_vars(node.right, used_names)
        return node, used_names

    return node, used_names

def extract_one_quantifier(node):
    if node is None:
        return node, False

    if isinstance(node, Operation) and node.operator == 'implies':
        if node.left and isinstance(node.left, Quantifier):
            q = node.left
            new_inner = Operation('implies', q.child, node.right)
            if q.quantifier == 'forall':
                new_quant = Quantifier('exists', q.variable, new_inner)
            else:
                new_quant = Quantifier('forall', q.variable, new_inner)
            return new_quant, True

        if node.right and isinstance(node.right, Quantifier):
            q = node.right
            new_inner = Operation('implies', node.left, q.child)
            new_quant = Quantifier(q.quantifier, q.variable, new_inner)
            return new_quant, True

    if isinstance(node, Operation):
        if node.left:
            new_left, changed = extract_one_quantifier(node.left)
            if changed:
                node.left = new_left
                return node, True
        if node.right:
            new_right, changed = extract_one_quantifier(node.right)
            if changed:
                node.right = new_right
                return node, True

    elif isinstance(node, Quantifier):
        if node.child:
            new_child, changed = extract_one_quantifier(node.child)
            if changed:
                node.child = new_child
                return node, True

    return node, False


def get_free_vars(node, bound=None):
    if bound is None:
        bound = set()

    if isinstance(node, Variable):
        if node.name not in bound:
            return {node.name}
        return set()

    if isinstance(node, Predicate):
        free = set()
        for arg in node.args:
            if isinstance(arg, Variable) and arg.name not in bound:
                free.add(arg.name)
        return free

    if isinstance(node, Quantifier):
        return get_free_vars(node.child, bound | {node.variable.name})

    if isinstance(node, Operation):
        free = set()
        if node.left:
            free |= get_free_vars(node.left, bound)
        if node.right:
            free |= get_free_vars(node.right, bound)
        return free

    return set()

class Transformer:

    def eliminate_implications(self, node):
        node = copy.deepcopy(node)
        return self._elim(node)

    def _elim(self, node):
        if isinstance(node, Operation):
            node.left = self._elim(node.left)
            if node.right:
                node.right = self._elim(node.right)
            if node.operator == 'implies':
                return Operation('or', Operation('not', node.left), node.right)
        if isinstance(node, Quantifier):
            node.child = self._elim(node.child)
        return node

    def extract_one_quantifier(self, node):
        return extract_one_quantifier(node)

    def to_prenex(self, node):
        node = copy.deepcopy(node)
        node = self.eliminate_implications(node)
        node = self._push_negations(node)
        node = self._pull_quantifiers(node)
        return node

    def _push_negations(self, node):
        if node is None:
            return None

        if isinstance(node, Operation) and node.operator == 'not':
            child = node.left

            if isinstance(child, Operation) and child.operator == 'not':
                return self._push_negations(child.left)

            if isinstance(child, Operation) and child.operator == 'and':
                new_left = self._push_negations(Operation('not', child.left))
                new_right = self._push_negations(Operation('not', child.right))
                return Operation('or', new_left, new_right)

            if isinstance(child, Operation) and child.operator == 'or':
                new_left = self._push_negations(Operation('not', child.left))
                new_right = self._push_negations(Operation('not', child.right))
                return Operation('and', new_left, new_right)

            if isinstance(child, Quantifier) and child.quantifier == 'forall':
                new_body = self._push_negations(Operation('not', child.child))
                return Quantifier('exists', child.variable, new_body)

            if isinstance(child, Quantifier) and child.quantifier == 'exists':
                new_body = self._push_negations(Operation('not', child.child))
                return Quantifier('forall', child.variable, new_body)

            return node

        if isinstance(node, Operation):
            if node.left:
                node.left = self._push_negations(node.left)
            if node.right:
                node.right = self._push_negations(node.right)
            return node

        if isinstance(node, Quantifier):
            node.child = self._push_negations(node.child)
            return node

        return node

    def _pull_quantifiers(self, node):
        if node is None:
            return None

        if isinstance(node, Operation):
            node.left = self._pull_quantifiers(node.left)
            node.right = self._pull_quantifiers(node.right)

        if isinstance(node, Quantifier):
            node.child = self._pull_quantifiers(node.child)
            return node

        if isinstance(node, Operation) and node.operator in ['and', 'or']:
            left = node.left
            right = node.right

            if left and isinstance(left, Quantifier):
                if left.variable.name not in get_free_vars(right):
                    new_inner = Operation(node.operator, left.child, right)
                    return Quantifier(left.quantifier, left.variable, self._pull_quantifiers(new_inner))

            if right and isinstance(right, Quantifier):
                if right.variable.name not in get_free_vars(left):
                    new_inner = Operation(node.operator, left, right.child)
                    return Quantifier(right.quantifier, right.variable, self._pull_quantifiers(new_inner))
        return node