import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace(
    'detection = {"type": "customs_declaration_import", "name": "Tờ khai Hàng hóa Nhập khẩu"}',
    'detection = {"type": "customs_declaration_import", "name": "Tờ khai Hàng hóa Nhập khẩu", "confidence": 1.0, "icon": "📝", "scores": {}}'
)

content = content.replace(
    'detection = {"type": "customs_declaration_export", "name": "Tờ khai Hàng hóa Xuất khẩu"}',
    'detection = {"type": "customs_declaration_export", "name": "Tờ khai Hàng hóa Xuất khẩu", "confidence": 1.0, "icon": "📝", "scores": {}}'
)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
