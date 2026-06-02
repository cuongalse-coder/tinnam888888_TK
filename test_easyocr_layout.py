import sys
import easyocr
import numpy as np

def test_layout():
    # Giả lập kết quả của easyocr detail=1
    # bbox format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
    result = [
        ([[10, 10], [50, 10], [50, 20], [10, 20]], "Shipper:", 0.9),
        ([[200, 12], [250, 12], [250, 22], [200, 22]], "Invoice No:", 0.9),
        ([[60, 9], [150, 9], [150, 19], [60, 19]], "ABC Company", 0.9),
        ([[260, 11], [300, 11], [300, 21], [260, 21]], "INV-123", 0.9),
        ([[10, 30], [50, 30], [50, 40], [10, 40]], "Consignee:", 0.9),
        ([[60, 31], [150, 31], [150, 41], [60, 41]], "XYZ Corp", 0.9),
    ]

    # Sort by Y first
    result.sort(key=lambda item: item[0][0][1])

    lines = []
    current_line = []
    current_y = None
    y_threshold = 10 # 10 pixels

    for bbox, text, prob in result:
        y = bbox[0][1]
        x = bbox[0][0]
        if current_y is None:
            current_y = y
            current_line.append((x, text))
        elif abs(y - current_y) < y_threshold:
            current_line.append((x, text))
            # Cập nhật current_y trung bình
            current_y = (current_y * (len(current_line)-1) + y) / len(current_line)
        else:
            current_line.sort(key=lambda item: item[0])
            lines.append("\t".join([item[1] for item in current_line]))
            current_line = [(x, text)]
            current_y = y

    if current_line:
        current_line.sort(key=lambda item: item[0])
        lines.append("\t".join([item[1] for item in current_line]))

    output = "\n".join(lines)
    print("OUTPUT:")
    print(output)

if __name__ == '__main__':
    test_layout()
