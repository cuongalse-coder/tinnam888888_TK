import sys
import io
import os

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from paddleocr import PaddleOCR
    # Chỉ định model storage tới ổ E: để tải model về
    model_dir = 'E:/PaddleOCR_Models'
    os.makedirs(model_dir, exist_ok=True)
    
    print(f"Khởi tạo PaddleOCR và lưu model tại {model_dir}...")
    ocr = PaddleOCR(use_angle_cls=True, lang="vi", det_model_dir=f"{model_dir}/det", rec_model_dir=f"{model_dir}/rec", cls_model_dir=f"{model_dir}/cls")
    print("Khởi tạo PaddleOCR thành công!")
except Exception as e:
    import traceback
    traceback.print_exc()
