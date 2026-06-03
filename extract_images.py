import zipfile
import os
import shutil

excel_file = r"D:\CONG TY HYC\cac dang tk.xlsx"
extract_dir = r"C:\Users\GHC\.gemini\antigravity\scratch\excel_images"

os.makedirs(extract_dir, exist_ok=True)

try:
    with zipfile.ZipFile(excel_file, 'r') as zip_ref:
        for item in zip_ref.namelist():
            if item.startswith('xl/media/'):
                zip_ref.extract(item, extract_dir)
    print("Extract images success!")
except Exception as e:
    print("Error:", e)
