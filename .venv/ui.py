import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import json
import shutil
import copy
import re
import os

from parser_engine import LogicParser
from transformations import Transformer
from visualizer import FormulaVisualizer
from database import FormulaDatabase
from ontology import OntologyManager
from ast_nodes import Variable, Predicate, Operation, Quantifier
from interpreter import FormulaInterpreter, collect_predicates

class MainWindow:

    def __init__(self, root):
        self.root = root
        self.root.title('🔬 Трансформатор логических формул')
        self.root.geometry('1400x900')
        self.root.configure(bg='#f5f5f5')

        self.parser = LogicParser()
        self.transformer = Transformer()
        self.db = FormulaDatabase()
        self.ontology = OntologyManager()

        self.current_formula = None
        self.current_formula_links = []

        self.step_formula = None
        self.step_history = []
        self.step_original = None

        self.ontology.load()
        self.db.load()

        self.build_ui()
        self.update_formulas_list()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=10)
        main.pack(fill=tk.BOTH, expand=True)
        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(header, text='🔬 Трансформатор логических формул',
                  font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        toolbar = ttk.Frame(header)
        toolbar.pack(side=tk.RIGHT)

        for txt, cmd in [
            ('🆕 Новый', self.new_analysis),
            ('💾 Сохранить', self.save_project),
            ('📤 Загрузить', self.load_project),
            ('📚 Онтология', self.open_ontology_window),
            ('🔧 Сколемизация', self.skolemize),
            ('📋 LaTeX', self.export_to_latex),
            ('🔄 Сбросить шаги', self.reset_steps),

        ]:
            ttk.Button(toolbar, text=txt, command=cmd, width=12).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🧮 Вычислить", command=self.interpret_formula).pack(side=tk.LEFT, padx=2)

        paned = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(paned)
        paned.add(left, weight=1)

        right = ttk.Frame(paned)
        paned.add(right, weight=2)

        self.build_left_panel(left)
        self.build_formulas_panel(left)
        self.build_right_panel(right)

        self.status_var = tk.StringVar(value='✅ Система готова')
        ttk.Label(main, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W).pack(fill=tk.X, pady=(5, 0))

    def build_left_panel(self, parent):

        frame = ttk.LabelFrame(parent, text='✏️ Ввод и анализ формулы', padding=10)
        frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        sym_frame = ttk.Frame(frame)
        sym_frame.pack(fill=tk.X, pady=(0, 10))

        symbols = [('∀', 'forall'), ('∃', 'exists'), ('→', 'implies'),
                   ('∧', 'and'), ('∨', 'or'), ('¬', 'not'), ('↔', 'iff')]

        for i, (sym, _) in enumerate(symbols):
            btn = ttk.Button(sym_frame, text=sym, width=5,
                             command=lambda s=sym: self.insert_symbol(s))
            btn.grid(row=i // 4, column=i % 4, padx=2, pady=2)

        self.formula_text = scrolledtext.ScrolledText(frame, height=6, font=('Consolas', 12))
        self.formula_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ex_frame = ttk.Frame(frame)
        ex_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(ex_frame, text='Примеры:').pack(side=tk.LEFT)

        for txt, fml in [('∀xP(x)→Q', '∀xP(x)→Q'), ('¬(∀xP(x)→Q)', '¬(∀xP(x)→Q)'), ('P→∀xQ(x)', 'P→∀xQ(x)')]:
            ttk.Button(ex_frame, text=txt, command=lambda f=fml: self.load_example(f)).pack(side=tk.LEFT, padx=2)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill=tk.X)
        ttk.Button(btn_frame, text='🔍 Проанализировать', command=self.analyze).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='🎯 Вынести кванторы', command=self.extract_quantifiers).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text='📊 Предварённая форма', command=self.to_prenex_form).pack(side=tk.LEFT, padx=2)

        info_frame = ttk.LabelFrame(frame, text='📋 Информация о формуле', padding=10)
        info_frame.pack(fill=tk.X, pady=(10, 0))

        row1 = ttk.Frame(info_frame)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text='Имя:').pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row1, width=20)
        self.name_entry.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text='Роль:').pack(side=tk.LEFT)
        self.role_combo = ttk.Combobox(row1, width=15, values=['активатор', 'определение', 'выбор', 'норма', 'условие'])
        self.role_combo.set('активатор')
        self.role_combo.pack(side=tk.LEFT, padx=5)

        ttk.Label(row1, text='Истинность:').pack(side=tk.LEFT)
        self.truth_combo = ttk.Combobox(row1, width=12, values=['истина', 'ложь', 'неопределено'])
        self.truth_combo.set('неопределено')
        self.truth_combo.pack(side=tk.LEFT, padx=5)

        row2 = ttk.Frame(info_frame)
        row2.pack(fill=tk.X, pady=5)
        ttk.Button(row2, text='🔗 Связать с понятием', command=self.link_to_concept_dialog).pack(side=tk.LEFT, padx=5)
        ttk.Button(row2, text='💾 Сохранить формулу', command=self.save_formula).pack(side=tk.LEFT, padx=5)

    def build_formulas_panel(self, parent):

        frame = ttk.LabelFrame(parent, text='📁 База формул', padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ctrl = ttk.Frame(frame)
        ctrl.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(ctrl, text='🔄 Обновить', command=self.update_formulas_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text='📊 Показать все', command=self.show_all_formulas).pack(side=tk.LEFT, padx=2)
        ttk.Button(ctrl, text='🗑️ Очистить базу', command=self.clear_database).pack(side=tk.LEFT, padx=2)
        action_frame = ttk.Frame(frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(action_frame, text='📝 Загрузить', command=self.load_selected_formula).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text='👁️ Просмотреть', command=self.view_selected_formula).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text='🗑️ Удалить', command=self.delete_selected_formula).pack(side=tk.LEFT, padx=2)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.formulas_tree = ttk.Treeview(list_frame, columns=('num', 'formula', 'role', 'truth'),
                                          show='headings', height=10)
        self.formulas_tree.heading('num', text='№')
        self.formulas_tree.heading('formula', text='Формула')
        self.formulas_tree.heading('role', text='Роль')
        self.formulas_tree.heading('truth', text='Истинность')
        self.formulas_tree.column('num', width=50, anchor='center')
        self.formulas_tree.column('formula', width=300)
        self.formulas_tree.column('role', width=100)
        self.formulas_tree.column('truth', width=100)

        vsb = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.formulas_tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.formulas_tree.xview)
        self.formulas_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.formulas_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)

        actions = ttk.Frame(frame)
        actions.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(actions, text='📝 Загрузить', command=self.load_selected_formula).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text='👁️ Просмотреть', command=self.view_selected_formula).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions, text='🗑️ Удалить', command=self.delete_selected_formula).pack(side=tk.LEFT, padx=2)

        self.formulas_tree.bind('<<TreeviewSelect>>', self.on_formula_select)
        self.selected_formula_id = None

    def build_right_panel(self, parent):

        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        viz_frame = ttk.Frame(notebook, padding=10)
        notebook.add(viz_frame, text='🎨 Визуализация')
        viz_controls = ttk.Frame(viz_frame)
        viz_controls.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(viz_controls, text='Обновить визуализацию', command=self.refresh_visualization).pack(side=tk.LEFT)
        ttk.Button(viz_controls, text='Сохранить изображение...', command=self.save_image_as).pack(side=tk.LEFT, padx=5)

        self.viz_canvas = tk.Canvas(viz_frame, bg='white', relief=tk.SUNKEN)
        self.viz_canvas.pack(fill=tk.BOTH, expand=True)
        self.visualizer = FormulaVisualizer(self.viz_canvas)
        self.viz_canvas.bind('<Configure>', lambda e: self.visualizer.show())

        tree_frame = ttk.Frame(notebook, padding=10)
        notebook.add(tree_frame, text='🌳 Синтаксическое дерево')
        self.tree_text = scrolledtext.ScrolledText(tree_frame, font=('Consolas', 10))
        self.tree_text.pack(fill=tk.BOTH, expand=True)

        vars_frame = ttk.Frame(notebook, padding=10)
        notebook.add(vars_frame, text='📊 Анализ переменных')
        self.vars_text = scrolledtext.ScrolledText(vars_frame, font=('Consolas', 10))
        self.vars_text.pack(fill=tk.BOTH, expand=True)

        trans_frame = ttk.Frame(notebook, padding=10)
        notebook.add(trans_frame, text='🔄 Преобразования')
        self.trans_text = scrolledtext.ScrolledText(trans_frame, font=('Consolas', 10))
        self.trans_text.pack(fill=tk.BOTH, expand=True)

        json_frame = ttk.Frame(notebook, padding=10)
        notebook.add(json_frame, text='📋 JSON структура')
        self.json_text = scrolledtext.ScrolledText(json_frame, font=('Consolas', 9))
        self.json_text.pack(fill=tk.BOTH, expand=True)

    def interpret_formula(self):
        """Вычисление истинности формулы на заданной области"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала проанализируйте формулу')
            return

        dialog = tk.Toplevel(self.root)
        dialog.title('🧮 Интерпретация формулы')
        dialog.geometry('650x550')
        dialog.configure(bg='#f0f0f0')
        dialog.resizable(False, False)

        # Основной фрейм
        main_frame = ttk.Frame(dialog, padding="15 10 15 10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        info_frame = ttk.LabelFrame(main_frame, text="📋 Информация о формуле", padding="10 5 10 5")
        info_frame.pack(fill=tk.X, pady=(0, 15))

        role = self.role_combo.get()
        truth = self.truth_combo.get()
        concepts = ', '.join(self.current_formula_links) if self.current_formula_links else '—'

        ttk.Label(info_frame, text=f"📌 Роль: {role}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"🎯 Сохранённая истинность: {truth}").pack(anchor=tk.W)
        ttk.Label(info_frame, text=f"🔗 Связанные понятия: {concepts}").pack(anchor=tk.W)
        # ========== 1. Предметная область ==========
        domain_frame = ttk.LabelFrame(main_frame, text="📌 Предметная область", padding="10 5 10 5")
        domain_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(domain_frame, text="Элементы (через запятую):").pack(anchor=tk.W)
        domain_entry = ttk.Entry(domain_frame, width=50, font=('Consolas', 10))
        domain_entry.pack(fill=tk.X, pady=(5, 0))

        # ========== 2. Предикаты ==========
        pred_frame = ttk.LabelFrame(main_frame, text="🔍 Значения предикатов (1 = истина, 0 = ложь)",
                                    padding="10 5 10 5")
        pred_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        canvas = tk.Canvas(pred_frame, bg='#f0f0f0', highlightthickness=0)
        scrollbar = ttk.Scrollbar(pred_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Собираем предикаты
        predicates = collect_predicates(self.current_formula)
        pred_entries = []

        for pred in predicates:
            frame = ttk.Frame(scrollable_frame)
            frame.pack(fill=tk.X, pady=4)

            name = f"{pred['name']}({', '.join(pred['args'])})"
            ttk.Label(frame, text=name, width=20, font=('Consolas', 10)).pack(side=tk.LEFT)

            entry = ttk.Entry(frame, width=30, font=('Consolas', 10))
            entry.pack(side=tk.LEFT, padx=10)
            pred_entries.append((pred, entry))

            # Размерность
            arity = pred['arity']
            if arity == 1:
                ttk.Label(frame, text="(по одному на элемент)", foreground='gray', font=('Arial', 8)).pack(side=tk.LEFT)
            elif arity == 2:
                ttk.Label(frame, text="(матрица: строки × столбцы)", foreground='gray', font=('Arial', 8)).pack(
                    side=tk.LEFT)

        # ========== 3. Кнопка вычисления ==========
        def evaluate():
            try:
                domain_str = domain_entry.get().strip()
                if not domain_str:
                    messagebox.showerror('Ошибка', 'Введите предметную область')
                    return

                domain = []
                for item in domain_str.split(','):
                    item = item.strip()
                    try:
                        domain.append(int(item))
                    except ValueError:
                        domain.append(item)

                interpreter = FormulaInterpreter()
                interpreter.set_domain(domain)

                for pred, entry in pred_entries:
                    values_str = entry.get().strip()
                    if not values_str:
                        messagebox.showerror('Ошибка', f'Заполните значения для {pred["name"]}')
                        return
                    interpreter.set_predicate_from_string(pred['name'], pred['args'], values_str)

                result = interpreter.evaluate(self.current_formula)

                # Красивый результат
                result_text = "ИСТИНА" if result else "ЛОЖЬ"
                result_color = "#2e7d32" if result else "#c62828"

                messagebox.showinfo(
                    "✅ Результат интерпретации",
                    f"Формула:\n{self._node_to_str(self.current_formula)}\n\n"
                    f"📐 Область: {domain}\n\n"
                    f"🎯 Результат: {result_text}",
                    parent=dialog
                )
                dialog.destroy()

            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="🧮 ВЫЧИСЛИТЬ", command=evaluate, width=20).pack(pady=(5, 0))

        # Центрируем окно
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")

    def insert_symbol(self, sym):
        self.formula_text.insert(tk.INSERT, sym)

    def load_example(self, formula):
        self.formula_text.delete(1.0, tk.END)
        self.formula_text.insert(1.0, formula)
        self.auto_analyze()

    def auto_analyze(self):
        s = self.formula_text.get(1.0, tk.END).strip()
        if not s:
            return
        try:
            self.current_formula = self.parser.parse(s)
            self.step_original = copy.deepcopy(self.current_formula)
            self._update_display()
            self.status_var.set('✅ Формула корректна')
        except Exception as e:
            self.tree_text.delete(1.0, tk.END)
            self.tree_text.insert(tk.END, f'Ошибка: {e}')
            self.status_var.set(f'❌ {str(e)[:50]}')

    def analyze(self):
        self.auto_analyze()

    def _update_display(self):
        if self.current_formula is None:
            return

        self.tree_text.delete(1.0, tk.END)
        self.tree_text.insert(tk.END, '🌳 СИНТАКСИЧЕСКОЕ ДЕРЕВО\n' + '=' * 50 + '\n\n')
        self._print_tree(self.current_formula, 0)

        self._analyze_variables()

        self.json_text.delete(1.0, tk.END)
        try:
            self.json_text.insert(tk.END, json.dumps(self.current_formula, indent=2, default=lambda o: o.__dict__))
        except:
            self.json_text.insert(tk.END, str(self.current_formula))

        self.visualizer.visualize(self.current_formula)

    def _print_tree(self, node, level):
        if node is None:
            return
        indent = '    ' * level
        prefix = '├─ ' if level > 0 else ''
        node_type = type(node).__name__
        self.tree_text.insert(tk.END, f'{indent}{prefix}{node_type}\n')
        if hasattr(node, 'left'):
            self._print_tree(node.left, level + 1)
        if hasattr(node, 'right'):
            self._print_tree(node.right, level + 1)
        if hasattr(node, 'child'):
            self._print_tree(node.child, level + 1)

    def extract_quantifiers(self):
        """Пошаговый вынос кванторов"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала проанализируйте формулу')
            return

        if self.step_formula is None:
            self.step_formula = copy.deepcopy(self.current_formula)
            self.step_formula = self.transformer.rename_conflicting_vars(self.step_formula)
            self.step_history = [self._node_to_str(self.step_formula)]
            self.step_original = copy.deepcopy(self.current_formula)

        new_f, changed = self.transformer.extract_one_quantifier(self.step_formula)

        if not changed:
            self.trans_text.delete(1.0, tk.END)
            self.trans_text.insert(tk.END, '🔄 ПОШАГОВЫЙ ВЫНОС КВАНТОРОВ\n' + '=' * 55 + '\n\n')
            self.trans_text.insert(tk.END, '✅ Все возможные преобразования выполнены.\n')
            self.trans_text.insert(tk.END, f'\n📝 Итог: {self._node_to_str(self.step_formula)}\n')
            self.status_var.set('✅ Готово')
            self.step_formula = None
            self.step_history = []
            self.step_original = None
            return

        self.step_formula = new_f
        self.step_history.append(self._node_to_str(self.step_formula))
        self.current_formula = copy.deepcopy(self.step_formula)

        self.trans_text.delete(1.0, tk.END)
        self.trans_text.insert(tk.END, '🔄 ПОШАГОВЫЙ ВЫНОС КВАНТОРОВ\n' + '=' * 55 + '\n\n')
        self.trans_text.insert(tk.END, '📜 ИСТОРИЯ:\n')
        for i, fs in enumerate(self.step_history, 1):
            prefix = '→ ' if i > 1 else '  '
            self.trans_text.insert(tk.END, f'{i}. {prefix}{fs}\n')

        self._update_display()
        self.status_var.set(f'✅ Шаг {len(self.step_history)}')

    def to_prenex_form(self):
        """Приведение к предварённой нормальной форме"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала проанализируйте формулу')
            return

        try:
            original = self._node_to_str(self.current_formula)
            result = self.transformer.to_prenex(copy.deepcopy(self.current_formula))
            self.current_formula = result
            self._update_display()

            self.trans_text.delete(1.0, tk.END)
            self.trans_text.insert(tk.END, '📊 ПРЕДВАРЁННАЯ НОРМАЛЬНАЯ ФОРМА\n' + '=' * 55 + '\n\n')
            self.trans_text.insert(tk.END, f'📝 Исходная: {original}\n\n')
            self.trans_text.insert(tk.END, f'✨ ПНФ: {self._node_to_str(result)}\n')
            self.status_var.set('✅ Приведено к ПНФ')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def skolemize(self):
        """Сколемизация — удаление ∃-кванторов"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала проанализируйте формулу')
            return

        # Создаём копию и сколемизируем
        self.skolem_counter = 0
        result_node = self._skolemize_recursive(copy.deepcopy(self.current_formula), [])

        # Преобразуем результат в строку для отображения
        result_str = self._node_to_str(result_node)

        self.trans_text.delete(1.0, tk.END)
        self.trans_text.insert(tk.END, '🔧 СКОЛЕМИЗАЦИЯ\n' + '=' * 55 + '\n\n')
        self.trans_text.insert(tk.END, f'📝 Исходная: {self._node_to_str(self.current_formula)}\n\n')
        self.trans_text.insert(tk.END, f'✨ Результат: {result_str}\n')
        self.status_var.set('✅ Сколемизация выполнена')

        # Сохраняем результат (опционально)
        self.current_formula = result_node

    def _skolemize_recursive(self, node, universal_vars):
        """Рекурсивная сколемизация"""
        from ast_nodes import Quantifier, Operation, Predicate, Variable

        if node is None:
            return None

        # Квантор существования
        if isinstance(node, Quantifier) and node.quantifier == 'exists':
            var_name = node.variable.name

            if not universal_vars:
                # Константа
                const_name = f'c_{self.skolem_counter}'
                self.skolem_counter += 1
                # Заменяем переменную на константу в теле
                new_body = self._replace_var(node.child, var_name, Variable(const_name))
                return self._skolemize_recursive(new_body, universal_vars)
            else:
                # Функция от universal_vars
                func_name = f'f_{self.skolem_counter}'
                self.skolem_counter += 1
                # Создаём терм f(z, y, ...)
                func_term = Predicate(func_name, [Variable(v) for v in universal_vars])
                # Заменяем переменную на этот терм в теле
                new_body = self._replace_var(node.child, var_name, func_term)
                return self._skolemize_recursive(new_body, universal_vars)

        # Квантор всеобщности
        if isinstance(node, Quantifier) and node.quantifier == 'forall':
            new_universal_vars = universal_vars + [node.variable.name]
            new_child = self._skolemize_recursive(node.child, new_universal_vars)
            return Quantifier('forall', node.variable, new_child)

        # Операции
        if isinstance(node, Operation):
            new_left = self._skolemize_recursive(node.left, universal_vars)
            new_right = self._skolemize_recursive(node.right, universal_vars)
            return Operation(node.operator, new_left, new_right)

        # Предикат (может содержать термы-функции)
        if isinstance(node, Predicate):
            new_args = []
            for arg in node.args:
                new_args.append(self._skolemize_recursive(arg, universal_vars))
            return Predicate(node.name, new_args)

        # Переменная или константа
        return node

    def _replace_var(self, node, old_var_name, new_term):
        """Заменяет все вхождения переменной old_var_name на new_term"""
        from ast_nodes import Variable, Predicate, Operation, Quantifier

        if node is None:
            return None

        if isinstance(node, Variable):
            if node.name == old_var_name:
                return copy.deepcopy(new_term)
            return node

        if isinstance(node, Predicate):
            new_args = []
            for arg in node.args:
                new_args.append(self._replace_var(arg, old_var_name, new_term))
            return Predicate(node.name, new_args)

        if isinstance(node, Operation):
            new_left = self._replace_var(node.left, old_var_name, new_term)
            new_right = self._replace_var(node.right, old_var_name, new_term)
            return Operation(node.operator, new_left, new_right)

        if isinstance(node, Quantifier):
            # Если квантор связывает ту же переменную — не заменяем внутри
            if node.variable.name == old_var_name:
                return Quantifier(node.quantifier, node.variable,
                                  self._replace_var(node.child, old_var_name, new_term))
            else:
                return Quantifier(node.quantifier, node.variable,
                                  self._replace_var(node.child, old_var_name, new_term))

        return node

    def reset_steps(self):
        """Сбросить пошаговое преобразование к исходной формуле"""
        if self.step_original is not None:
            self.current_formula = copy.deepcopy(self.step_original)
            self.step_formula = None
            self.step_history = []
            self.step_original = None
            self._update_display()
            self.trans_text.delete(1.0, tk.END)
            self.trans_text.insert(tk.END, '🔄 Состояние сброшено\n')
            self.status_var.set('✅ Сброшено')
        else:
            self.status_var.set('Нет активного преобразования')

    def _node_to_str(self, node):
        """Преобразование узла в строку"""
        if node is None:
            return ''
        if isinstance(node, Variable):
            return node.name
        if isinstance(node, Predicate):
            if node.args:
                args = ','.join(self._node_to_str(a) for a in node.args)
                return f'{node.name}({args})'
            return node.name
        if isinstance(node, Quantifier):
            q = '∀' if node.quantifier == 'forall' else '∃'
            return f'{q}{node.variable.name}{self._node_to_str(node.child)}'
        if isinstance(node, Operation):
            if node.operator == 'not':
                return f'¬{self._node_to_str(node.left)}'
            ops = {'and': '∧', 'or': '∨', 'implies': '→'}
            op = ops.get(node.operator, node.operator)
            left = self._node_to_str(node.left) if node.left else ''
            right = self._node_to_str(node.right) if node.right else ''
            return f'({left}{op}{right})'
        return str(node)

    def export_to_latex(self):
        s = self.formula_text.get(1.0, tk.END).strip()
        if not s:
            return
        latex = s.replace('∀', '\\forall ').replace('∃', '\\exists ').replace('→', '\\to ')
        latex = latex.replace('∧', '\\land ').replace('∨', '\\lor ').replace('¬', '\\lnot ')
        latex = f'$${latex}$$'
        self.root.clipboard_clear()
        self.root.clipboard_append(latex)
        messagebox.showinfo('Успех', 'LaTeX код скопирован в буфер обмена')

    def _analyze_variables(self):
        """Анализ свободных и связанных переменных"""
        if self.current_formula is None:
            return

        all_vars = self._get_all_vars(self.current_formula)
        free_vars = self._get_free_vars(self.current_formula)
        bound_vars = self._get_bound_vars(self.current_formula)

        self.vars_text.delete(1.0, tk.END)
        self.vars_text.insert(tk.END, "📊 АНАЛИЗ ПЕРЕМЕННЫХ\n" + "=" * 50 + "\n\n")
        self.vars_text.insert(tk.END, f"Все переменные: {all_vars}\n")
        self.vars_text.insert(tk.END, f"Свободные переменные: {free_vars}\n")
        self.vars_text.insert(tk.END, f"Связанные переменные: {bound_vars}\n")

    def link_to_concept_dialog(self):
        """Диалог связи формулы с понятием"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала создайте формулу')
            return

        dialog = tk.Toplevel(self.root)
        dialog.title('Связать с понятием')
        dialog.geometry('400x300')

        ttk.Label(dialog, text='Выберите понятие:').pack(pady=5)

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for concept in self.ontology.concepts.values():
            listbox.insert(tk.END, concept.name)

        def link():
            sel = listbox.curselection()
            if sel and listbox.get(sel[0]) not in self.current_formula_links:
                self.current_formula_links.append(listbox.get(sel[0]))
                messagebox.showinfo('Успех', f"Связано с понятием '{listbox.get(sel[0])}'")
                dialog.destroy()

        ttk.Button(dialog, text='Связать', command=link).pack(pady=5)

    def _get_all_vars(self, node, bound=None):
        """Получить все переменные"""
        if bound is None:
            bound = set()

        if isinstance(node, Variable):
            return {node.name}
        if isinstance(node, Predicate):
            vars_set = set()
            for arg in node.args:
                if isinstance(arg, Variable):
                    vars_set.add(arg.name)
            return vars_set
        if isinstance(node, Quantifier):
            return self._get_all_vars(node.child, bound | {node.variable.name}) | {node.variable.name}
        if isinstance(node, Operation):
            vars_set = set()
            if node.left:
                vars_set |= self._get_all_vars(node.left, bound)
            if node.right:
                vars_set |= self._get_all_vars(node.right, bound)
            return vars_set
        return set()

    def _get_free_vars(self, node, bound=None):
        """Получить свободные переменные"""
        if bound is None:
            bound = set()

        if isinstance(node, Variable):
            if node.name not in bound:
                return {node.name}
            return set()
        if isinstance(node, Predicate):
            vars_set = set()
            for arg in node.args:
                if isinstance(arg, Variable) and arg.name not in bound:
                    vars_set.add(arg.name)
            return vars_set
        if isinstance(node, Quantifier):
            return self._get_free_vars(node.child, bound | {node.variable.name})
        if isinstance(node, Operation):
            vars_set = set()
            if node.left:
                vars_set |= self._get_free_vars(node.left, bound)
            if node.right:
                vars_set |= self._get_free_vars(node.right, bound)
            return vars_set
        return set()

    def _get_bound_vars(self, node, bound=None):
        """Получить связанные переменные"""
        if bound is None:
            bound = set()

        if isinstance(node, Quantifier):
            new_bound = bound | {node.variable.name}
            return self._get_bound_vars(node.child, new_bound) | {node.variable.name}
        if isinstance(node, Operation):
            vars_set = set()
            if node.left:
                vars_set |= self._get_bound_vars(node.left, bound)
            if node.right:
                vars_set |= self._get_bound_vars(node.right, bound)
            return vars_set
        return set()

    def new_analysis(self):
        self.formula_text.delete(1.0, tk.END)
        self.current_formula = None
        self.tree_text.delete(1.0, tk.END)
        self.vars_text.delete(1.0, tk.END)
        self.trans_text.delete(1.0, tk.END)
        self.json_text.delete(1.0, tk.END)
        self.viz_canvas.delete('all')
        self.status_var.set('✅ Готов к новому анализу')

    def save_project(self):
        """Сохранить проект (базу формул и онтологию)"""
        filename = filedialog.asksaveasfilename(
            defaultextension='.json',
            filetypes=[('JSON файлы', '*.json'), ('Все файлы', '*.*')],
            title='Сохранить проект'
        )
        if filename:
            try:
                project_data = {
                    'formulas': self.db.formulas,
                    'ontology_concepts': {name: {'description': c.description, 'symbols': getattr(c, 'symbols', [])}
                                          for name, c in self.ontology.concepts.items()},
                    'ontology_roles': {rid: {'name': r.name, 'description': r.description}
                                       for rid, r in self.ontology.roles.items()}
                }
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(project_data, f, ensure_ascii=False, indent=2)
                messagebox.showinfo('Успех', f'Проект сохранён в {filename}')
                self.status_var.set(f'✅ Проект сохранён: {os.path.basename(filename)}')
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def load_project(self):
        """Загрузить проект (базу формул и онтологию)"""
        filename = filedialog.askopenfilename(
            filetypes=[('JSON файлы', '*.json'), ('Все файлы', '*.*')],
            title='Загрузить проект'
        )
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    project_data = json.load(f)

                self.db.formulas = project_data.get('formulas', [])
                self.db.save()

                for name, cdata in project_data.get('ontology_concepts', {}).items():
                    if name not in self.ontology.concepts:
                        self.ontology.add_concept(name, cdata.get('description', ''))
                    if 'symbols' in cdata:
                        for sym in cdata['symbols']:
                            self.ontology.add_symbol(name, sym)

                for rid, rdata in project_data.get('ontology_roles', {}).items():
                    # Просто добавляем, если нет
                    if not any(r.name == rdata['name'] for r in self.ontology.roles.values()):
                        self.ontology.add_role(rdata['name'], rdata.get('description', ''))

                self.update_formulas_list()
                messagebox.showinfo('Успех', f'Проект загружен из {filename}')
                self.status_var.set(f'✅ Проект загружен: {os.path.basename(filename)}')
            except Exception as e:
                messagebox.showerror('Ошибка', str(e))

    def save_formula(self):
        """Сохранение формулы в базу"""
        formula_str = self.formula_text.get(1.0, tk.END).strip()
        if not formula_str:
            messagebox.showwarning('Ошибка', 'Нет формулы для сохранения')
            return

        name = self.name_entry.get().strip()
        if not name:
            name = f'Формула_{len(self.db.formulas) + 1}'

        formula_data = {
            'id': str(len(self.db.formulas) + 1),
            'name': name,
            'formula': formula_str,  # ← только строка
            'role': self.role_combo.get(),
            'truth': self.truth_combo.get(),
            'concepts': self.current_formula_links.copy()
        }

        self.db.formulas.append(formula_data)
        self.db.save()
        self.update_formulas_list()
        self.status_var.set(f'✅ Формула "{name}" сохранена')

    def update_formulas_list(self):
        """Обновить список формул в базе"""
        for item in self.formulas_tree.get_children():
            self.formulas_tree.delete(item)

        for i, f in enumerate(self.db.formulas, 1):
            # Берём имя, а не формулу
            name = f.get('name', 'Без имени')
            role = f.get('role', 'активатор')
            truth = f.get('truth', 'неопределено')
            self.formulas_tree.insert('', 'end', iid=str(i), values=(i, name, role, truth))

    def on_formula_select(self, event):
        sel = self.formulas_tree.selection()
        self.selected_formula_id = sel[0] if sel else None

    def load_selected_formula(self):
        """Загрузить выбранную формулу из базы"""
        if not self.selected_formula_id:
            messagebox.showwarning('Ошибка', 'Выберите формулу')
            return

        try:
            idx = int(self.selected_formula_id) - 1
            if idx < 0 or idx >= len(self.db.formulas):
                return

            formula_data = self.db.formulas[idx]

            formula_str = formula_data['formula']
            self.current_formula = self.parser.parse(formula_str)
            self.current_formula_links = formula_data.get('concepts', [])

            self.formula_text.delete(1.0, tk.END)
            self.formula_text.insert(1.0, formula_str)
            self.name_entry.delete(0, tk.END)
            self.name_entry.insert(0, formula_data['name'])
            self.role_combo.set(formula_data.get('role', 'активатор'))
            self.truth_combo.set(formula_data.get('truth', 'неопределено'))

            self._update_display()
            self.status_var.set(f'✅ Загружена формула: {formula_data["name"]}')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def view_selected_formula(self):
        """Просмотреть выбранную формулу"""
        if not self.selected_formula_id:
            messagebox.showwarning('Ошибка', 'Выберите формулу')
            return

        try:
            idx = int(self.selected_formula_id) - 1
            if idx < 0 or idx >= len(self.db.formulas):
                return

            formula_data = self.db.formulas[idx]

            win = tk.Toplevel(self.root)
            win.title(f"Просмотр: {formula_data['name']}")
            win.geometry("600x400")

            text = scrolledtext.ScrolledText(win, font=('Consolas', 10))
            text.pack(fill=tk.BOTH, expand=True)

            text.insert(tk.END, f"Название: {formula_data['name']}\n")
            text.insert(tk.END, f"Формула: {formula_data['formula']}\n")
            text.insert(tk.END, f"Роль: {formula_data.get('role', '—')}\n")
            text.insert(tk.END, f"Истинность: {formula_data.get('truth', '—')}\n")
            text.insert(tk.END, f"Связанные понятия: {', '.join(formula_data.get('concepts', []))}\n")

            text.config(state='disabled')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def delete_selected_formula(self):
        """Удалить выбранную формулу"""
        if not self.selected_formula_id:
            messagebox.showwarning('Ошибка', 'Выберите формулу')
            return

        try:
            idx = int(self.selected_formula_id) - 1
            if idx < 0 or idx >= len(self.db.formulas):
                return

            name = self.db.formulas[idx].get('name', 'без имени')
            if messagebox.askyesno('Подтверждение', f'Удалить формулу "{name}"?'):
                self.db.formulas.pop(idx)
                self.db.save()
                self.update_formulas_list()
                self.selected_formula_id = None
                self.status_var.set(f'✅ Формула "{name}" удалена')
        except Exception as e:
            messagebox.showerror('Ошибка', str(e))

    def show_all_formulas(self):
        if not self.db.formulas:
            messagebox.showinfo('Информация', 'База пуста')
            return
        win = tk.Toplevel(self.root)
        win.title('Все формулы')
        win.geometry('800x500')
        tree = ttk.Treeview(win, columns=('name', 'formula', 'role', 'truth'), show='headings')
        tree.heading('name', text='Название')
        tree.heading('formula', text='Формула')
        tree.heading('role', text='Роль')
        tree.heading('truth', text='Истинность')
        tree.pack(fill=tk.BOTH, expand=True)
        for f in self.db.formulas:
            tree.insert('', 'end', values=(f.get('name', ''), f.get('formula', '')[:80], f.get('role', ''), f.get('truth', '')))

    def clear_database(self):
        """Очистить всю базу формул"""
        if messagebox.askyesno('Подтверждение', 'Очистить всю базу формул?'):
            self.db.formulas.clear()
            self.db.save()
            self.update_formulas_list()
            self.status_var.set('✅ База формул очищена')

    def open_ontology_window(self):
        win = tk.Toplevel(self.root)
        win.title('Онтология')
        win.geometry('600x400')
        txt = scrolledtext.ScrolledText(win, font=('Consolas', 10))
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert(tk.END, 'Понятия:\n')
        for c in self.ontology.concepts.values():
            txt.insert(tk.END, f'  {c.name}\n')
        txt.config(state='disabled')

    def link_to_concept_dialog(self):
        """Диалог связи формулы с понятием"""
        if not self.current_formula:
            messagebox.showwarning('Ошибка', 'Сначала создайте формулу')
            return

        dialog = tk.Toplevel(self.root)
        dialog.title('Связать с понятием')
        dialog.geometry('400x300')

        ttk.Label(dialog, text='Выберите понятие:').pack(pady=5)

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        for concept in self.ontology.get_concepts():
            listbox.insert(tk.END, concept.name)

        if self.current_formula_links:
            ttk.Label(dialog, text=f"Текущие связи: {', '.join(self.current_formula_links)}").pack(pady=5)

        def link():
            sel = listbox.curselection()
            if sel and listbox.get(sel[0]) not in self.current_formula_links:
                self.current_formula_links.append(listbox.get(sel[0]))
                messagebox.showinfo('Успех', f"Связано с понятием '{listbox.get(sel[0])}'")
                dialog.destroy()
            elif sel:
                messagebox.showinfo('Информация', f"Формула уже связана с понятием '{listbox.get(sel[0])}'")

        ttk.Button(dialog, text='Связать', command=link).pack(pady=5)

    def refresh_visualization(self):
        if self.current_formula:
            self.visualizer.visualize(self.current_formula)

    def save_image_as(self):
        if hasattr(self.visualizer, 'path') and self.visualizer.path:
            from tkinter import filedialog
            import shutil
            f = filedialog.asksaveasfilename(defaultextension='.png', filetypes=[('PNG', '*.png')])
            if f:
                shutil.copy2(self.visualizer.path, f)
                messagebox.showinfo('Успех', f'Сохранено в {f}')