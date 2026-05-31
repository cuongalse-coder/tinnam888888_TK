import re

# Khôi phục file về trạng thái trước khi update (nhờ git reset)
with open("utils/parser.py", "r", encoding="utf-8") as f:
    content = f.read()

customs_declaration_replacement = """    "customs_declaration_export": {
        "name": "Tờ khai xuất khẩu",
        "icon": "📤",
        "keywords": [
            "tờ khai hàng hóa xuất khẩu", "export customs declaration", "hải quan xuất khẩu"
        ],
        "fields": {
            "declarationNo": {"label": "Số tờ khai", "keywords": ["số tờ khai", "declaration no", "số tk"], "type": "string"},
            "date": {"label": "Ngày đăng ký", "keywords": ["ngày đăng ký", "date"], "type": "date"},
            "exporter": {"label": "Người xuất khẩu", "keywords": ["người xuất khẩu", "exporter", "người gửi hàng"], "type": "string"},
            "importer": {"label": "Người nhập khẩu", "keywords": ["người nhập khẩu", "importer", "người nhận hàng"], "type": "string"},
            "typeCode": {"label": "Mã loại hình", "keywords": ["mã loại hình", "loại hình"], "type": "string"},
            "customsBranch": {"label": "Cơ quan Hải quan", "keywords": ["cơ quan hải quan", "chi cục hải quan"], "type": "string"},
            "blNo": {"label": "Số Vận đơn (B/L)", "keywords": ["số vận đơn", "b/l no", "bl no", "số bill"], "type": "string"},
            "vessel": {"label": "Tên tàu / Phương tiện VC", "keywords": ["phương tiện vận chuyển", "tên tàu", "vessel"], "type": "string"},
            "pol": {"label": "Cảng xếp hàng (POL)", "keywords": ["địa điểm xếp hàng", "cảng xếp hàng", "pol"], "type": "string"},
            "pod": {"label": "Cảng dỡ hàng (POD)", "keywords": ["địa điểm dỡ hàng", "cảng dỡ hàng", "pod"], "type": "string"},
            "packages": {"label": "Số lượng kiện", "keywords": ["số lượng kiện", "số kiện", "packages"], "type": "number"},
            "grossWeight": {"label": "Tổng trọng lượng", "keywords": ["tổng trọng lượng", "gross weight", "g/w"], "type": "number"},
            "invoiceNo": {"label": "Số Hóa đơn (Invoice)", "keywords": ["số hóa đơn", "invoice no", "commercial invoice no"], "type": "string"},
            "invoiceDate": {"label": "Ngày Hóa đơn", "keywords": ["ngày phát hành", "invoice date", "date of invoice"], "type": "date"},
            "value": {"label": "Trị giá hóa đơn", "keywords": ["trị giá hóa đơn", "tổng trị giá", "giá trị"], "type": "number"},
            "currency": {"label": "Mã đồng tiền", "keywords": ["mã đồng tiền", "loại tiền", "currency"], "type": "string"},
            "paymentMethod": {"label": "Phương thức thanh toán", "keywords": ["phương thức thanh toán", "thanh toán", "payment method", "điều kiện thanh toán"], "type": "string"},
            "incoterm": {"label": "Điều kiện giao hàng", "keywords": ["điều kiện giao hàng", "điều kiện giá hóa đơn", "incoterm", "term of delivery"], "type": "string"},
            "hsCode": {"label": "Mã số hàng hóa (HS)", "keywords": ["mã số hàng hóa", "mã hs", "hs code"], "type": "string"},
            "description": {"label": "Mô tả hàng hóa", "keywords": ["mô tả hàng hóa", "tên hàng", "description", "hàng hóa"], "type": "string"},
            "quantity": {"label": "Lượng (Quantity)", "keywords": ["lượng", "số lượng", "quantity", "qty"], "type": "number"},
            "unitPrice": {"label": "Đơn giá", "keywords": ["đơn giá", "unit price"], "type": "number"},
            "locationOfStorage": {"label": "Địa điểm lưu kho", "keywords": ["địa điểm lưu kho", "lưu kho", "địa điểm đích"], "type": "string"},
        },
    },
    "customs_declaration_import": {
        "name": "Tờ khai nhập khẩu",
        "icon": "📥",
        "keywords": [
            "tờ khai hàng hóa nhập khẩu", "import customs declaration", "hải quan nhập khẩu"
        ],
        "fields": {
            "declarationNo": {"label": "Số tờ khai", "keywords": ["số tờ khai", "declaration no", "số tk"], "type": "string"},
            "date": {"label": "Ngày đăng ký", "keywords": ["ngày đăng ký", "date"], "type": "date"},
            "exporter": {"label": "Người xuất khẩu", "keywords": ["người xuất khẩu", "exporter", "người gửi hàng"], "type": "string"},
            "importer": {"label": "Người nhập khẩu", "keywords": ["người nhập khẩu", "importer", "người nhận hàng"], "type": "string"},
            "typeCode": {"label": "Mã loại hình", "keywords": ["mã loại hình", "loại hình"], "type": "string"},
            "customsBranch": {"label": "Cơ quan Hải quan", "keywords": ["cơ quan hải quan", "chi cục hải quan"], "type": "string"},
            "blNo": {"label": "Số Vận đơn (B/L)", "keywords": ["số vận đơn", "b/l no", "bl no", "số bill"], "type": "string"},
            "vessel": {"label": "Tên tàu / Phương tiện VC", "keywords": ["phương tiện vận chuyển", "tên tàu", "vessel"], "type": "string"},
            "pol": {"label": "Cảng xếp hàng (POL)", "keywords": ["địa điểm xếp hàng", "cảng xếp hàng", "pol"], "type": "string"},
            "pod": {"label": "Cảng dỡ hàng (POD)", "keywords": ["địa điểm dỡ hàng", "cảng dỡ hàng", "pod"], "type": "string"},
            "packages": {"label": "Số lượng kiện", "keywords": ["số lượng kiện", "số kiện", "packages"], "type": "number"},
            "grossWeight": {"label": "Tổng trọng lượng", "keywords": ["tổng trọng lượng", "gross weight", "g/w"], "type": "number"},
            "invoiceNo": {"label": "Số Hóa đơn (Invoice)", "keywords": ["số hóa đơn", "invoice no", "commercial invoice no"], "type": "string"},
            "invoiceDate": {"label": "Ngày Hóa đơn", "keywords": ["ngày phát hành", "invoice date", "date of invoice"], "type": "date"},
            "value": {"label": "Trị giá hóa đơn", "keywords": ["trị giá hóa đơn", "tổng trị giá", "giá trị"], "type": "number"},
            "currency": {"label": "Mã đồng tiền", "keywords": ["mã đồng tiền", "loại tiền", "currency"], "type": "string"},
            "paymentMethod": {"label": "Phương thức thanh toán", "keywords": ["phương thức thanh toán", "thanh toán", "payment method", "điều kiện thanh toán"], "type": "string"},
            "incoterm": {"label": "Điều kiện giao hàng", "keywords": ["điều kiện giao hàng", "điều kiện giá hóa đơn", "incoterm", "term of delivery"], "type": "string"},
            "hsCode": {"label": "Mã số hàng hóa (HS)", "keywords": ["mã số hàng hóa", "mã hs", "hs code"], "type": "string"},
            "description": {"label": "Mô tả hàng hóa", "keywords": ["mô tả hàng hóa", "tên hàng", "description", "hàng hóa"], "type": "string"},
            "quantity": {"label": "Lượng (Quantity)", "keywords": ["lượng", "số lượng", "quantity", "qty"], "type": "number"},
            "unitPrice": {"label": "Đơn giá", "keywords": ["đơn giá", "unit price"], "type": "number"},
            "locationOfStorage": {"label": "Địa điểm lưu kho", "keywords": ["địa điểm lưu kho", "lưu kho", "địa điểm đích"], "type": "string"},
        },
    },"""

