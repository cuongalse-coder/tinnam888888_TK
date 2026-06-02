import re

with open("utils/parser.py", "r", encoding="utf-8") as f:
    content = f.read()

# I will replace the contents of 'fields' dict for both export and import.
with open("gen_dict_out.txt", "r", encoding="utf-8") as f:
    fields_content = f.read()
    
# Remove outer braces from fields_content for cleaner injection
fields_inner = fields_content.strip()[1:-1].strip()

# Replace export fields
export_pattern = re.compile(r'("customs_declaration_export":\s*\{.*?"fields":\s*\{)(.*?)(\n\s*\},)', re.DOTALL)
content = export_pattern.sub(r'\1\n' + fields_inner + r'\3', content)

# Replace import fields
import_pattern = re.compile(r'("customs_declaration_import":\s*\{.*?"fields":\s*\{)(.*?)(\n\s*\},)', re.DOTALL)
content = import_pattern.sub(r'\1\n' + fields_inner + r'\3', content)

with open("utils/parser.py", "w", encoding="utf-8") as f:
    f.write(content)
