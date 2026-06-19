from graphviz import Digraph
from PIL import Image, ImageTk
import tkinter as tk
import os
from ast_nodes import *

class FormulaVisualizer:

    def __init__(self, canvas):
        self.canvas = canvas
        self.photo = None
        self.path = None

    def visualize(self, formula):
        dot = Digraph(format='png')
        dot.attr(rankdir='TB')
        self._walk(dot, formula, None)
        os.makedirs('generated', exist_ok=True)
        self.path = dot.render(
            'generated/tree',
            format='png',
            cleanup=False
        )
        self.show()

    def show(self):
        if not self.path:
            return
        self.canvas.update_idletasks()
        img = Image.open(self.path)
        width = max(self.canvas.winfo_width(), 100)
        height = max(self.canvas.winfo_height(), 100)
        ratio = min(width / img.width, height / img.height)
        img = img.resize(
            (
                int(img.width * ratio * 0.9),
                int(img.height * ratio * 0.9)
            )
        )

        self.photo = ImageTk.PhotoImage(img)
        self.canvas.delete('all')
        self.canvas.create_image(
            width // 2,
            height // 2,
            image=self.photo,
            anchor=tk.CENTER
        )

    def _walk(self, dot, node, parent):
        if node is None:
            return

        node_id = str(id(node))
        label = self._get_label(node)

        if isinstance(node, Predicate):
            color = '#FFA500'
        elif isinstance(node, Quantifier):
            color = '#2196F3'
        elif isinstance(node, Operation):
            color = '#4CAF50'
        else:
            color = '#9E9E9E'

        dot.node(node_id, label, style='filled', fillcolor=color, fontcolor='white')

        if parent:
            dot.edge(parent, node_id)

        if isinstance(node, Operation):
            self._walk(dot, node.left, node_id)
            self._walk(dot, node.right, node_id)

        elif isinstance(node, Quantifier):
            self._walk(dot, node.child, node_id)

    def _get_label(self, node):

        if isinstance(node, Predicate):
            if node.args:
                args = ','.join(self._get_label(a) for a in node.args)
                return f'{node.name}({args})'
            return node.name

        if isinstance(node, Variable):
            return node.name

        if isinstance(node, Quantifier):
            if node.quantifier == 'forall':
                q = 'forall'
            else:
                q = 'exists'
            var_name = node.variable.name if hasattr(node.variable, 'name') else str(node.variable)
            return f'{q} {var_name}'

        if isinstance(node, Operation):
            op_map = {
                'and': 'AND',
                'or': 'OR',
                'implies': '->',
                'not': 'NOT'
            }
            return op_map.get(node.operator, node.operator)

        return str(node)