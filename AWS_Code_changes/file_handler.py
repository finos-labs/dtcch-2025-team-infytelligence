# file_handler.py
import os
import uuid
import boto3
import zipfile
import tempfile
import fitz  # PyMuPDF
import io
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

class FileHandler:
    def __init__(self):
        self.s3 = boto3.client("s3")
        self.bucket_name = os.getenv("BUCKET_NAME", "infy-corporate-actions-input")

    def save_uploaded_files(self, uploaded_files):
        """
        If you want to upload PDFs from a local machine via Streamlit, this will store them in S3.
        Return a list of S3 keys for each uploaded file.
        """
        file_keys = []
        for file in uploaded_files:
            if file.name.lower().endswith(".zip"):
                with tempfile.TemporaryDirectory() as tmpdir:
                    with zipfile.ZipFile(file) as zip_ref:
                        zip_ref.extractall(tmpdir)
                    for root, _, files in os.walk(tmpdir):
                        for fname in files:
                            if fname.lower().endswith(".pdf"):
                                unique_filename = f"{uuid.uuid4()}_{fname}"
                                s3_key = f"uploads/{unique_filename}"
                                local_path = os.path.join(root, fname)
                                self.s3.upload_file(local_path, self.bucket_name, s3_key)
                                file_keys.append(s3_key)
            else:
                # Single PDF
                unique_name = f"{uuid.uuid4()}_{file.name}"
                s3_key = f"uploads/{unique_name}"
                self.s3.upload_fileobj(file, self.bucket_name, s3_key)
                file_keys.append(s3_key)
        return file_keys

    def extract_text_from_pdf(self, s3_key):
        """
        Download the PDF from S3 into an in-memory buffer, use PyMuPDF to extract text.
        """
        pdf_stream = io.BytesIO()
        self.s3.download_fileobj(self.bucket_name, s3_key, pdf_stream)
        pdf_stream.seek(0)

        doc_text = []
        with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
            for page in doc:
                doc_text.append(page.get_text())
        return "\n".join(doc_text)

    def get_preview_image(self, s3_key):
        """
        Return a PIL Image of page 1 so Streamlit can show a preview.
        """
        try:
            pdf_stream = io.BytesIO()
            self.s3.download_fileobj(self.bucket_name, s3_key, pdf_stream)
            pdf_stream.seek(0)
            with fitz.open(stream=pdf_stream, filetype="pdf") as doc:
                if doc.page_count > 0:
                    page = doc.load_page(0)
                    pix = page.get_pixmap()
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    return image
        except Exception as e:
            print(f"Preview image error: {e}")
        return None

    def save_json_to_s3(self, data, s3_key):
        """
        Serialize `data` as JSON and upload to S3 at the given s3_key (e.g. 'output/my_data.json').
        """
        import json
        self.s3.put_object(
            Bucket=self.bucket_name,
            Key=s3_key,
            Body=json.dumps(data, indent=2),
            ContentType="application/json"
        )
        return f"s3://{self.bucket_name}/{s3_key}"

    def upload_file_to_s3(self, local_file_path, s3_key):
        """
        Upload any local file to S3 (e.g., a generated PDF).
        """
        self.s3.upload_file(local_file_path, self.bucket_name, s3_key)
        return f"s3://{self.bucket_name}/{s3_key}"
