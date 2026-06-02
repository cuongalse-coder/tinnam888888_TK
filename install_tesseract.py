import urllib.request
import ssl
import os
import subprocess

ssl._create_default_https_context = ssl._create_unverified_context

url = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
out_path = "E:\\tesseract_setup.exe"

print("Downloading Tesseract installer...")
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)', 'Referer': 'https://digi.bib.uni-mannheim.de/tesseract/', 'Accept': 'application/octet-stream'})
with urllib.request.urlopen(req) as response, open(out_path, 'wb') as out_file:
    out_file.write(response.read())
print("Download complete. Installing silently to E:\\Tesseract-OCR...")

subprocess.run([out_path, "/S", "/D=E:\\Tesseract-OCR"], check=True)
print("Installation complete.")

vie_url = "https://github.com/tesseract-ocr/tessdata/raw/main/vie.traineddata"
vie_path = "E:\\Tesseract-OCR\\tessdata\\vie.traineddata"
print("Downloading Vietnamese language model...")
req_vie = urllib.request.Request(vie_url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req_vie) as response, open(vie_path, 'wb') as out_file:
    out_file.write(response.read())
print("Language model downloaded.")

os.remove(out_path)
print("Cleanup complete.")
