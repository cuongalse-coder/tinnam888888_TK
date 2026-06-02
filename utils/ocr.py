"""
OCR module: Trích xuất text từ PDF scan bằng Google Gemini Native OCR.

Bỏ qua EasyOCR để tránh lỗi PyTorch nặng, dùng trực tiếp Gemini Vision.
"""
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def ocr_pdf_page(page, api_key: str = "", dpi: int = 200, ocr_languages: list[str] | None = None) -> str:
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
            
            # Map Tesseract language codes from Streamlit UI to EasyOCR codes
            easyocr_langs = []
            if ocr_languages:
                for lang in ocr_languages:
                    if lang == 'vie': easyocr_langs.append('vi')
                    elif lang == 'eng': easyocr_langs.append('en')
                    elif lang == 'chi_sim': easyocr_langs.append('ch_sim')
                    elif lang == 'chi_tra': easyocr_langs.append('ch_tra')
            
            if not easyocr_langs:
                easyocr_langs = ['vi', 'en']
                
            # Xử lý xung đột EasyOCR: Không thể mix tiếng Trung và tiếng Việt cùng lúc
            if 'ch_sim' in easyocr_langs or 'ch_tra' in easyocr_langs:
                easyocr_langs = [l for l in easyocr_langs if l != 'vi'] # Xóa 'vi' để tránh lỗi ValueError
                if 'ch_sim' in easyocr_langs and 'ch_tra' in easyocr_langs:
                    easyocr_langs.remove('ch_tra') # Không thể mix cả 2 loại tiếng Trung
            
            if 'en' not in easyocr_langs:
                easyocr_langs.append('en') # Luôn thêm tiếng Anh để nhận diện số và ký tự Latin
            
            # Khởi tạo reader lưu model vào ổ E:
            reader = easyocr.Reader(easyocr_langs, model_storage_directory='E:/EasyOCR_Models', download_enabled=True)
            # Chuyển PIL sang numpy array
            img_np = np.array(img)
            
            # Sử dụng detail=1 để lấy tọa độ bbox, phục vụ việc giữ nguyên cấu trúc dòng (layout)
            result = reader.readtext(img_np, detail=1)
            
            if not result:
                return ""
                
            # Sắp xếp các bounding box theo tọa độ Y (top-left) từ trên xuống dưới
            result.sort(key=lambda item: item[0][0][1])
            
            lines = []
            current_line = []
            current_y = None
            
            # Tính toán threshold Y dựa trên chiều cao trung bình của text box (thường khoảng 15-20 pixels)
            # Thay vì set cứng, dùng 15 pixels làm mặc định
            y_threshold = 15 
            
            for bbox, text, prob in result:
                y = bbox[0][1]
                x = bbox[0][0]
                
                # Chiều cao của bbox (y2 - y1)
                h = bbox[2][1] - bbox[0][1]
                # Dùng một nửa chiều cao làm threshold để xem có cùng dòng hay không
                dyn_threshold = max(h * 0.5, 10)
                
                if current_y is None:
                    current_y = y
                    current_line.append((x, text))
                elif abs(y - current_y) < dyn_threshold:
                    current_line.append((x, text))
                    # Cập nhật Y trung bình của dòng
                    current_y = (current_y * (len(current_line) - 1) + y) / len(current_line)
                else:
                    # Sort các text box trong cùng 1 dòng theo tọa độ X từ trái sang phải
                    current_line.sort(key=lambda item: item[0])
                    # Nối bằng phím tab để regex của parser.py có thể nhận diện dạng bảng
                    lines.append("\t".join([item[1] for item in current_line]))
                    current_line = [(x, text)]
                    current_y = y
                    
            if current_line:
                current_line.sort(key=lambda item: item[0])
                lines.append("\t".join([item[1] for item in current_line]))
                
            return "\n".join(lines)
            
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
