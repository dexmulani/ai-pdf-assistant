from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse
import fitz  # PyMuPDF
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import ollama
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

# Load environment variables
load_dotenv()

app = FastAPI()

# Thread pool for running blocking Ollama calls without freezing the server
executor = ThreadPoolExecutor(max_workers=4)


# ─────────────────────────────────────────────
# Helper: Run Ollama in a separate thread
# ─────────────────────────────────────────────
def run_ollama(text: str) -> str:
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": f"Summarize this text in a clear and concise way:\n\n{text[:4000]}"
            }
        ]
    )
    return response["message"]["content"]


@app.get("/")
def home():
    return {"message": "AI PDF Assistant is running!"}


# ─────────────────────────────────────────────
# 1. UPLOAD & SUMMARIZE
# ─────────────────────────────────────────────
@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        page_count = len(doc)

        # Extract text from all pages
        extracted_text = ""
        for page in doc:
            extracted_text += page.get_text()
        doc.close()

        # Run Ollama in thread pool — won't block other requests
        loop = asyncio.get_event_loop()
        summary = await loop.run_in_executor(executor, run_ollama, extracted_text)

        return {
            "filename": file.filename,
            "pages": page_count,
            "extracted_text": extracted_text,  # full text for editing
            "summary": summary
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


# ─────────────────────────────────────────────
# 2. EDIT & DOWNLOAD AS PDF
# ─────────────────────────────────────────────
@app.post("/download-edited-pdf")
async def download_edited_pdf(
    edited_text: str = Form(...),
    filename: str = Form("edited_document")
):
    try:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=60,
            bottomMargin=60
        )
        styles = getSampleStyleSheet()
        story = []

        # Split by newline and add each line as a paragraph
        for line in edited_text.split("\n"):
            if line.strip() == "":
                story.append(Spacer(1, 8))
            else:
                story.append(Paragraph(line.strip(), styles["Normal"]))
                story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)

        safe_filename = filename.replace(".pdf", "") + "_edited.pdf"

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
        )

    except Exception as e:
        return {"error": f"Failed to generate PDF: {str(e)}"}