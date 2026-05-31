"""Module trích xuất nội dung từ các định dạng tài liệu khác nhau.

Hỗ trợ: Excel (.xlsx, .xls), CSV (.csv), PDF (.pdf),
         Hình ảnh (.jpg, .jpeg, .png), Word (.docx).

Mỗi hàm trả về dict chuẩn chứa ``raw_text`` và dữ liệu có cấu trúc,
hoặc ``{'error': str}`` nếu xảy ra lỗi.
"""

from __future__ import annotations

import csv
import io
from pathlib import PurePosixPath
from typing import Any

import pandas as pd
import pdfplumber
import pytesseract
from docx import Document
from PIL import Image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_seek(file: Any) -> None:
    """Đặt lại con trỏ đọc về đầu nếu có thể."""
    if hasattr(file, "seek"):
        file.seek(0)


def _file_ext(file: Any) -> str:
    """Trả về phần mở rộng file (viết thường, bao gồm dấu chấm)."""
    name: str = getattr(file, "name", "")
    return PurePosixPath(name).suffix.lower()


def _dataframe_to_raw_text(df: pd.DataFrame) -> str:
    """Chuyển DataFrame thành chuỗi text thô (tab-separated)."""
    lines: list[str] = []
    # Header
    lines.append("\t".join(str(c) for c in df.columns))
    for _, row in df.iterrows():
        lines.append("\t".join(str(v) for v in row.values))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Excel / CSV
# ---------------------------------------------------------------------------

def extract_excel(file: Any) -> dict[str, Any]:
    """Trích xuất dữ liệu từ file Excel (.xlsx/.xls) hoặc CSV.

    Parameters
    ----------
    file : UploadedFile
        Đối tượng file từ Streamlit (có ``.read()``, ``.name``, ``.type``).

    Returns
    -------
    dict
        ``{'sheets': [...], 'raw_text': str}`` hoặc ``{'error': str}``.
    """
    try:
        _safe_seek(file)
        ext = _file_ext(file)
        sheets: list[dict[str, Any]] = []

        if ext == ".csv":
            df = pd.read_csv(file)
            raw = _dataframe_to_raw_text(df)
            sheets.append({"name": "Sheet1", "dataframe": df, "raw_text": raw})
        else:
            # Excel – đọc tất cả sheet
            _safe_seek(file)
            xls = pd.ExcelFile(file, engine="openpyxl" if ext == ".xlsx" else None)
            for sheet_name in xls.sheet_names:
                df = pd.read_excel(xls, sheet_name=sheet_name)
                raw = _dataframe_to_raw_text(df)
                sheets.append({
                    "name": sheet_name,
                    "dataframe": df,
                    "raw_text": raw,
                })

        all_raw = "\n\n".join(s["raw_text"] for s in sheets)
        return {"sheets": sheets, "raw_text": all_raw}

    except Exception as exc:
        return {"error": f"Lỗi khi đọc file Excel/CSV: {exc}"}


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def extract_pdf(file: Any) -> dict[str, Any]:
    """Trích xuất văn bản và bảng từ file PDF.

    Parameters
    ----------
    file : UploadedFile
        Đối tượng file PDF.

    Returns
    -------
    dict
        ``{'pages': [...], 'raw_text': str, 'page_count': int}``
        hoặc ``{'error': str}``.
    """
    try:
        _safe_seek(file)
        pages_data: list[dict[str, Any]] = []

        with pdfplumber.open(file) as pdf:
            for idx, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                pages_data.append({
                    "page_num": idx,
                    "text": text,
                    "tables": tables,
                })

        raw_text = "\n\n".join(p["text"] for p in pages_data)
        return {
            "pages": pages_data,
            "raw_text": raw_text,
            "page_count": len(pages_data),
        }

    except Exception as exc:
        return {"error": f"Lỗi khi đọc file PDF: {exc}"}


# ---------------------------------------------------------------------------
# Image (OCR)
# ---------------------------------------------------------------------------

