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
    
    prompt = f"""Bạn là một Trưởng phòng Xuất Nhập Khẩu/Hải quan dày dặn kinh nghiệm.
Hệ thống phần mềm soi chéo chứng từ vừa phát hiện các lỗi sai lệch dữ liệu sau đây:

{issues_text}

Nhiệm vụ của bạn:
1. Đánh giá nhanh mức độ nghiêm trọng của những lỗi này.
2. Chỉ ra rủi ro nghiệp vụ hải quan, logistics hoặc thanh toán nếu để nguyên (VD: bị phạt tiền, rớt luồng đỏ, hải quan bác bỏ C/O, ngân hàng từ chối L/C...).
3. Đề xuất hành động khắc phục cụ thể, rõ ràng cho nhân viên chứng từ (VD: Yêu cầu sửa chứng từ nào, theo chứng từ gốc nào...).

Trả lời bằng tiếng Việt, chuyên nghiệp, ngắn gọn, súc tích (dùng bullet points), format markdown có sử dụng emoji phù hợp để làm nổi bật cảnh báo.
"""
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"❌ Lỗi khi kết nối với AI: {str(e)}"
