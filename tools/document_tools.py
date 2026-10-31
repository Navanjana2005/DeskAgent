"""
tools/document_tools.py
Document reading and writing tools: PDF, Word (DOCX), Excel.

Required packages: pip install pdfplumber PyPDF2 python-docx openpyxl
"""

import os
from langchain_core.tools import tool

import re
from datetime import datetime

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable, ListFlowable, ListItem
    )
    from reportlab.pdfgen import canvas as pdf_canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False

try:
    from PyPDF2 import PdfReader, PdfWriter
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from docx import Document as DocxDocument
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False


# ─────────────────────────────────────────────────────────────────────────────
# PDF TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def read_pdf(file_path: str, max_pages: int = 10) -> str:
    """Extracts and returns the text content from a PDF file.

    Args:
        file_path: Path to the PDF file.
        max_pages: Maximum number of pages to read (default 10).
    """
    if not HAS_PDFPLUMBER:
        return "❌ pdfplumber not installed. Run: pip install pdfplumber"
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
            pages_to_read = min(max_pages, total_pages)
            text_parts = []
            for i, page in enumerate(pdf.pages[:pages_to_read]):
                text = page.extract_text() or ""
                if text.strip():
                    text_parts.append(f"--- Page {i + 1} ---\n{text.strip()}")
        if not text_parts:
            return "⚠️  No extractable text found in the PDF (may be scanned/image-based)."
        header = f"📄 {os.path.basename(file_path)} | {total_pages} pages (showing {pages_to_read})\n{'─' * 50}\n"
        return header + "\n\n".join(text_parts)
    except Exception as e:
        return f"❌ Error reading PDF: {e}"


@tool
def merge_pdfs(input_paths: str, output_path: str) -> str:
    """Merges multiple PDF files into a single PDF.

    Args:
        input_paths: Comma-separated paths to PDF files to merge (in order).
        output_path: Path to save the merged PDF.
    """
    if not HAS_PYPDF2:
        return "❌ PyPDF2 not installed. Run: pip install PyPDF2"
    try:
        paths = [p.strip() for p in input_paths.split(",")]
        writer = PdfWriter()
        total_pages = 0
        for path in paths:
            if not os.path.exists(path):
                return f"❌ File not found: {path}"
            reader = PdfReader(path)
            for page in reader.pages:
                writer.add_page(page)
                total_pages += 1
        with open(output_path, "wb") as f:
            writer.write(f)
        size_kb = os.path.getsize(output_path) / 1024
        return (
            f"✅ PDFs merged successfully!\n"
            f"Files merged: {len(paths)}\n"
            f"Total pages:  {total_pages}\n"
            f"Output:       {output_path} ({size_kb:.1f} KB)"
        )
    except Exception as e:
        return f"❌ Error merging PDFs: {e}"


@tool
def split_pdf(input_path: str, output_folder: str = "", pages_per_file: int = 1) -> str:
    """Splits a PDF into multiple files by page or page groups.

    Args:
        input_path: Path to the source PDF file.
        output_folder: Folder to save split files (defaults to same folder as input).
        pages_per_file: Number of pages per output file (default 1 = one file per page).
    """
    if not HAS_PYPDF2:
        return "❌ PyPDF2 not installed. Run: pip install PyPDF2"
    try:
        if not os.path.exists(input_path):
            return f"❌ File not found: {input_path}"
        if not output_folder:
            output_folder = os.path.dirname(os.path.abspath(input_path))
        os.makedirs(output_folder, exist_ok=True)

        reader = PdfReader(input_path)
        total = len(reader.pages)
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        files_created = []

        for start in range(0, total, pages_per_file):
            end = min(start + pages_per_file, total)
            writer = PdfWriter()
            for i in range(start, end):
                writer.add_page(reader.pages[i])
            suffix = f"_{start + 1}-{end}" if pages_per_file > 1 else f"_page{start + 1}"
            out_path = os.path.join(output_folder, f"{base_name}{suffix}.pdf")
            with open(out_path, "wb") as f:
                writer.write(f)
            files_created.append(out_path)

        return (
            f"✅ PDF split into {len(files_created)} file(s)\n"
            f"Total pages: {total}\n"
            f"Output folder: {output_folder}\n"
            f"Files: {', '.join(os.path.basename(f) for f in files_created[:10])}"
        )
    except Exception as e:
        return f"❌ Error splitting PDF: {e}"


