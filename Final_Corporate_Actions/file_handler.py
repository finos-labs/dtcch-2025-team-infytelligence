# file_handler.py
import os
import uuid
import zipfile
import tempfile
import fitz  # PyMuPDF
import io
from PIL import Image

class FileHandler:
    def __init__(self):
        self.upload_dir = "uploads"
        self.output_dir = "output"
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

    def save_uploaded_files(self, uploaded_files):
        file_paths = []
        for file in uploaded_files:
            if file.name.lower().endswith(".zip"):
                # Unzip to temp directory
                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(file) as zip_ref:
                        zip_ref.extractall(tmpdir)

                    # Traverse and find all PDFs
                    for root, _, files in os.walk(tmpdir):
                        for fname in files:
                            if fname.lower().endswith(".pdf"):
                                src = os.path.join(root, fname)
                                # Generate a unique filename for each PDF
                                unique_filename = f"{uuid.uuid4()}_{fname}"
                                dest = os.path.join(self.upload_dir, unique_filename)
                                os.rename(src, dest)  # won't fail with collisions now
                                file_paths.append(dest)
            else:
                # It's a single PDF
                unique_name = f"{uuid.uuid4()}_{file.name}"
                dest = os.path.join(self.upload_dir, unique_name)
                with open(dest, "wb") as f_out:
                    f_out.write(file.getbuffer())
                file_paths.append(dest)

        return file_paths

    def extract_text_from_pdf(self, file_path):
        doc_text = []
        with fitz.open(file_path) as doc:
            for page in doc:
                doc_text.append(page.get_text())
        return "\n".join(doc_text)

    def get_preview_image(self, file_path):
        try:
            with fitz.open(file_path) as doc:
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    return image
        except:
            pass
        return None 