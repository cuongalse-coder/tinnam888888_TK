"""
OCR module: Trích xuất text từ PDF/ảnh scan bằng EasyOCR.

Workflow:
1. pdfplumber extract text → nếu text rỗng/quá ngắn
2. Chuyển PDF page thành ảnh (dùng pdfplumber hoặc pdf2image)
3. EasyOCR đọc ảnh → trả text
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy-load EasyOCR reader (tải model 1 lần)
_ocr_reader = None


def _get_reader():
    """Lazy init EasyOCR reader."""
    global _ocr_reader
    if _ocr_reader is None:
        try:
            import easyocr
            logger.info("Đang khởi tạo EasyOCR reader (lần đầu sẽ tải model)...")
            _ocr_reader = easyocr.Reader(
                ['en'],  # Tiếng Anh đủ cho B/L (chứng từ quốc tế)
                gpu=False,  # CPU mode cho tương thích
                verbose=False,
            )
            logger.info("EasyOCR reader sẵn sàng.")
        except ImportError:
            logger.warning("EasyOCR chưa cài. Chạy: pip install easyocr")
            return None
        except Exception as e:
            logger.error("Lỗi khởi tạo EasyOCR: %s", e)
            return None
    return _ocr_reader


def ocr_pdf_page(page, dpi: int = 200) -> str:
    """OCR một trang PDF (pdfplumber page object) → text.
    
    Parameters
    ----------
    page : pdfplumber.page.Page
        Trang PDF cần OCR.
    dpi : int
        Độ phân giải khi render ảnh (mặc định 200).
    
    Returns
    -------
    str
        Text trích xuất từ OCR, hoặc chuỗi rỗng nếu thất bại.
    """
    reader = _get_reader()
    if reader is None:
        return ""

    try:
        # Chuyển PDF page thành PIL Image
        img = page.to_image(resolution=dpi).original

        # Chuyển sang bytes để EasyOCR đọc
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='PNG')
        img_bytes.seek(0)

        # OCR
        results = reader.readtext(img_bytes.getvalue(), detail=0, paragraph=True)
        text = "\n".join(results)
        return text

    except Exception as e:
        logger.error("OCR lỗi: %s", e)
        return ""


def ocr_image_file(image_path: str) -> str:
    """OCR một file ảnh (PNG/JPG/TIFF) → text.
    
    Parameters
    ----------
    image_path : str
        Đường dẫn tới file ảnh.
    
    Returns
    -------
    str
        Text trích xuất từ OCR.
    """
    reader = _get_reader()
    if reader is None:
        return ""

    try:
        results = reader.readtext(image_path, detail=0, paragraph=True)
        return "\n".join(results)
    except Exception as e:
        logger.error("OCR ảnh lỗi: %s", e)
        return ""


def extract_text_with_ocr_fallback(pdf_path: str, max_pages: int = 3) -> str:
    """Trích xuất text từ PDF, tự động fallback sang OCR nếu cần.
    
    Parameters
    ----------
    pdf_path : str
        Đường dẫn file PDF.
    max_pages : int
        Số trang tối đa cần xử lý.
    
    Returns
    -------
    str
        Text tổng hợp từ tất cả trang.
    """
    import pdfplumber

    all_text = []
    ocr_used = False

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages[:max_pages]):
                # Thử pdfplumber trước
                text = page.extract_text() or ""

                # Nếu text quá ngắn (< 50 ký tự) → có thể là ảnh scan
                if len(text.strip()) < 50:
                    logger.info("Trang %d: text ngắn (%d chars), thử OCR...", i + 1, len(text.strip()))
                    ocr_text = ocr_pdf_page(page)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        ocr_used = True
                        logger.info("Trang %d: OCR thành công (%d chars)", i + 1, len(ocr_text.strip()))

                all_text.append(text)

    except Exception as e:
        logger.error("Lỗi đọc PDF %s: %s", pdf_path, e)

    return "\n".join(all_text), ocr_used


def is_ocr_available() -> bool:
    """Kiểm tra EasyOCR có sẵn không."""
    try:
        import easyocr
        return True
    except ImportError:
        return False
