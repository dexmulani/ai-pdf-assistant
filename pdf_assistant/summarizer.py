from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import fitz
from dotenv import load_dotenv
from openai import OpenAI


DEFAULT_MODEL = "gpt-4.1-mini"
MAX_CHUNK_CHARS = 12_000


@dataclass(frozen=True)
class ExtractedPdf:
    filename: str
    pages: int
    text: str


def extract_pdf_text(pdf_bytes: bytes, filename: str = "uploaded.pdf") -> ExtractedPdf:
    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # PyMuPDF raises several exception types here.
        raise ValueError("The uploaded file could not be opened as a PDF.") from exc

    try:
        page_text: list[str] = []
        for index, page in enumerate(document, start=1):
            text = page.get_text("text").strip()
            if text:
                page_text.append(f"[Page {index}]\n{text}")

        return ExtractedPdf(
            filename=filename,
            pages=len(document),
            text="\n\n".join(page_text).strip(),
        )
    finally:
        document.close()


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    paragraphs = [part.strip() for part in text.splitlines() if part.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + 1
        if current and current_len + paragraph_len > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0

        if paragraph_len > max_chars:
            chunks.extend(
                paragraph[i : i + max_chars]
                for i in range(0, len(paragraph), max_chars)
            )
            continue

        current.append(paragraph)
        current_len += paragraph_len

    if current:
        chunks.append("\n".join(current))

    return chunks


def build_client() -> OpenAI:
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing. Add it to your .env file.")
    return OpenAI(api_key=api_key)


def _summarize_chunk(client: OpenAI, chunk: str, model: str, chunk_number: int, total: int) -> str:
    response = client.responses.create(
        model=model,
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": (
                    "You summarize PDF content for busy readers. Preserve important facts, "
                    "numbers, dates, entities, action items, and conclusions. Be concise."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Summarize chunk {chunk_number} of {total}. Return concise bullets "
                    "with no invented details.\n\n"
                    f"{chunk}"
                ),
            },
        ],
    )
    return response.output_text.strip()


def _combine_summaries(client: OpenAI, summaries: Iterable[str], model: str) -> str:
    joined = "\n\n".join(summaries)
    response = client.responses.create(
        model=model,
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": (
                    "Create a final PDF summary from chunk summaries. Keep it faithful, "
                    "use headings, and make it easy to scan."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Write the final answer with these sections:\n"
                    "1. Overview\n"
                    "2. Key points\n"
                    "3. Important details\n"
                    "4. Action items or open questions, if any\n\n"
                    f"{joined}"
                ),
            },
        ],
    )
    return response.output_text.strip()


def summarize_pdf_text(text: str, model: str = DEFAULT_MODEL) -> dict[str, object]:
    if not text.strip():
        raise ValueError("No selectable text was found in the PDF.")

    client = build_client()
    chunks = chunk_text(text)
    chunk_summaries = [
        _summarize_chunk(client, chunk, model, index, len(chunks))
        for index, chunk in enumerate(chunks, start=1)
    ]

    if len(chunk_summaries) == 1:
        final_summary = _combine_summaries(client, chunk_summaries, model)
    else:
        final_summary = _combine_summaries(client, chunk_summaries, model)

    return {
        "summary": final_summary,
        "chunks": len(chunks),
        "model": model,
    }