field_mapping_replacement = """FIELD_MAPPING: list[list[str]] = [
    [
        "customs_declaration_export.exporter", "customs_declaration_import.exporter", 
        "booking.shipper", "bill_of_lading.shipper", "invoice.seller", "packing_list.shipper",
    ],
    [
        "customs_declaration_export.importer", "customs_declaration_import.importer", 
        "booking.consignee", "bill_of_lading.consignee", "invoice.buyer",
        "packing_list.consignee", "arrival_notice.consignee",
    ],
    [
        "customs_declaration_export.description", "customs_declaration_import.description",
        "bill_of_lading.description", "invoice.description", "packing_list.description",
        "arrival_notice.description",
    ],
    [
        "customs_declaration_export.quantity", "customs_declaration_import.quantity",
        "invoice.quantity", "packing_list.quantity",
    ],
    [
        "customs_declaration_export.grossWeight", "customs_declaration_import.grossWeight",
        "bill_of_lading.grossWeight", "packing_list.grossWeight", "arrival_notice.grossWeight",
    ],
    [
        "customs_declaration_export.value", "customs_declaration_import.value", 
        "invoice.totalAmount"
    ],
    [
        "customs_declaration_export.vessel", "customs_declaration_import.vessel",
        "booking.vessel", "bill_of_lading.vessel", "arrival_notice.vessel", 
        "invoice.vessel", "packing_list.vessel"
    ],
    [
        "customs_declaration_export.pol", "customs_declaration_import.pol",
        "booking.pol", "bill_of_lading.pol", "invoice.pol", "packing_list.pol"
    ],
    [
        "customs_declaration_export.pod", "customs_declaration_import.pod",
        "booking.pod", "bill_of_lading.pod", "invoice.pod", "packing_list.pod"
    ],
    [
        "customs_declaration_export.blNo", "customs_declaration_import.blNo",
        "bill_of_lading.blNo", "arrival_notice.blNo"
    ],
    ["bill_of_lading.notifyParty", "arrival_notice.notifyParty"],
    [
        "bill_of_lading.measurement", "packing_list.measurement",
        "arrival_notice.measurement",
    ],
    [
        "bill_of_lading.packages", "packing_list.packages",
        "arrival_notice.packages", "customs_declaration_export.packages", "customs_declaration_import.packages",
    ],
    [
        "customs_declaration_export.invoiceNo", "customs_declaration_import.invoiceNo", 
        "invoice.invoiceNo", "packing_list.invoiceNo"
    ],
    ["customs_declaration_export.invoiceDate", "customs_declaration_import.invoiceDate", "invoice.date"],
    ["customs_declaration_export.incoterm", "customs_declaration_import.incoterm", "invoice.incoterm"],
    ["booking.eta", "arrival_notice.eta"],
    ["customs_declaration_export.paymentMethod", "customs_declaration_import.paymentMethod", "invoice.paymentMethod"],
]"""

# Thay thế bằng split để chắc chắn không dính lỗi RegEx
# Tìm khối customs_declaration
start_idx1 = content.find('    "customs_declaration": {')
end_idx1 = content.find('    "booking": {')
if start_idx1 != -1 and end_idx1 != -1:
    content = content[:start_idx1] + customs_declaration_replacement + "\n" + content[end_idx1:]

# Tìm khối FIELD_MAPPING
start_idx2 = content.find('FIELD_MAPPING: list[list[str]] = [')
end_idx2 = content.find(']\n\n\n# ═══════════════════════════════════════════════════════════════════════════\n# Regex')
if start_idx2 != -1 and end_idx2 != -1:
    content = content[:start_idx2] + field_mapping_replacement + content[end_idx2+1:]

with open("utils/parser.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated utils/parser.py perfectly!")
