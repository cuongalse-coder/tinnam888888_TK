import re

# 1. Update comparator.py
with open("utils/comparator.py", "r", encoding="utf-8") as f:
    comp_content = f.read()

comp_replacement = """def compare_ecus_centric(docs: list[dict[str, Any]]) -> dict:
    \"\"\"Tạo bảng so sánh lấy Tờ khai Hải quan (ECUS) làm chuẩn.
    Tự động phát hiện Import/Export.
    \"\"\"
    from utils.parser import DOCUMENT_TYPES, FIELD_MAPPING

    # Xác định loại tờ khai (ưu tiên Import nếu có, không thì Export mặc định)
    ecus_doc_type = "customs_declaration_export"
    for d in docs:
        if d.get("doc_type") == "customs_declaration_import":
            ecus_doc_type = "customs_declaration_import"
            break

    ecus_fields = {}
    for key, data in DOCUMENT_TYPES.get(ecus_doc_type, {}).get("fields", {}).items():
        ecus_fields[key] = data["label"]

    mapping_lookup: dict[str, list[tuple[str, str]]] = {k: [] for k in ecus_fields.keys()}
    
    for mapping_group in FIELD_MAPPING:
        ecus_keys_in_group = [f.split(".")[1] for f in mapping_group if f.startswith(ecus_doc_type)]
        if not ecus_keys_in_group:
            ecus_keys_in_group = [f.split(".")[1] for f in mapping_group if f.startswith("customs_declaration")]
            
        if not ecus_keys_in_group:
            continue
        
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
            
            if doc_type.startswith("customs_declaration"):
                if ecus_key in doc.get("fields", {}):
                    val = doc["fields"][ecus_key].get("value", "")
            else:
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
        else:
            row["Trạng thái"] = "➖ Trống"
            
        results.append(row)
            
    return {
        "type": ecus_doc_type,
        "results": results
    }
"""

pattern = re.compile(r"def compare_ecus_centric\(docs: list\[dict\[str, Any\]\]\) -> list\[dict\[str, Any\]\]:.*?return results\n", re.DOTALL)
comp_content = pattern.sub(comp_replacement, comp_content)

with open("utils/comparator.py", "w", encoding="utf-8") as f:
    f.write(comp_content)


# 2. Update app.py
with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

app_replacement = """def _render_multi_comparison(multi_result, docs):
    \"\"\"Render comparison result based on ECUS standard fields, split into tabs.\"\"\"
    from utils.comparator import compare_ecus_centric
    
    st.divider()
    
    if not docs:
        st.info("Chưa có chứng từ nào để so sánh.")
        return

    ecus_output = compare_ecus_centric(docs)
    
    if not ecus_output or not ecus_output.get("results"):
        st.warning("Không thể tạo bảng đối chiếu ECUS. Vui lòng kiểm tra lại chứng từ tải lên.")
        return
        
    ecus_results = ecus_output["results"]
    ecus_type = ecus_output["type"]
    
    title_suffix = "(Nhập Khẩu)" if ecus_type == "customs_declaration_import" else "(Xuất Khẩu)"
    st.subheader(f"📊 Bảng Đối Chiếu Chuẩn ECUS VNACCS {title_suffix}")
    st.markdown(f"Bảng tổng hợp đối chiếu tất cả các chứng từ dựa trên bộ tiêu chí chuẩn của Tờ khai Hải quan {title_suffix}.")

    def highlight_match(row):
        val = row.get('Trạng thái', '')
        if isinstance(val, pd.Series):
            val = val.iloc[0] if not val.empty else ''
        val = str(val)
        if '✅' in val:
            return ['background-color: rgba(16,185,129,0.08)'] * len(row)
        elif '❌' in val:
            return ['background-color: rgba(239,68,68,0.08)'] * len(row)
        else:
            return [''] * len(row)

    display_data = []
    
    from utils.parser import DOCUMENT_TYPES
    col_map = {}
    for doc in docs:
        doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})
        icon = doc_type_info.get('icon', '📄')
        col_map[doc['id']] = f"{icon} {doc['file_name'][:30]}"
        
    for row in ecus_results:
        display_row = {"Tiêu chí ECUS": row["Tiêu chí ECUS"]}
        for doc in docs:
            display_row[col_map[doc['id']]] = row.get(doc['id'], "—")
        display_row["Trạng thái"] = row.get("Trạng thái", "")
        display_data.append(display_row)

    df = pd.DataFrame(display_data)
"""

pattern2 = re.compile(r"def _render_multi_comparison\(multi_result, docs\):.*?df = pd\.DataFrame\(display_data\)\n", re.DOTALL)
app_content = pattern2.sub(app_replacement, app_content)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)
print("Updated comparator.py and app.py to support dynamic Import/Export types")
