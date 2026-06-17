from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import List
import fitz  # PyMuPDF
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import ollama
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
import io
import re

# Load environment variables
load_dotenv()

app = FastAPI()

# Thread pool for running blocking Ollama calls without freezing the server
executor = ThreadPoolExecutor(max_workers=4)


# ─────────────────────────────────────────────
# Helper: Detect if a line looks like a heading
# ─────────────────────────────────────────────
def is_heading(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    # All caps and short = likely heading
    if line.isupper() and len(line) < 80:
        return True
    # Ends with colon
    if line.endswith(":") and len(line) < 80:
        return True
    # Numbered heading like "1. Introduction" or "1.1 Background"
    if re.match(r"^\d+[\.\d]*\s+[A-Z]", line):
        return True
    # Common heading keywords
    heading_keywords = [
        "introduction", "conclusion", "summary", "abstract",
        "background", "methodology", "results", "references",
        "overview", "chapter", "section", "appendix"
    ]
    lower = line.lower()
    if any(lower.startswith(kw) for kw in heading_keywords) and len(line) < 80:
        return True
    return False


# ─────────────────────────────────────────────
# Helper: Build a polished PDF from text
# ─────────────────────────────────────────────
def build_pdf(text: str, title: str = "Document") -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=1 * inch,
        leftMargin=1 * inch,
        topMargin=1 * inch,
        bottomMargin=0.8 * inch
    )

    styles = getSampleStyleSheet()

    # ── Custom styles ──────────────────────────────────────
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Title"],
        fontSize=20,
        textColor=colors.HexColor("#1a3a5c"),
        spaceAfter=6,
        spaceBefore=0,
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        leading=26,
    )
    heading1_style = ParagraphStyle(
        "H1",
        parent=styles["Heading1"],
        fontSize=14,
        textColor=colors.HexColor("#1a3a5c"),
        spaceBefore=16,
        spaceAfter=4,
        fontName="Helvetica-Bold",
        borderPad=0,
        leading=18,
    )
    heading2_style = ParagraphStyle(
        "H2",
        parent=styles["Heading2"],
        fontSize=12,
        textColor=colors.HexColor("#2e6da4"),
        spaceBefore=12,
        spaceAfter=3,
        fontName="Helvetica-Bold",
        leading=16,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10.5,
        leading=16,
        spaceAfter=6,
        spaceBefore=0,
        alignment=TA_JUSTIFY,
        fontName="Helvetica",
        textColor=colors.HexColor("#1a1a1a"),
    )
    # ──────────────────────────────────────────────────────

    story = []

    # Document title
    safe_title = re.sub(r"[^\w\s\-]", "", title.replace(".pdf", "")).strip()
    story.append(Paragraph(safe_title or "Document", title_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2e6da4"), spaceAfter=12))

    lines = text.split("\n")
    paragraph_buffer = []

    def flush_paragraph():
        """Flush buffered lines as a single justified paragraph."""
        joined = " ".join(paragraph_buffer).strip()
        if joined:
            story.append(Paragraph(joined, body_style))
        paragraph_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if stripped == "":
            # Blank line → flush current paragraph buffer
            flush_paragraph()
            story.append(Spacer(1, 4))
            continue

        if is_heading(stripped):
            flush_paragraph()
            # Decide heading level by length / pattern
            if re.match(r"^\d+\.\d+", stripped) or len(stripped) < 40:
                story.append(Paragraph(stripped, heading2_style))
            else:
                story.append(Paragraph(stripped, heading1_style))
            story.append(HRFlowable(width="100%", thickness=0.4, color=colors.HexColor("#cccccc"), spaceAfter=4))
        else:
            paragraph_buffer.append(stripped)

    # Flush any remaining text
    flush_paragraph()

    doc.build(story)
    buffer.seek(0)
    return buffer


# ─────────────────────────────────────────────
# Helper: Run Ollama summary
# ─────────────────────────────────────────────
def run_ollama_summary(text: str, tone: str = "clear and concise") -> str:
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Summarize the following text in a {tone} way. "
                    f"Keep the summary informative and well-structured:\n\n{text[:4000]}"
                )
            }
        ]
    )
    return response["message"]["content"]


# ─────────────────────────────────────────────
# Helper: Run Ollama edit
# ─────────────────────────────────────────────
def run_ollama_edit(text: str, instruction: str, tone: str) -> str:
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": (
                    f"Edit the following text with these instructions: {instruction}\n"
                    f"Use a {tone} tone. Return only the edited text, no explanations.\n\n{text[:4000]}"
                )
            }
        ]
    )
    return response["message"]["content"]


@app.get("/")
def home():
    return {"message": "AI PDF Assistant is running!"}


# ─────────────────────────────────────────────
# 1. UPLOAD SINGLE PDF & SUMMARIZE
# ─────────────────────────────────────────────
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)

        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text()
        doc.close()

        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(executor, run_ollama_summary, extracted_text, "clear and concise")

        return {
            "filename": file.filename,
            "pages": page_count,
            "extracted_text": extracted_text,
            "summary": summary
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


# ─────────────────────────────────────────────
# 2. UPLOAD MULTIPLE PDFs & SUMMARIZE EACH
# ─────────────────────────────────────────────
@app.post("/upload-multiple-pdfs")
async def upload_multiple_pdfs(files: List[UploadFile] = File(...)):
    results = []
    loop = asyncio.get_event_loop()

    async def process_one(file: UploadFile):
        try:
            pdf_bytes = await file.read()
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            page_count = len(doc)

            extracted_text = ""
            for page in doc:
                extracted_text += page.get_text()
            doc.close()

            summary = await loop.run_in_executor(executor, run_ollama_summary, extracted_text, "clear and concise")

            return {
                "filename": file.filename,
                "pages": page_count,
                "extracted_text": extracted_text,
                "summary": summary,
                "error": None
            }
        except Exception as e:
            return {
                "filename": file.filename,
                "pages": 0,
                "extracted_text": "",
                "summary": "",
                "error": str(e)
            }

    # Process all PDFs concurrently
    tasks = [process_one(f) for f in files]
    results = await asyncio.gather(*tasks)
    return {"results": list(results)}


# ─────────────────────────────────────────────
# 3. AI EDIT TEXT
# ─────────────────────────────────────────────
@app.post("/ai-edit")
async def ai_edit(
    text: str = Form(...),
    instruction: str = Form("Improve clarity and fix grammar"),
    tone: str = Form("professional")
):
    try:
        loop = asyncio.get_event_loop()
        edited = await loop.run_in_executor(executor, run_ollama_edit, text, instruction, tone)
        return {"edited_text": edited}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────
# 4. GENERATE & DOWNLOAD PDF
# ─────────────────────────────────────────────
@app.post("/download-edited-pdf")
async def download_edited_pdf(
    edited_text: str = Form(...),
    filename: str = Form("edited_document")
):
    try:
        buffer = build_pdf(edited_text, title=filename)
        safe_filename = filename.replace(".pdf", "") + "_edited.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )

    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}