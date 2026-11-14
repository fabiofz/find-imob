"""Generate an Excel workbook from the favourites already selected by the UI."""
from io import BytesIO
from urllib.parse import urlparse

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Alignment, Font, PatternFill

from utils.funcs import preco_para_float


def favorites_workbook(groups):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Favoritos'
    sheet.append(['Imobiliária', 'Imóvel', 'Aluguel (R$)', 'Descrição', 'Link do imóvel'])
    for agency, properties in groups.items():
        for property in properties:
            row = [
                agency, property.get('preview_titulo') or property.get('titulo') or '',
                preco_para_float(str(property.get('preco') or '')),
                property.get('descricao') or '', property.get('link') or '',
            ]
            row = [ILLEGAL_CHARACTERS_RE.sub('', str(value or ''))[:32767]
                   if index != 2 else value for index, value in enumerate(row)]
            sheet.append(row)
            for cell in sheet[sheet.max_row]:
                if cell.column != 3:
                    # Scraped content must remain text, including leading '='.
                    cell.value = ILLEGAL_CHARACTERS_RE.sub('', str(cell.value or ''))[:32767]
                    cell.data_type = 's'
                cell.alignment = Alignment(vertical='top', wrap_text=True)
            price = sheet.cell(sheet.max_row, 3)
            price.number_format = '"R$" #,##0.00'
            link = sheet.cell(sheet.max_row, 5)
            try:
                parsed = urlparse(link.value)
                if parsed.scheme in {'https', 'http'} and parsed.hostname:
                    link.hyperlink = link.value
                    link.font = Font(color='207B4C', underline='single')
            except ValueError:
                pass
    for cell in sheet[1]:
        cell.fill = PatternFill('solid', fgColor='207B4C')
        cell.font = Font(color='FFFFFF', bold=True)
        cell.alignment = Alignment(vertical='center')
    for column, width in {'A': 28, 'B': 55, 'C': 18, 'D': 65, 'E': 60}.items():
        sheet.column_dimensions[column].width = width
    sheet.row_dimensions[1].height = 26
    sheet.freeze_panes = 'A2'
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    output = BytesIO()
    workbook.save(output)
    return output.getvalue()
