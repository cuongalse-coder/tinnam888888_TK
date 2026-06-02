"""Module nhận diện loại chứng từ và trích xuất trường dữ liệu.

Hỗ trợ 9 loại chứng từ xuất nhập khẩu:
  - Tờ khai hải quan xuất khẩu (customs_declaration_export)
  - Tờ khai hải quan nhập khẩu (customs_declaration_import)
  - Booking (booking)
  - Bill of Lading (bill_of_lading)
  - Invoice (invoice)
  - Packing List (packing_list)
  - Giấy thông báo hàng đến (arrival_notice)
  - Debit Note (debit_note)
  - DS Hàng hóa Giám sát HQ (customs_monitoring_list)

Sử dụng ``rapidfuzz`` cho so khớp mờ và ``re`` cho trích xuất mẫu.

Changelog v2.0:
  - Phase 1: Sửa bug _parse_number, dead code, keyword collision
  - Phase 2: Cải thiện generic parser (multi-line, hsCode, paymentMethod)
  - Phase 3: Thêm 5 specialized parsers (B/L, Booking, PL, DN, CML)
  - Phase 4: Bổ sung ~15 trường dữ liệu mới (netWeight, sealNo, C/O, L/C...)
  - Phase 5: Cải thiện AI parse prompt + hybrid merge
  - Phase 6: Sửa FIELD_MAPPING gaps
"""

from __future__ import annotations

import re
import json
from datetime import datetime
from typing import Any

from rapidfuzz import fuzz
from google import genai
from pydantic import BaseModel

# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENT_TYPES – Định nghĩa 9 loại chứng từ (Phase 4: bổ sung trường mới)
# ═══════════════════════════════════════════════════════════════════════════

