import logging
import pdfplumber
import httpx
import io
import asyncio
from datetime import datetime
from scraper.date_extractor import extract_date
from core.config import SSL_VERIFY_EXEMPT

logger = logging.getLogger("PDF_PROCESSOR")

def _process_pdf_sync(pdf_bytes):
    """Synchronous CPU-bound PDF parsing."""
    try:
        with pdfplumber.open(pdf_bytes) as pdf:
            if not pdf.pages:
                return None
            
            # 1. Metadata Check
            meta_date = pdf.metadata.get('CreationDate')
            if meta_date and "2026" in meta_date:
                try:
                    return datetime.strptime(meta_date[2:10], "%Y%m%d")
                except:
                    pass

            # 2. Header Area Check (Top 25%)
            p = pdf.pages[0]
            header_area = (0, 0, p.width, p.height * 0.25)
            header_text = p.within_bbox(header_area).extract_text()
            
            found_date = extract_date(header_text)
            if found_date:
                return found_date
            
            # 3. Full Page Fallback
            return extract_date(p.extract_text())
    except Exception as e:
        logger.error(f"Internal PDF Parsing Error: {e}")
        return None

async def get_date_from_pdf(pdf_url):
    """Asynchronous wrapper for PDF downloading and parsing[cite: 98]."""
    # Determine SSL verification 
    verify = not any(domain in pdf_url for domain in SSL_VERIFY_EXEMPT)
    
    try:
        async with httpx.AsyncClient(verify=verify, timeout=20.0) as client:
            response = await client.get(pdf_url)
            if response.status_code != 200:
                return None
            
            pdf_bytes = io.BytesIO(response.content)
            
            # FIX: Offload CPU-bound task to thread to prevent loop blocking [cite: 100]
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _process_pdf_sync, pdf_bytes)

    except Exception as e:
        logger.error(f"PDF Download Error: {pdf_url} | {e}")
        return None