import re

# 1. Update utils/parser.py
with open("utils/parser.py", "r", encoding="utf-8") as f:
    parser_content = f.read()

# Add itemTax to fields in DOCUMENT_TYPES
new_item_fields = '''            "quantity": {"label": "Lượng (Quantity)", "keywords": ["lượng"], "type": "number"},
            "uom": {"label": "ĐVT", "keywords": ["đvt"], "type": "string"},
            "unitPrice": {"label": "Đơn giá", "keywords": ["đơn giá"], "type": "number"},
            "itemValue": {"label": "Trị giá", "keywords": ["trị giá mặt hàng"], "type": "number"},
            "itemTax": {"label": "Thuế mặt hàng", "keywords": ["thuế mặt hàng", "thuế nhập khẩu", "thuế xuất khẩu"], "type": "number"},'''

parser_content = re.sub(
    r'"quantity": \{.*?type": "number"\},.*?uom": \{.*?type": "string"\},.*?unitPrice": \{.*?type": "number"\},.*?itemValue": \{.*?type": "number"\},',
    new_item_fields,
    parser_content,
    flags=re.DOTALL
)

# Update item_fields list in ai_parse_fields
parser_content = parser_content.replace(
    'item_fields = ["hsCode", "description", "origin", "quantity", "uom", "unitPrice", "itemValue"]',
    'item_fields = ["hsCode", "description", "origin", "quantity", "uom", "unitPrice", "itemValue", "itemTax"]'
)

# Update prompt to emphasize ALL items and include itemTax
old_prompt_rule = '6. Tờ khai Hải quan thường có danh sách nhiều mặt hàng. ĐỐI VỚI CÁC TRƯỜNG THUỘC VỀ DANH SÁCH MẶT HÀNG (hsCode, description, origin, quantity, uom, unitPrice, itemValue): Hãy trả về dưới dạng mảng (array) các object (ví dụ: "items": [ {{"hsCode": "...", "description": "..."}}, {{"hsCode": "...", ...}} ]). Các trường chung khác vẫn nằm ở root JSON.'
new_prompt_rule = '6. Tờ khai Hải quan thường có danh sách nhiều mặt hàng (dài qua nhiều trang). BẮT BUỘC PHẢI LẤY TẤT CẢ CÁC MẶT HÀNG KHÔNG ĐƯỢC BỎ SÓT. ĐỐI VỚI CÁC TRƯỜNG THUỘC VỀ DANH SÁCH MẶT HÀNG (hsCode, description, origin, quantity, uom, unitPrice, itemValue, itemTax): Hãy trả về dưới dạng mảng (array) các object (ví dụ: "items": [ {{"hsCode": "...", "description": "..."}}, {{"hsCode": "...", ...}} ]). Các trường chung khác vẫn nằm ở root JSON.'

parser_content = parser_content.replace(old_prompt_rule, new_prompt_rule)

with open("utils/parser.py", "w", encoding="utf-8") as f:
    f.write(parser_content)


# 2. Update app.py
with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

old_list = '"Mã số hàng hóa (HS)", "Mô tả hàng hóa", "Xuất xứ", "Lượng (Quantity)", "ĐVT", "Đơn giá", "Trị giá"'
new_list = '"Mã số hàng hóa (HS)", "Mô tả hàng hóa", "Xuất xứ", "Lượng (Quantity)", "ĐVT", "Đơn giá", "Trị giá", "Thuế mặt hàng"'
app_content = app_content.replace(old_list, new_list)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)
