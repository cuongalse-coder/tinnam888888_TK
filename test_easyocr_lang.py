import sys
import io
import easyocr
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    print("Khởi tạo EasyOCR với ['ch_sim', 'en', 'vi']...")
    reader = easyocr.Reader(['ch_sim', 'en', 'vi'], model_storage_directory='E:/EasyOCR_Models', download_enabled=True)
    print("Thành công!")
except Exception as e:
    import traceback
    traceback.print_exc()
