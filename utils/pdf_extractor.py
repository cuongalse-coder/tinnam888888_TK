import io
import re
import fitz  # PyMuPDF
import pdfplumber
import numpy as np
from PIL import Image
import pytesseract
import cv2
import os

# Cấu hình đường dẫn Tesseract (dựa trên cài đặt chuẩn Windows)
tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path
# Môi trường Linux trên Streamlit Cloud
elif os.path.exists('/usr/bin/tesseract'):
    pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'

# Cấu hình thư mục chứa dữ liệu ngôn ngữ (tessdata) cục bộ nếu chạy trên Windows
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tessdata_dir = os.path.join(project_dir, 'tessdata')
if os.path.exists(tessdata_dir):
    os.environ['TESSDATA_PREFIX'] = tessdata_dir

# Cấu hình tiếng Việt cho Tesseract
TESS_CONFIG = r'--oem 3 --psm 6 -l vie+eng'

def is_scanned_pdf(pdf_bytes: bytes, text_threshold: int = 50) -> bool:
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            total_text = ""
            for page in pdf.pages[:2]:
                t = page.extract_text() or ""
                total_text += t
        return len(total_text.strip()) < text_threshold
    except Exception:
        return True

def preprocess_image_for_ocr(pil_image: Image.Image) -> Image.Image:
    img = np.array(pil_image)
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    else:
        gray = img
    
    # Tiền xử lý để đọc chữ rõ hơn
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 5)
    return Image.fromarray(binary)

def extract_text_from_pdf(pdf_bytes: bytes) -> dict:
    result = {"pages": [], "full_text": "", "is_scanned": False, "tables": []}
    scanned = is_scanned_pdf(pdf_bytes)
    result["is_scanned"] = scanned

    if scanned:
        result["pages"] = _extract_ocr(pdf_bytes)
    else:
        result["pages"] = _extract_text_and_tables(pdf_bytes)

    all_texts = [p["text"] for p in result["pages"]]
    result["full_text"] = "\n".join(all_texts)
    
    # Gộp tất cả bảng
    for page in result["pages"]:
        if page.get("tables"):
            result["tables"].extend(page["tables"])
            
    return result

def _extract_text_and_tables(pdf_bytes: bytes) -> list:
    pages = []
    try:
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(x_tolerance=2, y_tolerance=2) or ""
                
                # Trích xuất bảng
                tables = []
                raw_tables = page.extract_tables()
                if raw_tables:
                    for tbl in raw_tables:
                        clean_tbl = []
                        for row in tbl:
                            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            clean_tbl.append(clean_row)
                        tables.append(clean_tbl)
                
                pages.append({"page_num": i + 1, "text": page_text, "tables": tables, "is_ocr": False})
    except Exception:
        pass
    return pages

def _extract_ocr(pdf_bytes: bytes) -> list:
    pages = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for i in range(len(doc)):
            page = doc[i]
            mat = fitz.Matrix(2.0, 2.0)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            pil_img = Image.open(io.BytesIO(pix.tobytes("png")))
            processed_img = preprocess_image_for_ocr(pil_img)
            
            try:
                page_text = pytesseract.image_to_string(processed_img, config=TESS_CONFIG)
            except Exception:
                page_text = pytesseract.image_to_string(pil_img)
            
            pages.append({"page_num": i + 1, "text": page_text, "tables": [], "is_ocr": True})
        doc.close()
    except Exception:
        pass
    return pages

def parse_customs_declaration(text: str) -> dict:
    """Thuật toán bóc tách dữ liệu Tờ Khai VNACCS chính xác cao"""
    data = {}
    
    # Chuẩn hóa khoảng trắng để dễ regex
    text_norm = re.sub(r'\s+', ' ', text)
    
    def extract_field(pattern, default="Không tìm thấy"):
        match = re.search(pattern, text_norm, re.IGNORECASE)
        return match.group(1).strip() if match else default

    # 1. Thông tin chung
    data['Số Tờ Khai'] = extract_field(r'(?:Số TK|Số tờ khai|SỐ TK)\s*[:\-]?\s*([0-9]{10,12})')
    data['Ngày Đăng Ký'] = extract_field(r'(?:Ngày đăng ký|Ngày ĐK)\s*[:\-]?\s*([0-9]{2}/[0-9]{2}/[0-9]{4})')
    data['Mã Loại Hình'] = extract_field(r'(?:Mã loại hình|Mã LH)\s*[:\-]?\s*([A-Z0-9]{3,5})')
    data['Cơ Quan Hải Quan'] = extract_field(r'(?:Cơ quan Hải quan|Hải quan|HQ)\s*[:\-]?\s*([^0-9]+?)(?=\sMã|\sNgày|\sSố|$)')
    
    # 2. Thông tin doanh nghiệp
    data['Người Xuất Khẩu'] = extract_field(r'(?:Người xuất khẩu|Người gửi hàng)\s*[:\-]?\s*(.+?)(?=\sMã|\sĐịa chỉ|\sNgười nhập khẩu)')
    data['Mã số thuế NXK'] = extract_field(r'Mã(?: số thuế)?\s*[:\-]?\s*([0-9\-\s]{10,14})')
    data['Người Nhập Khẩu'] = extract_field(r'(?:Người nhập khẩu|Người nhận hàng)\s*[:\-]?\s*(.+?)(?=\sMã|\sĐịa chỉ|\sĐại lý)')
    
    # 3. Thông tin vận tải
    data['Số Vận Đơn (B/L)'] = extract_field(r'(?:Số vận đơn|B/L|Số B/L|Số Vận Đơn)\s*[:\-]?\s*([A-Z0-9\-]+)')
    data['Số Lượng Kiện'] = extract_field(r'(?:Số lượng kiện|Số kiện)\s*[:\-]?\s*([0-9\,\.]+)')
    data['Tổng Trọng Lượng (Gross Weight)'] = extract_field(r'(?:Tổng trọng lượng|Gross weight)\s*[:\-]?\s*([0-9\,\.]+\s*[A-Z]+)')
    
    # 4. Trị giá & Thuế
    data['Tổng Trị Giá Hóa Đơn'] = extract_field(r'(?:Tổng trị giá hóa đơn|Trị giá hóa đơn)\s*[:\-]?\s*([0-9\.,]+\s*[A-Z]{3})')
    data['Điều Kiện Giao Hàng'] = extract_field(r'(?:Điều kiện giao hàng|ĐK giao hàng)\s*[:\-]?\s*([A-Z]{3})')
    
    # 5. Thông tin Hàng hóa (Bắt danh sách các mã HS)
    hs_codes = re.findall(r'\b([0-9]{4}\.[0-9]{2}\.[0-9]{2})\b', text_norm)
    data['Các Mã HS'] = ", ".join(sorted(list(set(hs_codes)))) if hs_codes else "Không tìm thấy"

    return data
