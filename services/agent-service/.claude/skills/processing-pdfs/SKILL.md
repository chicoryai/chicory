---
name: processing-pdfs
description: Extracts text and tables from PDF files, takes screenshots of pages, merges/splits documents, creates new PDFs, and fills forms. Use when working with PDF files, .pdf extensions, document extraction, form filling, PDF manipulation, or rendering PDF pages as images.
---

# PDF Processing

## Contents
- Text extraction (priority order)
- Table extraction (pdfplumber)
- **Screenshot/render pages to images**
- Merge, split, rotate (pypdf)
- Create PDFs (reportlab)
- Command-line tools (qpdf, pdftotext)
- OCR for scanned PDFs

**Form filling**: See [forms.md](forms.md)
**Advanced features**: See [reference.md](reference.md)

## Text Extraction - Priority Order

**ALWAYS try methods in this order:**

### 1. Built-in Read Tool (FIRST CHOICE)
```
Read("document.pdf")
```
The Read tool natively supports PDF text extraction. Try this first - it's the simplest and often sufficient.

### 2. pypdf (FALLBACK - Best accuracy)
Use if Read tool fails or returns poor results:
```python
from pypdf import PdfReader

reader = PdfReader("document.pdf")
text = ""
for page in reader.pages:
    text += page.extract_text()
```
**Benchmark: 72-97% word accuracy** on academic PDFs.

### 3. pdfplumber (For tables or layout-sensitive text)
Use when you need tables or layout preservation:
```python
import pdfplumber

with pdfplumber.open("document.pdf") as pdf:
    for page in pdf.pages:
        text = page.extract_text()
```
**Note:** Lower accuracy for plain text (35-61%), but excellent for tables.

### 4. pdftotext CLI (Quick extraction)
```bash
pdftotext -layout input.pdf output.txt
```

### Decision Flow
```
PDF Text Extraction:
├── Try Read("file.pdf") first
│   ├── Success? → Done
│   └── Failed/Poor quality? → Continue
├── Try pypdf (best accuracy)
│   ├── Success? → Done
│   └── Failed? → Continue
├── Has tables? → Use pdfplumber
└── Scanned/Image PDF? → Use OCR (pytesseract)
```

## Screenshot PDF Pages

Take screenshots of PDF pages to render them as images. Useful for visual inspection, image-based analysis, or when you need to see the exact layout.

**Constraints:**
- File must have `.pdf` extension
- Maximum file size: 100MB
- Page numbers must be >= 1

### Single Page Screenshot
```python
from pdf2image import convert_from_path
from PIL import Image

def screenshot_page(pdf_path, page_number=1, output_path=None, dpi=150, max_dim=1500):
    """Take a screenshot of a specific page from a PDF."""
    images = convert_from_path(
        pdf_path, 
        dpi=dpi, 
        first_page=page_number, 
        last_page=page_number
    )
    
    image = images[0]
    
    # Scale if needed
    width, height = image.size
    if width > max_dim or height > max_dim:
        scale_factor = min(max_dim / width, max_dim / height)
        image = image.resize(
            (int(width * scale_factor), int(height * scale_factor)), 
            Image.Resampling.LANCZOS
        )
    
    if output_path is None:
        output_path = f"page_{page_number}.png"
    
    image.save(output_path, "PNG")
    return output_path
```

### Multiple Pages Screenshot
```python
from pdf2image import convert_from_path

# Screenshot all pages
images = convert_from_path("document.pdf", dpi=150)
for i, image in enumerate(images):
    image.save(f"page_{i+1}.png", "PNG")

# Screenshot specific pages (1, 3, 5)
for page_num in [1, 3, 5]:
    images = convert_from_path(
        "document.pdf", 
        dpi=150, 
        first_page=page_num, 
        last_page=page_num
    )
    images[0].save(f"page_{page_num}.png", "PNG")
```

### Command Line Screenshot
```bash
# Using the screenshot_pdf_page.py script
python screenshot_pdf_page.py document.pdf 1              # Screenshot page 1
python screenshot_pdf_page.py document.pdf --all          # Screenshot all pages
python screenshot_pdf_page.py document.pdf 3 output.png   # Screenshot page 3 to output.png

# Using pdftoppm (poppler-utils) - fastest method
pdftoppm -png -r 150 document.pdf output_prefix

# Screenshot specific page (page 3)
pdftoppm -png -r 150 -f 3 -l 3 document.pdf page_3

# High resolution screenshot
pdftoppm -png -r 300 document.pdf high_res
```

### Screenshot Decision Flow
```
Need PDF Screenshot:
├── Single page? → Use pdf2image with first_page/last_page
├── All pages? → Use convert_from_path() or --all flag
├── High quality needed? → Use dpi=300 or higher
└── Need to scale? → Use PIL Image.resize() with Resampling.LANCZOS
```

## Python Libraries

### pypdf - Basic Operations

#### Merge PDFs
```python
from pypdf import PdfWriter, PdfReader

writer = PdfWriter()
for pdf_file in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    reader = PdfReader(pdf_file)
    for page in reader.pages:
        writer.add_page(page)

with open("merged.pdf", "wb") as output:
    writer.write(output)
```

#### Split PDF
```python
reader = PdfReader("input.pdf")
for i, page in enumerate(reader.pages):
    writer = PdfWriter()
    writer.add_page(page)
    with open(f"page_{i+1}.pdf", "wb") as output:
        writer.write(output)
```

#### Extract Metadata
```python
reader = PdfReader("document.pdf")
meta = reader.metadata
print(f"Title: {meta.title}")
print(f"Author: {meta.author}")
print(f"Subject: {meta.subject}")
print(f"Creator: {meta.creator}")
```

