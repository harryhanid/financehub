from html import escape
import docx
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph


def _run_html(run):
    text = escape(run.text)
    if not text:
        return ""
    if run.bold:
        text = f"<strong>{text}</strong>"
    if run.italic:
        text = f"<em>{text}</em>"
    return text


def _paragraph_html(paragraph):
    rendered = "".join(_run_html(r) for r in paragraph.runs)
    return rendered if rendered else escape(paragraph.text)


def _table_html(table):
    rows_html = []
    for row in table.rows:
        cells_html = "".join(f"<td>{escape(cell.text)}</td>" for cell in row.cells)
        rows_html.append(f"<tr>{cells_html}</tr>")
    return "<table class='sop-table'>" + "".join(rows_html) + "</table>"


def _table_data_rows(table):
    return [[cell.text for cell in row.cells] for row in table.rows[1:]]


def parse_docx(file_path):
    document = docx.Document(file_path)
    title = ""
    sections = []
    current = None
    revisi_rows = []
    pending_list = None  # (tag, [items_html])

    def flush_list():
        nonlocal pending_list
        if pending_list and current is not None:
            tag, items = pending_list
            current["html"] += f"<{tag}>" + "".join(f"<li>{i}</li>" for i in items) + f"</{tag}>"
        pending_list = None

    for child in document.element.body:
        if child.tag == qn("w:p"):
            paragraph = Paragraph(child, document)
            style_name = paragraph.style.name if paragraph.style else ""
            text = paragraph.text.strip()

            if style_name == "Title":
                if not title:
                    title = text
                continue
            if style_name in ("Heading 1", "Heading 2"):
                flush_list()
                current = {
                    "heading": text,
                    "level": 1 if style_name == "Heading 1" else 2,
                    "html": "",
                }
                sections.append(current)
                continue
            if not text:
                continue
            if style_name == "List Bullet":
                if not pending_list or pending_list[0] != "ul":
                    flush_list()
                    pending_list = ("ul", [])
                pending_list[1].append(_paragraph_html(paragraph))
                continue
            if style_name == "List Number":
                if not pending_list or pending_list[0] != "ol":
                    flush_list()
                    pending_list = ("ol", [])
                pending_list[1].append(_paragraph_html(paragraph))
                continue
            flush_list()
            if current is not None:
                current["html"] += f"<p>{_paragraph_html(paragraph)}</p>"
        elif child.tag == qn("w:tbl"):
            flush_list()
            table = Table(child, document)
            headers = [c.text.strip() for c in table.rows[0].cells] if table.rows else []
            if headers[:1] == ["Versi"]:
                revisi_rows = [
                    {"versi": r[0], "tanggal": r[1], "deskripsi": r[2], "oleh": r[3]}
                    for r in _table_data_rows(table)
                ]
            elif current is not None:
                current["html"] += _table_html(table)
    flush_list()

    return {"title": title, "sections": sections, "revisi_rows": revisi_rows}
