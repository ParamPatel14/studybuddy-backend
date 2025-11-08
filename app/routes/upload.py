from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.services.pdf_service import PDFService
from app.services.ai_service import AIService
from app.models.models import UploadedFile
from typing import List, Optional
import traceback
import json

router = APIRouter(prefix="/api/upload", tags=["upload"])
pdf_service = PDFService()
ai_service = AIService()

@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    plan_id: Optional[int] = Form(None),
    file_type: str = Form("pyq"),
    db: Session = Depends(get_db)
):
    """
    Step 1: Upload PDF, extract text, and save to JSON
    Returns the JSON path for later use
    """
    
    # Validate file type
    if not pdf_service.validate_pdf(file):
        raise HTTPException(status_code=400, detail="File must be a PDF")
    
    try:
        print(f"\n{'='*60}")
        print(f"📄 Processing file: {file.filename}")
        print(f"   Type: {file_type}")
        print(f"{'='*60}")
        
        # Step 1: Read file content
        file_content = await file.read()
        print(f"✓ File read successfully: {len(file_content)} bytes")
        
        # Step 2: Save original PDF
        pdf_path = pdf_service.save_pdf_file(file_content, file.filename)
        print(f"✓ PDF saved to: {pdf_path}")
        
        # Step 3: Extract text from PDF
        # Reset file pointer for extraction
        await file.seek(0)
        extracted_text = await pdf_service.extract_text_from_pdf(file)
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="No text could be extracted from PDF")
        
        print(f"✓ Text extracted successfully: {len(extracted_text)} characters")
        
        # Step 4: Save extracted text to JSON
        json_data = pdf_service.save_extracted_text_to_json(
            text=extracted_text,
            filename=file.filename,
            file_type=file_type
        )
        
        print(f"✓ Extracted text saved to JSON")
        print(f"   JSON file: {json_data['json_filename']}")
        print(f"   Preview: {json_data['preview'][:100]}...")
        
        # Step 5: Save metadata to database if plan_id exists
        if plan_id:
            uploaded_file = UploadedFile(
                plan_id=plan_id,
                filename=file.filename,
                file_type=file_type,
                extracted_text=extracted_text[:1000]  # Store only preview in DB
            )
            db.add(uploaded_file)
            db.commit()
            db.refresh(uploaded_file)
            print(f"✓ Saved to database with ID: {uploaded_file.id}")
        
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "filename": file.filename,
            "file_type": file_type,
            "text_length": len(extracted_text),
            "json_path": json_data['json_path'],
            "json_filename": json_data['json_filename'],
            "preview": json_data['preview']
        }
            
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n❌ ERROR in upload_pdf:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")

@router.post("/extract-topics-from-json")
async def extract_topics_from_json(
    json_paths: List[str]
):
    """
    Step 2: Read text from JSON files and extract topics using Gemini
    This separates file upload from AI processing
    """
    try:
        print(f"\n{'='*60}")
        print(f"🤖 Extracting topics from JSON files")
        print(f"   Number of files: {len(json_paths)}")
        print(f"{'='*60}")
        
        # Step 1: Read and combine text from all JSON files
        combined_text = pdf_service.combine_multiple_json_texts(json_paths)
        
        if not combined_text or len(combined_text.strip()) == 0:
            raise HTTPException(status_code=400, detail="No text found in JSON files")
        
        print(f"✓ Combined text length: {len(combined_text)} characters")
        print(f"   Preview: {combined_text[:200]}...")
        
        # Step 2: Extract subject from first JSON (or use default)
        first_json_data = pdf_service.read_extracted_text_from_json(json_paths[0])
        subject = first_json_data.get('subject', 'General Studies')
        
        # Step 3: Send to Gemini for topic extraction
        print(f"📤 Sending to Gemini API for topic extraction...")
        topics = await ai_service.extract_topics(combined_text, subject)
        
        print(f"✓ Topics extracted successfully: {len(topics)} topics")
        for i, topic in enumerate(topics, 1):
            print(f"   {i}. {topic['name']} (weight: {topic['weight']})")
        
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "topics": topics,
            "model": "gemini-2.5-pro",
            "source_files": len(json_paths),
            "text_length": len(combined_text)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n❌ ERROR in extract_topics_from_json:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=f"Error extracting topics: {str(e)}")

@router.post("/extract-topics")
async def extract_topics_legacy(
    text: str,
    subject: str
):
    """
    Legacy endpoint: Direct text to Gemini (kept for backward compatibility)
    """
    try:
        print(f"\n{'='*60}")
        print(f"🤖 Direct topic extraction (legacy method)")
        print(f"   Subject: {subject}")
        print(f"   Text length: {len(text)}")
        print(f"{'='*60}")
        
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="Text cannot be empty")
        
        topics = await ai_service.extract_topics(text, subject)
        
        print(f"✓ Topics extracted: {len(topics)} topics")
        print(f"{'='*60}\n")
        
        return {
            "success": True,
            "topics": topics,
            "model": "gemini-2.5-pro"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"\n❌ ERROR in extract_topics_legacy:")
        print(error_trace)
        raise HTTPException(status_code=500, detail=f"Error extracting topics: {str(e)}")

@router.get("/list-extracted-files")
async def list_extracted_files():
    """List all extracted JSON files for debugging"""
    import os
    extracted_dir = "uploads/extracted_texts"
    
    if not os.path.exists(extracted_dir):
        return {"files": []}
    
    files = []
    for filename in os.listdir(extracted_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(extracted_dir, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            files.append({
                "filename": filename,
                "filepath": filepath,
                "original_filename": data.get('filename'),
                "file_type": data.get('file_type'),
                "text_length": data.get('text_length'),
                "extracted_at": data.get('extracted_at')
            })
    
    return {"files": files}

@router.get("/read-json/{filename}")
async def read_json_file(filename: str):
    """Read and return content of a specific JSON file"""
    import os
    json_path = os.path.join("uploads/extracted_texts", filename)
    
    if not os.path.exists(json_path):
        raise HTTPException(status_code=404, detail="JSON file not found")
    
    try:
        data = pdf_service.read_extracted_text_from_json(json_path)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
