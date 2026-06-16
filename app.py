import streamlit as st
import requests

# ─────────────────────────────────────────────
# Page Config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="AI PDF Assistant",
    page_icon="📄",
    layout="wide"
)

st.title("🤖 AI PDF Assistant")
st.markdown("Upload a PDF to **summarize** or **edit** its content.")

BACKEND_URL = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────
# Session State (keeps data between interactions)
# ─────────────────────────────────────────────
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "filename" not in st.session_state:
    st.session_state.filename = "document"

# ─────────────────────────────────────────────
# Step 1: Upload PDF
# ─────────────────────────────────────────────
st.header("📤 Step 1: Upload your PDF")
uploaded_file = st.file_uploader("Choose a PDF file", type=["pdf"])

if uploaded_file is not None:
    if st.button("🚀 Extract & Summarize"):
        with st.spinner("Reading and summarizing your PDF..."):
            response = requests.post(
                f"{BACKEND_URL}/upload-pdf",
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            )

        if response.status_code == 200:
            data = response.json()

            if "error" in data:
                st.error(f"❌ Error: {data['error']}")
            else:
                st.session_state.extracted_text = data.get("extracted_text", "")
                st.session_state.summary = data.get("summary", "")
                st.session_state.filename = data.get("filename", "document")
                st.success(f"✅ Done! Pages found: {data.get('pages', 'N/A')}")
        else:
            st.error("❌ Could not connect to the backend. Is your FastAPI server running?")

# ─────────────────────────────────────────────
# Step 2: Show Summary
# ─────────────────────────────────────────────
if st.session_state.summary:
    st.header("📋 Step 2: AI Summary")
    st.info(st.session_state.summary)

# ─────────────────────────────────────────────
# Step 3: Edit Text
# ─────────────────────────────────────────────
if st.session_state.extracted_text:
    st.header("✏️ Step 3: Edit the Extracted Text")
    st.markdown("You can modify the text below. Once done, download it as a new PDF.")

    edited_text = st.text_area(
        label="Edit your PDF content here:",
        value=st.session_state.extracted_text,
        height=400,
        key="editor"
    )

    # ─────────────────────────────────────────────
    # Step 4: Download Edited PDF
    # ─────────────────────────────────────────────
    st.header("📥 Step 4: Download Edited PDF")

    if st.button("📄 Generate & Download Edited PDF"):
        with st.spinner("Generating your edited PDF..."):
            download_response = requests.post(
                f"{BACKEND_URL}/download-edited-pdf",
                data={
                    "edited_text": edited_text,
                    "filename": st.session_state.filename
                }
            )

        if download_response.status_code == 200:
            edited_filename = st.session_state.filename.replace(".pdf", "") + "_edited.pdf"
            st.download_button(
                label="⬇️ Click here to Download",
                data=download_response.content,
                file_name=edited_filename,
                mime="application/pdf"
            )
            st.success("✅ Your edited PDF is ready!")
        else:
            st.error("❌ Failed to generate the edited PDF. Check your backend.")