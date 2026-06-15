from __future__ import annotations

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from .summarizer import DEFAULT_MODEL, extract_pdf_text, summarize_pdf_text


app = FastAPI(title="AI PDF Assistant", version="1.0.0")


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AI PDF Assistant</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f6f7f9;
      color: #18202a;
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; }
    main {
      width: min(920px, calc(100vw - 32px));
      margin: 0 auto;
      padding: 48px 0;
    }
    header { margin-bottom: 28px; }
    h1 { margin: 0 0 8px; font-size: clamp(2rem, 4vw, 3.4rem); letter-spacing: 0; }
    p { color: #5a6472; line-height: 1.6; }
    form, section {
      background: #ffffff;
      border: 1px solid #dfe4ea;
      border-radius: 8px;
      padding: 24px;
      box-shadow: 0 12px 32px rgba(24, 32, 42, 0.06);
    }
    label { display: block; font-weight: 700; margin-bottom: 10px; }
    input[type="file"] {
      width: 100%;
      padding: 16px;
      border: 1px dashed #8c99a8;
      border-radius: 6px;
      background: #fbfcfd;
    }
    button {
      margin-top: 18px;
      border: 0;
      border-radius: 6px;
      background: #176b5d;
      color: white;
      font-weight: 800;
      padding: 12px 18px;
      cursor: pointer;
    }
    button:disabled { opacity: 0.65; cursor: wait; }
    section { margin-top: 22px; white-space: pre-wrap; }
    .meta { color: #5a6472; margin-bottom: 14px; }
    .error { color: #9d1c1c; }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>AI PDF Assistant</h1>
      <p>Upload a text-based PDF and get a concise AI summary with key points and follow-ups.</p>
    </header>
    <form id="pdf-form">
      <label for="pdf">PDF file</label>
      <input id="pdf" name="file" type="file" accept="application/pdf" required />
      <button type="submit">Summarize PDF</button>
    </form>
    <section id="result" hidden></section>
  </main>
  <script>
    const form = document.querySelector("#pdf-form");
    const result = document.querySelector("#result");
    const button = form.querySelector("button");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      result.hidden = false;
      result.className = "";
      result.textContent = "Summarizing...";
      button.disabled = true;

      try {
        const response = await fetch("/summarize", {
          method: "POST",
          body: new FormData(form),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Unable to summarize PDF.");

        result.innerHTML = "";
        const meta = document.createElement("div");
        meta.className = "meta";
        meta.textContent = `${data.filename} - ${data.pages} page(s), ${data.characters} extracted characters, ${data.chunks} chunk(s)`;
        const summary = document.createElement("div");
        summary.textContent = data.summary;
        result.append(meta, summary);
      } catch (error) {
        result.className = "error";
        result.textContent = error.message;
      } finally {
        button.disabled = false;
      }
    });
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/summarize")
async def summarize(file: UploadFile = File(...), model: str = DEFAULT_MODEL) -> dict[str, object]:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        extracted = extract_pdf_text(pdf_bytes, file.filename or "uploaded.pdf")
        summary = summarize_pdf_text(extracted.text, model=model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "filename": extracted.filename,
        "pages": extracted.pages,
        "characters": len(extracted.text),
        "text_preview": extracted.text[:2000],
        **summary,
    }

