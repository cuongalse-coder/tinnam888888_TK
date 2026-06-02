import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    import easyocr
    # Just initialize the reader to trigger model download to E:
    print("Khởi tạo EasyOCR và tải model về E:/EasyOCR_Models...")
    reader = easyocr.Reader(['vi', 'en'], model_storage_directory='E:/EasyOCR_Models', download_enabled=True)
    print("Khởi tạo thành công! Models đã được lưu vào ổ E:.")
except Exception as e:
    import traceback
    traceback.print_exc()
