from fastapi import FastAPI, UploadFile, File
import fitz  # PyMuPDF
import ollama

app = FastAPI()


@app.get("/")
def home():
    return {
        "message": "AI PDF Assistant is running with Ollama!"
    }


@app.get("/test-ai")
def test_ai():
    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {
                "role": "user",
                "content": "Reply with exactly: AI connection successful!"
            }
        ]
    )

    return {
        "response": response["message"]["content"]
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Read the uploaded PDF
    pdf_bytes = await file.read()

    # Open it with PyMuPDF
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")

    extracted_text = ""
    for page in doc:
        extracted_text += page.get_text()

    doc.close()

    # Keep only the first part to avoid sending too much text
    prompt = (
        "Summarize the following PDF in simple bullet points:\n\n"
        + extracted_text[:5000]
    )

    response = ollama.chat(
        model="llama3.1:8b",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return {
        "filename": file.filename,
        "summary": response["message"]["content"]
    }