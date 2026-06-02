import sys
import os
import json

# Add project root to path
sys.path.append(r"C:\Users\GHC\.gemini\antigravity\scratch\doc-compare-streamlit")

from utils.extractors import extract_pdf
from utils.parser import parse_fields, DOCUMENT_TYPES

files_to_test = [
    r"E:\tuyet\NAM 2023\THANG 01\03.01\DOOSUN - HD 887\TKX 305254446030.pdf",
    r"E:\tuyet\NAM 2023\THANG 01\03.01\dynapac 8194\TKX HD 8194.pdf",
    r"E:\tuyet\AIR\17.03\7IFI692\7IFI692 -dn.pdf"
]

for file_path in files_to_test:
    print(f"\n--- Testing: {os.path.basename(file_path)} ---")
    try:
        with open(file_path, "rb") as f:
            pdf_data = extract_pdf(f)
            
        if "error" in pdf_data:
            print("Extract error:", pdf_data["error"])
            continue
            
        # Parse fields
        parsed = parse_fields(pdf_data["raw_text"])
        
        # Check what was found
        doc_type = parsed.get("doc_type", "unknown")
        print(f"Detected Doc Type: {doc_type}")
        
        fields = parsed.get("fields", {})
        print("Extracted fields:")
        for k, v in fields.items():
            print(f"  {k}: {v.get('value')} (conf: {v.get('confidence')})")
            
        # Optional: Print first 500 chars of raw_text to understand structure
        print("\nRaw text sample:")
        print(pdf_data["raw_text"][:500])
        
    except Exception as e:
        print(f"Failed to process {file_path}: {e}")
