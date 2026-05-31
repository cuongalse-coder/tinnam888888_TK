"""Module so sánh chứng từ xuất nhập khẩu.

Cung cấp các hàm so sánh từng cặp hoặc nhiều tài liệu cùng lúc,
xuất kết quả dưới dạng DataFrame hoặc file Excel.
"""

from __future__ import annotations

import io
import re
from typing import Any

import pandas as pd
from rapidfuzz import fuzz

from utils.parser import (
    DOCUMENT_TYPES,
    FIELD_MAPPING,
    get_field_label,
)


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_str(value: Any) -> str:
    """Chuẩn hoá chuỗi trước khi so sánh: xoá toàn bộ khoảng trắng, ký tự đặc biệt."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    s = str(value).lower()
    # Loại bỏ hậu tố .0 nếu bị ép kiểu dư
    s = re.sub(r"\.0+$", "", s)
    # Loại bỏ tất cả các ký tự không phải chữ cái/số
    s = re.sub(r"[^\w\d]", "", s)
    return s


def _try_float(value: str) -> float | None:
    """Thử chuyển chuỗi thành float, trả None nếu không được."""
    try:
        cleaned = value.replace(",", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _compare_values(
    val1: str,
    val2: str,
    field_type: str,
) -> tuple[str, float]:
    """So sánh hai giá trị theo kiểu dữ liệu.

    Parameters
    ----------
    val1, val2 : str
        Hai giá trị cần so sánh.
    field_type : str
        Loại dữ liệu: ``'string'``, ``'number'``, ``'date'``.

    Returns
    -------
    tuple[str, float]
        ``(status, similarity)`` – status ∈ {'match', 'mismatch'}.
    """
    if field_type == "number":
        n1 = _try_float(val1)
        n2 = _try_float(val2)
        if n1 is not None and n2 is not None:
            if n1 == 0 and n2 == 0:
                return "match", 100.0
            max_abs = max(abs(n1), abs(n2))
            diff_ratio = abs(n1 - n2) / max_abs if max_abs != 0 else 0.0
            if diff_ratio <= 0.01:
                return "match", 100.0
            similarity = max(0.0, (1.0 - diff_ratio) * 100)
            return "mismatch", round(similarity, 2)

    if field_type == "date":
        # So sánh chính xác chuỗi ngày (đã chuẩn hoá ở parser)
        if _normalize_str(val1) == _normalize_str(val2):
            return "match", 100.0
        return "mismatch", 0.0

    # String – dùng fuzzy matching
    sim = fuzz.ratio(_normalize_str(val1), _normalize_str(val2))
    status = "match" if sim >= 80 else "mismatch"
    return status, round(float(sim), 2)


def _build_field_lookup(doc_type: str) -> dict[str, str]:
    """Tạo bảng tra {field_key: field_type} cho 1 loại chứng từ."""
    if doc_type not in DOCUMENT_TYPES:
        return {}
    return {
        k: v["type"]
        for k, v in DOCUMENT_TYPES[doc_type]["fields"].items()
    }


def _find_mapping_pairs(
    type1: str,
    type2: str,
) -> list[tuple[str, str, str]]:
    """Tìm các cặp trường tương đương giữa 2 loại chứng từ.

    Returns
    -------
    list[tuple[str, str, str]]
        Danh sách ``(field_key_1, field_key_2, label)`` – label lấy
        từ doc1.
    """
    prefix1 = f"{type1}."
    prefix2 = f"{type2}."
    pairs: list[tuple[str, str, str]] = []
    seen_keys: set[tuple[str, str]] = set()

    for group in FIELD_MAPPING:
        keys1 = [
            e.split(".", 1)[1] for e in group
            if e.startswith(prefix1)
        ]
        keys2 = [
            e.split(".", 1)[1] for e in group
            if e.startswith(prefix2)
        ]
        for k1 in keys1:
            for k2 in keys2:
                if (k1, k2) not in seen_keys:
                    label = get_field_label(type1, k1)
                    pairs.append((k1, k2, label))
                    seen_keys.add((k1, k2))

    # Thêm các trường cùng tên (chưa nằm trong mapping)
    if type1 in DOCUMENT_TYPES and type2 in DOCUMENT_TYPES:
        fields1 = set(DOCUMENT_TYPES[type1]["fields"].keys())
        fields2 = set(DOCUMENT_TYPES[type2]["fields"].keys())
        common = fields1 & fields2
        for key in common:
            if (key, key) not in seen_keys:
                label = get_field_label(type1, key)
                pairs.append((key, key, label))
                seen_keys.add((key, key))

    return pairs


# ═══════════════════════════════════════════════════════════════════════════
# So sánh 2 tài liệu
# ═══════════════════════════════════════════════════════════════════════════

def compare_documents(doc1: dict[str, Any], doc2: dict[str, Any]) -> dict[str, Any]:
    """So sánh hai tài liệu và trả về kết quả chi tiết.

    Parameters
    ----------
    doc1, doc2 : dict
        Cấu trúc: ``{'id': str, 'doc_type': str, 'fields': dict, 'file_name': str}``.
        Trong đó ``fields`` là output của ``parse_fields()``:
        ``{field_key: {'value': str, 'confidence': float, 'label': str}}``.

    Returns
    -------
    dict
        ``{'doc1_name': str, 'doc2_name': str, 'doc1_type': str,
           'doc2_type': str, 'results': list, 'summary': dict}``
    """
    try:
        type1 = doc1.get("doc_type", "")
        type2 = doc2.get("doc_type", "")
        fields1: dict[str, Any] = doc1.get("fields", {})
        fields2: dict[str, Any] = doc2.get("fields", {})
        lookup1 = _build_field_lookup(type1)
        lookup2 = _build_field_lookup(type2)

        mapping_pairs = _find_mapping_pairs(type1, type2)
        results: list[dict[str, Any]] = []
        processed: set[tuple[str, str]] = set()

        for key1, key2, label in mapping_pairs:
            f1 = fields1.get(key1)
            f2 = fields2.get(key2)
            val1 = f1["value"] if f1 else None
            val2 = f2["value"] if f2 else None

            if val1 is None and val2 is None:
                continue

            if val1 is not None and val2 is not None:
                field_type = lookup1.get(key1, "string")
                status, similarity = _compare_values(val1, val2, field_type)
            elif val1 is not None:
                status, similarity = "missing", 0.0
            else:
                status, similarity = "missing", 0.0

            results.append({
                "label": label,
                "doc1_key": key1,
                "doc2_key": key2,
                "doc1_value": val1 or "",
                "doc2_value": val2 or "",
                "status": status,
                "similarity": similarity,
            })
            processed.add((key1, key2))

        # Tổng kết
        total = len(results)
        matches = sum(1 for r in results if r["status"] == "match")
        mismatches = sum(1 for r in results if r["status"] == "mismatch")
        missing = sum(1 for r in results if r["status"] == "missing")
        match_rate = (matches / total * 100) if total > 0 else 0.0

        return {
            "doc1_name": doc1.get("file_name", "Tài liệu 1"),
            "doc2_name": doc2.get("file_name", "Tài liệu 2"),
            "doc1_type": type1,
            "doc2_type": type2,
            "results": results,
            "summary": {
                "total": total,
                "matches": matches,
                "mismatches": mismatches,
                "missing": missing,
                "match_rate": round(match_rate, 2),
            },
        }

    except Exception as exc:
        return {
            "doc1_name": doc1.get("file_name", ""),
            "doc2_name": doc2.get("file_name", ""),
            "doc1_type": doc1.get("doc_type", ""),
            "doc2_type": doc2.get("doc_type", ""),
            "results": [],
            "summary": {
                "total": 0,
                "matches": 0,
                "mismatches": 0,
                "missing": 0,
                "match_rate": 0.0,
            },
            "error": f"Lỗi khi so sánh tài liệu: {exc}",
        }


# ═══════════════════════════════════════════════════════════════════════════
# So sánh nhiều tài liệu (Cấu trúc mới theo Cụm Đối Chiếu)
# ═══════════════════════════════════════════════════════════════════════════

def _build_aggregate_for_docs(docs: list[dict[str, Any]], target_fields: list[str]) -> list[dict[str, Any]]:
    """Tạo bảng đối chiếu cho danh sách tài liệu, chỉ so sánh các trường trong target_fields."""
    field_values: dict[str, dict[str, str]] = {}
    
    # Gom dữ liệu từ các tài liệu
    for doc in docs:
        doc_id: str = doc.get("id", doc.get("file_name", ""))
        fields = doc.get("fields", {})
        doc_type = doc.get("doc_type", "")
        
        for field_key, field_data in fields.items():
            full_key = f"{doc_type}.{field_key}"
            # Chỉ lấy các trường có trong danh sách target (hoặc nếu target rỗng thì lấy hết)
            if target_fields and full_key not in target_fields:
                continue
                
            label = field_data.get("label", get_field_label(doc_type, field_key))
            if label not in field_values:
                field_values[label] = {}
            field_values[label][doc_id] = field_data.get("value", "")

    # Đánh giá khớp/sai
    aggregate: list[dict[str, Any]] = []
    for label, values_map in field_values.items():
        unique_values = set(
            _normalize_str(v) for v in values_map.values() if v
        )
        all_match = len(unique_values) <= 1
        aggregate.append({
            "label": label,
            "values": values_map,
            "all_match": all_match,
        })
    return aggregate


def compare_by_clusters(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """Phân loại và đối chiếu tài liệu theo từng cụm nghiệp vụ cụ thể."""
    try:
        invoices = [d for d in docs if d.get("doc_type") == "invoice"]
        pls = [d for d in docs if d.get("doc_type") == "packing_list"]
        bls = [d for d in docs if d.get("doc_type") in ("bill_of_lading", "arrival_notice", "booking")]
        customs = [d for d in docs if d.get("doc_type") == "customs_declaration"]
        
        clusters = {}
        
        if invoices and pls:
            clusters["Invoice vs Packing List"] = _build_aggregate_for_docs(invoices + pls, [
                "invoice.seller", "packing_list.shipper",
                "invoice.buyer", "packing_list.consignee",
                "invoice.description", "packing_list.description",
                "invoice.quantity", "packing_list.quantity",
                "invoice.grossWeight", "packing_list.grossWeight",
                "invoice.netWeight", "packing_list.netWeight",
                "invoice.invoiceNo", "packing_list.invoiceNo",
            ])
            
        if bls and pls:
            clusters["Bill of Lading vs Packing List"] = _build_aggregate_for_docs(bls + pls, [
                "bill_of_lading.containerNo", "packing_list.containerNo", "arrival_notice.containerNo", "booking.containerNo",
                "bill_of_lading.grossWeight", "packing_list.grossWeight", "arrival_notice.grossWeight",
                "bill_of_lading.measurement", "packing_list.measurement", "arrival_notice.measurement",
                "bill_of_lading.packages", "packing_list.packages", "arrival_notice.packages",
                "bill_of_lading.vessel", "packing_list.vessel", "arrival_notice.vessel", "booking.vessel",
                "bill_of_lading.voyage", "packing_list.voyage", "arrival_notice.voyage", "booking.voyage",
                "bill_of_lading.pol", "packing_list.pol", "booking.pol",
                "bill_of_lading.pod", "packing_list.pod", "booking.pod",
                "bill_of_lading.sealNo", "packing_list.sealNo",
            ])
            
        if customs and (invoices or pls or bls):
            clusters["Tờ khai Hải quan vs Chứng từ khác"] = _build_aggregate_for_docs(customs + invoices + pls + bls, [
                "customs_declaration.exporter", "invoice.seller", "packing_list.shipper", "bill_of_lading.shipper",
                "customs_declaration.importer", "invoice.buyer", "packing_list.consignee", "bill_of_lading.consignee",
                "customs_declaration.description", "invoice.description", "packing_list.description",
                "customs_declaration.quantity", "invoice.quantity", "packing_list.quantity",
                "customs_declaration.grossWeight", "bill_of_lading.grossWeight", "packing_list.grossWeight", "arrival_notice.grossWeight",
                "customs_declaration.containerNo", "bill_of_lading.containerNo", "packing_list.containerNo", "arrival_notice.containerNo", "invoice.containerNo",
                "customs_declaration.value", "invoice.totalAmount",
                "customs_declaration.invoiceNo", "invoice.invoiceNo", "packing_list.invoiceNo",
                "customs_declaration.invoiceDate", "invoice.date",
                "customs_declaration.incoterm", "invoice.incoterm",
                "customs_declaration.paymentMethod", "invoice.paymentMethod",
                "customs_declaration.blNo", "bill_of_lading.blNo", "arrival_notice.blNo",
                "customs_declaration.hsCode",
            ])
            
        # Nếu chỉ upload những file không nằm trong các cụm trên, ta tạo một cụm đối chiếu chung
        if not clusters:
            clusters["Đối chiếu Chung (Tất cả chứng từ)"] = _build_aggregate_for_docs(docs, [])
            
        # Thêm aggregate tổng hợp cho AI
        all_aggregate = []
        seen_labels = set()
        for agg_list in clusters.values():
            for item in agg_list:
                if item["label"] not in seen_labels:
                    all_aggregate.append(item)
                    seen_labels.add(item["label"])
                    
        return {
            "pair_results": [],
            "aggregate": all_aggregate,
            "clusters": clusters,
        }
    except Exception as exc:
        return {
            "pair_results": [],
            "aggregate": [],
            "clusters": {},
            "error": f"Lỗi khi phân nhóm so sánh: {exc}",
        }


def compare_multiple(docs: list[dict[str, Any]]) -> dict[str, Any]:
    """So sánh tất cả các cặp tài liệu và tổng hợp kết quả.

    Parameters
    ----------
    docs : list[dict]
        Danh sách tài liệu, mỗi phần tử cùng cấu trúc ``doc`` như
        ``compare_documents``.

    Returns
    -------
    dict
        ``{'pair_results': list, 'aggregate': list}``
    """
    try:
        pair_results: list[dict[str, Any]] = []

        # So sánh từng cặp
        for i in range(len(docs)):
            for j in range(i + 1, len(docs)):
                result = compare_documents(docs[i], docs[j])
                pair_results.append(result)

        # Tổng hợp: mỗi trường xuất hiện trên tất cả tài liệu
        field_values: dict[str, dict[str, str]] = {}  # label → {doc_id: value}

        for doc in docs:
            doc_id: str = doc.get("id", doc.get("file_name", ""))
            fields = doc.get("fields", {})
            doc_type = doc.get("doc_type", "")
            for field_key, field_data in fields.items():
                label = field_data.get("label", get_field_label(doc_type, field_key))
                if label not in field_values:
                    field_values[label] = {}
                field_values[label][doc_id] = field_data.get("value", "")

        # Kiểm tra xem tất cả giá trị có khớp không
        aggregate: list[dict[str, Any]] = []
        for label, values_map in field_values.items():
            unique_values = set(
                _normalize_str(v) for v in values_map.values() if v
            )
            all_match = len(unique_values) <= 1
            aggregate.append({
                "label": label,
                "values": values_map,
                "all_match": all_match,
            })

        return {
            "pair_results": pair_results,
            "aggregate": aggregate,
        }

    except Exception as exc:
        return {
            "pair_results": [],
            "aggregate": [],
            "error": f"Lỗi khi so sánh nhiều tài liệu: {exc}",
        }


# ═══════════════════════════════════════════════════════════════════════════
# Xuất kết quả
# ═══════════════════════════════════════════════════════════════════════════

_STATUS_VI: dict[str, str] = {
    "match": "Khớp",
    "mismatch": "Sai lệch",
    "missing": "Thiếu",
}


def results_to_dataframe(comparison_result: dict[str, Any]) -> pd.DataFrame:
    """Chuyển kết quả so sánh thành DataFrame để hiển thị / xuất file.

    Parameters
    ----------
    comparison_result : dict
        Output của ``compare_documents()``.

    Returns
    -------
    pd.DataFrame
        Cột: ``['Trường', doc1_name, doc2_name, 'Trạng thái', 'Tương đồng (%)']``.
    """
    try:
        doc1_name = comparison_result.get("doc1_name", "Tài liệu 1")
        doc2_name = comparison_result.get("doc2_name", "Tài liệu 2")
        results = comparison_result.get("results", [])

        rows: list[dict[str, Any]] = []
        for r in results:
            rows.append({
                "Trường": r["label"],
                doc1_name: r["doc1_value"],
                doc2_name: r["doc2_value"],
                "Trạng thái": _STATUS_VI.get(r["status"], r["status"]),
                "Tương đồng (%)": r["similarity"],
            })

        return pd.DataFrame(rows)

    except Exception:
        return pd.DataFrame()


def export_to_excel(comparison_result: dict[str, Any]) -> bytes:
    """Tạo file Excel trong bộ nhớ với định dạng màu sắc.

    Parameters
    ----------
    comparison_result : dict
        Output của ``compare_documents()``.

    Returns
    -------
    bytes
        Nội dung file Excel sẵn sàng cho ``st.download_button()``.
    """
    try:
        buf = io.BytesIO()
        doc1_name = comparison_result.get("doc1_name", "Tài liệu 1")
        doc2_name = comparison_result.get("doc2_name", "Tài liệu 2")
        summary = comparison_result.get("summary", {})
        results = comparison_result.get("results", [])

        with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
            wb = writer.book

            # ── Sheet 1: Tổng kết ──────────────────────────────────────
            ws_summary = wb.add_worksheet("Tổng kết")
            writer.sheets["Tổng kết"] = ws_summary

            title_fmt = wb.add_format({
                "bold": True, "font_size": 14, "font_color": "#1a237e",
            })
            header_fmt = wb.add_format({
                "bold": True, "bg_color": "#e3f2fd", "border": 1,
            })
            cell_fmt = wb.add_format({"border": 1})

            ws_summary.write(0, 0, "BÁO CÁO SO SÁNH CHỨNG TỪ", title_fmt)
            ws_summary.write(2, 0, "Tài liệu 1:", header_fmt)
            ws_summary.write(2, 1, doc1_name, cell_fmt)
            ws_summary.write(3, 0, "Tài liệu 2:", header_fmt)
            ws_summary.write(3, 1, doc2_name, cell_fmt)

            ws_summary.write(5, 0, "Chỉ tiêu", header_fmt)
            ws_summary.write(5, 1, "Giá trị", header_fmt)

            summary_data = [
                ("Tổng số trường so sánh", summary.get("total", 0)),
                ("Số trường khớp", summary.get("matches", 0)),
                ("Số trường sai lệch", summary.get("mismatches", 0)),
                ("Số trường thiếu", summary.get("missing", 0)),
                ("Tỷ lệ khớp (%)", summary.get("match_rate", 0.0)),
            ]
            for idx, (label, value) in enumerate(summary_data, start=6):
                ws_summary.write(idx, 0, label, cell_fmt)
                ws_summary.write(idx, 1, value, cell_fmt)

            ws_summary.set_column(0, 0, 30)
            ws_summary.set_column(1, 1, 20)

            # ── Sheet 2: Chi tiết ──────────────────────────────────────
            df = results_to_dataframe(comparison_result)
            if not df.empty:
                df.to_excel(writer, sheet_name="Chi tiết", index=False, startrow=1)
                ws_detail = writer.sheets["Chi tiết"]

                # Header
                for col_idx, col_name in enumerate(df.columns):
                    ws_detail.write(1, col_idx, col_name, header_fmt)

                # Conditional formatting theo trạng thái
                green_fmt = wb.add_format({
                    "bg_color": "#c8e6c9", "border": 1,
                })
                red_fmt = wb.add_format({
                    "bg_color": "#ffcdd2", "border": 1,
                })
                yellow_fmt = wb.add_format({
                    "bg_color": "#fff9c4", "border": 1,
                })

                status_col = list(df.columns).index("Trạng thái")
                for row_idx in range(len(df)):
                    status = df.iloc[row_idx]["Trạng thái"]
                    if status == "Khớp":
                        fmt = green_fmt
                    elif status == "Sai lệch":
                        fmt = red_fmt
                    else:
                        fmt = yellow_fmt

                    for col_idx in range(len(df.columns)):
                        cell_value = df.iloc[row_idx, col_idx]
                        ws_detail.write(row_idx + 2, col_idx, cell_value, fmt)

                # Độ rộng cột
                ws_detail.set_column(0, 0, 25)  # Trường
                ws_detail.set_column(1, 2, 35)  # Giá trị tài liệu
                ws_detail.set_column(3, 3, 15)  # Trạng thái
                ws_detail.set_column(4, 4, 15)  # Tương đồng

                # Tiêu đề
                ws_detail.write(
                    0, 0,
                    "CHI TIẾT SO SÁNH CHỨNG TỪ",
                    title_fmt,
                )

        buf.seek(0)
        return buf.getvalue()

    except Exception as exc:
        # Trả về file Excel rỗng với thông báo lỗi
        fallback = io.BytesIO()
        with pd.ExcelWriter(fallback, engine="xlsxwriter") as writer:
            pd.DataFrame(
                {"Lỗi": [f"Không thể tạo báo cáo: {exc}"]}
            ).to_excel(writer, index=False)
        fallback.seek(0)
        return fallback.getvalue()

def compare_ecus_centric(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Tạo bảng so sánh lấy Tờ khai Hải quan (ECUS) làm chuẩn.
    
    Parameters
    ----------
    docs : list[dict]
        Danh sách tài liệu đã được parse.
        
    Returns
    -------
    list[dict]
        Danh sách các dòng cho bảng hiển thị ECUS.
    """
    from utils.parser import DOCUMENT_TYPES, FIELD_MAPPING

    # Xác định các trường ECUS (dùng chung cho cả Export/Import vì chúng tương tự nhau)
    ecus_fields = {}
    for key, data in DOCUMENT_TYPES.get("customs_declaration_export", {}).get("fields", {}).items():
        ecus_fields[key] = data["label"]

    # Ánh xạ ngược từ Tờ khai ra các document khác
    # field_key (ecus) -> [(doc_type, doc_field_key), ...]
    mapping_lookup: dict[str, list[tuple[str, str]]] = {k: [] for k in ecus_fields.keys()}
    
    for mapping_group in FIELD_MAPPING:
        # Tìm xem group này có chứa trường của customs_declaration không
        ecus_keys_in_group = [f.split(".")[1] for f in mapping_group if f.startswith("customs_declaration")]
        if not ecus_keys_in_group:
            continue
        
        # Có thể có nhiều customs_declaration trong cùng 1 group (VD: export và import)
        # Ta lấy key đầu tiên làm chuẩn vì tên key giống nhau
        primary_ecus_key = ecus_keys_in_group[0]
        if primary_ecus_key in mapping_lookup:
            for f in mapping_group:
                parts = f.split(".")
                if len(parts) == 2:
                    mapping_lookup[primary_ecus_key].append((parts[0], parts[1]))

    results = []
    
    for ecus_key, label in ecus_fields.items():
        row = {"Tiêu chí ECUS": label}
        
        has_value = False
        values_to_compare = []

        for doc in docs:
            doc_id = doc["id"]
            doc_type = doc["doc_type"]
            val = ""
            
            # Nếu doc này là ECUS
            if doc_type.startswith("customs_declaration"):
                if ecus_key in doc.get("fields", {}):
                    val = doc["fields"][ecus_key].get("value", "")
            else:
                # Nếu là doc khác, tìm qua mapping
                for mapped_type, mapped_key in mapping_lookup.get(ecus_key, []):
                    if doc_type == mapped_type:
                        val = doc.get("fields", {}).get(mapped_key, {}).get("value", "")
                        break
            
            val_str = str(val) if val else ""
            if val_str:
                has_value = True
                values_to_compare.append(_normalize_str(val_str))
            
            row[doc_id] = val_str if val_str else "—"
            
        if has_value:
            unique_vals = set(values_to_compare)
            if len(unique_vals) <= 1:
                row["Trạng thái"] = "✅ Khớp"
            else:
                row["Trạng thái"] = "❌ Sai lệch"
                
            results.append(row)
            
    return results

