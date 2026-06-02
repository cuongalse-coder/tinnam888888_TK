"""
OCR module: Trích xuất text từ PDF scan bằng Google Gemini Native OCR.

Bỏ qua EasyOCR để tránh lỗi PyTorch nặng, dùng trực tiếp Gemini Vision.
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def ocr_pdf_page(page, api_key: str = "", dpi: int = 200) -> str:
    """OCR một trang PDF bằng Gemini Vision (ưu tiên) hoặc EasyOCR (local fallback)."""
    try:
        # Chuyển PDF page thành PIL Image
        img = page.to_image(resolution=dpi).original
        
        if api_key:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = "Extract all text from this image exactly as written. Return ONLY the raw text, no markdown formatting. If there is no text, return empty."
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, img],
            )
            return response.text.strip() if response.text else ""
        else:
            # Fallback to local EasyOCR
            logger.info("Không có API Key, sử dụng EasyOCR Local Fallback...")
            import easyocr
            import numpy as np
            # Khởi tạo reader lưu model vào ổ E:
            reader = easyocr.Reader(['vi', 'en'], model_storage_directory='E:/EasyOCR_Models', download_enabled=True)
            # Chuyển PIL sang numpy array
            img_np = np.array(img)
            result = reader.readtext(img_np, detail=0, paragraph=True)
            return "\n".join(result)
            
    except Exception as e:
        logger.error("OCR lỗi: %s", e)
        return ""


def extract_text_with_ocr_fallback(pdf_path: str, api_key: str = "", max_pages: int = 3) -> str:
    """Trích xuất text từ PDF, tự động fallback sang OCR nếu cần.
    
    Parameters
    ----------
    pdf_path : str
        Đường dẫn file PDF.
    api_key : str
        Gemini API Key
    max_pages : int
        Số trang tối đa cần xử lý.
    
    Returns
    -------
    tuple(str, bool)
        Text tổng hợp từ tất cả trang, và cờ báo có dùng OCR hay không.
    """
    import pdfplumber

    all_text = []
    ocr_used = False

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                text = page.extract_text() or ""
                if len(text.strip()) < 50:
                    ocr_text = ocr_pdf_page(page, api_key)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        ocr_used = True

                all_text.append(text)

    except Exception as e:
        logger.error("Lỗi đọc PDF %s: %s", pdf_path, e)

    return "\n".join(all_text), ocr_used


def is_ocr_available() -> bool:
    """Luôn True vì giờ dùng Gemini API thay vì thư viện local."""
    return True
