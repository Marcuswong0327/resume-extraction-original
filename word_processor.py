import docx
import streamlit as st
from io import BytesIO


class WordProcessor:
    """Handles Word documents (.docx) and legacy Word 97-2003 (.doc) text extraction."""

    def __init__(self):
        pass

    def _extract_text_from_doc_bytes(self, doc_bytes: bytes) -> str:
        """
        Extract plain text from a legacy .doc (binary) file using Spire.Doc (pip install only;
        no LibreOffice or Microsoft Word on the host).
        """
        try:
            from spire.doc import Document, FileFormat
            from spire.doc.common import Stream
        except ImportError:
            st.error(
                "Legacy .doc support requires the `spire.doc` package. "
                "Add it to requirements.txt and redeploy (e.g. `pip install spire.doc`)."
            )
            return ""

        stream = None
        doc = None
        try:
            stream = Stream(doc_bytes)
            doc = Document(stream, FileFormat.Doc)
            text = doc.GetText()
            return (text or "").strip()
        except Exception as e:
            st.error(f"Could not read legacy .doc file: {e}")
            return ""
        finally:
            if doc is not None:
                try:
                    doc.Dispose()
                except Exception:
                    pass
            if stream is not None:
                try:
                    stream.Dispose()
                except Exception:
                    pass

    def extract_text_from_docx(self, file_path_or_bytes):
        """
        Extract text from DOCX file.
        Accepts a file path or BytesIO object.
        """
        try:
            document = docx.Document(file_path_or_bytes)

            text_content = []

            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text.strip())

            for table in document.tables:
                for row in table.rows:
                    for cell in row.cells:
                        if cell.text.strip():
                            text_content.append(cell.text.strip())

            return "\n".join(text_content)

        except Exception as e:
            st.error(f"Error extracting text from DOCX file: {str(e)}")
            return ""

    def process_word_file(self, uploaded_file):
        """
        Process DOCX (python-docx) or legacy DOC (Spire.Doc text extraction).
        """
        try:
            file_extension = uploaded_file.name.lower().split(".")[-1]

            if file_extension == "docx":
                file_content = uploaded_file.read()
                return self.extract_text_from_docx(BytesIO(file_content))

            if file_extension == "doc":
                file_content = uploaded_file.read()
                return self._extract_text_from_doc_bytes(file_content)

            st.error(f"Unsupported file format: {file_extension}")
            return ""

        except Exception as e:
            st.error(f"Error processing Word file: {str(e)}")
            return ""
