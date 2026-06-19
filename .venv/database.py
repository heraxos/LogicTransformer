import json
import os
from ontology import OntologyManager

class FormulaDatabase:

    def __init__(self):

        self.path = 'data/formulas.json'
        self.ontology = OntologyManager()
        self.formulas = []
        os.makedirs('data', exist_ok=True)
        self.load()

    def load(self):

        if not os.path.exists(self.path):
            self.formulas = []
            return

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.formulas = data.get('formulas', [])
        except (json.JSONDecodeError, FileNotFoundError):
            self.formulas = []
            self.save()

    def save(self):

        data = {
            'formulas': self.formulas
        }

        with open(self.path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)