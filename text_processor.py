import streamlit as st


class TextProcessor:
    """Handles plain text (.txt) resume uploads."""

    def process_text_file(self, uploaded_file):
        raw = uploaded_file.read()
        for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