DOCUMENT_TYPES: dict[str, dict[str, Any]] = {
    "customs_declaration_export": {
        "name": "Tờ khai xuất khẩu",
        "icon": "📤",
        "keywords": [
            "tờ khai hàng hóa xuất khẩu", "export customs declaration", "hải quan xuất khẩu"
        ],
        "fields": {
"declarationNo": {"label": "Số tờ khai", "keywords": ["số tờ khai"], "type": "string"},
            "firstDeclarationNo": {"label": "Số tờ khai đầu tiên", "keywords": ["số tờ khai đầu tiên"], "type": "string"},
            "branchDeclarationNo": {"label": "Số nhánh", "keywords": ["số nhánh"], "type": "string"},
            "tempExportDeclarationNo": {"label": "Số tờ khai tạm nhập tái xuất tương ứng", "keywords": ["số tờ khai tạm nhập tái xuất"], "type": "string"},
            "typeCode": {"label": "Mã loại hình", "keywords": ["mã loại hình"], "type": "string"},
            "goodsClassificationCode": {"label": "Mã phân loại hàng hóa", "keywords": ["mã phân loại hàng hóa"], "type": "string"},
            "customsBranch": {"label": "Cơ quan Hải quan", "keywords": ["cơ quan hải quan"], "type": "string"},
            "processingBranchCode": {"label": "Mã bộ phận xử lý tờ khai", "keywords": ["mã bộ phận xử lý"], "type": "string"},
            "personType": {"label": "Phân loại cá nhân/tổ chức", "keywords": ["phân loại cá nhân"], "type": "string"},
            "date": {"label": "Ngày đăng ký / khai báo", "keywords": ["ngày đăng ký"], "type": "date"},
            "reexportDeadline": {"label": "Thời hạn tái xuất/tái nhập", "keywords": ["thời hạn tái xuất"], "type": "string"},
            "transportMethod": {"label": "Phương thức vận chuyển", "keywords": ["phương thức vận chuyển"], "type": "string"},
            "exporterCode": {"label": "Mã người xuất khẩu", "keywords": ["mã người xuất khẩu"], "type": "string"},
            "exporter": {"label": "Tên người xuất khẩu", "keywords": ["người xuất khẩu"], "type": "string"},
            "exporterZip": {"label": "Mã bưu chính (Người XK)", "keywords": ["mã bưu chính xk"], "type": "string"},
            "exporterAddress": {"label": "Địa chỉ người xuất khẩu", "keywords": ["địa chỉ người xuất khẩu"], "type": "string"},
            "exporterPhone": {"label": "Điện thoại (Người XK)", "keywords": ["điện thoại xk"], "type": "string"},
            "exporterCountry": {"label": "Mã nước (Người XK)", "keywords": ["mã nước xk"], "type": "string"},
            "importerCode": {"label": "Mã người nhập khẩu", "keywords": ["mã người nhập khẩu"], "type": "string"},
            "importer": {"label": "Tên người nhập khẩu", "keywords": ["người nhập khẩu"], "type": "string"},
            "importerZip": {"label": "Mã bưu chính (Người NK)", "keywords": ["mã bưu chính nk"], "type": "string"},
            "importerAddress": {"label": "Địa chỉ người nhập khẩu", "keywords": ["địa chỉ người nhập khẩu"], "type": "string"},
            "importerPhone": {"label": "Điện thoại (Người NK)", "keywords": ["điện thoại nk"], "type": "string"},
            "importerCountry": {"label": "Mã nước (Người NK)", "keywords": ["mã nước nk"], "type": "string"},
            "entrustedCode": {"label": "Mã người ủy thác", "keywords": ["mã người ủy thác"], "type": "string"},
            "entrustedName": {"label": "Tên người ủy thác", "keywords": ["tên người ủy thác"], "type": "string"},
            "customsAgentCode": {"label": "Mã đại lý / NV Hải quan", "keywords": ["mã đại lý"], "type": "string"},
            "blNo": {"label": "Số Vận đơn (B/L)", "keywords": ["số vận đơn"], "type": "string"},
            "packages": {"label": "Số lượng kiện", "keywords": ["số lượng kiện"], "type": "number"},
            "packageType": {"label": "Loại kiện", "keywords": ["loại kiện"], "type": "string"},
            "grossWeight": {"label": "Tổng trọng lượng", "keywords": ["tổng trọng lượng", "gross weight"], "type": "number"},
            "grossWeightUnit": {"label": "ĐVT Trọng lượng", "keywords": ["đvt trọng lượng"], "type": "string"},
            "locationOfStorage": {"label": "Địa điểm lưu kho", "keywords": ["địa điểm lưu kho"], "type": "string"},
            "pod": {"label": "Địa điểm nhận hàng cuối cùng (POD)", "keywords": ["địa điểm nhận hàng"], "type": "string"},
            "pol": {"label": "Địa điểm xếp hàng (POL)", "keywords": ["địa điểm xếp hàng"], "type": "string"},
            "vessel": {"label": "Phương tiện vận chuyển dự kiến", "keywords": ["phương tiện vận chuyển dự kiến"], "type": "string"},
            "departureDate": {"label": "Ngày hàng đi dự kiến", "keywords": ["ngày hàng đi"], "type": "date"},
            "containerNo": {"label": "Số container", "keywords": ["container no"], "type": "string"},
            "sealNo": {"label": "Số seal", "keywords": ["seal no"], "type": "string"},
            "netWeight": {"label": "Trọng lượng tịnh (N/W)", "keywords": ["net weight"], "type": "number"},
            "exportLicense": {"label": "Giấy phép xuất nhập khẩu", "keywords": ["giấy phép xuất khẩu"], "type": "string"},
            "invoiceNo": {"label": "Số hóa đơn", "keywords": ["số hóa đơn"], "type": "string"},
            "invoiceDate": {"label": "Ngày phát hành hóa đơn", "keywords": ["ngày phát hành hóa đơn"], "type": "date"},
            "electronicInvoiceCode": {"label": "Số tiếp nhận hóa đơn điện tử", "keywords": ["số tiếp nhận hóa đơn điện tử"], "type": "string"},
            "paymentMethod": {"label": "Phương thức thanh toán", "keywords": ["phương thức thanh toán"], "type": "string"},
            "incoterm": {"label": "Điều kiện giao hàng", "keywords": ["điều kiện giao hàng", "incoterm"], "type": "string"},
            "currency": {"label": "Mã đồng tiền hóa đơn", "keywords": ["mã đồng tiền"], "type": "string"},
            "value": {"label": "Tổng trị giá hóa đơn", "keywords": ["trị giá hóa đơn"], "type": "number"},
            "taxValue": {"label": "Tổng trị giá tính thuế", "keywords": ["trị giá tính thuế"], "type": "number"},
            "taxCurrency": {"label": "Mã đồng tiền tính thuế", "keywords": ["mã đồng tiền tính thuế"], "type": "string"},
            "exchangeRate": {"label": "Tỷ giá tính thuế", "keywords": ["tỷ giá tính thuế"], "type": "number"},
            "taxPaymentMethod": {"label": "Mã xác định thời hạn nộp thuế", "keywords": ["mã xác định thời hạn"], "type": "string"},
            "taxAmount": {"label": "Tổng tiền thuế xuất/nhập khẩu", "keywords": ["tổng tiền thuế"], "type": "number"},
            "feeAmount": {"label": "Tổng số tiền lệ phí", "keywords": ["tổng số tiền lệ phí"], "type": "number"},
            "guaranteeAmount": {"label": "Số tiền bảo lãnh", "keywords": ["số tiền bảo lãnh"], "type": "number"},
            "internalCode": {"label": "Số quản lý nội bộ doanh nghiệp", "keywords": ["số quản lý nội bộ"], "type": "string"},
            "totalPages": {"label": "Tổng số trang", "keywords": ["tổng số trang"], "type": "number"},
            "totalLines": {"label": "Tổng số dòng hàng", "keywords": ["tổng số dòng hàng"], "type": "number"},
            "coNo": {"label": "Số C/O", "keywords": ["số c/o"], "type": "string"},
            "lcNo": {"label": "Số L/C", "keywords": ["số l/c"], "type": "string"},
            "freightAmount": {"label": "Phí vận chuyển", "keywords": ["phí vận chuyển"], "type": "number"},
            "insuranceAmount": {"label": "Phí bảo hiểm", "keywords": ["phí bảo hiểm"], "type": "number"},
            "hsCode": {"label": "Mã số hàng hóa (HS)", "keywords": ["mã hs"], "type": "string"},
            "description": {"label": "Mô tả hàng hóa", "keywords": ["mô tả"], "type": "string"},
            "origin": {"label": "Xuất xứ", "keywords": ["xuất xứ"], "type": "string"},
            "quantity": {"label": "Lượng (Quantity)", "keywords": ["lượng"], "type": "number"},
            "uom": {"label": "ĐVT", "keywords": ["đvt"], "type": "string"},
            "unitPrice": {"label": "Đơn giá", "keywords": ["đơn giá"], "type": "number"},
            "itemValue": {"label": "Trị giá", "keywords": ["trị giá mặt hàng"], "type": "number"},
        },
    },
    "customs_declaration_import": {
        "name": "Tờ khai nhập khẩu",
        "icon": "📥",
        "keywords": [
            "tờ khai hàng hóa nhập khẩu", "import customs declaration", "hải quan nhập khẩu"
        ],
        "fields": {
"declarationNo": {"label": "Số tờ khai", "keywords": ["số tờ khai"], "type": "string"},
            "firstDeclarationNo": {"label": "Số tờ khai đầu tiên", "keywords": ["số tờ khai đầu tiên"], "type": "string"},
            "branchDeclarationNo": {"label": "Số nhánh", "keywords": ["số nhánh"], "type": "string"},
            "tempExportDeclarationNo": {"label": "Số tờ khai tạm nhập tái xuất tương ứng", "keywords": ["số tờ khai tạm nhập tái xuất"], "type": "string"},
            "typeCode": {"label": "Mã loại hình", "keywords": ["mã loại hình"], "type": "string"},
            "goodsClassificationCode": {"label": "Mã phân loại hàng hóa", "keywords": ["mã phân loại hàng hóa"], "type": "string"},
            "customsBranch": {"label": "Cơ quan Hải quan", "keywords": ["cơ quan hải quan"], "type": "string"},
            "processingBranchCode": {"label": "Mã bộ phận xử lý tờ khai", "keywords": ["mã bộ phận xử lý"], "type": "string"},
            "personType": {"label": "Phân loại cá nhân/tổ chức", "keywords": ["phân loại cá nhân"], "type": "string"},
            "date": {"label": "Ngày đăng ký / khai báo", "keywords": ["ngày đăng ký"], "type": "date"},
            "reexportDeadline": {"label": "Thời hạn tái xuất/tái nhập", "keywords": ["thời hạn tái xuất"], "type": "string"},
            "transportMethod": {"label": "Phương thức vận chuyển", "keywords": ["phương thức vận chuyển"], "type": "string"},
            "exporterCode": {"label": "Mã người xuất khẩu", "keywords": ["mã người xuất khẩu"], "type": "string"},
            "exporter": {"label": "Tên người xuất khẩu", "keywords": ["người xuất khẩu"], "type": "string"},
            "exporterZip": {"label": "Mã bưu chính (Người XK)", "keywords": ["mã bưu chính xk"], "type": "string"},
            "exporterAddress": {"label": "Địa chỉ người xuất khẩu", "keywords": ["địa chỉ người xuất khẩu"], "type": "string"},
            "exporterPhone": {"label": "Điện thoại (Người XK)", "keywords": ["điện thoại xk"], "type": "string"},
            "exporterCountry": {"label": "Mã nước (Người XK)", "keywords": ["mã nước xk"], "type": "string"},
            "importerCode": {"label": "Mã người nhập khẩu", "keywords": ["mã người nhập khẩu"], "type": "string"},
            "importer": {"label": "Tên người nhập khẩu", "keywords": ["người nhập khẩu"], "type": "string"},
            "importerZip": {"label": "Mã bưu chính (Người NK)", "keywords": ["mã bưu chính nk"], "type": "string"},
            "importerAddress": {"label": "Địa chỉ người nhập khẩu", "keywords": ["địa chỉ người nhập khẩu"], "type": "string"},
            "importerPhone": {"label": "Điện thoại (Người NK)", "keywords": ["điện thoại nk"], "type": "string"},
            "importerCountry": {"label": "Mã nước (Người NK)", "keywords": ["mã nước nk"], "type": "string"},
            "entrustedCode": {"label": "Mã người ủy thác", "keywords": ["mã người ủy thác"], "type": "string"},
            "entrustedName": {"label": "Tên người ủy thác", "keywords": ["tên người ủy thác"], "type": "string"},
            "customsAgentCode": {"label": "Mã đại lý / NV Hải quan", "keywords": ["mã đại lý"], "type": "string"},
            "blNo": {"label": "Số Vận đơn (B/L)", "keywords": ["số vận đơn"], "type": "string"},
            "packages": {"label": "Số lượng kiện", "keywords": ["số lượng kiện"], "type": "number"},
            "packageType": {"label": "Loại kiện", "keywords": ["loại kiện"], "type": "string"},
            "grossWeight": {"label": "Tổng trọng lượng", "keywords": ["tổng trọng lượng", "gross weight"], "type": "number"},
            "grossWeightUnit": {"label": "ĐVT Trọng lượng", "keywords": ["đvt trọng lượng"], "type": "string"},
            "locationOfStorage": {"label": "Địa điểm lưu kho", "keywords": ["địa điểm lưu kho"], "type": "string"},
            "pod": {"label": "Địa điểm nhận hàng cuối cùng (POD)", "keywords": ["địa điểm nhận hàng"], "type": "string"},
            "pol": {"label": "Địa điểm xếp hàng (POL)", "keywords": ["địa điểm xếp hàng"], "type": "string"},
            "vessel": {"label": "Phương tiện vận chuyển dự kiến", "keywords": ["phương tiện vận chuyển dự kiến"], "type": "string"},
            "departureDate": {"label": "Ngày hàng đi dự kiến", "keywords": ["ngày hàng đi"], "type": "date"},
            "containerNo": {"label": "Số container", "keywords": ["container no"], "type": "string"},
            "sealNo": {"label": "Số seal", "keywords": ["seal no"], "type": "string"},
            "netWeight": {"label": "Trọng lượng tịnh (N/W)", "keywords": ["net weight"], "type": "number"},
            "exportLicense": {"label": "Giấy phép xuất nhập khẩu", "keywords": ["giấy phép xuất khẩu"], "type": "string"},
            "invoiceNo": {"label": "Số hóa đơn", "keywords": ["số hóa đơn"], "type": "string"},
            "invoiceDate": {"label": "Ngày phát hành hóa đơn", "keywords": ["ngày phát hành hóa đơn"], "type": "date"},
            "electronicInvoiceCode": {"label": "Số tiếp nhận hóa đơn điện tử", "keywords": ["số tiếp nhận hóa đơn điện tử"], "type": "string"},
            "paymentMethod": {"label": "Phương thức thanh toán", "keywords": ["phương thức thanh toán"], "type": "string"},
            "incoterm": {"label": "Điều kiện giao hàng", "keywords": ["điều kiện giao hàng", "incoterm"], "type": "string"},
            "currency": {"label": "Mã đồng tiền hóa đơn", "keywords": ["mã đồng tiền"], "type": "string"},
            "value": {"label": "Tổng trị giá hóa đơn", "keywords": ["trị giá hóa đơn"], "type": "number"},
            "taxValue": {"label": "Tổng trị giá tính thuế", "keywords": ["trị giá tính thuế"], "type": "number"},
            "taxCurrency": {"label": "Mã đồng tiền tính thuế", "keywords": ["mã đồng tiền tính thuế"], "type": "string"},
            "exchangeRate": {"label": "Tỷ giá tính thuế", "keywords": ["tỷ giá tính thuế"], "type": "number"},
            "taxPaymentMethod": {"label": "Mã xác định thời hạn nộp thuế", "keywords": ["mã xác định thời hạn"], "type": "string"},
            "taxAmount": {"label": "Tổng tiền thuế xuất/nhập khẩu", "keywords": ["tổng tiền thuế"], "type": "number"},
            "feeAmount": {"label": "Tổng số tiền lệ phí", "keywords": ["tổng số tiền lệ phí"], "type": "number"},
            "guaranteeAmount": {"label": "Số tiền bảo lãnh", "keywords": ["số tiền bảo lãnh"], "type": "number"},
            "internalCode": {"label": "Số quản lý nội bộ doanh nghiệp", "keywords": ["số quản lý nội bộ"], "type": "string"},
            "totalPages": {"label": "Tổng số trang", "keywords": ["tổng số trang"], "type": "number"},
            "totalLines": {"label": "Tổng số dòng hàng", "keywords": ["tổng số dòng hàng"], "type": "number"},
            "coNo": {"label": "Số C/O", "keywords": ["số c/o"], "type": "string"},
            "lcNo": {"label": "Số L/C", "keywords": ["số l/c"], "type": "string"},
            "freightAmount": {"label": "Phí vận chuyển", "keywords": ["phí vận chuyển"], "type": "number"},
            "insuranceAmount": {"label": "Phí bảo hiểm", "keywords": ["phí bảo hiểm"], "type": "number"},
            "hsCode": {"label": "Mã số hàng hóa (HS)", "keywords": ["mã hs"], "type": "string"},
            "description": {"label": "Mô tả hàng hóa", "keywords": ["mô tả"], "type": "string"},
            "origin": {"label": "Xuất xứ", "keywords": ["xuất xứ"], "type": "string"},
            "quantity": {"label": "Lượng (Quantity)", "keywords": ["lượng"], "type": "number"},
            "uom": {"label": "ĐVT", "keywords": ["đvt"], "type": "string"},
            "unitPrice": {"label": "Đơn giá", "keywords": ["đơn giá"], "type": "number"},
            "itemValue": {"label": "Trị giá", "keywords": ["trị giá mặt hàng"], "type": "number"},
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
                "keywords": ["booking no", "booking number", "booking ref", "booking confirmation no"],
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
            "notifyParty": {
                "label": "Notify Party",
                "keywords": ["notify party", "notify", "bên thông báo"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu", "ship", "tên tàu", "vessel name"],
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
                "keywords": ["container type", "loại cont", "container size", "equipment"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container", "cont no"],
                "type": "string",
            },
            "sealNo": {
                "label": "Số seal",
                "keywords": ["seal no", "số seal", "seal number"],
                "type": "string",
            },
            "containerQuantity": {
                "label": "Số lượng container",
                "keywords": ["số lượng container", "number of containers", "qty of containers"],
                "type": "number",
            },
            "etd": {
                "label": "ETD",
                "keywords": ["etd", "estimated time of departure", "ngày đi", "sailing date"],
                "type": "date",
            },
            "eta": {
                "label": "ETA",
                "keywords": ["eta", "estimated time of arrival", "ngày đến"],
                "type": "date",
            },
            "portOfTransshipment": {
                "label": "Cảng chuyển tải",
                "keywords": ["transshipment", "port of transshipment", "cảng chuyển tải", "via"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "commodity", "cargo", "mô tả hàng"],
                "type": "string",
            },
            "grossWeight": {
                "label": "Trọng lượng",
                "keywords": ["gross weight", "weight", "trọng lượng", "g/w"],
                "type": "number",
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
                "keywords": ["date", "ngày", "issue date", "ngày phát hành", "date of issue"],
                "type": "date",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "người gửi hàng", "shipper/exporter"],
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
                "keywords": ["vessel", "tàu", "ocean vessel", "vessel name"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến", "voy no", "voy"],
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
            "placeOfDelivery": {
                "label": "Nơi giao hàng",
                "keywords": ["place of delivery", "nơi giao hàng", "final destination"],
                "type": "string",
            },
            "portOfTransshipment": {
                "label": "Cảng chuyển tải",
                "keywords": ["transshipment", "port of transshipment", "cảng chuyển tải"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả hàng", "description of goods", "particulars"],
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
                "keywords": ["gross weight", "trọng lượng", "weight", "g/w"],
                "type": "number",
            },
            "netWeight": {
                "label": "Trọng lượng tịnh (N/W)",
                "keywords": ["net weight", "n/w", "trọng lượng tịnh"],
                "type": "number",
            },
            "measurement": {
                "label": "Thể tích (CBM)",
                "keywords": ["measurement", "cbm", "thể tích", "cubic meter", "volume"],
                "type": "number",
            },
            "packages": {
                "label": "Số kiện",
                "keywords": ["packages", "số kiện", "no of packages", "number of packages"],
                "type": "number",
            },
            "freightTerms": {
                "label": "Điều kiện cước",
                "keywords": ["freight", "freight prepaid", "freight collect", "freight terms"],
                "type": "string",
            },
            "onBoardDate": {
                "label": "Ngày On Board",
                "keywords": ["on board date", "shipped on board", "laden on board"],
                "type": "date",
            },
            "blType": {
                "label": "Loại B/L",
                "keywords": ["original", "copy", "telex release", "surrendered", "express"],
                "type": "string",
            },
            "containerQuantity": {
                "label": "Số lượng container",
                "keywords": ["number of containers", "số lượng container"],
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
                "keywords": ["invoice no", "inv no", "số hóa đơn", "invoice number", "số (no.)", "invoice ref"],
                "type": "string",
            },
            "date": {
                "label": "Ngày",
                "keywords": ["date", "ngày", "invoice date", "ngày (date)"],
                "type": "date",
            },
            "seller": {
                "label": "Người bán",
                "keywords": ["seller", "người bán", "exporter", "beneficiary", "đơn vị bán hàng", "shipper", "shipper/ exporter", "shipper's name"],
                "type": "string",
            },
            "buyer": {
                "label": "Người mua",
                "keywords": ["buyer", "người mua", "importer", "applicant", "tên đơn vị", "company's name", "purchaser", "consignee's name", "for account"],
                "type": "string",
            },
            "description": {
                "label": "Mô tả hàng hóa",
                "keywords": ["description", "mô tả", "goods", "commodity", "description of goods"],
                "type": "string",
            },
            "quantity": {
                "label": "Số lượng",
                "keywords": ["quantity", "qty", "số lượng"],
                "type": "number",
            },
            "unitPrice": {
                "label": "Đơn giá",
                "keywords": ["unit price", "đơn giá", "price per unit"],
                "type": "number",
            },
            "totalAmount": {
                "label": "Tổng giá trị",
                "keywords": [
                    "total amount", "total", "tổng",
                    "tổng giá trị", "amount",
                    "tổng cộng tiền thanh toán", "payment total",
                    "grand total", "amount due",
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
                "keywords": ["incoterm", "terms of delivery", "trade terms", "điều kiện giao hàng"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container"],
                "type": "string",
            },
            "sealNo": {
                "label": "Số seal",
                "keywords": ["seal no", "số seal"],
                "type": "string",
            },
            "origin": {
                "label": "Xuất xứ",
                "keywords": ["origin", "xuất xứ", "country of origin", "made in"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến"],
                "type": "string",
            },
            "pol": {
                "label": "Cảng xếp (POL)",
                "keywords": ["pol", "port of loading"],
                "type": "string",
            },
            "pod": {
                "label": "Cảng dỡ (POD)",
                "keywords": ["pod", "port of discharge", "port of destination"],
                "type": "string",
            },
            "contractNo": {
                "label": "Số Hợp đồng",
                "keywords": ["số hợp đồng", "contract no", "contract number", "số hđ", "hợp đồng số"],
                "type": "string",
            },
            "contractDate": {
                "label": "Ngày Hợp đồng",
                "keywords": ["ngày hợp đồng", "contract date"],
                "type": "date",
            },
            "paymentMethod": {
                "label": "Phương thức thanh toán",
                "keywords": ["phương thức thanh toán", "payment method", "terms of payment", "payment terms"],
                "type": "string",
            },
            "coNo": {
                "label": "Số C/O",
                "keywords": ["c/o no", "certificate of origin", "số c/o"],
                "type": "string",
            },
            "lcNo": {
                "label": "Số L/C",
                "keywords": ["l/c no", "letter of credit", "số l/c"],
                "type": "string",
            },
            "grossWeight": {
                "label": "Trọng lượng cả bì (G/W)",
                "keywords": ["gross weight", "g/w", "gw", "trọng lượng cả bì"],
                "type": "number",
            },
            "netWeight": {
                "label": "Trọng lượng tịnh (N/W)",
                "keywords": ["net weight", "n/w", "nw", "trọng lượng tịnh"],
                "type": "number",
            },
            "packages": {
                "label": "Số kiện",
                "keywords": ["packages", "số kiện", "cartons", "ctns"],
                "type": "number",
            },
            "hsCode": {
                "label": "Mã HS",
                "keywords": ["hs code", "mã hs", "mã số hàng hóa", "tariff code"],
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
                "keywords": ["shipper", "người gửi", "seller", "exporter"],
                "type": "string",
            },
            "consignee": {
                "label": "Consignee",
                "keywords": ["consignee", "người nhận", "buyer", "importer"],
                "type": "string",
            },
            "notifyParty": {
                "label": "Notify Party",
                "keywords": ["notify party", "notify"],
                "type": "string",
            },
            "invoiceNo": {
                "label": "Invoice No",
                "keywords": ["invoice no", "inv ref", "số hóa đơn", "invoice ref"],
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
            "sealNo": {
                "label": "Số seal",
                "keywords": ["seal no", "số seal", "seal number"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến"],
                "type": "string",
            },
            "pol": {
                "label": "Cảng xếp (POL)",
                "keywords": ["pol", "port of loading"],
                "type": "string",
            },
            "pod": {
                "label": "Cảng dỡ (POD)",
                "keywords": ["pod", "port of discharge"],
                "type": "string",
            },
            "contractNo": {
                "label": "Số Hợp đồng",
                "keywords": ["số hợp đồng", "contract no", "số hđ"],
                "type": "string",
            },
            "contractDate": {
                "label": "Ngày Hợp đồng",
                "keywords": ["ngày hợp đồng", "contract date"],
                "type": "date",
            },
            "hsCode": {
                "label": "Mã HS",
                "keywords": ["hs code", "mã hs"],
                "type": "string",
            },
            "origin": {
                "label": "Xuất xứ",
                "keywords": ["origin", "xuất xứ", "country of origin"],
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
            "cargo arrival notice",
        ],
        "fields": {
            "blNo": {
                "label": "B/L No",
                "keywords": ["b/l no", "bl no", "bill of lading", "b/l number"],
                "type": "string",
            },
            "bookingNo": {
                "label": "Booking No",
                "keywords": ["booking no", "booking number"],
                "type": "string",
            },
            "vessel": {
                "label": "Tàu",
                "keywords": ["vessel", "tàu", "ship name", "vessel / voy"],
                "type": "string",
            },
            "voyage": {
                "label": "Chuyến",
                "keywords": ["voyage", "chuyến", "voy"],
                "type": "string",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "shipper / exporter"],
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
            "sealNo": {
                "label": "Số seal",
                "keywords": ["seal no", "số seal"],
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
            "pol": {
                "label": "Cảng xếp (POL)",
                "keywords": ["pol", "port of loading", "cảng xếp"],
                "type": "string",
            },
            "pod": {
                "label": "Cảng dỡ (POD)",
                "keywords": ["pod", "port of discharge", "cảng dỡ"],
                "type": "string",
            },
            "freeTimeExpiry": {
                "label": "Hạn Free Time",
                "keywords": ["free time", "demurrage", "free time until", "free time expires"],
                "type": "date",
            },
        },
    },
    "debit_note": {
        "name": "Debit Note",
        "icon": "💳",
        "keywords": [
            "debit note", "d/n no", "debit", "phí vận chuyển",
        ],
        "fields": {
            "dnNo": {
                "label": "D/N No",
                "keywords": ["d/n no", "debit note no", "dn no", "debit note number"],
                "type": "string",
            },
            "date": {
                "label": "Ngày",
                "keywords": ["date", "ngày", "issue date"],
                "type": "date",
            },
            "shipper": {
                "label": "Shipper",
                "keywords": ["shipper", "người gửi", "from company", "issued by"],
                "type": "string",
            },
            "consignee": {
                "label": "Consignee / To",
                "keywords": ["consignee", "người nhận", "bill to", "attention", "attn"],
                "type": "string",
            },
            "truckBill": {
                "label": "Truck Bill",
                "keywords": ["truck bill", "truck bill no", "số phiếu xe"],
                "type": "string",
            },
            "truckNo": {
                "label": "Truck No",
                "keywords": ["truck no", "biển số xe", "plate no", "license plate"],
                "type": "string",
            },
            "blNo": {
                "label": "B/L No",
                "keywords": ["b/l no", "bl no", "bill of lading"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container", "cont no"],
                "type": "string",
            },
            "origin": {
                "label": "Nơi đi (From)",
                "keywords": ["from location", "nơi đi", "origin", "pickup"],
                "type": "string",
            },
            "destination": {
                "label": "Nơi đến (To)",
                "keywords": ["destination", "nơi đến", "delivery to", "deliver to"],
                "type": "string",
            },
            "etd": {
                "label": "ETD",
                "keywords": ["etd", "ngày đi", "departure date"],
                "type": "date",
            },
            "eta": {
                "label": "ETA",
                "keywords": ["eta", "ngày đến", "arrival date"],
                "type": "date",
            },
            "totalAmount": {
                "label": "Tổng phí",
                "keywords": ["total amount", "total", "tổng cộng", "grand total", "amount due"],
                "type": "number",
            },
            "currency": {
                "label": "Loại tiền",
                "keywords": ["currency", "loại tiền"],
                "type": "string",
            },
        },
    },
    "customs_monitoring_list": {
        "name": "DS Hàng hóa Giám sát HQ",
        "icon": "📋",
        "keywords": [
            "danh sách hàng hóa", "đủ điều kiện qua khu vực giám sát",
            "giám sát hải quan",
        ],
        "fields": {
            "declarationNo": {
                "label": "Số tờ khai",
                "keywords": ["số tờ khai", "declaration no"],
                "type": "string",
            },
            "date": {
                "label": "Ngày tờ khai",
                "keywords": ["ngày tờ khai", "date"],
                "type": "date",
            },
            "company": {
                "label": "Đơn vị XNK",
                "keywords": ["đơn vị xnk", "đơn vị xuất nhập khẩu", "tên doanh nghiệp", "công ty"],
                "type": "string",
            },
            "taxCode": {
                "label": "Mã số thuế",
                "keywords": ["mã số thuế", "tax code", "mst"],
                "type": "string",
            },
            "typeCode": {
                "label": "Loại hình",
                "keywords": ["loại hình", "type", "mã loại hình"],
                "type": "string",
            },
            "status": {
                "label": "Trạng thái",
                "keywords": ["trạng thái tờ khai", "trạng thái", "status"],
                "type": "string",
            },
            "lane": {
                "label": "Luồng",
                "keywords": ["luồng", "lane", "phân luồng"],
                "type": "string",
            },
            "customsBranch": {
                "label": "Chi cục HQ giám sát",
                "keywords": ["chi cục hải quan giám sát", "chi cục hải quan", "cơ quan hải quan"],
                "type": "string",
            },
            "containerNo": {
                "label": "Số container",
                "keywords": ["container no", "số container"],
                "type": "string",
            },
            "blNo": {
                "label": "Số Vận đơn",
                "keywords": ["số vận đơn", "b/l no", "bl no"],
                "type": "string",
            },
        },
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# FIELD_MAPPING – Ánh xạ ngữ nghĩa giữa các loại chứng từ (Phase 6: bổ sung)
# ═══════════════════════════════════════════════════════════════════════════

FIELD_MAPPING: list[list[str]] = [
    # Shipper/Exporter/Seller
    [
        "customs_declaration_export.exporter", "customs_declaration_import.exporter",
        "booking.shipper", "bill_of_lading.shipper", "invoice.seller", "packing_list.shipper",
        "arrival_notice.shipper", "debit_note.shipper",
    ],
    # Consignee/Importer/Buyer
    [
        "customs_declaration_export.importer", "customs_declaration_import.importer",
        "booking.consignee", "bill_of_lading.consignee", "invoice.buyer",
        "packing_list.consignee", "arrival_notice.consignee", "debit_note.consignee",
    ],
    # Description
    [
        "customs_declaration_export.description", "customs_declaration_import.description",
        "bill_of_lading.description", "invoice.description", "packing_list.description",
        "arrival_notice.description", "booking.description",
    ],
    # Quantity
    [
        "customs_declaration_export.quantity", "customs_declaration_import.quantity",
        "invoice.quantity", "packing_list.quantity",
    ],
    # Gross Weight
    [
        "customs_declaration_export.grossWeight", "customs_declaration_import.grossWeight",
        "bill_of_lading.grossWeight", "packing_list.grossWeight", "arrival_notice.grossWeight",
        "invoice.grossWeight", "booking.grossWeight",
    ],
    # Net Weight
    [
        "customs_declaration_export.netWeight", "customs_declaration_import.netWeight",
        "bill_of_lading.netWeight", "packing_list.netWeight", "invoice.netWeight",
    ],
    # Value/Total Amount
    [
        "customs_declaration_export.value", "customs_declaration_import.value",
        "invoice.totalAmount",
    ],
    # Vessel
    [
        "customs_declaration_export.vessel", "customs_declaration_import.vessel",
        "booking.vessel", "bill_of_lading.vessel", "arrival_notice.vessel",
        "invoice.vessel", "packing_list.vessel",
    ],
    # Voyage
    [
        "booking.voyage", "bill_of_lading.voyage", "arrival_notice.voyage",
        "invoice.voyage", "packing_list.voyage",
    ],
    # POL
    [
        "customs_declaration_export.pol", "customs_declaration_import.pol",
        "booking.pol", "bill_of_lading.pol", "invoice.pol", "packing_list.pol",
        "arrival_notice.pol",
    ],
    # POD
    [
        "customs_declaration_export.pod", "customs_declaration_import.pod",
        "booking.pod", "bill_of_lading.pod", "invoice.pod", "packing_list.pod",
        "arrival_notice.pod",
    ],
    # B/L No
    [
        "customs_declaration_export.blNo", "customs_declaration_import.blNo",
        "bill_of_lading.blNo", "arrival_notice.blNo", "debit_note.blNo",
        "customs_monitoring_list.blNo",
    ],
    # Container No
    [
        "booking.containerNo", "bill_of_lading.containerNo", "packing_list.containerNo",
        "arrival_notice.containerNo", "invoice.containerNo", "debit_note.containerNo",
        "customs_declaration_export.containerNo", "customs_declaration_import.containerNo",
        "customs_monitoring_list.containerNo",
    ],
    # Seal No
    [
        "bill_of_lading.sealNo", "booking.sealNo", "packing_list.sealNo",
        "arrival_notice.sealNo", "invoice.sealNo",
        "customs_declaration_export.sealNo", "customs_declaration_import.sealNo",
    ],
    # Notify Party
    [
        "bill_of_lading.notifyParty", "arrival_notice.notifyParty",
        "booking.notifyParty", "packing_list.notifyParty",
    ],
    # Measurement/CBM
    [
        "bill_of_lading.measurement", "packing_list.measurement",
        "arrival_notice.measurement",
    ],
    # Packages
    [
        "bill_of_lading.packages", "packing_list.packages",
        "arrival_notice.packages", "customs_declaration_export.packages",
        "customs_declaration_import.packages", "invoice.packages",
    ],
    # Invoice No
    [
        "customs_declaration_export.invoiceNo", "customs_declaration_import.invoiceNo",
        "invoice.invoiceNo", "packing_list.invoiceNo",
    ],
    # Invoice Date
    ["customs_declaration_export.invoiceDate", "customs_declaration_import.invoiceDate", "invoice.date"],
    # Incoterm
    ["customs_declaration_export.incoterm", "customs_declaration_import.incoterm", "invoice.incoterm"],
    # ETA
    ["booking.eta", "arrival_notice.eta", "debit_note.eta"],
    # ETD
    ["booking.etd", "debit_note.etd"],
    # Payment Method
    ["customs_declaration_export.paymentMethod", "customs_declaration_import.paymentMethod", "invoice.paymentMethod"],
    # Contract No
    ["invoice.contractNo", "packing_list.contractNo"],
    # C/O No
    ["customs_declaration_export.coNo", "customs_declaration_import.coNo", "invoice.coNo"],
    # L/C No
    ["customs_declaration_export.lcNo", "customs_declaration_import.lcNo", "invoice.lcNo"],
    # Declaration No ↔ Monitoring List
    [
        "customs_declaration_export.declarationNo", "customs_declaration_import.declarationNo",
        "customs_monitoring_list.declarationNo",
    ],
    # Booking No
    ["booking.bookingNo", "arrival_notice.bookingNo"],
    # HS Code
    [
        "customs_declaration_export.hsCode", "customs_declaration_import.hsCode",
        "invoice.hsCode", "packing_list.hsCode",
    ],
    # Origin
    ["invoice.origin", "packing_list.origin"],
    # Port of Transshipment
    ["booking.portOfTransshipment", "bill_of_lading.portOfTransshipment"],
]


# ═══════════════════════════════════════════════════════════════════════════
# Regex patterns dùng chung
# ═══════════════════════════════════════════════════════════════════════════

_CONTAINER_PATTERN = re.compile(r"[A-Z]{4}\d{7}", re.IGNORECASE)
_SEAL_PATTERN = re.compile(r"(?:SEAL|seal)\s*(?:NO|no|#|:)?\s*:?\s*([A-Z0-9]{5,15})", re.IGNORECASE)
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

# Incoterm & Payment method patterns (Phase 2: mở rộng)
_INCOTERM_PATTERN = re.compile(
    r'\b(FOB|CIF|EXW|FCA|CPT|CIP|DAP|DPU|DDP|FAS|CFR|DAT)\b', re.IGNORECASE
)
_PAYMENT_PATTERN = re.compile(
    r'\b(T/T|TT|L/C|LC|D/P|D/A|CAD|CASH|O/A|OPEN\s+ACCOUNT|'
    r'WIRE\s+TRANSFER|TELEGRAPHIC\s+TRANSFER|LETTER\s+OF\s+CREDIT|'
    r'AT\s+SIGHT|USANCE|DP\s+AT\s+SIGHT|DA\s+\d+\s+DAYS?)\b', re.IGNORECASE
)
_HS_CODE_PATTERN = re.compile(
    r'\b(\d{4}[.\s]?\d{2}(?:[.\s]?\d{2,4}){0,2})\b'
)


# ═══════════════════════════════════════════════════════════════════════════
# Hàm phụ trợ
# ═══════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Chuẩn hoá văn bản: lowercase, gộp khoảng trắng."""
    return re.sub(r"\s+", " ", text.lower().strip())


def _parse_number(raw: str) -> float | None:
    """Chuyển chuỗi số (có thể chứa dấu phân cách hàng nghìn) thành float.
    
    Phase 1 fix: Xử lý đúng "1,234" vs "1,23" (hàng nghìn vs thập phân).
    """
    try:
        cleaned = raw.strip()
        # Kiểm tra dạng 1.234,56 (EU) hay 1,234.56 (US)
        if re.search(r"\.\d{3},", cleaned):
            # EU: 1.234,56 → 1234.56
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned and "." in cleaned:
            # US: 1,234.56 → 1234.56
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            # Phân biệt: "1,234" (nghìn) vs "1,23" (thập phân)
            parts = cleaned.split(",")
            if len(parts) == 2 and len(parts[1]) <= 2 and len(parts[0]) <= 3:
                # "1,23" hoặc "12,5" → thập phân
                cleaned = cleaned.replace(",", ".")
            else:
                # "1,234" hoặc "1,234,567" → hàng nghìn
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


def _extract_multiline_value(
    text: str,
    keyword: str,
    max_lines: int = 4,
    stop_keywords: list[str] | None = None,
) -> str | None:
    """Trích xuất giá trị nhiều dòng sau keyword (Phase 2).
    
    Bắt tiếp các dòng tiếp theo cho đến khi gặp:
    - Dòng trống
    - Keyword tiếp theo (stop_keywords)
    - Đạt max_lines
    """
    if stop_keywords is None:
        stop_keywords = []
    
    escaped_kw = re.escape(keyword)
    # Tìm vị trí keyword
    m = re.search(rf'(?:{escaped_kw})\s*[:\-]?\s*\n', text, re.IGNORECASE)
    if not m:
        # Thử với keyword : value trên cùng dòng
        m = re.search(rf'(?:{escaped_kw})\s*[:\-]\s*([^\n]+)', text, re.IGNORECASE)
        if m:
            first_line = m.group(1).strip()
            if first_line:
                # Bắt thêm các dòng tiếp theo
                pos = m.end()
                lines = [first_line]
                remaining = text[pos:]
                for line in remaining.split('\n')[:max_lines - 1]:
                    line = line.strip()
                    if not line:
                        break
                    # Kiểm tra stop keywords
                    is_stop = False
                    for sk in stop_keywords:
                        if sk.lower() in line.lower():
                            is_stop = True
                            break
                    if is_stop:
                        break
                    # Dừng nếu dòng bắt đầu bằng label mới (VD: "Consignee:", "2)")
                    if re.match(r'^(?:\d+\)|[A-Z][a-z]+\s*[:\/])', line):
                        break
                    lines.append(line)
                return ' | '.join(lines)
        return None
    
    # Keyword trên dòng riêng, giá trị ở dòng dưới
    pos = m.end()
    remaining = text[pos:]
    lines = []
    for line in remaining.split('\n')[:max_lines]:
        line = line.strip()
        if not line:
            break
        is_stop = False
        for sk in stop_keywords:
            if sk.lower() in line.lower():
                is_stop = True
                break
        if is_stop:
            break
        if re.match(r'^(?:\d+\)|[A-Z][a-z]+\s*[:\/])', line) and len(lines) > 0:
            break
        lines.append(line)
    
    return ' | '.join(lines) if lines else None


def _extract_all_containers(text: str) -> list[str]:
    """Trích xuất TẤT CẢ container numbers từ văn bản."""
    return list(set(_CONTAINER_PATTERN.findall(text.upper())))


def _extract_all_seals(text: str) -> list[str]:
    """Trích xuất tất cả seal numbers từ văn bản."""
    seals = _SEAL_PATTERN.findall(text)
    if not seals:
        # Fallback: tìm seal number gần container number
        for m in re.finditer(r'[A-Z]{4}\d{7}\s*[/\s]*(?:SEAL|SL)\s*[:\s]*([A-Z0-9]{5,15})', text, re.IGNORECASE):
            seals.append(m.group(1))
    return list(set(seals))


def _extract_value_near_keyword(
    text: str,
    keyword: str,
    field_type: str,
    field_key: str = "",
) -> tuple[str | None, float]:
    """Tìm giá trị gần keyword trong văn bản (Phase 2: cải thiện).

    Thử nhiều chiến lược regex:
    1. keyword[separator]value (cùng dòng, cách bởi : - tab space)
    2. keyword\tvalue (tab-separated — phổ biến trong Excel)
    3. keyword\nvalue (xuống dòng — phổ biến trong PDF)

    Returns
    -------
    tuple[str | None, float]
        (giá_trị, confidence)
    """
    escaped_kw = re.escape(keyword)

    # Chiến lược 1-6: Nhiều pattern khác nhau
    _patterns = [
        # keyword (English/note): value — phổ biến trong hóa đơn song ngữ VN
        re.compile(
            rf"(?:{escaped_kw})\s*\([^)]*\)\s*[.:\-]+\s*([^\t\n]{{1,200}}?)(?=\t|\n|\s{{2,}}|$)",
            re.IGNORECASE,
        ),
        # keyword: value hoặc keyword - value
        re.compile(
            rf"(?:{escaped_kw})\s*[.:\-]+\s*([^\t\n]{{1,200}}?)(?=\t|\n|\s{{2,}}|$)",
            re.IGNORECASE,
        ),
        # keyword\tvalue (tab-separated)
        re.compile(
            rf"(?:{escaped_kw})\t+([^\t\n]{{1,200}})",
            re.IGNORECASE,
        ),
        # keyword    value (nhiều dấu cách)
        re.compile(
            rf"(?:{escaped_kw})\s{{2,}}([^\t\n]{{1,200}}?)(?=\t|\n|\s{{3,}}|$)",
            re.IGNORECASE,
        ),
        # keyword\nvalue (xuống dòng)
        re.compile(
            rf"(?:{escaped_kw})\s*\n\s*([^\n]{{1,200}})",
            re.IGNORECASE,
        ),
        # keyword có 1 space rồi value (ít ưu tiên nhất)
        re.compile(
            rf"(?:{escaped_kw})\s+([^\t\n]{{1,200}}?)(?=\t|\n|\s{{2,}}|$)",
            re.IGNORECASE,
        ),
    ]

    raw_value = None
    for pat in _patterns:
        match = pat.search(text)
        if match:
            candidate = match.group(1).strip()
            if candidate and len(candidate) > 0:
                raw_value = candidate
                break

    if not raw_value:
        return None, 0.0

    # Xử lý đặc biệt cho một số trường nghiệp vụ (Phase 2: cải thiện)
    if field_key == "incoterm":
        inco_match = _INCOTERM_PATTERN.search(raw_value)
        if inco_match:
            return inco_match.group(1).upper(), 0.95
        inco_match = _INCOTERM_PATTERN.search(text)
        if inco_match:
            return inco_match.group(1).upper(), 0.50  # Phase 2: giảm confidence
        return None, 0.0

    if field_key == "paymentMethod":
        pay_match = _PAYMENT_PATTERN.search(raw_value)
        if pay_match:
            return pay_match.group(0).strip().upper(), 0.95
        pay_match = _PAYMENT_PATTERN.search(text)
        if pay_match:
            return pay_match.group(0).strip().upper(), 0.50  # Phase 2: giảm confidence
        return None, 0.0

    if field_key == "hsCode":
        # Phase 2: hỗ trợ 6/8/10-digit HS codes
        hs_match = _HS_CODE_PATTERN.search(raw_value)
        if hs_match:
            return re.sub(r'[\.\s]', '', hs_match.group(1)), 0.95
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
    value = raw_value[:300].strip()
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

    # === Nhận diện nhanh bằng pattern cố định (ưu tiên cao) ===
    lower_head = raw_text[:3000].lower()

    # Tờ khai xuất/nhập - nhận diện nhanh
    if "tờ khai hàng hóa xuất khẩu" in lower_head or "<exp>" in lower_head:
        return {"type": "customs_declaration_export", "confidence": 0.95,
                "name": DOCUMENT_TYPES["customs_declaration_export"]["name"],
                "icon": DOCUMENT_TYPES["customs_declaration_export"]["icon"], "scores": {}}
    if "tờ khai hàng hóa nhập khẩu" in lower_head or "<imp>" in lower_head:
        return {"type": "customs_declaration_import", "confidence": 0.95,
                "name": DOCUMENT_TYPES["customs_declaration_import"]["name"],
                "icon": DOCUMENT_TYPES["customs_declaration_import"]["icon"], "scores": {}}

    # Cargo Arrival Notice (ĐẶT TRƯỚC bill_of_lading và debit_note)
    is_arrival = False
    if "cargo arrival notice" in lower_head:
        is_arrival = True
    elif "arrival notice" in lower_head and ("b/l" in lower_head or "bl no" in lower_head or "vessel" in lower_head):
        is_arrival = True
    elif "arrival notice" in lower_head and ("consignee" in lower_head or "shipper" in lower_head):
        is_arrival = True
    elif "est. arrival date" in lower_head and "b/l no" in lower_head:
        is_arrival = True
    elif "subject" in lower_head and "arrival notice" in lower_head:
        is_arrival = True

    if is_arrival:
        return {"type": "arrival_notice", "confidence": 0.95,
                "name": DOCUMENT_TYPES["arrival_notice"]["name"],
                "icon": DOCUMENT_TYPES["arrival_notice"]["icon"], "scores": {}}

    # DS Hàng hóa Giám sát HQ
    if "danh sách hàng hóa" in lower_head and "giám sát" in lower_head:
        return {"type": "customs_monitoring_list", "confidence": 0.95,
                "name": DOCUMENT_TYPES["customs_monitoring_list"]["name"],
                "icon": DOCUMENT_TYPES["customs_monitoring_list"]["icon"], "scores": {}}

    # Debit Note (chỉ detect khi CÓ "debit note" + "truck" hoặc "d/n")
    if "debit note" in lower_head and ("truck" in lower_head or "d/n no" in lower_head):
        return {"type": "debit_note", "confidence": 0.95,
                "name": DOCUMENT_TYPES["debit_note"]["name"],
                "icon": DOCUMENT_TYPES["debit_note"]["icon"], "scores": {}}

    # Commercial Invoice & Packing List
    if ("commercial invoice" in lower_head and "packing list" in lower_head) or \
       ("invoice & packing list" in lower_head) or ("invoice &packing list" in lower_head):
        return {"type": "invoice", "confidence": 0.90,
                "name": DOCUMENT_TYPES["invoice"]["name"],
                "icon": DOCUMENT_TYPES["invoice"]["icon"], "scores": {}}

    # Packing List (trước Invoice vì PL thường chứa "invoice" reference)
    if "packing list" in lower_head and "invoice" not in lower_head[:500].lower():
        return {"type": "packing_list", "confidence": 0.90,
                "name": DOCUMENT_TYPES["packing_list"]["name"],
                "icon": DOCUMENT_TYPES["packing_list"]["icon"], "scores": {}}

    # Bill of Lading
    if "bill of lading" in lower_head and ("shipper" in lower_head or "consignee" in lower_head):
        return {"type": "bill_of_lading", "confidence": 0.90,
                "name": DOCUMENT_TYPES["bill_of_lading"]["name"],
                "icon": DOCUMENT_TYPES["bill_of_lading"]["icon"], "scores": {}}

    # Booking Confirmation
    if "booking" in lower_head and ("confirmation" in lower_head or "booking no" in lower_head):
        return {"type": "booking", "confidence": 0.85,
                "name": DOCUMENT_TYPES["booking"]["name"],
                "icon": DOCUMENT_TYPES["booking"]["icon"], "scores": {}}

    # === Fuzzy keyword scoring (fallback) ===
    for doc_type, doc_def in DOCUMENT_TYPES.items():
        score = 0
        total = 0

        for kw in doc_def["keywords"]:
            total += 3
            if kw.lower() in text_lower:
                score += 3

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
    """Trích xuất giá trị các trường từ văn bản dựa trên loại chứng từ (Phase 3: dispatch mới).

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

    # Tờ khai Hải quan cần parser chuyên biệt
    if doc_type.startswith("customs_declaration"):
        return _parse_customs_declaration(raw_text, doc_type)

    # Bill of Lading — Phase 3
    if doc_type == "bill_of_lading":
        result = _parse_bill_of_lading(raw_text)
        if len(result) >= 3:
            return result

    # Booking — Phase 3
    if doc_type == "booking":
        result = _parse_booking(raw_text)
        if len(result) >= 2:
            return result

    # Commercial Invoice & Packing List - format "1) Shipper" hoặc Samsung SDS
    if doc_type == "invoice":
        lower = raw_text[:2000].lower()
        if ("1) shipper" in lower or "shipper/ exporter" in lower or
            "shipper's name" in lower or "invoice & packing list" in lower or
            "commercial invoice & packing list" in lower or
            "commercial invoice &packing list" in lower):
            result = _parse_commercial_invoice_pl(raw_text)
            if len(result) >= 3:
                return result

    # Packing List — Phase 3
    if doc_type == "packing_list":
        result = _parse_packing_list(raw_text)
        if len(result) >= 2:
            return result

    # Arrival Notice - parser chuyên biệt
    if doc_type == "arrival_notice":
        result = _parse_arrival_notice(raw_text)
        if len(result) >= 2:
            return result

    # Debit Note — Phase 3
    if doc_type == "debit_note":
        result = _parse_debit_note(raw_text)
        if len(result) >= 2:
            return result

    # DS Hàng hóa Giám sát HQ — Phase 3
    if doc_type == "customs_monitoring_list":
        result = _parse_customs_monitoring_list(raw_text)
        if len(result) >= 2:
            return result

    # === Generic parser fallback ===
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
            containers = _extract_all_containers(raw_text)
            if containers:
                best_value = ", ".join(containers[:5])
                best_conf = 0.90

        # Xử lý đặc biệt cho seal number
        if field_key == "sealNo":
            seals = _extract_all_seals(raw_text)
            if seals:
                best_value = ", ".join(seals[:5])
                best_conf = 0.85

        # Thử từng keyword, giữ kết quả có confidence cao nhất
        for kw in keywords:
            value, conf = _extract_value_near_keyword(raw_text, kw, field_type, field_key)
            if value and conf >= best_conf:
                best_value = value
                best_conf = conf

        if best_value is not None:
            results[field_key] = {
                "value": best_value,
                "confidence": round(best_conf, 2),
                "label": label,
            }

    return results


# ═══════════════════════════════════════════════════════════════════════════
# Specialized Parsers
# ═══════════════════════════════════════════════════════════════════════════

def _parse_customs_declaration(
    raw_text: str,
    doc_type: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Tờ khai Hải quan VNACCS/ECUS.
    
    Hỗ trợ cả Xuất khẩu (7X/EXP) và Nhập khẩu (7N/IMP).
    Phase 1: Sửa bug blNo, customsBranch, paymentMethod.
    Phase 4: Thêm trường mới (netWeight, coNo, lcNo, taxAmount...).
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES[doc_type]["fields"]

    def _set(key: str, value: str, conf: float = 0.90):
        if key in fields_def and value and value.strip() and value.strip() not in ('-', '/', '/ /', ''):
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- Số tờ khai ---
    m = re.search(r'Số tờ khai\s+(\d{10,15})', raw_text)
    if not m:
        m = re.search(r'Số tờ khai\s+([A-Z0-9]{8,15})', raw_text, re.IGNORECASE)
    if m:
        _set("declarationNo", m.group(1))

    # --- Ngày đăng ký ---
    m = re.search(r'Ngày đăng ký\s+(\d{1,2}/\d{1,2}/\d{4})', raw_text)
    if m:
        parsed = _parse_date(m.group(1))
        _set("date", parsed or m.group(1))

    # --- Mã loại hình ---
    m = re.search(r'Mã loại hình\s+(\w+\d*\s*\d*)', raw_text)
    if m:
        _set("typeCode", m.group(1).strip())

    # --- Cơ quan Hải quan (Phase 1: bắt multi-word) ---
    m = re.search(r'Tên cơ quan Hải quan tiếp nhận tờ khai\s+(.+?)(?:\n|$)', raw_text)
    if m:
        _set("customsBranch", m.group(1).strip()[:100])
    else:
        m = re.search(r'Chi cục Hải quan\s+(.+?)(?:\n|$)', raw_text)
        if m:
            _set("customsBranch", m.group(1).strip()[:100])

    # --- Người xuất khẩu (section-based) ---
    m = re.search(r'Người xuất khẩu\s*\n.*?Tên\s+(.+?)(?:\n|Mã bưu chính)', raw_text, re.DOTALL)
    if m:
        _set("exporter", m.group(1).strip())
    else:
        m = re.search(r'Người xuất khẩu.*?Tên\t+(.+?)(?:\t|\n)', raw_text, re.DOTALL)
        if m:
            _set("exporter", m.group(1).strip())

    # --- Người nhập khẩu (section-based) ---
    m = re.search(r'Người nhập khẩu\s*\n.*?Tên\s+(.+?)(?:\n|Mã bưu chính)', raw_text, re.DOTALL)
    if m:
        _set("importer", m.group(1).strip())
    else:
        m = re.search(r'Người nhập khẩu.*?Tên\t+([^\t\n]+)', raw_text, re.DOTALL)
        if m:
            _set("importer", m.group(1).strip())

    # --- Số vận đơn (Phase 1: hỗ trợ BL bắt đầu bằng chữ) ---
    m = re.search(r'Số vận đơn\s+([A-Z0-9][\w.\-]+)', raw_text, re.IGNORECASE)
    if m:
        _set("blNo", m.group(1))
    else:
        m = re.search(r'Số vận đơn.*?\n\s*\d+\.?\s+(\S+)', raw_text, re.DOTALL)
        if m:
            _set("blNo", m.group(1))

    # --- Phương tiện vận chuyển ---
    m = re.search(r'Phương tiện vận chuyển(?:\s+dự kiến)?\s*\n\s*([^\n]{1,100}?)(?:\n|$)', raw_text)
    if m:
        val = m.group(1).strip()
        if val and not val.startswith('Ngày') and not val.startswith('Ký hiệu') and val not in ('dự kiến', ''):
            _set("vessel", val)
    if "vessel" not in results:
        m = re.search(r'(\w{2}\d{3,4}/\d{1,2}\w{3})', raw_text)
        if m:
            _set("vessel", m.group(1))

    # --- Cảng xếp hàng (POL) ---
    m = re.search(r'Địa điểm xếp hàng\s+(\S+)\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
    if m:
        _set("pol", f"{m.group(1)} {m.group(2).strip()}")
    else:
        m = re.search(r'Địa điểm xếp hàng\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
        if m:
            _set("pol", m.group(1).strip())

    # --- Cảng dỡ hàng (POD) ---
    m = re.search(r'Địa điểm nhận hàng cuối cùng\s+(\S+)\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
    if m:
        _set("pod", f"{m.group(1)} {m.group(2).strip()}")
    else:
        m = re.search(r'Địa điểm dỡ hàng\s+(\S+)\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
        if m:
            _set("pod", f"{m.group(1)} {m.group(2).strip()}")
        else:
            m = re.search(r'Địa điểm nhận hàng cuối cùng\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
            if m:
                _set("pod", m.group(1).strip())

    # --- Số lượng kiện ---
    m = re.search(r'Số lượng\s+([\d.,]+)\s*(\w+)?', raw_text)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed is not None:
            _set("packages", str(parsed))

    # --- Tổng trọng lượng ---
    m = re.search(r'Tổng trọng lượng hàng\s*\(Gross\)\s+([\d.,]+)', raw_text)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed is not None:
            _set("grossWeight", str(parsed))

    # --- Trọng lượng tịnh (Phase 4) ---
    m = re.search(r'Tổng trọng lượng hàng\s*\(Net\)\s+([\d.,]+)', raw_text)
    if not m:
        m = re.search(r'Trọng lượng tịnh\s+([\d.,]+)', raw_text)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed is not None:
            _set("netWeight", str(parsed))

    # --- Địa điểm lưu kho ---
    m = re.search(r'Địa điểm lưu kho\s+(\S+)\s+([^\t\n]+?)(?:\t|\n|$)', raw_text)
    if m:
        _set("locationOfStorage", f"{m.group(1)} {m.group(2).strip()}")

    # --- Số hóa đơn ---
    m = re.search(r'Số hóa đơn\s+(.+?)(?:\n|$)', raw_text)
    if m:
        val = m.group(1).strip()
        val = re.sub(r'\t+', ' ', val).strip()
        val = re.sub(r'^[A-Z]\s*[-–]\s*', '', val).strip()
        if val:
            parts = val.split()
            clean_val = parts[0] if parts else val
            _set("invoiceNo", clean_val)

    # --- Ngày phát hành hóa đơn ---
    m = re.search(r'Ngày phát hành\s+(\d{1,2}/\d{1,2}/\d{4})', raw_text)
    if m:
        parsed = _parse_date(m.group(1))
        _set("invoiceDate", parsed or m.group(1))

    # --- Tổng trị giá hóa đơn ---
    m = re.search(r'Tổng trị giá hóa đơn\s+(.+?)(?:\n|$)', raw_text)
    if m:
        val = m.group(1).strip()
        nums = re.findall(r'[\d.,]+', val)
        for n in nums:
            parsed = _parse_number(n)
            if parsed is not None and parsed > 0:
                _set("value", str(parsed))
                break
        curr_match = re.search(r'\b(USD|EUR|JPY|CNY|KRW|VND|GBP|SGD|THB|TWD)\b', val)
        if curr_match:
            _set("currency", curr_match.group(1))

    # --- Điều kiện giao hàng (Incoterm) ---
    m = re.search(r'Tổng trị giá hóa đơn\s+\w?\s*-?\s*' + _INCOTERM_PATTERN.pattern, raw_text, re.IGNORECASE)
    if m:
        _set("incoterm", m.group(1).upper())
    else:
        m = re.search(r'Điều kiện giao hàng\s*[:\s]+' + _INCOTERM_PATTERN.pattern, raw_text, re.IGNORECASE)
        if m:
            _set("incoterm", m.group(1).upper())

    # --- Phương thức thanh toán (Phase 1: fix regex) ---
    m = re.search(r'Phương thức thanh toán\s+([\w/]+(?:\s+\w+){0,3})', raw_text)
    if m:
        val = m.group(1).strip()
        pay_match = _PAYMENT_PATTERN.search(val)
        if pay_match:
            _set("paymentMethod", pay_match.group(0).strip().upper())
        else:
            _set("paymentMethod", val)
    else:
        m = re.search(r'PHUONG THUC THANH TOAN[:\s]+([\w/]+(?:\s+\w+){0,3})', raw_text, re.IGNORECASE)
        if m:
            _set("paymentMethod", m.group(1).strip())

    # --- Mã số hàng hóa (HS Code) ---
    hs_matches = re.findall(r'\b(\d{4}\.\d{2}(?:\.\d{2,4}){0,2})\b', raw_text)
    if hs_matches:
        _set("hsCode", hs_matches[0].replace('.', ''))

    # --- Mô tả hàng hóa ---
    m = re.search(r'Tên hàng\s+(.+?)(?:\n|$)', raw_text)
    if m:
        _set("description", m.group(1).strip()[:300])
    else:
        m = re.search(r'Phần ghi chú\s+(.+?)(?:\n|$)', raw_text)
        if m:
            _set("description", m.group(1).strip()[:300])

    # --- Lượng (Quantity) ---
    qty_matches = re.findall(r'(?<!\w)Lượng\s+([\d.,]+)', raw_text)
    if qty_matches:
        parsed = _parse_number(qty_matches[0])
        if parsed is not None:
            _set("quantity", str(parsed))

    # --- Đơn giá ---
    up_matches = re.findall(r'Đơn giá nguyên tệ\s+([\d.,]+)', raw_text)
    if up_matches:
        parsed = _parse_number(up_matches[0])
        if parsed is not None:
            _set("unitPrice", str(parsed))

    # --- Container No (Phase 4) ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))

    # --- Seal No (Phase 4) ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- Thuế (Phase 4) ---
    m = re.search(r'Tổng số tiền thuế\s+([\d.,]+)', raw_text)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed is not None:
            _set("taxAmount", str(parsed))

    # --- Tỷ giá (Phase 4) ---
    m = re.search(r'Tỷ giá tính thuế\s+([\d.,]+)', raw_text)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed is not None:
            _set("exchangeRate", str(parsed))

    # --- C/O (Phase 4) ---
    m = re.search(r'(?:C/O|Certificate of Origin)\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("coNo", m.group(1))

    # --- L/C (Phase 4) ---
    m = re.search(r'(?:L/C|Letter of Credit)\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("lcNo", m.group(1))

    return results


def _parse_bill_of_lading(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Bill of Lading (Phase 3).
    
    Xử lý multi-line shipper/consignee, combined vessel/voyage,
    container/seal table, freight terms, on-board date.
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["bill_of_lading"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- B/L Number ---
    for pat in [
        r'B/L\s*(?:Number|No\.?)\s*:?\s*([A-Z0-9][\w\-]+)',
        r'BL\s*NO\.?\s*:?\s*([A-Z0-9][\w\-]+)',
        r'Bill\s*of\s*Lading\s*No\.?\s*:?\s*([A-Z0-9][\w\-]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("blNo", m.group(1).strip(), 0.95)
            break

    # --- Date of Issue ---
    for pat in [
        r'(?:Date|Dated)\s*(?:of\s*Issue)?\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
        r'Place\s*and\s*Date\s*of\s*Issue.*?(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            _set("date", parsed or m.group(1))
            break

    # --- Shipper (multi-line) ---
    stop_kws = ["consignee", "notify", "vessel", "port", "b/l"]
    val = _extract_multiline_value(raw_text, "Shipper", max_lines=4, stop_keywords=stop_kws)
    if val:
        _set("shipper", val)

    # --- Consignee (multi-line) ---
    stop_kws = ["notify", "vessel", "port", "b/l", "shipper"]
    val = _extract_multiline_value(raw_text, "Consignee", max_lines=4, stop_keywords=stop_kws)
    if val:
        _set("consignee", val)

    # --- Notify Party (multi-line) ---
    stop_kws = ["vessel", "port", "b/l", "shipper", "consignee", "description"]
    val = _extract_multiline_value(raw_text, "Notify Party", max_lines=4, stop_keywords=stop_kws)
    if not val:
        val = _extract_multiline_value(raw_text, "Notify", max_lines=3, stop_keywords=stop_kws)
    if val and val.lower() not in ('party', 'same as consignee'):
        _set("notifyParty", val)

    # --- Vessel / Voyage (combined split) ---
    for pat in [
        r'(?:Ocean\s*)?Vessel\s*/?\s*Voy(?:age)?\s*[:\s]*([^\n]+)',
        r'Vessel\s*(?:Name)?\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            # Split "EVER GIVEN / 123E" or "EVER GIVEN V.123E"
            split_m = re.match(r'(.+?)\s*[/\\]\s*(\S+)\s*$', val)
            if split_m:
                _set("vessel", split_m.group(1).strip())
                _set("voyage", split_m.group(2).strip())
            elif re.match(r'(.+?)\s+V\.?\s*(\S+)\s*$', val):
                split_m = re.match(r'(.+?)\s+V\.?\s*(\S+)\s*$', val)
                _set("vessel", split_m.group(1).strip())
                _set("voyage", split_m.group(2).strip())
            else:
                _set("vessel", val)
            break

    # Voyage standalone
    if "voyage" not in results:
        m = re.search(r'Voyage?\s*(?:No\.?)?\s*:?\s*(\S+)', raw_text, re.IGNORECASE)
        if m:
            _set("voyage", m.group(1))

    # --- POL ---
    for pat in [
        r'Port\s*of\s*Loading\s*:?\s*([^\n\t]+?)(?:\t|\n|Port|$)',
        r'POL\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("pol", m.group(1).strip())
            break

    # --- POD ---
    for pat in [
        r'Port\s*of\s*Discharge\s*:?\s*([^\n\t]+?)(?:\t|\n|Port|Place|$)',
        r'POD\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("pod", m.group(1).strip())
            break

    # --- Place of Delivery ---
    for pat in [
        r'Place\s*of\s*Delivery\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
        r'Final\s*Destination\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("placeOfDelivery", m.group(1).strip())
            break

    # --- Port of Transshipment ---
    m = re.search(r'(?:Port\s*of\s*)?Trans(?:ship|-)ment\s*:?\s*([^\n\t]+?)(?:\t|\n|$)', raw_text, re.IGNORECASE)
    if m:
        _set("portOfTransshipment", m.group(1).strip())

    # --- Container No (all) ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))
        _set("containerQuantity", str(len(containers)), 0.80) if len(containers) > 0 else None

    # --- Seal No ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- Description of Goods (multi-line) ---
    stop_kws = ["gross weight", "measurement", "total", "freight", "packages", "container"]
    val = _extract_multiline_value(raw_text, "Description of Goods", max_lines=5, stop_keywords=stop_kws)
    if not val:
        val = _extract_multiline_value(raw_text, "Particulars", max_lines=5, stop_keywords=stop_kws)
    if val:
        _set("description", val[:400])

    # --- Gross Weight ---
    m = re.search(r'(?:Gross|G\.?\s*W\.?)\s*(?:Weight)?\s*:?\s*([\d,.]+)\s*(?:KGS?|KG|MT)?', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("grossWeight", str(parsed))

    # --- Net Weight ---
    m = re.search(r'(?:Net|N\.?\s*W\.?)\s*(?:Weight)?\s*:?\s*([\d,.]+)\s*(?:KGS?|KG|MT)?', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("netWeight", str(parsed))

    # --- Measurement / CBM ---
    m = re.search(r'(?:Measurement|CBM|Volume)\s*:?\s*([\d,.]+)', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("measurement", str(parsed))

    # --- Packages ---
    m = re.search(r'(\d+)\s*(?:PKGS?|PACKAGES?|CTNS?|PLTS?|PCS|CARTONS?|CASES?)', raw_text, re.IGNORECASE)
    if m:
        _set("packages", m.group(1))

    # --- Freight Terms ---
    if re.search(r'FREIGHT\s*PREPAID', raw_text, re.IGNORECASE):
        _set("freightTerms", "FREIGHT PREPAID")
    elif re.search(r'FREIGHT\s*COLLECT', raw_text, re.IGNORECASE):
        _set("freightTerms", "FREIGHT COLLECT")

    # --- On Board Date ---
    m = re.search(r'(?:SHIPPED|LADEN)\s*ON\s*BOARD.*?(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("onBoardDate", parsed or m.group(1))

    # --- B/L Type ---
    if re.search(r'ORIGINAL', raw_text, re.IGNORECASE):
        _set("blType", "ORIGINAL", 0.70)
    elif re.search(r'(?:TELEX|SURRENDERED|EXPRESS)\s*RELEASE', raw_text, re.IGNORECASE):
        _set("blType", "SURRENDERED/TELEX RELEASE", 0.80)

    return results


def _parse_booking(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Booking Confirmation (Phase 3)."""
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["booking"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- Booking No ---
    for pat in [
        r'Booking\s*(?:No\.?|Number|Ref\.?|Confirmation\s*No\.?)\s*:?\s*([A-Z0-9][\w\-]+)',
        r'BKG\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("bookingNo", m.group(1), 0.95)
            break

    # --- Date ---
    m = re.search(r'(?:Booking\s*)?Date\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("date", parsed or m.group(1))

    # --- Shipper (multi-line) ---
    stop_kws = ["consignee", "notify", "vessel", "port", "booking"]
    val = _extract_multiline_value(raw_text, "Shipper", max_lines=3, stop_keywords=stop_kws)
    if val:
        _set("shipper", val)

    # --- Consignee (multi-line) ---
    stop_kws = ["notify", "vessel", "port", "shipper", "booking"]
    val = _extract_multiline_value(raw_text, "Consignee", max_lines=3, stop_keywords=stop_kws)
    if val:
        _set("consignee", val)

    # --- Notify Party ---
    val = _extract_multiline_value(raw_text, "Notify Party", max_lines=3, stop_keywords=["vessel", "port"])
    if val:
        _set("notifyParty", val)

    # --- Vessel / Voyage ---
    for pat in [
        r'Vessel\s*/?\s*Voy(?:age)?\s*:?\s*([^\n]+)',
        r'Vessel\s*(?:Name)?\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            split_m = re.match(r'(.+?)\s*[/\\]\s*(\S+)\s*$', val)
            if split_m:
                _set("vessel", split_m.group(1).strip())
                _set("voyage", split_m.group(2).strip())
            else:
                _set("vessel", val)
            break

    if "voyage" not in results:
        m = re.search(r'Voyage?\s*(?:No\.?)?\s*:?\s*(\S+)', raw_text, re.IGNORECASE)
        if m:
            _set("voyage", m.group(1))

    # --- POL ---
    for pat in [
        r'(?:Port\s*of\s*Loading|POL|Place\s*of\s*Receipt)\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("pol", m.group(1).strip())
            break

    # --- POD ---
    for pat in [
        r'(?:Port\s*of\s*Discharge|POD|Place\s*of\s*Delivery)\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("pod", m.group(1).strip())
            break

    # --- Container Type (20'GP, 40'HC, 20RF, etc.) ---
    m = re.search(r"(\d{2})'?\s*(GP|HC|HQ|RF|OT|FR|TK|ST)", raw_text, re.IGNORECASE)
    if m:
        _set("containerType", f"{m.group(1)}'{m.group(2).upper()}")
    else:
        m = re.search(r'(?:Equipment|Container\s*Type|Size/Type)\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
        if m:
            _set("containerType", m.group(1).strip()[:30])

    # --- Container No (all) ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))
        _set("containerQuantity", str(len(containers)), 0.80)

    # --- Seal No ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- ETD ---
    for pat in [
        r'ETD\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
        r'Sailing\s*(?:Date|On)\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
        r'Departure\s*(?:Date)?\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            _set("etd", parsed or m.group(1))
            break

    # --- ETA ---
    for pat in [
        r'ETA\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
        r'Arrival\s*(?:Date)?\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            _set("eta", parsed or m.group(1))
            break

    # --- Transshipment ---
    m = re.search(r'(?:Trans(?:ship|-)ment|Via)\s*:?\s*([^\n\t]+?)(?:\t|\n|$)', raw_text, re.IGNORECASE)
    if m:
        _set("portOfTransshipment", m.group(1).strip())

    # --- Description ---
    for pat in [
        r'(?:Commodity|Cargo|Description)\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("description", m.group(1).strip()[:300])
            break

    # --- Gross Weight ---
    m = re.search(r'(?:Gross|G\.?\s*W\.?)\s*(?:Weight)?\s*:?\s*([\d,.]+)\s*(?:KGS?|KG|MT)?', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("grossWeight", str(parsed))

    return results


def _parse_packing_list(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Packing List (Phase 3).
    
    Xử lý table-format, N/W, G/W, CBM, multi-item totals.
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["packing_list"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- P/L No ---
    for pat in [
        r'(?:Packing\s*List|P/?L)\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9][\w\-./]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("plNo", m.group(1), 0.90)
            break

    # --- Date ---
    m = re.search(r'Date\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("date", parsed or m.group(1))

    # --- Shipper / Seller ---
    stop_kws = ["consignee", "buyer", "notify", "invoice", "vessel"]
    for kw in ["Shipper", "Seller", "Exporter", "From"]:
        val = _extract_multiline_value(raw_text, kw, max_lines=3, stop_keywords=stop_kws)
        if val and len(val) > 3:
            _set("shipper", val)
            break

    # --- Consignee / Buyer ---
    stop_kws = ["shipper", "seller", "notify", "invoice", "vessel", "description"]
    for kw in ["Consignee", "Buyer", "Importer", "Ship To"]:
        val = _extract_multiline_value(raw_text, kw, max_lines=3, stop_keywords=stop_kws)
        if val and len(val) > 3:
            _set("consignee", val)
            break

    # --- Invoice No ---
    m = re.search(r'Invoice\s*(?:No\.?|Ref\.?)\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("invoiceNo", m.group(1))

    # --- Description ---
    stop_kws = ["quantity", "qty", "weight", "total", "packages", "carton"]
    val = _extract_multiline_value(raw_text, "Description", max_lines=4, stop_keywords=stop_kws)
    if not val:
        val = _extract_multiline_value(raw_text, "Commodity", max_lines=3, stop_keywords=stop_kws)
    if val:
        _set("description", val[:400])

    # --- Quantity (TOTAL line preferred) ---
    total_qty = re.findall(r'(?:TOTAL|Total)\s*(?:QTY|Quantity)?\s*:?\s*([\d,]+)', raw_text, re.IGNORECASE)
    if total_qty:
        parsed = _parse_number(total_qty[-1])
        if parsed:
            _set("quantity", str(parsed))
    else:
        m = re.search(r'(?:QTY|Quantity)\s*:?\s*([\d,]+)', raw_text, re.IGNORECASE)
        if m:
            parsed = _parse_number(m.group(1))
            if parsed:
                _set("quantity", str(parsed))

    # --- Packages (TOTAL preferred) ---
    total_pkg = re.findall(r'(?:TOTAL|Total)\s*:?\s*([\d,]+)\s*(?:PKGS?|PACKAGES?|CTNS?|CARTONS?|PCS)', raw_text, re.IGNORECASE)
    if total_pkg:
        _set("packages", total_pkg[-1].replace(',', ''))
    else:
        m = re.search(r'(\d+)\s*(?:PKGS?|PACKAGES?|CTNS?|CARTONS?|CASES?)', raw_text, re.IGNORECASE)
        if m:
            _set("packages", m.group(1))

    # --- Net Weight (TOTAL preferred) ---
    nw_matches = re.findall(r'(?:TOTAL\s*)?(?:N\.?\s*W\.?|NET\s*(?:WEIGHT|WT))\s*:?\s*([\d,.]+)\s*(?:KGS?|KG|MT)?', raw_text, re.IGNORECASE)
    if nw_matches:
        parsed = _parse_number(nw_matches[-1])
        if parsed:
            _set("netWeight", str(parsed))

    # --- Gross Weight (TOTAL preferred) ---
    gw_matches = re.findall(r'(?:TOTAL\s*)?(?:G\.?\s*W\.?|GROSS\s*(?:WEIGHT|WT))\s*:?\s*([\d,.]+)\s*(?:KGS?|KG|MT)?', raw_text, re.IGNORECASE)
    if gw_matches:
        parsed = _parse_number(gw_matches[-1])
        if parsed:
            _set("grossWeight", str(parsed))

    # --- Measurement / CBM ---
    cbm_matches = re.findall(r'(?:Measurement|CBM|Volume)\s*:?\s*([\d,.]+)', raw_text, re.IGNORECASE)
    if cbm_matches:
        parsed = _parse_number(cbm_matches[-1])
        if parsed:
            _set("measurement", str(parsed))

    # --- Container No ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))

    # --- Seal No ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- Vessel ---
    m = re.search(r'Vessel\s*:?\s*([^\n\t]+?)(?:\t|\n|$)', raw_text, re.IGNORECASE)
    if m:
        _set("vessel", m.group(1).strip())

    # --- POL / POD ---
    m = re.search(r'(?:Port\s*of\s*Loading|POL)\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("pol", m.group(1).strip())
    m = re.search(r'(?:Port\s*of\s*Discharge|POD)\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("pod", m.group(1).strip())

    # --- Contract No ---
    m = re.search(r'(?:Contract|S/C|Hợp đồng)\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("contractNo", m.group(1))

    # --- HS Code ---
    hs_match = _HS_CODE_PATTERN.search(raw_text)
    if hs_match:
        _set("hsCode", re.sub(r'[\.\s]', '', hs_match.group(1)))

    # --- Origin ---
    m = re.search(r'(?:Country\s*of\s*Origin|Origin|Made\s*in)\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("origin", m.group(1).strip()[:50])

    return results


def _parse_debit_note(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Debit Note (Phase 3).
    
    Phase 1: Sửa keyword collision (to/from, truck bill/no).
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["debit_note"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- D/N No ---
    for pat in [
        r'D/?N\s*(?:No\.?|Number)\s*:?\s*([A-Z0-9][\w\-./]+)',
        r'Debit\s*Note\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("dnNo", m.group(1), 0.95)
            break

    # --- Date ---
    m = re.search(r'Date\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("date", parsed or m.group(1))

    # --- Shipper/From (company) — dùng context để phân biệt ---
    for pat in [
        r'(?:Issued\s*by|From\s*Company|Shipper)\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("shipper", m.group(1).strip())
            break

    # --- Consignee/Bill To — dùng "Bill To" hoặc "Attention" thay vì "To" chung ---
    for pat in [
        r'(?:Bill\s*To|Attention|Attn|Consignee)\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("consignee", m.group(1).strip())
            break

    # --- Truck Bill ---
    m = re.search(r'Truck\s*Bill\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("truckBill", m.group(1))

    # --- Truck No (license plate) ---
    m = re.search(r'(?:Truck\s*No\.?|Plate\s*No\.?|License\s*Plate|Biển\s*số)\s*:?\s*([A-Z0-9][\w\-. ]+)', raw_text, re.IGNORECASE)
    if m:
        _set("truckNo", m.group(1).strip())

    # --- B/L No ---
    m = re.search(r'B/?L\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-]+)', raw_text, re.IGNORECASE)
    if m:
        _set("blNo", m.group(1))

    # --- Container No ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:3]))

    # --- Origin (From location) — dùng "From" + context check ---
    m = re.search(r'From\s*(?:Location|Port|Place)?\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        # Exclude if it's an email or person name (basic heuristic)
        if '@' not in val and len(val) > 2:
            _set("origin", val)

    # --- Destination ---
    for pat in [
        r'(?:Deliver(?:y)?\s*To|Destination|To\s*(?:Location|Port|Place))\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("destination", m.group(1).strip())
            break

    # --- ETD/ETA ---
    m = re.search(r'ETD\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("etd", parsed or m.group(1))
    m = re.search(r'ETA\s*:?\s*(\d{1,4}[\-/\.]\d{1,2}[\-/\.]\d{1,4})', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1))
        _set("eta", parsed or m.group(1))

    # --- Total Amount ---
    totals = re.findall(r'(?:Total|Grand\s*Total|Amount\s*Due|Tổng\s*cộng)\s*:?\s*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
    if totals:
        for t in totals:
            parsed = _parse_number(t)
            if parsed is not None and parsed > 0:
                _set("totalAmount", str(parsed))
                break

    # --- Currency ---
    m = re.search(r'\b(USD|EUR|JPY|CNY|KRW|VND|GBP|SGD|THB|TWD)\b', raw_text)
    if m:
        _set("currency", m.group(1))

    return results


def _parse_customs_monitoring_list(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho DS Hàng hóa Giám sát HQ (Phase 3)."""
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["customs_monitoring_list"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- Số tờ khai ---
    m = re.search(r'Số tờ khai\s*:?\s*(\d{10,15})', raw_text)
    if not m:
        m = re.search(r'Số TK\s*:?\s*(\d{10,15})', raw_text, re.IGNORECASE)
    if m:
        _set("declarationNo", m.group(1))

    # --- Ngày tờ khai ---
    m = re.search(r'Ngày\s*(?:tờ khai|ĐK|đăng ký)\s*:?\s*(\d{1,2}/\d{1,2}/\d{4})', raw_text)
    if m:
        parsed = _parse_date(m.group(1))
        _set("date", parsed or m.group(1))

    # --- Đơn vị XNK ---
    m = re.search(r'(?:Đơn vị XNK|Đơn vị xuất nhập khẩu|Tên doanh nghiệp|Công ty)\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
    if m:
        _set("company", m.group(1).strip()[:100])

    # --- Mã số thuế ---
    m = re.search(r'(?:Mã số thuế|MST|Tax\s*Code)\s*:?\s*(\d{10,14})', raw_text, re.IGNORECASE)
    if m:
        _set("taxCode", m.group(1))

    # --- Loại hình ---
    m = re.search(r'(?:Loại hình|Mã loại hình)\s*:?\s*(\w+)', raw_text)
    if m:
        _set("typeCode", m.group(1))

    # --- Trạng thái ---
    m = re.search(r'Trạng thái\s*(?:tờ khai)?\s*:?\s*([^\n\t]+)', raw_text)
    if m:
        _set("status", m.group(1).strip()[:50])

    # --- Luồng ---
    m = re.search(r'(?:Luồng|Phân luồng)\s*:?\s*(\S+)', raw_text)
    if m:
        _set("lane", m.group(1))

    # --- Chi cục HQ ---
    m = re.search(r'(?:Chi cục|Cơ quan)\s*(?:Hải quan|HQ)\s*(?:giám sát)?\s*:?\s*([^\n]+)', raw_text)
    if m:
        _set("customsBranch", m.group(1).strip()[:100])

    # --- Container No ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:3]))

    # --- B/L No ---
    m = re.search(r'(?:Số vận đơn|B/?L\s*No\.?)\s*:?\s*([A-Z0-9][\w\-]+)', raw_text, re.IGNORECASE)
    if m:
        _set("blNo", m.group(1))

    return results


def _parse_arrival_notice(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Giấy thông báo hàng đến (Arrival Notice).

    Hỗ trợ các format:
    - HMM/Hyundai: CARGO ARRIVAL NOTICE, B/L Number:, Vessel / VOY:
    - Wan Hai: B/L No:, Est. Arrival Date:, CY-Terminal:
    - Evergreen: TO:, From:, Subject: ARRIVAL NOTICE
    - Heung-A: ARRIVAL NOTICE, B/L NO.:, VESSEL:
    
    Phase 4: Thêm POL, POD, voyage, sealNo, freeTimeExpiry.
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["arrival_notice"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- B/L Number ---
    for pat in [
        r'B/L\s*(?:Number|No\.?)\s*:?\s*([A-Z0-9][\w\-]+)',
        r'BL\s*NO\.?\s*:?\s*([A-Z0-9][\w\-]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            _set("blNo", m.group(1).strip())
            break

    # --- Booking No ---
    m = re.search(r'Booking\s*No\.?\s*:?\s*([A-Z0-9][\w\-]+)', raw_text, re.IGNORECASE)
    if m:
        _set("bookingNo", m.group(1).strip())

    # --- Vessel / VOY ---
    for pat in [
        r'Vessel\s*/?\s*VOY\s*:?\s*([^\n]+)',
        r'VESSEL\s*:?\s*([^\n]+)',
        r'Vessel\s*Name\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 2:
                # Try to split vessel/voyage
                split_m = re.match(r'(.+?)\s*[/\\]\s*(\S+)\s*$', val)
                if split_m:
                    _set("vessel", split_m.group(1).strip())
                    _set("voyage", split_m.group(2).strip())
                else:
                    _set("vessel", val)
                break

    # Voyage standalone
    if "voyage" not in results:
        m = re.search(r'Voyage?\s*:?\s*(\S+)', raw_text, re.IGNORECASE)
        if m:
            _set("voyage", m.group(1))

    # --- ETA ---
    for pat in [
        r'Est\.?\s*Arrival\s*Date\s*:?\s*([^\n]+)',
        r'ETA\s*:?\s*([^\n]+)',
        r'Arrival\s*Date\s*:?\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            parsed = _parse_date(val)
            _set("eta", parsed or val[:30])
            break

    # --- Shipper ---
    for pat in [
        r'Shipper\s*/?\s*Exporter\s*[:\n]\s*([^\n]+)',
        r'Shipper\s*:?\s*\n\s*([^\n]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'\s*Consignee.*$', '', val).strip()
            if val and len(val) > 3:
                _set("shipper", val)
                break

    # --- Consignee (multi-line) ---
    stop_kws = ["notify", "vessel", "port", "shipper", "description"]
    val = _extract_multiline_value(raw_text, "Consignee", max_lines=3, stop_keywords=stop_kws)
    if val and len(val) > 3:
        _set("consignee", val)
    else:
        m = re.search(r'TO\s*:\s*([^\n]+)', raw_text, re.IGNORECASE)
        if m and len(m.group(1).strip()) > 3:
            _set("consignee", m.group(1).strip())

    # --- Notify Party (multi-line) ---
    val = _extract_multiline_value(raw_text, "Notify Party", max_lines=3, stop_keywords=["vessel", "port"])
    if val and val.lower() != 'party' and len(val) > 3:
        _set("notifyParty", val)

    # --- Container No ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))

    # --- Seal No (Phase 4) ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- POL (Phase 4) ---
    m = re.search(r'(?:Port\s*of\s*Loading|POL)\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("pol", m.group(1).strip())

    # --- POD (Phase 4) ---
    m = re.search(r'(?:Port\s*of\s*Discharge|POD|Discharge\s*Port)\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("pod", m.group(1).strip())

    # --- CY-Terminal / Description ---
    m = re.search(r'CY-Terminal\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
    if m:
        _set("description", "CY: " + m.group(1).strip())

    # --- Gross Weight ---
    m = re.search(r'(?:Gross|G\.?\s*W\.?)\s*(?:Weight)?\s*:?\s*([\d,.]+)\s*(?:KGS?|KG)', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("grossWeight", str(parsed))

    # --- Measurement / CBM ---
    m = re.search(r'(?:Measurement|CBM|Volume)\s*:?\s*([\d,.]+)', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("measurement", str(parsed))

    # --- Packages ---
    m = re.search(r'(\d+)\s*(?:PKGS?|PACKAGES?|CTNS?|PLTS?|PCS)', raw_text, re.IGNORECASE)
    if m:
        _set("packages", m.group(1))

    # --- Freight Charges ---
    m = re.search(r'(?:Freight|Ocean\s*Freight|Cước)\s*(?:Charges?)?\s*:?\s*([\d,.]+)', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_number(m.group(1))
        if parsed:
            _set("freightCharges", str(parsed))

    # --- Free Time Expiry (Phase 4) ---
    m = re.search(r'Free\s*Time\s*(?:Until|Expires?|Expiry)\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(1).strip())
        if parsed:
            _set("freeTimeExpiry", parsed)
        else:
            _set("freeTimeExpiry", m.group(1).strip()[:30])

    # --- From (sending agent, fallback for shipper) ---
    if "shipper" not in results:
        m = re.search(r'From\s*:\s*([^\n]+)', raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 5:
                _set("shipper", val)

    return results


def _parse_commercial_invoice_pl(
    raw_text: str,
) -> dict[str, dict[str, Any]]:
    """Parser chuyên biệt cho Commercial Invoice & Packing List format Samsung.
    
    Hỗ trợ 2 format:
    - "1) Shipper/ Exporter" format
    - "Invoice No. XXX    Invoice Date YYYY/MM/DD" format (Samsung SDS)
    
    Phase 1: Fix dead code (grossWeight, netWeight, sailingDate).
    Phase 4: Thêm trường mới.
    """
    results: dict[str, dict[str, Any]] = {}
    fields_def = DOCUMENT_TYPES["invoice"]["fields"]

    def _set(key: str, value: str, conf: float = 0.85):
        if key in fields_def and value and value.strip() and len(value.strip()) > 1:
            results[key] = {
                "value": value.strip(),
                "confidence": conf,
                "label": fields_def[key]["label"],
            }

    # --- Invoice No ---
    m = re.search(r'(?:NO\.\s*&\s*DATE|NO\.\s*AND\s*DATE)\s*\n?\s*([A-Z0-9][\w.-]+)', raw_text, re.IGNORECASE)
    if m:
        _set("invoiceNo", m.group(1))
    else:
        m = re.search(r'Invoice\s*No\.?:?\s+([A-Z0-9][\w.-]+)', raw_text, re.IGNORECASE)
        if m:
            _set("invoiceNo", m.group(1))

    # --- Date ---
    m = re.search(r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}', raw_text, re.IGNORECASE)
    if m:
        parsed = _parse_date(m.group(0))
        _set("date", parsed or m.group(0))
    else:
        m = re.search(r'Invoice\s*Date:?\s+(\d{4}/\d{1,2}/\d{1,2})', raw_text, re.IGNORECASE)
        if m:
            parsed = _parse_date(m.group(1))
            _set("date", parsed or m.group(1))

    # --- Shipper / Exporter / Seller ---
    for pattern in [
        r'(?:1\)\s*)?Shipper/?\s*Exporter\s*:?\s*\n\s*([^\n]+)',
        r"Shipper's\s*Name\s*&\s*Address\s*:?\s*\n\s*([^\n]+)",
        r"Seller's\s*Name\s*&\s*Address\s*:?\s*\n\s*([^\n]+)",
    ]:
        m = re.search(pattern, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'\s*\d+\)\s*.*$', '', val).strip()
            if val and not val.startswith('8)') and len(val) > 3:
                _set("seller", val)
                break

    # --- Buyer / Consignee ---
    for pattern in [
        r'(?:2\)\s*)?For\s*Account\s*&\s*Risk\s*(?:of\s*messers)?\s*:?\s*\n\s*([^\n]+)',
        r"Consignee's\s*Name\s*&\s*Address\s*:?\s*\n\s*([^\n]+)",
        r'Sold\s*to\s*:?\s*\n?\s*([^\n]+)',
        r'Ship\s*to\s*:?\s*\n?\s*([^\n]+)',
    ]:
        m = re.search(pattern, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            val = re.sub(r'\s*\d+\)\s*.*$', '', val).strip()
            if val and len(val) > 3:
                _set("buyer", val)
                break

    # --- Incoterm ---
    m = re.search(r'\*\s*' + _INCOTERM_PATTERN.pattern, raw_text, re.IGNORECASE)
    if m:
        _set("incoterm", m.group(1).upper())
    else:
        m = re.search(r'Terms\s*of\s*Delivery\s*:?\s*' + _INCOTERM_PATTERN.pattern, raw_text, re.IGNORECASE)
        if m:
            _set("incoterm", m.group(1).upper())

    # --- POL ---
    m = re.search(r'PORT\s*OF\s*LOAD(?:ING)?\s*:?\s*([^\n\t]+?)(?:\t|\n|$)', raw_text, re.IGNORECASE)
    if m:
        _set("pol", m.group(1).strip())

    # --- POD / Final Destination ---
    for pat in [
        r'FINAL\s*DESTINATION\s*:?\s*([^\n\t]+?)(?:\t|\n|Carrier|Shipped|$)',
        r'PORT\s*OF\s*DISCHARGE\s*:?\s*([^\n\t]+?)(?:\t|\n|$)',
        r'PORT\s*OF\s*DESTINATION\s*:?\s*([^\n\t]+?)(?:\t|\n|Final|Carrier|$)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 2:
                _set("pod", val)
                break

    # --- Vessel / Flight ---
    for pat in [
        r'VESSEL/?\s*FLIGHT\s*:?\s*([^\n]+)',
        r'VESSEL\s*/?\s*VOY\s*:?\s*([^\n]+)',
        r'Shipped\s*via\s*:?\s*([^\n\t]+)',
    ]:
        m = re.search(pat, raw_text, re.IGNORECASE)
        if m:
            val = m.group(1).strip()
            if val and len(val) > 1:
                _set("vessel", val)
                break

    # --- Payment Terms ---
    m = re.search(r'Terms\s*of\s*Payment\s*:?\s*([^\n\t]+)', raw_text, re.IGNORECASE)
    if m:
        _set("paymentMethod", m.group(1).strip()[:80])

    # --- Currency ---
    m = re.search(r'\b(USD|EUR|JPY|CNY|KRW|VND|GBP|SGD|THB|TWD)\b', raw_text)
    if m:
        _set("currency", m.group(1))

    # --- Total Amount ---
    totals = re.findall(r'(?:TOTAL|Grand\s*Total|Amount\s*Due)\s*:?\s*([\d,]+\.?\d*)', raw_text, re.IGNORECASE)
    if totals:
        for t in totals:
            parsed = _parse_number(t)
            if parsed is not None and parsed > 0:
                _set("totalAmount", str(parsed))
                break

    # --- Container No ---
    containers = _extract_all_containers(raw_text)
    if containers:
        _set("containerNo", ", ".join(containers[:5]))

    # --- Seal No ---
    seals = _extract_all_seals(raw_text)
    if seals:
        _set("sealNo", ", ".join(seals[:5]))

    # --- Origin ---
    m = re.search(r'(?:COUNTRY\s*OF\s*ORIGIN|ORIGIN)\s*:?\s*([^\n]+)', raw_text, re.IGNORECASE)
    if m:
        _set("origin", m.group(1).strip()[:50])

    # --- Gross Weight (Phase 1: fix dead code) ---
    gw_matches = re.findall(r'(?:G\.?\s*W\.?|GROSS\s*(?:WEIGHT|WT))\s*:?\s*([\d,.]+)\s*(?:KGS?|KG)', raw_text, re.IGNORECASE)
    if gw_matches:
        for g in gw_matches:
            parsed = _parse_number(g)
            if parsed is not None and parsed > 0:
                _set("grossWeight", str(parsed))
                break

    # --- Net Weight (Phase 1: fix dead code) ---
    nw_matches = re.findall(r'(?:N\.?\s*W\.?|NET\s*(?:WEIGHT|WT))\s*:?\s*([\d,.]+)\s*(?:KGS?|KG)', raw_text, re.IGNORECASE)
    if nw_matches:
        for n in nw_matches:
            parsed = _parse_number(n)
            if parsed is not None and parsed > 0:
                _set("netWeight", str(parsed))
                break

    # --- Packages ---
    m = re.search(r'(\d+)\s*(?:PKGS?|PACKAGES?|CTNS?|CARTONS?)', raw_text, re.IGNORECASE)
    if m:
        _set("packages", m.group(1))

    # --- Quantity ---
    qty_matches = re.findall(r'(?:QTY|QUANTITY)\s*:?\s*([\d,]+)', raw_text, re.IGNORECASE)
    if qty_matches:
        parsed = _parse_number(qty_matches[0])
        if parsed is not None:
            _set("quantity", str(parsed))

    # --- HS Code ---
    hs_match = _HS_CODE_PATTERN.search(raw_text)
    if hs_match:
        _set("hsCode", re.sub(r'[\.\s]', '', hs_match.group(1)))

    # --- Contract No ---
    m = re.search(r'(?:Contract|S/C)\s*(?:No\.?)?\s*:?\s*([A-Z0-9][\w\-./]+)', raw_text, re.IGNORECASE)
    if m:
        _set("contractNo", m.group(1))

    # --- Description ---
    stop_kws = ["quantity", "qty", "total", "unit price", "amount"]
    val = _extract_multiline_value(raw_text, "Description of Goods", max_lines=4, stop_keywords=stop_kws)
    if not val:
        val = _extract_multiline_value(raw_text, "Description", max_lines=3, stop_keywords=stop_kws)
    if val:
        _set("description", val[:400])

    return results


# ═══════════════════════════════════════════════════════════════════════════
# AI Parse (Phase 5: cải thiện prompt, confidence, hybrid merge)
# ═══════════════════════════════════════════════════════════════════════════

def ai_parse_fields(
    raw_text: str,
    doc_type: str,
    api_key: str,
) -> dict[str, dict[str, Any]]:
    """Trích xuất giá trị các trường bằng AI (Google Gemini) + Hybrid merge với regex."""
    regex_results = parse_fields(raw_text, doc_type)

    if not api_key:
        return regex_results

    if doc_type not in DOCUMENT_TYPES:
        return regex_results

    fields_def = DOCUMENT_TYPES[doc_type]["fields"]
    
    schema_hint = {}
    for key, fdef in fields_def.items():
        schema_hint[key] = f"{fdef['label']} (type: {fdef['type']})"
        
    prompt = f"""Bạn là một AI chuyên gia đọc hiểu chứng từ xuất nhập khẩu quốc tế.
Nhiệm vụ: Phân tích văn bản chứng từ dưới đây và trích xuất thông tin theo định dạng JSON.

LOẠI CHỨNG TỪ: {DOCUMENT_TYPES[doc_type]['name']}
CÁC TRƯỜNG CẦN TÌM:
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

QUY TẮC QUAN TRỌNG:
1. Trường number (số lượng, trị giá, trọng lượng): Trả về con số thực không có dấu phẩy (VD: 1234.56, không phải 1,234.56).
2. Trường date: Trả về chuẩn YYYY-MM-DD. Ưu tiên DD/MM/YYYY cho tài liệu tiếng Việt.
3. Nếu hoàn toàn không thấy dữ liệu cho một trường, trả về null.
4. Container number format: 4 chữ + 7 số (VD: HDMU1234567). Nếu có nhiều, phân cách bằng dấu phẩy.
5. HS Code: loại bỏ dấu chấm, trả về dạng liền (VD: "8473.30.90" → "84733090").
6. Tờ khai Hải quan thường có danh sách nhiều mặt hàng. ĐỐI VỚI CÁC TRƯỜNG THUỘC VỀ DANH SÁCH MẶT HÀNG (hsCode, description, origin, quantity, uom, unitPrice, itemValue): Hãy trả về dưới dạng mảng (array) các object (ví dụ: "items": [ {{"hsCode": "...", "description": "..."}}, {{"hsCode": "...", ...}} ]). Các trường chung khác vẫn nằm ở root JSON.
7. Nếu shipper/consignee có địa chỉ nhiều dòng, cố gắng phân tách Tên và Địa chỉ vào đúng trường tương ứng.
8. Incoterm chỉ trả về mã viết tắt: FOB, CIF, EXW, FCA, CPT, CIP, DAP, DPU, DDP, FAS, CFR, DAT.
9. Payment method: T/T, L/C, D/P, D/A, CASH, O/A, etc.
10. Với văn bản OCR lộn xộn: cố gắng ghép lại từ bị tách, bỏ qua ký tự rác.
11. Chỉ output DUY NHẤT một cục JSON hợp lệ, tuyệt đối không bình luận thêm.

VÍ DỤ OUTPUT:
{{"invoiceNo": "INV-2024-001", "date": "2024-01-15", "totalAmount": 50000.00, "currency": "USD", "items": [{{"description": "LAPTOP", "quantity": 10}}]}}

--- BẮT ĐẦU VĂN BẢN CHỨNG TỪ ---
{raw_text[:20000]}
--- KẾT THÚC VĂN BẢN CHỨNG TỪ ---
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        resp_text = response.text.strip()
        resp_text = re.sub(r'^```(?:json)?\s*\n?', '', resp_text)
        resp_text = re.sub(r'\n?```\s*$', '', resp_text)
            
        ai_data = json.loads(resp_text.strip())
        
        ai_results: dict[str, dict[str, Any]] = {}
        
        item_fields = ["hsCode", "description", "origin", "quantity", "uom", "unitPrice", "itemValue"]
        
        for field_key, field_def in fields_def.items():
            if field_key in item_fields:
                continue
                
            val = ai_data.get(field_key)
            if val is not None and str(val).strip() and str(val).strip().lower() != "null":
                if field_def["type"] == "number":
                    try:
                        parsed_val = str(float(str(val).replace(',', '')))
                    except (ValueError, TypeError):
                        parsed_val = str(val)
                else:
                    parsed_val = str(val)

                ai_results[field_key] = {
                    "value": parsed_val,
                    "confidence": 0.90,
                    "label": field_def["label"]
                }
                
        items = ai_data.get("items", [])
        if isinstance(items, list):
            for i, item in enumerate(items):
                idx = i + 1
                for k, v in item.items():
                    if k in fields_def and k in item_fields and v is not None and str(v).strip() and str(v).strip().lower() != "null":
                        field_def = fields_def[k]
                        if field_def["type"] == "number":
                            try:
                                parsed_val = str(float(str(v).replace(',', '')))
                            except (ValueError, TypeError):
                                parsed_val = str(v)
                        else:
                            parsed_val = str(v)
                        
                        dynamic_key = f"{k}_{idx}"
                        ai_results[dynamic_key] = {
                            "value": parsed_val,
                            "confidence": 0.95,
                            "label": f"{field_def['label']} [Hàng {idx}]"
                        }
        
        merged = dict(ai_results)
        for key, regex_field in regex_results.items():
            if key not in merged or merged[key]["value"] == "":
                merged[key] = regex_field
        
        return merged
    except Exception as e:
        print(f"Lỗi AI parse: {e}")
        return regex_results


def = DOCUMENT_TYPES[doc_type]["fields"]
    
    # Tạo schema hướng dẫn AI
    schema_hint = {}
    for key, fdef in fields_def.items():
        schema_hint[key] = f"{fdef['label']} (type: {fdef['type']})"
        
    prompt = f"""Bạn là một AI chuyên gia đọc hiểu chứng từ xuất nhập khẩu quốc tế.
Nhiệm vụ: Phân tích văn bản chứng từ dưới đây và trích xuất thông tin theo định dạng JSON.

LOẠI CHỨNG TỪ: {DOCUMENT_TYPES[doc_type]['name']}
CÁC TRƯỜNG CẦN TÌM:
{json.dumps(schema_hint, ensure_ascii=False, indent=2)}

QUY TẮC QUAN TRỌNG:
1. Trường number (số lượng, trị giá, trọng lượng): Trả về con số thực không có dấu phẩy (VD: 1234.56, không phải 1,234.56).
2. Trường date: Trả về chuẩn YYYY-MM-DD. Ưu tiên DD/MM/YYYY cho tài liệu tiếng Việt.
3. Nếu hoàn toàn không thấy dữ liệu cho một trường, trả về null.
4. Container number format: 4 chữ + 7 số (VD: HDMU1234567). Nếu có nhiều, phân cách bằng dấu phẩy.
5. HS Code: loại bỏ dấu chấm, trả về dạng liền (VD: "8473.30.90" → "84733090").
6. Nếu shipper/consignee có địa chỉ nhiều dòng, chỉ lấy TÊN CÔNG TY (dòng đầu).
7. Incoterm chỉ trả về mã viết tắt: FOB, CIF, EXW, FCA, CPT, CIP, DAP, DPU, DDP, FAS, CFR, DAT.
8. Payment method: T/T, L/C, D/P, D/A, CASH, O/A, etc.
9. Với văn bản OCR lộn xộn: cố gắng ghép lại từ bị tách, bỏ qua ký tự rác.
10. Chỉ output DUY NHẤT một cục JSON hợp lệ, tuyệt đối không bình luận thêm.

VÍ DỤ OUTPUT:
{{"invoiceNo": "INV-2024-001", "date": "2024-01-15", "totalAmount": 50000.00, "currency": "USD", "seller": "ABC COMPANY", "buyer": "XYZ CORPORATION", "incoterm": "FOB"}}

--- BẮT ĐẦU VĂN BẢN CHỨNG TỪ ---
{raw_text[:20000]}
--- KẾT THÚC VĂN BẢN CHỨNG TỪ ---
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        
        resp_text = response.text.strip()
        # Xóa markdown code block nếu AI sinh ra
        resp_text = re.sub(r'^```(?:json)?\s*\n?', '', resp_text)
        resp_text = re.sub(r'\n?```\s*$', '', resp_text)
            
        ai_data = json.loads(resp_text.strip())
        
        ai_results: dict[str, dict[str, Any]] = {}
        for field_key, field_def in fields_def.items():
            val = ai_data.get(field_key)
            if val is not None and str(val).strip() and str(val).strip().lower() != "null":
                # Chuyển đổi an toàn
                if field_def["type"] == "number":
                    try:
                        parsed_val = str(float(str(val).replace(',', '')))
                    except (ValueError, TypeError):
                        parsed_val = str(val)
                else:
                    parsed_val = str(val)

                ai_results[field_key] = {
                    "value": parsed_val,
                    "confidence": 0.90,  # Phase 5: confidence hợp lý hơn
                    "label": field_def["label"]
                }

        # === Phase 5: Hybrid merge ===
        # AI results as base, fill gaps from regex
        merged = dict(ai_results)
        for key, regex_field in regex_results.items():
            if key not in merged:
                # Regex found it but AI didn't → keep regex result
                merged[key] = regex_field
            elif regex_field.get('confidence', 0) > merged[key].get('confidence', 0):
                # Regex has higher confidence → prefer regex
                merged[key] = regex_field
        
        return merged
        
    except Exception as e:
        print(f"Lỗi AI Parser: {e}. Đang dùng regex fallback...")
        return regex_results



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