@tool
def text_to_pdf(text: str, output_path: str, title: str = "Document") -> str:
    """Converts plain text to a formatted PDF document.

    Args:
        text: Text content to write to the PDF.
        output_path: Path to save the PDF file.
        title: Document title shown at the top (default 'Document').
    """
    if not HAS_FPDF:
        return "❌ fpdf2 not installed. Run: pip install fpdf2"
    try:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 12, title, ln=True, align="C")
        pdf.ln(4)
        pdf.set_font("Helvetica", size=11)
        pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
        pdf.ln(4)

        pdf.set_font("Helvetica", size=10)
        for line in text.splitlines():
            safe_line = line.encode("latin-1", errors="replace").decode("latin-1")
            pdf.multi_cell(0, 6, safe_line)

        pdf.output(output_path)
        size_kb = os.path.getsize(output_path) / 1024
        return (
            f"✅ PDF created!\n"
            f"Title:  {title}\n"
            f"Lines:  {len(text.splitlines())}\n"
            f"Output: {output_path} ({size_kb:.1f} KB)"
        )
    except Exception as e:
        return f"❌ Error creating PDF: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# WORD DOCUMENT TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def read_docx(file_path: str) -> str:
    """Extracts and returns the text content from a Microsoft Word (.docx) file.

    Args:
        file_path: Path to the .docx file.
    """
    if not HAS_DOCX:
        return "❌ python-docx not installed. Run: pip install python-docx"
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        doc = DocxDocument(file_path)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        if not paragraphs:
            return "⚠️  Document appears to be empty."
        header = f"📝 {os.path.basename(file_path)} | {len(paragraphs)} paragraphs\n{'─' * 50}\n"
        return header + "\n".join(paragraphs[:200])
    except Exception as e:
        return f"❌ Error reading DOCX: {e}"


@tool
def create_docx(file_path: str, title: str, content: str) -> str:
    """Creates a simple Word document (.docx) with a title and content.

    Args:
        file_path: Output path for the .docx file.
        title: Document title (will be formatted as Heading 1).
        content: Body content (use newlines to separate paragraphs).
    """
    if not HAS_DOCX:
        return "❌ python-docx not installed. Run: pip install python-docx"
    try:
        doc = DocxDocument()
        doc.add_heading(title, level=1)
        for paragraph in content.split("\n"):
            if paragraph.strip():
                doc.add_paragraph(paragraph.strip())
        doc.save(file_path)
        size_kb = os.path.getsize(file_path) / 1024
        return f"✅ Word document created: {file_path} ({size_kb:.1f} KB)"
    except Exception as e:
        return f"❌ Error creating DOCX: {e}"


# ── Theme ────────────────────────────────────────────────────────────
if HAS_REPORTLAB:
    ACCENT = colors.HexColor("#2E5EAA")
    TEXT_DARK = colors.HexColor("#1A1A1A")
    TEXT_GRAY = colors.HexColor("#5A5A5A")

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="DocTitle", fontName="Helvetica-Bold", fontSize=26,
        textColor=ACCENT, alignment=TA_CENTER, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="DocSubtitle", fontName="Helvetica", fontSize=11,
        textColor=TEXT_GRAY, alignment=TA_CENTER, spaceAfter=24,
    ))
    styles.add(ParagraphStyle(
        name="H1", fontName="Helvetica-Bold", fontSize=17,
        textColor=ACCENT, spaceBefore=18, spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        name="H2", fontName="Helvetica-Bold", fontSize=13,
        textColor=TEXT_DARK, spaceBefore=12, spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        name="Body", fontName="Helvetica", fontSize=10.5,
        textColor=TEXT_DARK, leading=16, spaceAfter=8, alignment=TA_LEFT,
    ))
    styles.add(ParagraphStyle(
        name="DocBullet", fontName="Helvetica", fontSize=10.5,
        textColor=TEXT_DARK, leading=15,
    ))


def _add_page_number(canv, doc):
    canv.saveState()
    canv.setFont("Helvetica", 8)
    canv.setFillColor(TEXT_GRAY)
    canv.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canv.drawString(2 * cm, 1.2 * cm, datetime.now().strftime("%Y-%m-%d"))
    canv.restoreState()


def _parse_markdown_lite(text: str, story: list):
    """Converts simple markdown (#, ##, -, **bold**) into Platypus flowables."""
    bullet_buffer = []

    def flush_bullets():
        if bullet_buffer:
            items = [ListItem(Paragraph(b, styles["DocBullet"]), leftIndent=12) for b in bullet_buffer]
            story.append(ListFlowable(items, bulletType="bullet", start="•", leftIndent=18))
            story.append(Spacer(1, 8))
            bullet_buffer.clear()

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush_bullets()
            continue

        # bold: **text** -> <b>text</b>
        line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)

        if line.startswith("## "):
            flush_bullets()
            story.append(Paragraph(line[3:], styles["H2"]))
        elif line.startswith("# "):
            flush_bullets()
            story.append(Paragraph(line[2:], styles["H1"]))
        elif line.startswith("- ") or line.startswith("* "):
            bullet_buffer.append(line[2:])
        else:
            flush_bullets()
            story.append(Paragraph(line, styles["Body"]))

    flush_bullets()


