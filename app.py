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
# Styling
# ─────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 2rem; }
    .pdf-card {
        background: #0f1e30;
        border: 1px solid #1e3a5f;
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 12px;
    }
    .pdf-title {
        color: #4A90D9;
        font-size: 16px;
        font-weight: 600;
        margin-bottom: 4px;
    }
    .pdf-meta {
        color: #7a9bbf;
        font-size: 13px;
    }
    .section-label {
        font-size: 13px;
        color: #7a9bbf;
        margin-bottom: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Session State Init
# ─────────────────────────────────────────────
if "mode" not in st.session_state:
    st.session_state.mode = "single"          # "single" | "multi"

# Single PDF state
if "single" not in st.session_state:
    st.session_state.single = {
        "uploaded": False,
        "filename": "",
        "pages": 0,
        "extracted_text": "",
        "edited_text": "",
        "summary": "",
        "user_choice": None,
        "edit_saved": False,
    }

# Multi PDF state — list of dicts per PDF
if "multi_pdfs" not in st.session_state:
    st.session_state.multi_pdfs = []

if "multi_processed" not in st.session_state:
    st.session_state.multi_processed = False


# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
    <h1 style='text-align:center; color:#4A90D9;'>🤖 AI PDF Assistant</h1>
    <p style='text-align:center; color:#7a9bbf;'>Upload • Edit • Summarize • Download</p>
    <hr style='border-color:#1e3a5f;'>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Mode Selector
# ─────────────────────────────────────────────
col_l, col_m, col_r = st.columns([2, 3, 2])
with col_m:
    mode = st.radio(
        "Select Mode",
        options=["Single PDF", "Multiple PDFs"],
        horizontal=True,
        label_visibility="collapsed"
    )
    st.session_state.mode = "single" if mode == "Single PDF" else "multi"

st.markdown("<br>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
# ███  SINGLE PDF MODE  ████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════
if st.session_state.mode == "single":
    s = st.session_state.single

    st.markdown("### 📤 Upload your PDF")
    uploaded_file = st.file_uploader("", type=["pdf"], key="single_uploader")

    if uploaded_file and not s["uploaded"]:
        with st.spinner("📖 Reading your PDF..."):
            response = requests.post(
                f"{BACKEND_URL}/upload-pdf",
                files={"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
            )
        if response.status_code == 200:
            data = response.json()
            if "error" in data and data["error"]:
                st.error(f"❌ {data['error']}")
            else:
                s["extracted_text"] = data.get("extracted_text", "")
                s["edited_text"]    = data.get("extracted_text", "")
                s["summary"]        = data.get("summary", "")
                s["filename"]       = data.get("filename", "document")
                s["pages"]          = data.get("pages", 0)
                s["uploaded"]       = True
                s["user_choice"]    = None
                s["edit_saved"]     = False
        else:
            st.error("❌ Could not connect to backend.")

    if not uploaded_file:
        s["uploaded"]    = False
        s["user_choice"] = None
        s["edit_saved"]  = False

    # ── Loaded State ─────────────────────────────────────────
    if s["uploaded"]:
        st.markdown("---")
        st.markdown(f"### ✅ **{s['filename']}** &nbsp;|&nbsp; 📄 {s['pages']} page(s)")

        # ── Choose action ───────────────────────────────────
        if s["user_choice"] is None:
            st.markdown("### 🤔 What would you like to do?")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("""
                    <div class='pdf-card' style='text-align:center;'>
                        <div style='font-size:28px;'>✏️</div>
                        <div class='pdf-title'>Edit PDF First</div>
                        <div class='pdf-meta'>Modify content before summarizing</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("✏️ Yes, I want to Edit", use_container_width=True, key="s_edit"):
                    s["user_choice"] = "edit"
                    st.rerun()
            with col2:
                st.markdown("""
                    <div class='pdf-card' style='text-align:center;'>
                        <div style='font-size:28px;'>⚡</div>
                        <div class='pdf-title' style='color:#4CAF50;'>Summarize Directly</div>
                        <div class='pdf-meta'>Skip editing, go straight to AI summary</div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("⚡ Skip, Just Summarize", use_container_width=True, key="s_sum"):
                    s["user_choice"] = "summarize"
                    st.rerun()

        # ── Edit Flow ───────────────────────────────────────
        if s["user_choice"] == "edit":
            st.markdown("---")
            st.markdown("### ✏️ Edit Your PDF Content")
            st.caption("Make changes below, then Save & Continue.")

            edited = st.text_area(
                label="",
                value=s["edited_text"],
                height=400,
                key="s_edit_area"
            )

            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("💾 Save & Continue", use_container_width=True):
                    s["edited_text"] = edited
                    s["edit_saved"]  = True
                    st.success("✅ Changes saved!")
            with col2:
                if st.button("🔄 Reset to Original", use_container_width=True):
                    s["edited_text"] = s["extracted_text"]
                    s["edit_saved"]  = False
                    st.info("↩️ Reset to original.")
            with col3:
                # AI-assisted edit
                with st.expander("🤖 AI Edit Assist"):
                    ai_instruction = st.text_input("Instruction", value="Improve clarity and fix grammar", key="s_ai_inst")
                    ai_tone = st.selectbox("Tone", ["professional", "casual", "formal", "simple"], key="s_ai_tone")
                    if st.button("✨ Apply AI Edit", use_container_width=True, key="s_ai_apply"):
                        with st.spinner("AI is editing..."):
                            r = requests.post(f"{BACKEND_URL}/ai-edit", data={
                                "text": edited,
                                "instruction": ai_instruction,
                                "tone": ai_tone
                            })
                        if r.status_code == 200 and "edited_text" in r.json():
                            s["edited_text"] = r.json()["edited_text"]
                            s["edit_saved"]  = True
                            st.success("✅ AI edits applied!")
                            st.rerun()
                        else:
                            st.error("AI edit failed.")

        # ── Summary + Download ──────────────────────────────
        show_summary = (
            s["user_choice"] == "summarize" or
            (s["user_choice"] == "edit" and s["edit_saved"])
        )

        if show_summary:
            st.markdown("---")
            st.markdown("### 🤖 AI Summary")

            # Tuning params — always visible here, with sensible defaults
            with st.expander("⚙️ Summary Settings", expanded=False):
                sum_tone = st.selectbox(
                    "Summary tone",
                    ["clear and concise", "detailed", "bullet points", "simple language", "technical"],
                    index=0,
                    key="s_sum_tone"
                )
                if st.button("🔄 Regenerate Summary", key="s_regen"):
                    with st.spinner("Regenerating summary..."):
                        r = requests.post(f"{BACKEND_URL}/ai-edit", data={
                            "text": s["edited_text"],
                            "instruction": f"Summarize this text in a {sum_tone} way",
                            "tone": sum_tone
                        })
                    if r.status_code == 200:
                        s["summary"] = r.json().get("edited_text", s["summary"])
                        st.rerun()

            if s["summary"]:
                st.info(s["summary"])
            else:
                st.warning("Summary not available.")

            st.markdown("---")
            st.markdown("### 📝 Final Review Before Download")
            st.caption("Make any last edits below.")

            final_text = st.text_area(
                label="",
                value=s["edited_text"],
                height=300,
                key="s_final_area"
            )

            st.markdown("---")
            st.markdown("### 📥 Download")

            if st.button("📄 Generate PDF", use_container_width=True, key="s_gen_pdf"):
                with st.spinner("Building your PDF..."):
                    dl_response = requests.post(
                        f"{BACKEND_URL}/download-edited-pdf",
                        data={"edited_text": final_text, "filename": s["filename"]}
                    )
                if dl_response.status_code == 200:
                    fname = s["filename"].replace(".pdf", "") + "_edited.pdf"
                    st.download_button(
                        label="⬇️ Download PDF",
                        data=dl_response.content,
                        file_name=fname,
                        mime="application/pdf",
                        use_container_width=True,
                        key="s_dl"
                    )
                    st.success("✅ PDF ready!")
                else:
                    st.error("❌ Failed to generate PDF.")


# ═══════════════════════════════════════════════════════════════
# ███  MULTI PDF MODE  █████████████████████████████████████████
# ═══════════════════════════════════════════════════════════════
else:
    st.markdown("### 📤 Upload Multiple PDFs")
    st.caption("Upload up to 10 PDFs. Each will be processed separately.")

    uploaded_files = st.file_uploader(
        "",
        type=["pdf"],
        accept_multiple_files=True,
        key="multi_uploader"
    )

    if uploaded_files:
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚀 Process All PDFs", use_container_width=True):
                st.session_state.multi_pdfs = []
                st.session_state.multi_processed = False

                with st.spinner(f"Processing {len(uploaded_files)} PDF(s)... this may take a moment."):
                    files_payload = [
                        ("files", (f.name, f.getvalue(), "application/pdf"))
                        for f in uploaded_files
                    ]
                    response = requests.post(
                        f"{BACKEND_URL}/upload-multiple-pdfs",
                        files=files_payload
                    )

                if response.status_code == 200:
                    results = response.json().get("results", [])
                    for r in results:
                        st.session_state.multi_pdfs.append({
                            "filename":       r["filename"],
                            "pages":          r["pages"],
                            "extracted_text": r["extracted_text"],
                            "edited_text":    r["extracted_text"],
                            "summary":        r["summary"],
                            "error":          r["error"],
                            "edit_saved":     False,
                        })
                    st.session_state.multi_processed = True
                    st.rerun()
                else:
                    st.error("❌ Backend error. Make sure FastAPI is running.")

    # ── Render each PDF as its own section ─────────────────
    if st.session_state.multi_processed and st.session_state.multi_pdfs:
        st.markdown("---")
        st.markdown(f"### 📂 {len(st.session_state.multi_pdfs)} PDF(s) Loaded")

        # Batch download all button
        if st.button("📥 Download ALL as Edited PDFs", use_container_width=False):
            st.info("ℹ️ Use the individual download buttons below for each PDF.")

        for idx, pdf in enumerate(st.session_state.multi_pdfs):
            key = f"pdf_{idx}"

            with st.expander(
                f"📄 {pdf['filename']}  ·  {pdf['pages']} page(s)"
                + ("  ⚠️ Error" if pdf["error"] else ""),
                expanded=(idx == 0)
            ):
                if pdf["error"]:
                    st.error(f"❌ Could not process: {pdf['error']}")
                    continue

                tabs = st.tabs(["🤖 Summary", "✏️ Edit & Download"])

                # ── Tab 1: Summary ─────────────────────────
                with tabs[0]:
                    with st.expander("⚙️ Summary Settings", expanded=False):
                        sum_tone = st.selectbox(
                            "Tone",
                            ["clear and concise", "detailed", "bullet points", "simple language", "technical"],
                            index=0,
                            key=f"{key}_sum_tone"
                        )
                        if st.button("🔄 Regenerate Summary", key=f"{key}_regen"):
                            with st.spinner("Regenerating..."):
                                r = requests.post(f"{BACKEND_URL}/ai-edit", data={
                                    "text": pdf["extracted_text"],
                                    "instruction": f"Summarize this text in a {sum_tone} way",
                                    "tone": sum_tone
                                })
                            if r.status_code == 200:
                                st.session_state.multi_pdfs[idx]["summary"] = r.json().get("edited_text", pdf["summary"])
                                st.rerun()

                    if pdf["summary"]:
                        st.info(pdf["summary"])
                    else:
                        st.warning("No summary available.")

                # ── Tab 2: Edit & Download ─────────────────
                with tabs[1]:
                    edited = st.text_area(
                        "Edit content",
                        value=pdf["edited_text"],
                        height=350,
                        key=f"{key}_edit_area",
                        label_visibility="collapsed"
                    )

                    col1, col2, col3 = st.columns([1, 1, 2])
                    with col1:
                        if st.button("💾 Save", use_container_width=True, key=f"{key}_save"):
                            st.session_state.multi_pdfs[idx]["edited_text"] = edited
                            st.session_state.multi_pdfs[idx]["edit_saved"]  = True
                            st.success("✅ Saved!")
                    with col2:
                        if st.button("↩️ Reset", use_container_width=True, key=f"{key}_reset"):
                            st.session_state.multi_pdfs[idx]["edited_text"] = pdf["extracted_text"]
                            st.session_state.multi_pdfs[idx]["edit_saved"]  = False
                            st.info("Reset to original.")
                    with col3:
                        with st.expander("🤖 AI Edit Assist"):
                            ai_inst = st.text_input("Instruction", value="Improve clarity and fix grammar", key=f"{key}_ai_inst")
                            ai_tone = st.selectbox("Tone", ["professional", "casual", "formal", "simple"], key=f"{key}_ai_tone")
                            if st.button("✨ Apply AI Edit", key=f"{key}_ai_apply"):
                                with st.spinner("AI editing..."):
                                    r = requests.post(f"{BACKEND_URL}/ai-edit", data={
                                        "text": edited,
                                        "instruction": ai_inst,
                                        "tone": ai_tone
                                    })
                                if r.status_code == 200:
                                    st.session_state.multi_pdfs[idx]["edited_text"] = r.json().get("edited_text", edited)
                                    st.session_state.multi_pdfs[idx]["edit_saved"]  = True
                                    st.success("✅ AI edits applied!")
                                    st.rerun()

                    st.markdown("---")
                    if st.button("📄 Generate PDF", use_container_width=True, key=f"{key}_gen"):
                        current_text = st.session_state.multi_pdfs[idx]["edited_text"]
                        with st.spinner("Building PDF..."):
                            dl_r = requests.post(
                                f"{BACKEND_URL}/download-edited-pdf",
                                data={"edited_text": current_text, "filename": pdf["filename"]}
                            )
                        if dl_r.status_code == 200:
                            fname = pdf["filename"].replace(".pdf", "") + "_edited.pdf"
                            st.download_button(
                                label=f"⬇️ Download {fname}",
                                data=dl_r.content,
                                file_name=fname,
                                mime="application/pdf",
                                use_container_width=True,
                                key=f"{key}_dl"
                            )
                            st.success("✅ Ready!")
                        else:
                            st.error("❌ Failed to generate PDF.")