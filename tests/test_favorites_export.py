from io import BytesIO
import unittest

from openpyxl import load_workbook
from favorites_export import favorites_workbook


class FavoritesExportTests(unittest.TestCase):
    def test_excel_contains_every_agency_numeric_prices_and_clickable_links(self):
        groups = {'Agência A': [{'titulo': 'Casa Centro', 'preco': 'R$ 2.150,50', 'link': 'https://example.com/casa', 'descricao': '3 quartos'}],
                  'Agência B': [{'titulo': 'Apartamento', 'preco': 'A consultar', 'link': ''}]}
        sheet = load_workbook(BytesIO(favorites_workbook(groups))).active
        self.assertEqual(sheet.title, 'Favoritos')
        self.assertEqual(sheet.max_row, 3)
        self.assertEqual(sheet['A3'].value, 'Agência B')
        self.assertEqual(sheet['C2'].value, 2150.5)
        self.assertIsNone(sheet['C3'].value)
        self.assertEqual(sheet['E2'].hyperlink.target, 'https://example.com/casa')
        self.assertEqual(sheet.freeze_panes, 'A2')
        self.assertEqual(sheet.auto_filter.ref, 'A1:E3')

    def test_scraped_content_is_text_instead_of_an_excel_formula(self):
        sheet = load_workbook(BytesIO(favorites_workbook({'=1+2': [{'titulo': '=HYPERLINK("https://example.com")', 'descricao': 'Olá\x01', 'link': 'javascript:alert(1)'}]}))).active
        self.assertEqual(sheet['A2'].data_type, 's')
        self.assertEqual(sheet['B2'].data_type, 's')
        self.assertEqual(sheet['D2'].value, 'Olá')
        self.assertIsNone(sheet['E2'].hyperlink)
