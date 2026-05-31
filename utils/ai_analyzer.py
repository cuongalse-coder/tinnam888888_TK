import json
import time
import requests
import streamlit as st
from google import genai

# A simple rule-based dictionary for offline use
RULE_BASED_DICTIONARY = {
    "Tàu": ("Trung bình", "Khó theo dõi lịch trình, có thể trễ hạn giao hàng.", "Liên hệ Hãng tàu/Forwarder xin tu chỉnh B/L hoặc thông báo thay đổi tàu."),
    "Chuyến": ("Trung bình", "Trễ chuyến, rớt tàu, tốn phí lưu kho.", "Xác nhận lại Booking với Hãng tàu."),
    "Cảng xếp": ("Cao", "Lên nhầm tàu, sai tuyến đường, tốn chi phí vận chuyển lại.", "Kiểm tra lại hợp đồng và Booking, yêu cầu tu chỉnh ngay lập tức."),
    "Cảng dỡ": ("Cao", "Hàng đến sai đích, lưu kho bãi, không thông quan được.", "Tu chỉnh B/L khẩn cấp với Hãng tàu."),
    "B/L No": ("Cao", "Hải quan từ chối tờ khai, không lấy được lệnh giao hàng (D/O).", "Kiểm tra số B/L gốc, sửa lại Tờ khai hải quan hoặc Invoice/Packing List nếu sai."),
    "Số Vận đơn": ("Cao", "Hải quan từ chối tờ khai, không lấy được lệnh giao hàng (D/O).", "Kiểm tra số B/L gốc, sửa lại Tờ khai hải quan hoặc Invoice/Packing List nếu sai."),
    "Số container": ("Cao", "Rớt luồng đỏ, hải quan phạt tiền do sai khai báo manifest.", "Kiểm tra Phiếu cân (VGM) / EIR, xin tu chỉnh Manifest và sửa Tờ khai ngay."),
    "Số seal": ("Trung bình", "Hải quan nghi ngờ hàng bị mở, rớt luồng đỏ kiểm hóa.", "Xin xác nhận từ kho/cảng, tu chỉnh Manifest và Tờ khai."),
    "Người xuất khẩu": ("Cao", "Ngân hàng từ chối L/C, sai chủ thể hợp đồng.", "Yêu cầu Shipper sửa Invoice/Packing List hoặc tu chỉnh B/L."),
    "Người nhập khẩu": ("Cao", "Hải quan không cho thông quan, không lấy được D/O.", "Yêu cầu Shipper hoặc Hãng tàu sửa lại thông tin Consignee."),
    "Trọng lượng": ("Cao", "Hải quan phạt do khai sai trọng lượng, rớt luồng đỏ.", "Kiểm tra lại VGM, yêu cầu sửa Tờ khai và Manifest."),
    "Số lượng": ("Cao", "Thiếu/thừa hàng, hải quan bắt lỗi trốn thuế hoặc sai số liệu.", "Kiểm đếm lại hàng, sửa Invoice/Packing list và Tờ khai."),
    "Trị giá": ("Cao", "Ngân hàng từ chối thanh toán, Hải quan truy thu thuế hoặc phạt.", "Sửa đổi Tờ khai và Invoice gốc ngay lập tức."),
    "Điều kiện giao": ("Trung bình", "Tranh chấp chi phí vận tải, sai lệch tính thuế hải quan.", "Xác nhận lại với đối tác theo Hợp đồng."),
    "Số Invoice": ("Trung bình", "Khó thanh toán, sai lệch hồ sơ kế toán.", "Yêu cầu Shipper cấp lại Invoice đúng số."),
}

