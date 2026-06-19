from ast_nodes import Variable, Predicate, Operation, Quantifier
from typing import Dict, List, Any, Tuple, Set
import re


class FormulaInterpreter:

    def __init__(self):
        self.domain: List[Any] = []
        self.predicate_values: Dict[Tuple[str, int], Dict[Tuple, bool]] = {}
        self.skolem_functions: Dict[str, callable] = {}

    def set_domain(self, domain: List[Any]):
        self.domain = domain

    def set_predicate(self, name: str, args_count: int, values: Dict[Tuple, bool]):
        self.predicate_values[(name, args_count)] = values

    def set_predicate_from_string(self, name: str, args_names: List[str], value_string: str):
        values = value_string.split(',')
        args_count = len(args_names)
        values_dict = {}

        def parse_bool(val: str) -> bool:
            val = val.strip().lower()
            if val in ('1', 'истина', 'true', 'да', '+'):
                return True
            return False

        if args_count == 1:
            for i, obj in enumerate(self.domain):
                if i < len(values):
                    values_dict[(obj,)] = parse_bool(values[i])
                else:
                    values_dict[(obj,)] = False
        elif args_count == 2:
            idx = 0
            for obj1 in self.domain:
                for obj2 in self.domain:
                    if idx < len(values):
                        values_dict[(obj1, obj2)] = parse_bool(values[idx])
                    else:
                        values_dict[(obj1, obj2)] = False
                    idx += 1
        else:
            from itertools import product
            idx = 0
            for combo in product(self.domain, repeat=args_count):
                if idx < len(values):
                    values_dict[combo] = parse_bool(values[idx])
                else:
                    values_dict[combo] = False
                idx += 1

        self.predicate_values[(name, args_count)] = values_dict

    def set_skolem_function(self, name: str, func: callable):
        self.skolem_functions[name] = func

    def evaluate(self, node, context: Dict[str, Any] = None) -> bool:
        if node is None:
            return True

        if context is None:
            context = {}

        if isinstance(node, Predicate):
            return self._evaluate_predicate(node, context)

        if isinstance(node, Operation):
            return self._evaluate_operation(node, context)

        if isinstance(node, Quantifier):
            return self._evaluate_quantifier(node, context)

        if node.type == "variable":
            return self._evaluate_variable(node, context)

        return True

    def _evaluate_predicate(self, node, context) -> bool:
        args_values = []
        for arg in node.args:
            if arg.type == "variable":
                val = context.get(arg.name, None)
                if val is None:
                    raise ValueError(f"Переменная '{arg.name}' не определена в контексте")
                args_values.append(val)
            else:
                args_values.append(str(arg))

        key = (node.name, len(node.args))
        args_tuple = tuple(args_values)

        if key in self.predicate_values:
            return self.predicate_values[key].get(args_tuple, False)

        return self._evaluate_builtin_predicate(node, args_values, context)

    def _evaluate_builtin_predicate(self, node, args_values, context) -> bool:
        name = node.name

        if len(args_values) != 2:
            return False

        left, right = args_values[0], args_values[1]

        if name == '>':
            return left > right
        if name == '<':
            return left < right
        if name == '=' or name == '==':
            return left == right
        if name == '!=':
            return left != right
        if name == '>=':
            return left >= right
        if name == '<=':
            return left <= right
        if name == '+' or name == 'plus':
            return left + right > 0

        return False

    def _evaluate_operation(self, node, context) -> bool:
        if node.operator == 'not':
            return not self.evaluate(node.left, context)

        if node.operator == 'and':
            return self.evaluate(node.left, context) and self.evaluate(node.right, context)

        if node.operator == 'or':
            return self.evaluate(node.left, context) or self.evaluate(node.right, context)

        if node.operator == 'implies':
            return (not self.evaluate(node.left, context)) or self.evaluate(node.right, context)

        if node.operator == 'iff':
            left_val = self.evaluate(node.left, context)
            right_val = self.evaluate(node.right, context)
            return left_val == right_val

        return True

    def _evaluate_quantifier(self, node, context) -> bool:
        var_name = node.variable.name

        if node.quantifier == 'forall':
            for obj in self.domain:
                new_context = context.copy()
                new_context[var_name] = obj
                if not self.evaluate(node.child, new_context):
                    return False
            return True

        if node.quantifier == 'exists':
            for obj in self.domain:
                new_context = context.copy()
                new_context[var_name] = obj
                if self.evaluate(node.child, new_context):
                    return True
            return False

        return False

    def _evaluate_variable(self, node, context) -> Any:
        if node.name in context:
            return context[node.name]

        return node.name

    def get_free_variables(self, node, bound_vars: Set[str] = None) -> Set[str]:
        if bound_vars is None:
            bound_vars = set()

        if node is None:
            return set()

        if node.type == "variable":
            if node.name not in bound_vars:
                return {node.name}
            return set()

        if isinstance(node, Predicate):
            free = set()
            for arg in node.args:
                if arg.type == "variable" and arg.name not in bound_vars:
                    free.add(arg.name)
            return free

        if isinstance(node, Quantifier):
            new_bound = bound_vars | {node.variable.name}
            return self.get_free_variables(node.child, new_bound)

        if isinstance(node, Operation):
            free = set()
            if node.left:
                free |= self.get_free_variables(node.left, bound_vars)
            if node.right:
                free |= self.get_free_variables(node.right, bound_vars)
            return free

        return set()


class SimpleInterpreter:

    def __init__(self):
        self.domain = []

    def set_domain(self, domain: List[Any]):
        self.domain = domain

    def evaluate(self, formula_str: str) -> bool:
        import re
        formula_str = formula_str.replace(' ', '')
        match = re.match(r'∀([a-z])\(([a-z])>(\d+)\)', formula_str)
        if match:
            var = match.group(1)
            threshold = int(match.group(3))
            for obj in self.domain:
                if not (obj > threshold):
                    return False
            return True

        match = re.match(r'∃([a-z])\(([a-z])>(\d+)\)', formula_str)
        if match:
            threshold = int(match.group(3))
            for obj in self.domain:
                if obj > threshold:
                    return True
            return False

        return False

def collect_predicates(node):
    from ast_nodes import Predicate, Quantifier, Operation

    predicates = []
    if node is None:
        return predicates

    if isinstance(node, Predicate):
        arg_names = []
        for arg in node.args:
            if hasattr(arg, 'name'):
                arg_names.append(arg.name)
            else:
                arg_names.append(str(arg))
        predicates.append({
            'name': node.name,
            'args': arg_names,
            'arity': len(node.args)
        })

    elif isinstance(node, Quantifier):
        predicates.extend(collect_predicates(node.child))

    elif isinstance(node, Operation):
        if hasattr(node, 'left') and node.left:
            predicates.extend(collect_predicates(node.left))
        if hasattr(node, 'right') and node.right:
            predicates.extend(collect_predicates(node.right))

    if hasattr(node, 'child') and node.child:
        predicates.extend(collect_predicates(node.child))

    unique = []
    seen = set()
    for p in predicates:
        key = (p['name'], p['arity'])
        if key not in seen:
            seen.add(key)
            unique.append(p)

    return unique

def format_predicate_values(pred_info, domain):
    name = pred_info['name']
    arity = pred_info['arity']

    if arity == 1:
        labels = [str(obj) for obj in domain]
        return f"{name}(x): {', '.join(labels)}"
    elif arity == 2:
        labels = []
        for obj1 in domain:
            for obj2 in domain:
                labels.append(f"({obj1},{obj2})")
        return f"{name}(x,y): {', '.join(labels)}"
    else:
        return f"{name}: {arity} аргумента(ов)"