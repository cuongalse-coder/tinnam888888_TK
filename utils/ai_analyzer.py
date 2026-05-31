import json
from google import genai

def analyze_discrepancies(result: dict, is_multiple: bool, api_key: str, docs: list = None) -> str:
    """Gọi AI phân tích các lỗi sai lệch từ kết quả so sánh chứng từ."""
    if not api_key:
        return "⚠️ Vui lòng nhập Google Gemini API Key ở thanh công cụ bên trái (Sidebar) để sử dụng tính năng này."

    issues = []
    if not is_multiple:
        doc1 = result.get('doc1_name', 'Tài liệu 1')
        doc2 = result.get('doc2_name', 'Tài liệu 2')
        for r in result.get('results', []):
            if r.get('status') in ['mismatch', 'missing']:
                issues.append(f"- {r.get('label')}: {doc1}='{r.get('doc1_value')}' vs {doc2}='{r.get('doc2_value')}'")
    else:
        for r in result.get('aggregate', []):
            if not r.get('all_match'):
                vals = [f"{doc['file_name']}='{r.get('values', {}).get(doc['id'], '')}'" for doc in docs]
                issues.append(f"- {r.get('label')}: " + " vs ".join(vals))

    if not issues:
        return "✅ Tuyệt vời! Các chứng từ khớp nhau hoàn toàn, không có sai lệch nào cần phân tích."

    issues_text = "\n".join(issues)
    
    prompt = f"""Bạn là một Trưởng phòng Xuất Nhập Khẩu/Hải quan (Import-Export Manager) dày dặn kinh nghiệm, vô cùng tỉ mỉ và khắt khe.
Hệ thống phần mềm soi chéo chứng từ vừa phát hiện các lỗi sai lệch dữ liệu sau đây:

{issues_text}

Nhiệm vụ của bạn:
1. Đánh giá nhanh mức độ nghiêm trọng của những lỗi này (Cao/Trung bình/Thấp).
2. Phân tích chi tiết rủi ro nghiệp vụ hải quan, logistics hoặc thanh toán nếu để nguyên các sai lệch này (VD: bị phạt tiền, rớt luồng đỏ, hải quan bác bỏ C/O, ngân hàng từ chối thanh toán L/C...).
3. Đề xuất hành động khắc phục cụ thể, dứt khoát cho nhân viên chứng từ (CUS). (VD: Yêu cầu hãng tàu tu chỉnh B/L, hay yêu cầu Shipper sửa Invoice, theo chứng từ gốc nào).

Vui lòng trình bày kết quả NGẮN GỌN, CHUYÊN NGHIỆP theo cấu trúc sau:
### 🔴 Mức độ Rủi ro Tổng quan: [Cao/Trung bình/Thấp]

### 🔍 Chi tiết Phân tích Rủi ro
- **[Tên trường bị sai lệch]**: [Phân tích hậu quả nếu không sửa]
(Liệt kê cho từng lỗi)

### 💡 Hành động Khắc phục (Dành cho CUS)
- [Cần liên hệ ai, sửa giấy tờ gì, dựa trên giấy tờ gốc nào]
"""
    try:
        import streamlit as st
        import time
        
        client = genai.Client(api_key=api_key)
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                return response.text
            except Exception as e:
                error_str = str(e)
                if "429" in error_str and attempt < max_retries - 1:
                    delay = 15
                    st.warning(f"⏳ Trợ lý AI đang bận hoặc quá tải (Lỗi 429 từ Google). Tự động thử lại sau {delay} giây (Lần {attempt + 1}/{max_retries - 1})... Vui lòng chờ!")
                    time.sleep(delay)
                    continue
                return f"❌ Lỗi khi kết nối với AI: {error_str}"
    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"
