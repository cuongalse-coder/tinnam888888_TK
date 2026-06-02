import re

with open("utils/parser.py", "r", encoding="utf-8") as f:
    content = f.read()

new_ai_parse = '''def ai_parse_fields(
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
        resp_text = re.sub(r'^```(?:json)?\s*\\n?', '', resp_text)
        resp_text = re.sub(r'\\n?```\s*$', '', resp_text)
            
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
'''

start_idx = content.find("def ai_parse_fields(")
end_idx = content.find("def ", start_idx + 10)
if end_idx == -1:
    end_idx = len(content)

content = content[:start_idx] + new_ai_parse + "\n\n" + content[end_idx:]

with open("utils/parser.py", "w", encoding="utf-8") as f:
    f.write(content)
