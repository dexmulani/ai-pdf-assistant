# AI PDF Assistant

A small FastAPI app that extracts text from an uploaded PDF and summarizes it with OpenAI.

## Setup

1. Create a `.env` file with your API key:

   ```env
   OPENAI_API_KEY=your_api_key_here
   ```

2. Install dependencies:

   ```powershell
   venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

3. Run the server:

   ```powershell
   venv\Scripts\python.exe -m uvicorn main:app --reload
   ```

4. Open `http://127.0.0.1:8000` and upload a PDF.

## API

- `GET /health` returns app status.
- `POST /summarize` accepts multipart form data with a `file` field containing a PDF.

The app works best with PDFs that contain selectable text. Scanned image-only PDFs need OCR before summarization.

