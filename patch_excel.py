import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

old_logic = '''                raw_text = result.get('raw_text', '')
                detection = detect_document_type(raw_text)
                
                if detection['type'] == 'unknown':'''

new_logic = '''                raw_text = result.get('raw_text', '')
                
                # Force Excel files to be Customs Declarations based on user workflow
                is_excel = file.name.lower().endswith(('.xls', '.xlsx', '.csv', '.xlsm'))
                if is_excel:
                    if 'nhập' in raw_text.lower():
                        detection = {"type": "customs_declaration_import", "name": "Tờ khai Hàng hóa Nhập khẩu"}
                    else:
                        detection = {"type": "customs_declaration_export", "name": "Tờ khai Hàng hóa Xuất khẩu"}
                else:
                    detection = detect_document_type(raw_text)
                
                if detection['type'] == 'unknown':'''

content = content.replace(old_logic, new_logic)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
