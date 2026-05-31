"""Module nhận diện loại chứng từ và trích xuất trường dữ liệu.

Hỗ trợ 6 loại chứng từ xuất nhập khẩu:
  - Tờ khai hải quan (customs_declaration)
  - Booking (booking)
  - Bill of Lading (bill_of_lading)
  - Invoice (invoice)
  - Packing List (packing_list)
  - Giấy thông báo hàng đến (arrival_notice)

Sử dụng ``rapidfuzz`` cho so khớp mờ và ``re`` cho trích xuất mẫu.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz

# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT_TYPES – Định nghĩa 6 loại chứng từ
# ═══════════════════════════════════════════════════════════════════════════

DOCUMENT_TYPES: dict[str, dict[str, Any]] = {
    "customs_declaration": {
        "name": "Tờ khai nhập/xuất",
        "icon": "📋",
        "keywords": [
            "tờ khai", "customs", "declaration", "hải quan",
            "mã hs", "hs code", "người xuất khẩu", "người nhập khẩu",
        ],
        "fields": {
            "declarationNo": {
                "label": "Số tờ khai",
                "keywords": ["số tờ khai", "declaration no", "số tk"],
                "type": "string",
            },
            "date": {
                "label": "Ngày đăng ký",
                "keywords": ["ngày", "date", "ngày đăng ký"],
                "type": "date",
            },
            "exporter": {
                "label": "Người xuất khẩu",
                "keywords": ["người xuất khẩu", "exporter", "shipper"],
                "type": "string",
            },
            "importer": {
                "label": "Người nhập khẩu",
                "keywords": ["người nhập khẩu", "importer", "consignee"],
                "type": "string",
            },
            "hsCode": {
                "label": "Mã HS",
                "keywords": ["mã hs", "hs code", "mã số"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["mô tả", "description", "tên hàng", "goods"],
                "type": "string",
            },
            "quantity": {
                "label": "Số lượng",
                "keywords": ["số lượng", "quantity", "qty", "slg"],
                "type": "number",
            },
            "unit": {
                "label": "Đơn vị",
                "keywords": ["đơn vị", "unit"],
                "type": "string",
            },
            "grossWeight": {
                "label": "Trọng lượng",
                "keywords": ["trọng lượng", "gross weight", "weight", "g/w", "gw"],
                "type": "number",
            },
            "value": {
                "label": "Trị giá",
                "keywords": ["trị giá", "value", "amount", "giá trị"],
                "type": "number",
            },
            "currency": {
                "label": "Loại tiền",
                "keywords": ["loại tiền", "currency", "ccy"],
                "type": "string",
            },
            "origin": {
                "label": "Xuất xứ",
                "keywords": ["xuất xứ", "origin", "country of origin"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["số container", "container no", "cont no", "số cont"],
                "type": "string",
            },
        },
    },
    "booking": {
        "name": "Booking",
        "icon": "📦",
        "keywords": [
            "booking", "booking confirmation", "booking no",
            "xác nhận đặt chỗ",
        ],
        "fields": {
            "bookingNo": {
                "label": "Booking No",
                "keywords": ["booking no", "booking number", "booking ref"],
                "type": "string",
            },
            "date": {
                "label": "Ngày",
                "keywords": ["date", "ngày", "booking date"],
                "type": "date",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "người gửi", "người xuất khẩu"],
                "type": "string",
            },
            "consignee": {
                "label": "Consignee",
                "keywords": ["consignee", "người nhận", "người nhập khẩu"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu", "ship", "tên tàu"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến", "voy"],
                "type": "string",
            },
            "pol": {
                "label": "Cảng xếp (POL)",
                "keywords": ["pol", "port of loading", "cảng xếp", "cảng đi"],
                "type": "string",
            },
            "pod": {
                "label": "Cảng dỡ (POD)",
                "keywords": ["pod", "port of discharge", "cảng dỡ", "cảng đến"],
                "type": "string",
            },
            "containerType": {
                "label": "Loại container",
                "keywords": ["container type", "loại cont", "container size"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container", "cont no"],
                "type": "string",
            },
            "etd": {
                "label": "ETD",
                "keywords": ["etd", "estimated time of departure", "ngày đi"],
                "type": "date",
            },
            "eta": {
                "label": "ETA",
                "keywords": ["eta", "estimated time of arrival", "ngày đến"],
                "type": "date",
            },
        },
    },
    "bill_of_lading": {
        "name": "Bill of Lading",
        "icon": "🚢",
        "keywords": [
            "bill of lading", "b/l", "vận đơn", "bl no",
            "b/l no", "ocean bill",
        ],
        "fields": {
            "blNo": {
                "label": "B/L No",
                "keywords": ["b/l no", "bl no", "bill of lading no", "số vận đơn"],
                "type": "string",
            },
            "date": {
                "label": "Ngày phát hành",
                "keywords": ["date", "ngày", "issue date", "ngày phát hành"],
                "type": "date",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "người gửi hàng"],
                "type": "string",
            },
            "consignee": {
                "label": "Consignee",
                "keywords": ["consignee", "người nhận hàng"],
                "type": "string",
            },
            "notifyParty": {
                "label": "Notify Party",
                "keywords": ["notify party", "notify", "bên được thông báo"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu", "ocean vessel"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến", "voy no"],
                "type": "string",
            },
            "pol": {
                "label": "Cảng xếp (POL)",
                "keywords": ["pol", "port of loading", "cảng xếp hàng"],
                "type": "string",
            },
            "pod": {
                "label": "Cảng dỡ (POD)",
                "keywords": ["pod", "port of discharge", "cảng dỡ hàng"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả hàng", "description of goods"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container"],
                "type": "string",
            },
            "sealNo": {
                "label": "Số seal",
                "keywords": ["seal no", "số seal", "seal number"],
                "type": "string",
            },
            "grossWeight": {
                "label": "Trọng lượng",
                "keywords": ["gross weight", "trọng lượng", "weight"],
                "type": "number",
            },
            "measurement": {
                "label": "Thể tích (CBM)",
                "keywords": ["measurement", "cbm", "thể tích", "cubic meter"],
                "type": "number",
            },
            "packages": {
                "label": "Số kiện",
                "keywords": ["packages", "số kiện", "no of packages"],
                "type": "number",
            },
        },
    },
    "invoice": {
        "name": "Invoice",
        "icon": "💰",
        "keywords": [
            "invoice", "commercial invoice", "hóa đơn",
            "proforma", "inv no",
        ],
        "fields": {
            "invoiceNo": {
                "label": "Invoice No",
                "keywords": ["invoice no", "inv no", "số hóa đơn", "invoice number"],
                "type": "string",
            },
            "date": {
                "label": "Ngày",
                "keywords": ["date", "ngày", "invoice date"],
                "type": "date",
            },
            "seller": {
                "label": "Người bán",
                "keywords": ["seller", "người bán", "exporter", "beneficiary"],
                "type": "string",
            },
            "buyer": {
                "label": "Người mua",
                "keywords": ["buyer", "người mua", "importer", "applicant"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả", "goods", "commodity"],
                "type": "string",
            },
            "quantity": {
                "label": "Số lượng",
                "keywords": ["quantity", "qty", "số lượng"],
                "type": "number",
            },
            "unitPrice": {
                "label": "Đơn giá",
                "keywords": ["unit price", "đơn giá", "price"],
                "type": "number",
            },
            "totalAmount": {
                "label": "Tổng giá trị",
                "keywords": [
                    "total amount", "total", "tổng",
                    "tổng giá trị", "amount",
                ],
                "type": "number",
            },
            "currency": {
                "label": "Loại tiền",
                "keywords": ["currency", "loại tiền", "ccy"],
                "type": "string",
            },
            "incoterm": {
                "label": "Điều kiện giao hàng",
                "keywords": ["incoterm", "terms", "fob", "cif", "cfr", "điều kiện"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container"],
                "type": "string",
            },
            "origin": {
                "label": "Xuất xứ",
                "keywords": ["origin", "xuất xứ", "country of origin", "made in"],
                "type": "string",
            },
        },
    },
    "packing_list": {
        "name": "Packing List",
        "icon": "📝",
        "keywords": [
            "packing list", "danh sách đóng gói", "p/l", "packing",
        ],
        "fields": {
            "plNo": {
                "label": "P/L No",
                "keywords": ["packing list no", "p/l no", "pl no"],
                "type": "string",
            },
            "date": {
                "label": "Ngày",
                "keywords": ["date", "ngày"],
                "type": "date",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "người gửi", "from"],
                "type": "string",
            },
            "consignee": {
                "label": "Consignee",
                "keywords": ["consignee", "người nhận", "to"],
                "type": "string",
            },
            "invoiceNo": {
                "label": "Invoice No",
                "keywords": ["invoice no", "inv ref", "số hóa đơn"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả", "goods"],
                "type": "string",
            },
            "quantity": {
                "label": "Số lượng",
                "keywords": ["quantity", "qty", "số lượng"],
                "type": "number",
            },
            "packages": {
                "label": "Số kiện",
                "keywords": [
                    "packages", "số kiện", "cartons", "cases", "ctns",
                ],
                "type": "number",
            },
            "netWeight": {
                "label": "Trọng lượng tịnh (N/W)",
                "keywords": ["net weight", "n/w", "nw", "trọng lượng tịnh"],
                "type": "number",
            },
            "grossWeight": {
                "label": "Trọng lượng cả bì (G/W)",
                "keywords": [
                    "gross weight", "g/w", "gw", "trọng lượng cả bì",
                ],
                "type": "number",
            },
            "measurement": {
                "label": "Thể tích (CBM)",
                "keywords": ["measurement", "cbm", "thể tích", "volume", "cubic"],
                "type": "number",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container", "cont no"],
                "type": "string",
            },
        },
    },
    "arrival_notice": {
        "name": "Giấy thông báo hàng đến",
        "icon": "🔔",
        "keywords": [
            "arrival notice", "thông báo hàng đến",
            "notice of arrival", "giấy báo hàng",
        ],
        "fields": {
            "blNo": {
                "label": "B/L No",
                "keywords": ["b/l no", "bl no", "bill of lading"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu", "ship name"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến"],
                "type": "string",
            },
            "eta": {
                "label": "ETA",
                "keywords": ["eta", "ngày đến", "arrival date", "estimated arrival"],
                "type": "date",
            },
            "consignee": {
                "label": "Consignee",
                "keywords": ["consignee", "người nhận"],
                "type": "string",
            },
            "notifyParty": {
                "label": "Notify Party",
                "keywords": ["notify party", "notify", "bên thông báo"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả hàng", "goods description"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container"],
                "type": "string",
            },
            "packages": {
                "label": "Số kiện",
                "keywords": ["packages", "số kiện", "number of packages"],
                "type": "number",
            },
            "grossWeight": {
                "label": "Trọng lượng",
                "keywords": ["gross weight", "weight", "trọng lượng"],
                "type": "number",
            },
            "measurement": {
                "label": "Thể tích",
                "keywords": ["measurement", "cbm", "thể tích"],
                "type": "number",
            },
            "freightCharges": {
                "label": "Cước phí",
                "keywords": ["freight", "cước", "charges", "phí"],
                "type": "number",
            },
        },
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FIELD_MAPPING – Ánh xạ ngữ nghĩa giữa các loại chứng từ
# ═══════════════════════════════════════════════════════════════════════════

FIELD_MAPPING: list[list[str]] = [
    [
        "customs_declaration.exporter", "booking.shipper",
        "bill_of_lading.shipper", "invoice.seller", "packing_list.shipper",
    ],
    [
        "customs_declaration.importer", "booking.consignee",
        "bill_of_lading.consignee", "invoice.buyer",
        "packing_list.consignee", "arrival_notice.consignee",
    ],
    [
        "customs_declaration.description", "bill_of_lading.description",
        "invoice.description", "packing_list.description",
        "arrival_notice.description",
    ],
    [
        "customs_declaration.quantity", "invoice.quantity",
        "packing_list.quantity",
    ],
    [
        "customs_declaration.grossWeight", "bill_of_lading.grossWeight",
        "packing_list.grossWeight", "arrival_notice.grossWeight",
    ],
    [
        "customs_declaration.containerNo", "booking.containerNo",
        "bill_of_lading.containerNo", "invoice.containerNo",
        "packing_list.containerNo", "arrival_notice.containerNo",
    ],
    ["customs_declaration.value", "invoice.totalAmount"],
    [
        "booking.vessel", "bill_of_lading.vessel", "arrival_notice.vessel",
    ],
    [
        "booking.voyage", "bill_of_lading.voyage", "arrival_notice.voyage",
    ],
    ["booking.pol", "bill_of_lading.pol"],
    ["booking.pod", "bill_of_lading.pod"],
    ["bill_of_lading.blNo", "arrival_notice.blNo"],
    ["bill_of_lading.notifyParty", "arrival_notice.notifyParty"],
    [
        "bill_of_lading.measurement", "packing_list.measurement",
        "arrival_notice.measurement",
    ],
    [
        "bill_of_lading.packages", "packing_list.packages",
        "arrival_notice.packages",
    ],
    ["invoice.invoiceNo", "packing_list.invoiceNo"],
    ["booking.eta", "arrival_notice.eta"],
]


# ═══════════════════════════════════════════════════════════════════════════
# Regex patterns dùng chung
# ═══════════════════════════════════════════════════════════════════════════

_CONTAINER_PATTERN = re.compile(r"[A-Z]{4}\d{7}", re.IGNORECASE)
_NUMBER_PATTERN = re.compile(
    r"[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?",
)
_DATE_FORMATS = [
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%d %b %Y",
    "%d %B %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%m/%d/%Y",
]
_DATE_PATTERN = re.compile(
    r"\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4}"
    r"|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}"
    r"|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}",
    re.IGNORECASE,
)


# ═══════════════════════════════════════════════════════════════════════════
# Hàm phụ trợ
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Chuẩn hoá văn bản: lowercase, gộp khoảng trắng."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _parse_number(raw: str) -> float | None:
    """Chuyển chuỗi số (có thể chứa dấu phân cách hàng nghìn) thành float."""
    try:
        # Ưu tiên dấu chấm làm phần thập phân nếu nằm cuối
        cleaned = raw.strip()
        # Kiểm tra dạng 1.234,56 (EU) hay 1,234.56 (US)
        if re.search(r"\.\d{3},", cleaned):
            # EU: 1.234,56 → 1234.56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned and "." in cleaned:
            # US: 1,234.56 → 1234.56
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Có thể là 1234,56 hoặc 1,234
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2:
                cleaned = cleaned.replace(",", ".")
            else:
                cleaned = cleaned.replace(",", "")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _parse_date(raw: str) -> str | None:
    """Thử phân tích chuỗi ngày với nhiều định dạng, trả về ISO string."""
    raw = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def _extract_value_near_keyword(
    text: str,
    keyword: str,
    field_type: str,
) -> tuple[str | None, float]:
    """Tìm giá trị gần keyword trong văn bản.

    Returns
    -------
    tuple[str | None, float]
        (giá_trị, confidence)
    """
    escaped_kw = re.escape(keyword)
    pattern = re.compile(
        rf"(?:{escaped_kw})[:\s\t]+([^\n]{{1,200}})",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return None, 0.0

    raw_value = match.group(1).strip()
    if not raw_value:
        return None, 0.0

    if field_type == "number":
        num_match = _NUMBER_PATTERN.search(raw_value)
        if num_match:
            parsed = _parse_number(num_match.group())
            if parsed is not None:
                return str(parsed), 0.85
        return None, 0.0

    if field_type == "date":
        date_match = _DATE_PATTERN.search(raw_value)
        if date_match:
            parsed = _parse_date(date_match.group())
            if parsed:
                return parsed, 0.90
        return raw_value, 0.50

    # string – trả về nguyên giá trị (cắt bớt nếu quá dài)
    value = raw_value[:200].strip()
    # Loại bỏ ký tự thừa cuối (dấu hai chấm, tab, …)
    value = re.sub(r"[\t:]+$", "", value).strip()
    return value, 0.80


# ═══════════════════════════════════════════════════════════════════════════
# Hàm công khai
# ═══════════════════════════════════════════════════════════════════════════

def detect_document_type(raw_text: str) -> dict[str, Any]:
    """Nhận diện loại chứng từ dựa trên nội dung văn bản.

    Chấm điểm mỗi loại bằng cách đếm keyword trùng khớp:
    - Keyword cấp tài liệu: **3 điểm** mỗi từ
    - Keyword cấp trường: **1 điểm** mỗi từ

    Parameters
    ----------
    raw_text : str
        Nội dung văn bản thô của tài liệu.

    Returns
    -------
    dict
        ``{'type': str, 'name': str, 'icon': str,
           'confidence': float, 'scores': dict}``
    """
    text_lower = _normalize(raw_text)
    scores: dict[str, int] = {}
    max_possible: dict[str, int] = {}

    for doc_type, doc_def in DOCUMENT_TYPES.items():
        score = 0
        total = 0

        # Keyword cấp tài liệu (trọng số 3)
        for kw in doc_def["keywords"]:
            total += 3
            if kw.lower() in text_lower:
                score += 3

        # Keyword cấp trường (trọng số 1)
        for _field_key, field_def in doc_def["fields"].items():
            for kw in field_def["keywords"]:
                total += 1
                if kw.lower() in text_lower:
                    score += 1

        scores[doc_type] = score
        max_possible[doc_type] = total

    if not scores or max(scores.values()) == 0:
        return {
            "type": "unknown",
            "name": "Không xác định",
            "icon": "❓",
            "confidence": 0.0,
            "scores": scores,
        }

    best_type = max(scores, key=lambda k: scores[k])
    best_score = scores[best_type]
    best_max = max_possible[best_type]
    confidence = min(best_score / best_max, 1.0) if best_max > 0 else 0.0

    doc_def = DOCUMENT_TYPES[best_type]
    return {
        "type": best_type,
        "name": doc_def["name"],
        "icon": doc_def["icon"],
        "confidence": round(confidence, 4),
        "scores": scores,
    }


def parse_fields(
    raw_text: str,
    doc_type: str,
) -> dict[str, dict[str, Any]]:
    """Trích xuất giá trị các trường từ văn bản dựa trên loại chứng từ.

    Parameters
    ----------
    raw_text : str
        Nội dung văn bản thô.
    doc_type : str
        Mã loại chứng từ (key trong ``DOCUMENT_TYPES``).

    Returns
    -------
    dict
        ``{field_key: {'value': str, 'confidence': float, 'label': str}}``.
        Trả về ``{}`` nếu ``doc_type`` không hợp lệ.
    """
    if doc_type not in DOCUMENT_TYPES:
        return {}

    fields_def = DOCUMENT_TYPES[doc_type]["fields"]
    results: dict[str, dict[str, Any]] = {}

    for field_key, field_def in fields_def.items():
        label = field_def["label"]
        field_type = field_def["type"]
        keywords = field_def["keywords"]

        best_value: str | None = None
        best_conf: float = 0.0

        # Xử lý đặc biệt cho container number
        if field_key == "containerNo":
            container_match = _CONTAINER_PATTERN.search(raw_text)
            if container_match:
                best_value = container_match.group().upper()
                best_conf = 0.90

        # Thử từng keyword, giữ kết quả có confidence cao nhất
        for kw in keywords:
            value, conf = _extract_value_near_keyword(raw_text, kw, field_type)
            if value and conf > best_conf:
                best_value = value
                best_conf = conf

        if best_value is not None:
            results[field_key] = {
                "value": best_value,
                "confidence": round(best_conf, 2),
                "label": label,
            }

    return results


def get_field_label(doc_type: str, field_key: str) -> str:
    """Trả về nhãn hiển thị của một trường.

    Parameters
    ----------
    doc_type : str
        Mã loại chứng từ.
    field_key : str
        Khóa trường dữ liệu.

    Returns
    -------
    str
        Nhãn tiếng Việt, hoặc ``field_key`` nếu không tìm thấy.
    """
    try:
        return DOCUMENT_TYPES[doc_type]["fields"][field_key]["label"]
    except KeyError:
        return field_key


def find_equivalent_fields(
    doc_type: str,
    field_key: str,
) -> list[tuple[str, str]]:
    """Tìm các trường tương đương trên các loại chứng từ khác.

    Parameters
    ----------
    doc_type : str
        Mã loại chứng từ nguồn.
    field_key : str
        Khóa trường nguồn.

    Returns
    -------
    list[tuple[str, str]]
        Danh sách ``(other_doc_type, other_field_key)`` tương đương.
    """
    target = f"{doc_type}.{field_key}"
    equivalents: list[tuple[str, str]] = []

    for mapping_group in FIELD_MAPPING:
        if target in mapping_group:
            for entry in mapping_group:
                if entry != target:
                    parts = entry.split(".", 1)
                    if len(parts) == 2:
                        equivalents.append((parts[0], parts[1]))
            break  # Mỗi trường chỉ thuộc 1 nhóm mapping

    return equivalents
