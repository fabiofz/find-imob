import ast
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest


class ResultsGridTests(unittest.TestCase):
    def test_every_property_is_rendered_once_across_incomplete_rows(self):
        source = Path('app.py').read_text()
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'renderizar_previews')
        rendered = []
        namespace = {'st': SimpleNamespace(columns=lambda count, **kw: [nullcontext() for _ in range(count)]),
                     'renderizar_cartao': lambda agency, item, *args: rendered.append(item)}
        exec(ast.get_source_segment(source, node), namespace)
        for count in [1, 3, 4, 7, 12]:
            with self.subTest(count=count):
                rendered.clear()
                namespace['renderizar_previews']('Agency', list(range(count)), {}, False, set())
                self.assertEqual(rendered, list(range(count)))
