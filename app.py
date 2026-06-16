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

BACKEND_URL = "http://127.0.0.1:8000"

# ─────────────────────────────────────────────
# Session State
# ─────────────────────────────────────────────
if "extracted_text" not in st.session_state:
    st.session_state.extracted_text = ""
if "edited_text" not in st.session_state:
    st.session_state.edited_text = ""
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "filename" not in st.session_state:
    st.session_state.filename = "document"
if "pages" not in st.session_state:
    st.session_state.pages = 0
if "user_choice" not in st.session_state:
    st.session_state.user_choice = None  # "edit" or "summarize"
if "pdf_uploaded" not in st.session_state:
    st.session_state.pdf_uploaded = False
if "edit_saved" not in st.session_state:
    st.session_state.edit_saved = False

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
    <h1 style='text-align:center; color:#4A90D9;'>🤖 AI PDF Assistant</h1>
    <p style='text-align:center; color:gray;'>Upload • Edit • Summarize • Download</p>
    <hr>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Step 1: Upload PDF
# ─────────────────────────────────────────────
st.markdown("### 📤 Upload your PDF")
uploaded_file = st.file_uploader("", type=["pdf"])

if uploaded_file and not st.session_state.pdf_uploaded:
    with st.spinner("📖 Reading your PDF..."):
        response = requests.post(
            f"{BACKEND_URL}/upload-pdf",
            files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
        )
    if response.status_code == 200:
        data = response.json()
        if "error" in data:
            st.error(f"❌ {data['error']}")
        else:
            st.session_state.extracted_text = data.get("extracted_text", "")
            st.session_state.edited_text = data.get("extracted_text", "")
            st.session_state.summary = data.get("summary", "")
            st.session_state.filename = data.get("filename", "document")
            st.session_state.pages = data.get("pages", 0)
            st.session_state.pdf_uploaded = True
            st.session_state.user_choice = None
            st.session_state.edit_saved = False
    else:
        st.error("❌ Could not connect to backend.")

# Reset if new file uploaded
if not uploaded_file:
    st.session_state.pdf_uploaded = False
    st.session_state.user_choice = None
    st.session_state.edit_saved = False

# ─────────────────────────────────────────────
# Step 2: Ask user what they want to do
# ─────────────────────────────────────────────
if st.session_state.pdf_uploaded:
    st.markdown("---")
    st.markdown(f"### ✅ PDF Loaded — **{st.session_state.filename}** &nbsp;|&nbsp; 📄 {st.session_state.pages} page(s)")

    if st.session_state.user_choice is None:
        st.markdown("### 🤔 What would you like to do with this PDF?")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
                <div style='background:#1e3a5f; padding:24px; border-radius:12px; text-align:center;'>
                    <h2>✏️</h2>
                    <h4 style='color:#4A90D9;'>Edit PDF First</h4>
                    <p style='color:gray; font-size:13px;'>Modify the content before summarizing</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("✏️ Yes, I want to Edit", use_container_width=True):
                st.session_state.user_choice = "edit"
                st.rerun()

        with col2:
            st.markdown("""
                <div style='background:#1a3a2a; padding:24px; border-radius:12px; text-align:center;'>
                    <h2>⚡</h2>
                    <h4 style='color:#4CAF50;'>Summarize Directly</h4>
                    <p style='color:gray; font-size:13px;'>Skip editing and go straight to AI summary</p>
                </div>
            """, unsafe_allow_html=True)
            if st.button("⚡ Skip, Just Summarize", use_container_width=True):
                st.session_state.user_choice = "summarize"
                st.rerun()

    # ─────────────────────────────────────────────
    # EDIT FLOW
    # ─────────────────────────────────────────────
    if st.session_state.user_choice == "edit":
        st.markdown("---")
        st.markdown("### ✏️ Edit Your PDF Content")
        st.caption("Make your changes below. Once done, click Save & Continue.")

        edited = st.text_area(
            label="",
            value=st.session_state.edited_text,
            height=450,
            placeholder="Your PDF content will appear here for editing..."
        )

        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("💾 Save & Continue", use_container_width=True):
                st.session_state.edited_text = edited
                st.session_state.edit_saved = True
                st.success("✅ Changes saved!")

        with col2:
            if st.button("🔄 Reset to Original", use_container_width=True):
                st.session_state.edited_text = st.session_state.extracted_text
                st.session_state.edit_saved = False
                st.info("↩️ Reset to original PDF text.")

    # ─────────────────────────────────────────────
    # AI SUMMARY (shown for both flows)
    # ─────────────────────────────────────────────
    show_summary = (
        st.session_state.user_choice == "summarize" or
        (st.session_state.user_choice == "edit" and st.session_state.edit_saved)
    )

    if show_summary:
        st.markdown("---")
        st.markdown("### 🤖 AI Summary")
        if st.session_state.summary:
            st.info(st.session_state.summary)
        else:
            st.warning("Summary not available.")

        # ─────────────────────────────────────────────
        # Fine-tune edit section
        # ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📝 Fine-tune Before Downloading")
        st.caption("You can still make final edits here before downloading.")

        final_text = st.text_area(
            label="",
            value=st.session_state.edited_text,
            height=350
        )

        # ─────────────────────────────────────────────
        # Download
        # ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("### 📥 Download Your PDF")

        if st.button("📄 Generate Edited PDF", use_container_width=True):
            with st.spinner("Building your PDF..."):
                dl_response = requests.post(
                    f"{BACKEND_URL}/download-edited-pdf",
                    data={
                        "edited_text": final_text,
                        "filename": st.session_state.filename
                    }
                )
            if dl_response.status_code == 200:
                edited_filename = st.session_state.filename.replace(".pdf", "") + "_edited.pdf"
                st.download_button(
                    label="⬇️ Download Edited PDF",
                    data=dl_response.content,
                    file_name=edited_filename,
                    mime="application/pdf",
                    use_container_width=True
                )
                st.success("✅ Your PDF is ready to download!")
            else:
                st.error("❌ Failed to generate PDF. Check your backend.")