def analyze_discrepancies(result: dict, is_multiple: bool, config: dict, docs: list = None) -> str:
    """Gọi AI phân tích các lỗi sai lệch từ kết quả so sánh chứng từ."""
    
    issues = []
    if not is_multiple:
        doc1 = result.get('doc1_name', 'Tài liệu 1')
        doc2 = result.get('doc2_name', 'Tài liệu 2')
        for r in result.get('results', []):
            if r.get('status') in ['mismatch', 'missing']:
                issues.append({
                    "label": r.get('label'),
                    "detail": f"{doc1}='{r.get('doc1_value')}' vs {doc2}='{r.get('doc2_value')}'"
                })
    else:
        for r in result.get('aggregate', []):
            if not r.get('all_match'):
                vals = [f"{doc['file_name']}='{r.get('values', {}).get(doc['id'], '')}'" for doc in docs]
                issues.append({
                    "label": r.get('label'),
                    "detail": " vs ".join(vals)
                })

    if not issues:
        return "✅ Tuyệt vời! Các chứng từ khớp nhau hoàn toàn, không có sai lệch nào cần phân tích."

    ai_mode = config.get('ai_mode', '')
    
    # 1. THUẬT TOÁN CỨNG (RULE-BASED OFFLINE)
    if "Thuật toán Cứng" in ai_mode:
        return _analyze_rule_based(issues)
        
    # Chuẩn bị Prompt cho LLM
    issues_text = "\n".join([f"- {i['label']}: {i['detail']}" for i in issues])
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

    # 2. LOCAL LLM (OLLAMA)
    if "Local" in ai_mode:
        return _analyze_ollama(prompt, config.get('ollama_host', 'http://localhost:11434'), config.get('ollama_model', 'llama3'))
        
    # 3. ONLINE AI (GEMINI)
    api_key = config.get('api_key', '')
    if not api_key:
         return "⚠️ Vui lòng nhập Google Gemini API Key ở thanh công cụ bên trái (Sidebar) để sử dụng chế độ Online."
    return _analyze_gemini(prompt, api_key)


def _analyze_rule_based(issues: list) -> str:
    """Thuật toán xử lý tức thì, không cần Internet"""
    output = ["### ⚡ (Thuật toán Offline) Đánh giá Rủi ro & Khắc phục\n"]
    
    high_risk_count = 0
    for issue in issues:
        label = issue['label']
        detail = issue['detail']
        
        # Tìm rule phù hợp
        matched_rule = ("Thấp", "Gây khó khăn trong việc đối chiếu hồ sơ nội bộ.", "Kiểm tra lại chứng từ và xác nhận nội bộ.")
        for key, rule in RULE_BASED_DICTIONARY.items():
            if key.lower() in label.lower():
                matched_rule = rule
                break
                
        severity, risk, solution = matched_rule
        if severity == "Cao":
            high_risk_count += 1
            
        icon = "🔴" if severity == "Cao" else "🟡" if severity == "Trung bình" else "🔵"
        output.append(f"#### {icon} {label} (Mức độ: {severity})")
        output.append(f"- **Sai lệch:** {detail}")
        output.append(f"- **Rủi ro:** {risk}")
        output.append(f"- **Khắc phục:** {solution}\n")
        
    overall = "Cao 🔴" if high_risk_count > 0 else "Trung bình 🟡"
    output.insert(1, f"**Mức độ Rủi ro Tổng quan:** {overall}\n")
    return "\n".join(output)


def _analyze_gemini(prompt: str, api_key: str) -> str:
    try:
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
                return f"❌ Lỗi khi kết nối với Gemini AI: {error_str}"
    except Exception as e:
        return f"❌ Lỗi hệ thống: {str(e)}"


def _analyze_ollama(prompt: str, host: str, model: str) -> str:
    try:
        url = f"{host.rstrip('/')}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        st.info(f"Đang gửi yêu cầu tới Local LLM ({model}) tại {host}...")
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "Không có phản hồi từ Ollama.")
    except requests.exceptions.ConnectionError:
        return f"❌ Lỗi kết nối tới Ollama tại {host}. Vui lòng kiểm tra xem phần mềm Ollama đã được bật chưa."
    except Exception as e:
        return f"❌ Lỗi khi gọi Ollama AI: {str(e)}"