#### Rotate Pages
```python
reader = PdfReader("input.pdf")
writer = PdfWriter()

page = reader.pages[0]
page.rotate(90)  # Rotate 90 degrees clockwise
writer.add_page(page)

with open("rotated.pdf", "wb") as output:
    writer.write(output)
```

### pdfplumber - Table Extraction

#### Extract Tables
```python
with pdfplumber.open("document.pdf") as pdf:
    for i, page in enumerate(pdf.pages):
        tables = page.extract_tables()
        for j, table in enumerate(tables):
            print(f"Table {j+1} on page {i+1}:")
            for row in table:
                print(row)
```

#### Advanced Table Extraction
```python
import pandas as pd

with pdfplumber.open("document.pdf") as pdf:
    all_tables = []
    for page in pdf.pages:
        tables = page.extract_tables()
        for table in tables:
            if table:  # Check if table is not empty
                df = pd.DataFrame(table[1:], columns=table[0])
                all_tables.append(df)

# Combine all tables
if all_tables:
    combined_df = pd.concat(all_tables, ignore_index=True)
    combined_df.to_excel("extracted_tables.xlsx", index=False)
```

### reportlab - Create PDFs

#### Basic PDF Creation
```python
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

c = canvas.Canvas("hello.pdf", pagesize=letter)
width, height = letter

# Add text
c.drawString(100, height - 100, "Hello World!")
c.drawString(100, height - 120, "This is a PDF created with reportlab")

# Add a line
c.line(100, height - 140, 400, height - 140)

# Save
c.save()
```

#### Create PDF with Multiple Pages
```python
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet

doc = SimpleDocTemplate("report.pdf", pagesize=letter)
styles = getSampleStyleSheet()
story = []

# Add content
title = Paragraph("Report Title", styles['Title'])
story.append(title)
story.append(Spacer(1, 12))

body = Paragraph("This is the body of the report. " * 20, styles['Normal'])
story.append(body)
story.append(PageBreak())

# Page 2
story.append(Paragraph("Page 2", styles['Heading1']))
story.append(Paragraph("Content for page 2", styles['Normal']))

# Build PDF
doc.build(story)
```

## Command-Line Tools

### pdftotext (poppler-utils)
```bash
# Extract text
pdftotext input.pdf output.txt

# Extract text preserving layout
pdftotext -layout input.pdf output.txt

# Extract specific pages
pdftotext -f 1 -l 5 input.pdf output.txt  # Pages 1-5
```

### qpdf
```bash
# Merge PDFs
qpdf --empty --pages file1.pdf file2.pdf -- merged.pdf

# Split pages
qpdf input.pdf --pages . 1-5 -- pages1-5.pdf
qpdf input.pdf --pages . 6-10 -- pages6-10.pdf

# Rotate pages
qpdf input.pdf output.pdf --rotate=+90:1  # Rotate page 1 by 90 degrees

# Remove password
qpdf --password=mypassword --decrypt encrypted.pdf decrypted.pdf
```

### pdftk (if available)
```bash
# Merge
pdftk file1.pdf file2.pdf cat output merged.pdf

# Split
pdftk input.pdf burst

# Rotate
pdftk input.pdf rotate 1east output rotated.pdf
```

## Common Tasks

### Extract Text from Scanned PDFs
```python
# Requires: pip install pytesseract pdf2image
import pytesseract
from pdf2image import convert_from_path

# Convert PDF to images
images = convert_from_path('scanned.pdf')

# OCR each page
text = ""
for i, image in enumerate(images):
    text += f"Page {i+1}:\n"
    text += pytesseract.image_to_string(image)
    text += "\n\n"

print(text)
```

### Add Watermark
```python
from pypdf import PdfReader, PdfWriter

# Create watermark (or load existing)
watermark = PdfReader("watermark.pdf").pages[0]

# Apply to all pages
reader = PdfReader("document.pdf")
writer = PdfWriter()

for page in reader.pages:
    page.merge_page(watermark)
    writer.add_page(page)

with open("watermarked.pdf", "wb") as output:
    writer.write(output)
```

### Extract Images
```bash
# Using pdfimages (poppler-utils)
pdfimages -j input.pdf output_prefix

# This extracts all images as output_prefix-000.jpg, output_prefix-001.jpg, etc.
```

### Password Protection
```python
from pypdf import PdfReader, PdfWriter

reader = PdfReader("input.pdf")
writer = PdfWriter()

for page in reader.pages:
    writer.add_page(page)

# Add password
writer.encrypt("userpassword", "ownerpassword")

with open("encrypted.pdf", "wb") as output:
    writer.write(output)
```

## Quick Reference

| Task | Best Tool | Command/Code |
|------|-----------|--------------|
| **Extract text** | **1. Read tool** | `Read("file.pdf")` |
| Extract text (fallback) | 2. pypdf | `page.extract_text()` |
| Extract tables | pdfplumber | `page.extract_tables()` |
| **Screenshot page** | pdf2image | `convert_from_path(pdf, first_page=N, last_page=N)` |
| Screenshot (CLI) | pdftoppm | `pdftoppm -png -r 150 -f 1 -l 1 input.pdf output` |
| Merge PDFs | pypdf | `writer.add_page(page)` |
| Split PDFs | pypdf | One page per file |
| Create PDFs | reportlab | Canvas or Platypus |
| Command line extract | pdftotext | `pdftotext -layout input.pdf` |
| Command line merge | qpdf | `qpdf --empty --pages ...` |
| OCR scanned PDFs | pytesseract | Convert to image first |
| Fill PDF forms | pypdf or pdf-lib | See forms.md |

## Next Steps

- For advanced pypdfium2 usage, see reference.md
- For JavaScript libraries (pdf-lib), see reference.md
- If you need to fill out a PDF form, follow the instructions in forms.md
- For troubleshooting guides, see reference.md
