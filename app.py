import streamlit as st
import requests

st.set_page_config(
    page_title="AI PDF Assistant",
    page_icon="📄",
    layout="centered"
)

st.title("📄 AI PDF Assistant")
st.write("Upload a PDF and get an AI-generated summary.")

uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type=["pdf"]
)

if uploaded_file is not None:
    st.success(f"Selected: {uploaded_file.name}")

    if st.button("✨ Summarize PDF"):
        with st.spinner("Reading and summarizing your PDF..."):
            files = {
                "file": (
                    uploaded_file.name,
                    uploaded_file.getvalue(),
                    "application/pdf",
                )
            }

            try:
                response = requests.post(
                    "http://127.0.0.1:8000/upload-pdf",
                    files=files,
                    timeout=300,
                )

                if response.status_code == 200:
                    data = response.json()

                    st.subheader("📝 Summary")
                    st.write(data.get("summary", "No summary returned."))

                else:
                    st.error(f"Server returned status code {response.status_code}")
                    st.text(response.text)

            except Exception as e:
                st.error(f"Error: {e}")