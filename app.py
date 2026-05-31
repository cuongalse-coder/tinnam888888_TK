"""
DocCompare - Ứng dụng So sánh Chứng từ Xuất Nhập Khẩu
Streamlit App - Main Entry Point
"""

import streamlit as st
import pandas as pd
import uuid
import json
import io
from datetime import datetime

# Import utility modules
from utils.extractors import extract_file
from utils.parser import detect_document_type, parse_fields, ai_parse_fields, DOCUMENT_TYPES, FIELD_MAPPING
from utils.comparator import (
    compare_documents,
    compare_multiple,
    compare_by_clusters,
    results_to_dataframe,
    export_to_excel
)
from utils.ai_analyzer import analyze_discrepancies

# ============================================================
# Page Config
# ============================================================
st.set_page_config(
    page_title="DocCompare - So sánh Chứng từ XNK",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# Custom CSS
# ============================================================
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global overrides */
    .stApp {
        font-family: 'Inter', sans-serif;
    }

    /* Header styling */
    .main-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #0a1628 100%);
        padding: 1.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        border: 1px solid rgba(59, 130, 246, 0.2);
    }
    .main-header h1 {
        background: linear-gradient(135deg, #3b82f6, #60a5fa, #93c5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    .main-header p {
        color: #94a3b8;
        margin: 0.3rem 0 0 0;
        font-size: 0.9rem;
    }

    /* Card styling */
    .doc-card {
        background: linear-gradient(135deg, #111827, #1a2332);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 0.8rem;
        transition: all 0.2s ease;
    }
    .doc-card:hover {
        border-color: #3b82f6;
        transform: translateY(-1px);
        box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
    }

    /* Status badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-match {
        background: rgba(16, 185, 129, 0.15);
        color: #10b981;
        border: 1px solid rgba(16, 185, 129, 0.3);
    }
    .badge-mismatch {
        background: rgba(239, 68, 68, 0.15);
        color: #ef4444;
        border: 1px solid rgba(239, 68, 68, 0.3);
    }
    .badge-missing {
        background: rgba(245, 158, 11, 0.15);
        color: #f59e0b;
        border: 1px solid rgba(245, 158, 11, 0.3);
    }

    /* Summary metric cards */
    .metric-card {
        background: linear-gradient(135deg, #111827, #1a2332);
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .metric-card h3 {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
    }
    .metric-card p {
        color: #94a3b8;
        font-size: 0.85rem;
        margin: 0.3rem 0 0 0;
    }

    /* Comparison table */
    .compare-match { background-color: rgba(16, 185, 129, 0.08) !important; }
    .compare-mismatch { background-color: rgba(239, 68, 68, 0.08) !important; }
    .compare-missing { background-color: rgba(245, 158, 11, 0.08) !important; }

    /* File upload area */
    .upload-info {
        background: rgba(59, 130, 246, 0.08);
        border: 1px solid rgba(59, 130, 246, 0.2);
        border-radius: 10px;
        padding: 1rem;
        margin: 0.5rem 0;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {
        background: rgba(10, 14, 26, 0.8);
        backdrop-filter: blur(12px);
    }

    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d1117 0%, #111827 100%);
    }
    [data-testid="stSidebar"] .stRadio > label {
        font-weight: 600;
    }

    /* Security badge */
    .security-badge {
        background: rgba(16, 185, 129, 0.1);
        border: 1px solid rgba(16, 185, 129, 0.2);
        border-radius: 8px;
        padding: 0.5rem 0.8rem;
        font-size: 0.8rem;
        color: #10b981;
        text-align: center;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        font-weight: 600;
    }

    /* Divider */
    hr {
        border-color: #1e293b;
    }
</style>
""", unsafe_allow_html=True)


def main():
    # ============================================================
    # Session State Init
    # ============================================================
    if 'documents' not in st.session_state:
        st.session_state.documents = []
    if 'comparisons' not in st.session_state:
        st.session_state.comparisons = []
    if 'shipments' not in st.session_state:
        st.session_state.shipments = {}

    # ============================================================
    # Sidebar
    # ============================================================
    with st.sidebar:
        st.markdown('''
        <div style="text-align:center; padding: 1rem 0;">
            <div style="font-size: 3rem;">📋</div>
            <h1 style="background: linear-gradient(135deg, #3b82f6, #60a5fa, #93c5fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 1.5rem; font-weight: 800; margin: 0.5rem 0 0 0;">DocCompare</h1>
            <p style="color: #64748b; font-size: 0.75rem; letter-spacing: 2px; margin: 0;">SO SÁNH CHỨNG TỪ XNK</p>
        </div>
        ''', unsafe_allow_html=True)

        st.divider()
        st.markdown("🤖 **Cấu hình AI Phân tích Lỗi**")
        
        ai_mode = st.selectbox(
            "Chọn hệ thống AI",
            options=["⚡ Thuật toán Cứng (Siêu Tốc)", "🌐 AI Online (Gemini)", "🖥️ AI Local (Ollama)"],
            index=0,
            help="Chọn công cụ để phân tích rủi ro sai lệch chứng từ."
        )
        st.session_state.ai_mode = ai_mode
        
        if "Online" in ai_mode:
            default_api_key = ""
            try:
                default_api_key = st.secrets.get("GEMINI_API_KEY", "")
            except Exception:
                pass
                
            api_key = st.text_input(
                "Gemini API Key",
                value=default_api_key,
                type="password",
                placeholder="Nhập API Key..."
            )
            st.session_state.gemini_api_key = api_key
        elif "Local" in ai_mode:
            st.session_state.ollama_host = st.text_input("Ollama Host URL", value="http://localhost:11434")
            st.session_state.ollama_model = st.text_input("Tên Model", value="llama3")
        else:
            st.info("Chế độ này xử lý bằng thuật toán nội bộ, không cần Internet.")

        st.divider()
        doc_count = len(st.session_state.documents)
        st.markdown(f"📄 **Chứng từ đã tải:** `{doc_count}`")

        st.divider()
        with st.expander("⚙️ Quản lý dữ liệu"):
            if st.button("🗑️ Xóa tất cả tải lại", type="primary", use_container_width=True, key="clear_all"):
                st.session_state.documents = []
                st.success("✅ Đã xóa trắng dữ liệu!")
                st.rerun()

        st.divider()
        st.markdown('<div class="security-badge">🔒 Xử lý 100% trên trình duyệt<br><small>Dữ liệu không gửi ra ngoài</small></div>', unsafe_allow_html=True)

    # ============================================================
    # MAIN PAGE: Upload & Auto-Compare
    # ============================================================
    st.markdown('''
    <div class="main-header">
        <h1>📤 Tải lên & Tự động So sánh</h1>
        <p>Kéo thả các file chứng từ vào đây. Hệ thống sẽ tự động trích xuất và hiển thị ngay bảng so sánh chi tiết!</p>
    </div>
    ''', unsafe_allow_html=True)

    col1, col2 = st.columns([3, 1])
    with col2:
        ocr_langs = st.multiselect(
            "🌐 Ngôn ngữ OCR (cho ảnh)",
            options=['vie', 'eng', 'chi_sim', 'chi_tra'],
            default=['vie', 'eng'],
            format_func=lambda x: {'vie': '🇻🇳 Tiếng Việt', 'eng': '🇬🇧 English', 'chi_sim': '🇨🇳 中文简体', 'chi_tra': '🇹🇼 中文繁體'}.get(x, x),
            key="ocr_lang_select",
        )

    with col1:
        uploaded_files = st.file_uploader(
            "Kéo thả hoặc chọn file (chọn từ 2 file trở lên để so sánh)",
            type=['xlsx', 'xls', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx'],
            accept_multiple_files=True,
            key="file_uploader",
        )

    if uploaded_files is not None:
        current_file_names = [f.name for f in uploaded_files]
        # Xóa những file trong session state mà không còn trong file_uploader (người dùng đã bấm X)
        st.session_state.documents = [d for d in st.session_state.documents if d['file_name'] in current_file_names]

    if uploaded_files:
        st.divider()
        progress_bar = st.progress(0, text="Đang xử lý...")
        new_files_processed = False
        discarded_files = []
        for idx, file in enumerate(uploaded_files):
            existing = [d for d in st.session_state.documents if d.get('file_name') == file.name]
            if existing:
                continue
            progress_bar.progress((idx + 1) / len(uploaded_files), text=f"Đang xử lý: {file.name} ({idx + 1}/{len(uploaded_files)})")
            with st.spinner(f"⏳ Đang trích xuất: **{file.name}**..."):
                result = extract_file(file, ocr_languages=ocr_langs)
                if result.get('error'):
                    st.error(f"❌ Lỗi khi xử lý **{file.name}**: {result['error']}")
                    continue
                raw_text = result.get('raw_text', '')
                detection = detect_document_type(raw_text)
                
                if detection['type'] == 'unknown':
                    discarded_files.append(file.name)
                    continue

                api_key = st.session_state.get("gemini_api_key", "")
                fields = ai_parse_fields(raw_text, detection['type'], api_key)
                doc = {
                    'id': str(uuid.uuid4()),
                    'file_name': file.name,
                    'file_type': result.get('file_type', 'unknown'),
                    'doc_type': detection['type'],
                    'doc_type_confidence': detection['confidence'],
                    'fields': fields,
                    'raw_text': raw_text[:5000],
                    'upload_date': datetime.now().isoformat(),
                }
                st.session_state.documents.append(doc)
                new_files_processed = True
                
        progress_bar.progress(1.0, text="✅ Hoàn tất!")
        if discarded_files:
            st.warning(f"🗑️ Đã loại bỏ {len(discarded_files)} file không phải chứng từ XNK hợp lệ (như báo giá, hợp đồng...): {', '.join(discarded_files)}")

    if st.session_state.documents:
        st.divider()
        st.subheader(f"📄 Các chứng từ đã tải ({len(st.session_state.documents)})")
        
        for doc in st.session_state.documents:
            doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})
            icon = doc_type_info.get('icon', '📄')
            type_name = doc_type_info.get('name', doc['doc_type'])
            field_count = len([f for f in doc['fields'].values() if f.get('value')])
            
            with st.expander(f"📁 {doc['file_name']} — {icon} {type_name} — {field_count} trường", expanded=False):
                col_a, col_b = st.columns([3, 1])
                with col_a:
                    type_options = list(DOCUMENT_TYPES.keys())
                    current_idx = type_options.index(doc['doc_type']) if doc['doc_type'] in type_options else 0
                    new_type = st.selectbox(
                        "Đổi loại chứng từ (Nếu nhận diện sai):",
                        options=type_options,
                        index=current_idx,
                        format_func=lambda x: f"{DOCUMENT_TYPES[x]['icon']} {DOCUMENT_TYPES[x]['name']}",
                        key=f"type_{doc['id']}",
                    )
                    if new_type != doc['doc_type']:
                        doc['doc_type'] = new_type
                        api_key = st.session_state.get("gemini_api_key", "")
                        doc['fields'] = ai_parse_fields(doc.get('raw_text', ''), new_type, api_key)
                        st.rerun()
                with col_b:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Xóa file này", key=f"del_{doc['id']}", type="secondary"):
                        st.session_state.documents = [d for d in st.session_state.documents if d['id'] != doc['id']]
                        st.rerun()

                st.markdown("**📋 Dữ liệu trích xuất:**")
                field_data = []
                for key, field in doc['fields'].items():
                    if field.get('value'):
                        conf = field.get('confidence', 0)
                        conf_bar = "🟢" if conf >= 0.7 else "🟡" if conf >= 0.4 else "🔴"
                        field_data.append({
                            'Trường': field.get('label', key),
                            'Giá trị': str(field.get('value', '')),
                            'Độ tin cậy': f"{conf_bar} {conf:.0%}",
                        })
                if field_data:
                    df = pd.DataFrame(field_data)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("Không trích xuất được trường nào. Hãy thử đổi loại chứng từ.")

        if len(st.session_state.documents) >= 2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown('<div class="main-header" style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%); border-color: rgba(139, 92, 246, 0.3);"><h1>⚖️ Bảng So Sánh Tự Động</h1><p>Hệ thống tự động soi chiếu chéo dữ liệu giữa tất cả các chứng từ bạn vừa tải lên</p></div>', unsafe_allow_html=True)
            
            docs = st.session_state.documents
            if len(docs) == 2:
                with st.spinner("⏳ Đang đối chiếu dữ liệu..."):
                    result = compare_documents(docs[0], docs[1])
                _render_comparison_result(result)
                _render_ai_analyzer_section(result, False, docs)
            else:
                with st.spinner("⏳ Đang đối chiếu đa luồng..."):
                    multi_result = compare_by_clusters(docs)
                _render_multi_comparison(multi_result, docs)
                _render_ai_analyzer_section(multi_result, True, docs)
        else:
            st.info("👆 Hãy tải thêm ít nhất 1 chứng từ nữa để hệ thống tự động chạy bảng so sánh chéo nhé.")




def _render_ai_analyzer_section(result, is_multiple, docs):
    st.divider()
    st.subheader("🤖 AI Phân tích Lỗi & Khuyến nghị")
    st.info("Trợ lý AI sẽ đọc các lỗi sai lệch từ bảng trên và đóng vai trò Trưởng phòng Xuất Nhập Khẩu để tư vấn rủi ro.")
    
    if st.button("✨ Bắt đầu Phân tích Lỗi", type="secondary"):
        with st.spinner("AI đang phân tích rủi ro..."):
            config = {
                'ai_mode': st.session_state.get('ai_mode', '⚡ Thuật toán Cứng (Siêu Tốc)'),
                'api_key': st.session_state.get('gemini_api_key', ''),
                'ollama_host': st.session_state.get('ollama_host', 'http://localhost:11434'),
                'ollama_model': st.session_state.get('ollama_model', 'llama3')
            }
            response = analyze_discrepancies(result, is_multiple, config, docs)
            st.markdown(response)


def _render_comparison_result(result, key_suffix=""):
    """Render comparison result for 2 documents."""
    summary = result.get('summary', {})

    # Summary metrics
    st.divider()
    st.subheader("📊 Kết quả So sánh")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        match_rate = summary.get('match_rate', 0)
        color = "#10b981" if match_rate >= 0.8 else "#f59e0b" if match_rate >= 0.5 else "#ef4444"
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: {color};">{match_rate:.0%}</h3>
            <p>Tỷ lệ khớp</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #10b981;">{summary.get('matches', 0)}</h3>
            <p>✅ Khớp</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #ef4444;">{summary.get('mismatches', 0)}</h3>
            <p>❌ Sai lệch</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="color: #f59e0b;">{summary.get('missing', 0)}</h3>
            <p>⚠️ Thiếu</p>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    # Detailed results table
    results = result.get('results', [])
    if results:
        df = results_to_dataframe(result)
        
        GROUPS = {
            "🚢 Nhóm Thông tin Vận tải": ["Tàu", "Chuyến", "Cảng xếp (POL)", "Cảng dỡ (POD)", "B/L No", "Số Vận đơn (B/L)", "Số container", "Số seal", "Loại container", "Ngày On Board"],
            "🏢 Nhóm Thông tin Đối tác": ["Người xuất khẩu", "Người nhập khẩu", "Shipper", "Consignee", "Notify Party", "Người bán", "Người mua", "Bên được thông báo"],
            "📦 Nhóm Thông tin Hàng hóa": ["Mô tả hàng hóa", "Số lượng", "Trọng lượng", "Trọng lượng tịnh (N/W)", "Trọng lượng cả bì (G/W)", "Thể tích (CBM)", "Thể tích", "Số kiện", "Mã HS", "Đơn vị", "Đơn giá", "Xuất xứ"],
            "💰 Nhóm Tài chính & Hợp đồng": ["Trị giá", "Tổng giá trị", "Loại tiền", "Điều kiện giao hàng", "Điều kiện cước", "Số Hợp đồng", "Ngày Hợp đồng", "Phương thức thanh toán", "Tổng tiền thuế", "Số Invoice", "Invoice No", "Cước phí", "Số C/O"],
            "📅 Nhóm Thông tin Chung": ["Số tờ khai", "Ngày đăng ký", "Ngày phát hành", "Ngày", "ETD", "ETA", "Mã loại hình", "Cơ quan Hải quan", "Phương thức vận chuyển", "P/L No", "Booking No"]
        }

        # Apply styling
        def highlight_status(row):
            status = row.get('Trạng thái', '')
            if isinstance(status, pd.Series):
                status = status.iloc[0] if not status.empty else ''
            status = str(status)
            if 'Khớp' in status:
                return ['background-color: rgba(16,185,129,0.08)'] * len(row)
            elif 'Sai lệch' in status:
                return ['background-color: rgba(239,68,68,0.08)'] * len(row)
            elif 'Thiếu' in status:
                return ['background-color: rgba(245,158,11,0.08)'] * len(row)
            return [''] * len(row)

        rendered_labels = set()
        
        for group_name, keywords in GROUPS.items():
            group_df = df[df['Trường'].isin(keywords)]
            if not group_df.empty:
                st.markdown(f"#### {group_name}")
                styled_df = group_df.style.apply(highlight_status, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                rendered_labels.update(group_df['Trường'].tolist())
                
        # Other remaining fields
        other_df = df[~df['Trường'].isin(rendered_labels)]
        if not other_df.empty:
            st.markdown("#### 📌 Thông tin Khác")
            styled_df = other_df.style.apply(highlight_status, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)

        # Export buttons
        col1, col2 = st.columns(2)
        with col1:
            try:
                excel_bytes = export_to_excel(result)
                st.download_button(
                    "📊 Xuất Excel",
                    data=excel_bytes,
                    file_name=f"so-sanh-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    key=f"export_excel{key_suffix}",
                )
            except Exception as e:
                st.error(f"Lỗi xuất Excel: {e}")

        with col2:
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📄 Xuất CSV",
                data=csv_data,
                file_name=f"so-sanh-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
                key=f"export_csv{key_suffix}",
            )
    else:
        st.info("Không tìm thấy trường chung để so sánh giữa hai chứng từ.")


def _render_multi_comparison(multi_result, docs):
    """Render comparison result based on ECUS standard fields, split into tabs."""
    from utils.comparator import compare_ecus_centric
    
    st.divider()
    
    if not docs:
        st.info("Chưa có chứng từ nào để so sánh.")
        return

    ecus_output = compare_ecus_centric(docs)
    
    if not ecus_output or not ecus_output.get("results"):
        st.warning("Không thể tạo bảng đối chiếu ECUS. Vui lòng kiểm tra lại chứng từ tải lên.")
        return
        
    ecus_results = ecus_output["results"]
    ecus_type = ecus_output["type"]
    
    title_suffix = "(Nhập Khẩu)" if ecus_type == "customs_declaration_import" else "(Xuất Khẩu)"
    st.subheader(f"📊 Bảng Đối Chiếu Chuẩn ECUS VNACCS {title_suffix}")
    st.markdown(f"Bảng tổng hợp đối chiếu tất cả các chứng từ dựa trên bộ tiêu chí chuẩn của Tờ khai Hải quan {title_suffix}.")

    def highlight_match(row):
        val = row.get('Trạng thái', '')
        if isinstance(val, pd.Series):
            val = val.iloc[0] if not val.empty else ''
        val = str(val)
        if '✅' in val:
            return ['background-color: rgba(16,185,129,0.08)'] * len(row)
        elif '❌' in val:
            return ['background-color: rgba(239,68,68,0.08)'] * len(row)
        else:
            return [''] * len(row)

    display_data = []
    
    from utils.parser import DOCUMENT_TYPES
    col_map = {}
    for doc in docs:
        doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})
        icon = doc_type_info.get('icon', '📄')
        col_map[doc['id']] = f"{icon} {doc['file_name'][:30]}"
        
    for row in ecus_results:
        display_row = {"Tiêu chí ECUS": row["Tiêu chí ECUS"]}
        for doc in docs:
            display_row[col_map[doc['id']]] = row.get(doc['id'], "—")
        display_row["Trạng thái"] = row.get("Trạng thái", "")
        display_data.append(display_row)

    df = pd.DataFrame(display_data)
    
    TAB_GROUPS = {
        "Thông tin chung": [
            "Số tờ khai", "Ngày đăng ký", "Người xuất khẩu", "Người nhập khẩu", 
            "Mã loại hình", "Cơ quan Hải quan", "Số Vận đơn (B/L)", 
            "Tên tàu / Phương tiện VC", "Cảng xếp hàng (POL)", "Cảng dỡ hàng (POD)", 
            "Số lượng kiện", "Tổng trọng lượng", "Địa điểm lưu kho"
        ],
        "Thông tin chung 2": [
            "Số Hóa đơn (Invoice)", "Ngày Hóa đơn", "Trị giá hóa đơn", 
            "Mã đồng tiền", "Phương thức thanh toán", "Điều kiện giao hàng"
        ],
        "Danh sách hàng": [
            "Mã số hàng hóa (HS)", "Mô tả hàng hóa", "Lượng (Quantity)", "Đơn giá"
        ]
    }
    
    tabs = st.tabs(list(TAB_GROUPS.keys()))
    
    for idx, (tab_name, keywords) in enumerate(TAB_GROUPS.items()):
        with tabs[idx]:
            tab_df = df[df["Tiêu chí ECUS"].isin(keywords)]
            if not tab_df.empty:
                styled_df = tab_df.style.apply(highlight_match, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
            else:
                st.info(f"Không có dữ liệu cho phần {tab_name}.")
                
    # Các trường không thuộc 3 nhóm trên (nếu có)
    all_known_keys = [k for group in TAB_GROUPS.values() for k in group]
    other_df = df[~df["Tiêu chí ECUS"].isin(all_known_keys)]
    if not other_df.empty:
        with st.expander("📌 Các thông tin khác", expanded=False):
            styled_df = other_df.style.apply(highlight_match, axis=1)
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Export ECUS comparison
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        try:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Xuất ra nhiều sheet tương ứng
                for tab_name, keywords in TAB_GROUPS.items():
                    tab_df = df[df["Tiêu chí ECUS"].isin(keywords)]
                    if not tab_df.empty:
                        safe_sheet_name = tab_name[:31]
                        tab_df.to_excel(writer, index=False, sheet_name=safe_sheet_name)
                if not other_df.empty:
                    other_df.to_excel(writer, index=False, sheet_name="Khác")
                
                # Tạo thêm Sheet "Chi tiết đầy đủ" chứa toàn bộ thông tin gốc của các chứng từ
                raw_data = []
                for doc in docs:
                    for field_key, field_data in doc.get("fields", {}).items():
                        raw_data.append({
                            "Chứng từ": doc["file_name"],
                            "Loại chứng từ": doc["doc_type_name"],
                            "Mã trường (Key)": field_key,
                            "Tên trường (Label)": field_data.get("label", ""),
                            "Giá trị": field_data.get("value", "")
                        })
                if raw_data:
                    pd.DataFrame(raw_data).to_excel(writer, index=False, sheet_name="Chi tiết đầy đủ")
                    
            excel_bytes = output.getvalue()
            
            st.download_button(
                "📊 Xuất Bảng ECUS (Excel)",
                data=excel_bytes,
                file_name=f"ecus-compare-{datetime.now().strftime('%Y%m%d-%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_ecus_excel",
            )
        except Exception as e:
            st.error(f"Lỗi xuất Excel: {e}")

    with col2:
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📄 Xuất Bảng ECUS (CSV)",
            data=csv_data,
            file_name=f"ecus-compare-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            key="export_ecus_csv",
        )





if __name__ == '__main__':
    main()