@tool
def create_styled_pdf(file_path: str, title: str, content: str, subtitle: str = "") -> str:
    """
    Creates a modern, styled PDF document with headings, bullet points, and bold text.

    Content supports lightweight markdown:
    - '# Heading' for a main section heading
    - '## Subheading' for a sub-section
    - '- item' or '* item' for bullet points
    - '**bold text**' for bold
    Plain lines become normal paragraphs.

    Args:
        file_path: Output path for the .pdf file.
        title: Document title shown on the first page.
        content: Body content using the markdown syntax described above.
        subtitle: Optional subtitle/description shown under the title.
    """
    if not HAS_REPORTLAB:
        return "❌ reportlab not installed. Run: pip install reportlab"
    try:
        doc = SimpleDocTemplate(
            file_path, pagesize=A4,
            topMargin=2.5 * cm, bottomMargin=2.5 * cm,
            leftMargin=2 * cm, rightMargin=2 * cm,
        )

        story = []
        story.append(Paragraph(title, styles["DocTitle"]))
        if subtitle:
            story.append(Paragraph(subtitle, styles["DocSubtitle"]))
        story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceAfter=18))

        _parse_markdown_lite(content, story)

        doc.build(story, onFirstPage=_add_page_number, onLaterPages=_add_page_number)

        size_kb = os.path.getsize(file_path) / 1024
        return f"✅ Styled PDF created: {file_path} ({size_kb:.1f} KB)"
    except Exception as e:
        return f"❌ Error creating styled PDF: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# EXCEL TOOLS
# ─────────────────────────────────────────────────────────────────────────────

@tool
def read_excel(file_path: str, sheet_name: str = "", max_rows: int = 50) -> str:
    """Reads and displays data from an Excel (.xlsx) or CSV file.

    Args:
        file_path: Path to the Excel file.
        sheet_name: Sheet name to read (default: first sheet).
        max_rows: Maximum number of rows to display (default 50).
    """
    if not HAS_OPENPYXL:
        return "❌ openpyxl not installed. Run: pip install openpyxl"
    try:
        if not os.path.exists(file_path):
            return f"❌ File not found: {file_path}"
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        sheet = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active
        rows = list(sheet.iter_rows(values_only=True))

        if not rows:
            return "⚠️  Sheet appears to be empty."

        # Format as table
        header = [str(c) if c is not None else "" for c in rows[0]]
        col_widths = [max(len(h), 8) for h in header]

        # Calculate column widths from data
        for row in rows[1:max_rows]:
            for i, cell in enumerate(row):
                if i < len(col_widths):
                    col_widths[i] = min(max(col_widths[i], len(str(cell) if cell is not None else "")), 25)

        def fmt_row(r):
            return "  ".join(str(c if c is not None else "")[:w].ljust(w) for c, w in zip(r, col_widths))

        header_line = fmt_row(header)
        sep = "-" * len(header_line)
        data_lines = [fmt_row(r) for r in rows[1:max_rows]]

        total_rows = sheet.max_row - 1  # excluding header
        result = (
            f"📊 {os.path.basename(file_path)} | Sheet: '{sheet.title}' | "
            f"{total_rows} rows × {len(header)} columns\n"
            f"{'─' * 60}\n"
            f"{header_line}\n{sep}\n"
            + "\n".join(data_lines)
        )
        if total_rows > max_rows:
            result += f"\n... ({total_rows - max_rows} more rows not shown)"
        wb.close()
        return result
    except Exception as e:
        return f"❌ Error reading Excel: {e}"


@tool
def create_excel(file_path: str, data: str, sheet_name: str = "Sheet1") -> str:
    """Creates an Excel file from CSV-formatted text data.

    Args:
        file_path: Output path for the .xlsx file.
        data: CSV-formatted data with headers on the first line.
              Use comma as separator. Example:
              'Name,Age,City\\nAlice,30,London\\nBob,25,Paris'
        sheet_name: Name for the worksheet (default 'Sheet1').
    """
    if not HAS_OPENPYXL:
        return "❌ openpyxl not installed. Run: pip install openpyxl"
    try:
        import csv
        import io as _io

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        reader = csv.reader(_io.StringIO(data))
        rows = list(reader)

        # Style header row
        header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
        header_font = Font(color="FFFFFF", bold=True)

        for r_idx, row in enumerate(rows, 1):
            for c_idx, value in enumerate(row, 1):
                cell = ws.cell(row=r_idx, column=c_idx, value=value.strip())
                if r_idx == 1:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center")

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max((len(str(cell.value)) for cell in col if cell.value), default=8)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

        wb.save(file_path)
        size_kb = os.path.getsize(file_path) / 1024
        return (
            f"✅ Excel file created!\n"
            f"Rows: {len(rows) - 1} (+ 1 header)\n"
            f"Cols: {len(rows[0]) if rows else 0}\n"
            f"File: {file_path} ({size_kb:.1f} KB)"
        )
    except Exception as e:
        return f"❌ Error creating Excel: {e}"
