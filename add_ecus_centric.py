import re

with open("utils/comparator.py", "r", encoding="utf-8") as f:
    content = f.read()

new_func = """
def compare_ecus_centric(docs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    \"\"\"Tạo bảng so sánh lấy Tờ khai Hải quan (ECUS) làm chuẩn.
    
    Parameters
    ----------
    docs : list[dict]
        Danh sách tài liệu đã được parse.
        
    Returns
    -------
    list[dict]
        Danh sách các dòng cho bảng hiển thị ECUS.
    \"\"\"
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

"""

if "compare_ecus_centric" not in content:
    content += new_func
    with open("utils/comparator.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Added compare_ecus_centric to utils/comparator.py")
else:
    print("compare_ecus_centric already exists.")
