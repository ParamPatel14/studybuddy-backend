import PyPDF2
from io import BytesIO
from fastapi import UploadFile
import json
import os
from datetime import datetime

class PDFService:
    def __init__(self):
        self.upload_dir = "uploads/pdfs"
        self.extracted_dir = "uploads/extracted_texts"
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(self.extracted_dir, exist_ok=True)
    
    @staticmethod
    async def extract_text_from_pdf(file: UploadFile) -> str:
        """Extract text content from uploaded PDF file"""
        try:
            content = await file.read()
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            
            extracted_text = ""
            for page_num, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    extracted_text += f"\n--- Page {page_num + 1} ---\n"
                    extracted_text += text + "\n"
            
            return extracted_text.strip()
        except Exception as e:
            raise Exception(f"Error extracting PDF text: {str(e)}")
    
    @staticmethod
    def validate_pdf(file: UploadFile) -> bool:
        """Validate if uploaded file is a PDF"""
        return file.content_type == "application/pdf" or file.filename.endswith('.pdf')
    
    def save_pdf_file(self, file_content: bytes, filename: str) -> str:
        """Save PDF file to disk"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        file_path = os.path.join(self.upload_dir, safe_filename)
        
        with open(file_path, "wb") as f:
            f.write(file_content)
        
        return file_path
    
    def save_extracted_text_to_json(self, text: str, filename: str, file_type: str) -> dict:
        """Save extracted text to JSON file and return metadata"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"{timestamp}_{file_type}_{filename.replace('.pdf', '')}.json"
        json_path = os.path.join(self.extracted_dir, json_filename)
        
        data = {
            "filename": filename,
            "file_type": file_type,
            "extracted_at": timestamp,
            "text_length": len(text),
            "text": text,
            "preview": text[:500] if len(text) > 500 else text
        }
        
        # Write to JSON file
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"✓ Saved extracted text to: {json_path}")
        return {
            "json_path": json_path,
            "json_filename": json_filename,
            **data
        }
    
    def read_extracted_text_from_json(self, json_path: str) -> dict:
        """Read extracted text from JSON file"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception as e:
            raise Exception(f"Error reading JSON file: {str(e)}")
    
    def combine_multiple_json_texts(self, json_paths: list) -> str:
        """Combine text from multiple JSON files"""
        combined_text = ""
        
        for json_path in json_paths:
            if os.path.exists(json_path):
                data = self.read_extracted_text_from_json(json_path)
                file_type = data.get('file_type', 'unknown')
                combined_text += f"\n\n{'='*50}\n"
                combined_text += f"SOURCE: {file_type.upper()} - {data.get('filename', 'unknown')}\n"
                combined_text += f"{'='*50}\n\n"
                combined_text += data.get('text', '')
        
        return combined_text