def extract_image(
    file: Any,
    languages: list[str] | None = None,
) -> dict[str, Any]:
    """Trích xuất văn bản từ hình ảnh bằng Tesseract OCR.

    Parameters
    ----------
    file : UploadedFile
        Đối tượng file hình ảnh (.jpg, .jpeg, .png).
    languages : list[str] | None
        Danh sách mã ngôn ngữ Tesseract. Mặc định ``['vie', 'eng']``.

    Returns
    -------
    dict
        ``{'raw_text': str, 'confidence': float, 'details': pd.DataFrame}``
        hoặc ``{'error': str}``.
    """
    if languages is None:
        languages = ["vie", "eng"]
    lang_str = "+".join(languages)

    try:
        _safe_seek(file)
        image = Image.open(file)

        raw_text: str = pytesseract.image_to_string(image, lang=lang_str)

        # Chi tiết OCR (bao gồm confidence)
        details_df: pd.DataFrame = pytesseract.image_to_data(
            image, lang=lang_str, output_type=pytesseract.Output.DATAFRAME,
        )

        # Tính confidence trung bình (bỏ qua giá trị -1 = vùng không nhận dạng)
        valid_conf = details_df.loc[details_df["conf"] >= 0, "conf"]
        avg_confidence = float(valid_conf.mean()) if not valid_conf.empty else 0.0

        return {
            "raw_text": raw_text.strip(),
            "confidence": round(avg_confidence, 2),
            "details": details_df,
        }

    except pytesseract.TesseractNotFoundError:
        return {
            "error": (
                "Không tìm thấy Tesseract OCR. Vui lòng cài đặt Tesseract và "
                "đảm bảo đường dẫn được thêm vào biến môi trường PATH.\n"
                "Hướng dẫn: https://github.com/tesseract-ocr/tesseract#installing-tesseract"
            ),
        }
    except Exception as exc:
        return {"error": f"Lỗi khi OCR hình ảnh: {exc}"}


# ---------------------------------------------------------------------------
# Word (.docx)
# ---------------------------------------------------------------------------

def extract_word(file: Any) -> dict[str, Any]:
    """Trích xuất văn bản và bảng từ file Word (.docx).

    Parameters
    ----------
    file : UploadedFile
        Đối tượng file Word.

    Returns
    -------
    dict
        ``{'raw_text': str, 'paragraphs': [...], 'tables': [...]}``
        hoặc ``{'error': str}``.
    """
    try:
        _safe_seek(file)
        doc = Document(io.BytesIO(file.read()))

        # Đoạn văn
        paragraphs: list[str] = [p.text for p in doc.paragraphs if p.text.strip()]

        # Bảng
        tables: list[dict[str, Any]] = []
        for table in doc.tables:
            rows_data: list[list[str]] = []
            for row in table.rows:
                rows_data.append([cell.text.strip() for cell in row.cells])

            if rows_data:
                headers = rows_data[0]
                data_rows = rows_data[1:] if len(rows_data) > 1 else []
                tables.append({"headers": headers, "rows": data_rows})

        raw_text = "\n".join(paragraphs)
        if tables:
            for tbl in tables:
                raw_text += "\n" + "\t".join(tbl["headers"])
                for r in tbl["rows"]:
                    raw_text += "\n" + "\t".join(r)

        return {
            "raw_text": raw_text,
            "paragraphs": paragraphs,
            "tables": tables,
        }

    except Exception as exc:
        return {"error": f"Lỗi khi đọc file Word: {exc}"}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_EXT_MAP: dict[str, str] = {
    ".xlsx": "excel",
    ".xls": "excel",
    ".csv": "excel",
    ".pdf": "pdf",
    ".jpg": "image",
    ".jpeg": "image",
    ".png": "image",
    ".docx": "word",
}


def extract_file(
    file: Any,
    ocr_languages: list[str] | None = None,
) -> dict[str, Any]:
    """Tự động nhận diện loại file và trích xuất nội dung.

    Parameters
    ----------
    file : UploadedFile
        Đối tượng file từ Streamlit.
    ocr_languages : list[str] | None
        Ngôn ngữ OCR (chỉ dùng cho ảnh). Mặc định ``['vie', 'eng']``.

    Returns
    -------
    dict
        ``{'file_type': str, 'data': dict, 'raw_text': str, 'error': str|None}``.
    """
    ext = _file_ext(file)
    file_type = _EXT_MAP.get(ext)

    if file_type is None:
        supported = ", ".join(sorted(_EXT_MAP.keys()))
        return {
            "file_type": "unknown",
            "data": {},
            "raw_text": "",
            "error": (
                f"Định dạng file '{ext}' không được hỗ trợ. "
                f"Các định dạng hỗ trợ: {supported}"
            ),
        }

    extractors = {
        "excel": extract_excel,
        "pdf": extract_pdf,
        "image": lambda f: extract_image(f, languages=ocr_languages),
        "word": extract_word,
    }

    try:
        data = extractors[file_type](file)

        if "error" in data:
            return {
                "file_type": file_type,
                "data": {},
                "raw_text": "",
                "error": data["error"],
            }

        return {
            "file_type": file_type,
            "data": data,
            "raw_text": data.get("raw_text", ""),
            "error": None,
        }

    except Exception as exc:
        return {
            "file_type": file_type,
            "data": {},
            "raw_text": "",
            "error": f"Lỗi không xác định khi xử lý file: {exc}",
        }
