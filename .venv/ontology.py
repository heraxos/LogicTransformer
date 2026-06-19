from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json
import os

@dataclass
class Concept:
    name: str
    description: str = ""
    formulas: List[str] = field(default_factory=list)

@dataclass
class Role:
    name: str
    description: str = ""
    formulas: List[str] = field(default_factory=list)

class OntologyManager:
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.roles: Dict[str, Role] = {}
        self.formulas = []
        self._init_default()

    def _init_default(self):
        """Инициализация понятий и ролей по умолчанию"""
        # Понятия
        self.add_concept("число", "Математическое число")
        self.add_concept("множество", "Набор элементов")
        self.add_concept("элемент", "Элемент множества")
        self.add_concept("истинность", "Логическое значение")

        if "число" in self.concepts:
            for sym in ["x", "y", "z", "n", "m"]:
                self.add_symbol("число", sym)
        if "множество" in self.concepts:
            for sym in ["A", "B", "C"]:
                self.add_symbol("множество", sym)
        if "элемент" in self.concepts:
            for sym in ["a", "b", "c"]:
                self.add_symbol("элемент", sym)
        if "истинность" in self.concepts:
            for sym in ["P", "Q", "R"]:
                self.add_symbol("истинность", sym)

        self.add_role("активатор", "Активирует задачу при выполнении условия")
        self.add_role("определение", "Определяет понятие")
        self.add_role("выбор", "Выбирает метод решения")
        self.add_role("норма", "Нормативный показатель")
        self.add_role("условие", "Логическое условие")

    def add_concept(self, name, description=""):
        if name not in self.concepts:
            self.concepts[name] = Concept(name, description)

    def remove_concept(self, name):
        if name in self.concepts:
            del self.concepts[name]

    def add_symbol(self, concept_name, symbol):
        if concept_name in self.concepts:
            if not hasattr(self.concepts[concept_name], 'symbols'):
                self.concepts[concept_name].symbols = []
            if symbol not in self.concepts[concept_name].symbols:
                self.concepts[concept_name].symbols.append(symbol)

    def add_role(self, name, description=""):
        role_id = str(len(self.roles))
        self.roles[role_id] = Role(name, description)

    def get_roles(self):
        return list(self.roles.values())

    def get_concepts(self):
        return list(self.concepts.values())

    def find_concept_by_symbol(self, symbol):
        for concept in self.concepts.values():
            if hasattr(concept, 'symbols') and symbol in concept.symbols:
                return concept.name
        return None

    def save(self, filename="ontology.json"):
        data = {
            "concepts": {
                name: {
                    "description": c.description,
                    "symbols": getattr(c, 'symbols', []),
                    "formulas": c.formulas
                }
                for name, c in self.concepts.items()
            },
            "roles": {
                rid: {
                    "name": r.name,
                    "description": r.description,
                    "formulas": r.formulas
                }
                for rid, r in self.roles.items()
            }
        }
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def load(self, filename="ontology.json"):
        if not os.path.exists(filename):
            self._init_default()
            return
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.concepts.clear()
            self.roles.clear()
            for name, cdata in data.get("concepts", {}).items():
                concept = Concept(name, cdata.get("description", ""))
                concept.symbols = cdata.get("symbols", [])
                concept.formulas = cdata.get("formulas", [])
                self.concepts[name] = concept
            for rid, rdata in data.get("roles", {}).items():
                self.roles[rid] = Role(rdata.get("name", ""), rdata.get("description", ""))
        except:
            self._init_default()