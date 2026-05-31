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
from utils.parser import detect_document_type, parse_fields, DOCUMENT_TYPES, FIELD_MAPPING
from utils.comparator import compare_documents, compare_multiple, results_to_dataframe, export_to_excel

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
    st.markdown("""
    <div style="text-align:center; padding: 1rem 0;">
        <div style="font-size: 3rem;">📋</div>
        <h1 style="background: linear-gradient(135deg, #3b82f6, #60a5fa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 1.5rem; font-weight: 800; margin: 0.5rem 0 0 0;">DocCompare</h1>
        <p style="color: #64748b; font-size: 0.75rem; letter-spacing: 2px; margin: 0;">SO SÁNH CHỨNG TỪ XNK</p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    page = st.radio(
        "📌 Điều hướng",
        ["📤 Tải lên & Trích xuất", "📄 Quản lý Chứng từ", "🔍 So sánh Chứng từ"],
        label_visibility="collapsed",
    )

    st.divider()

    # Doc count
    doc_count = len(st.session_state.documents)
    st.markdown(f"📄 **Chứng từ đã tải:** `{doc_count}`")

    # Shipment count
    shipment_ids = set(d.get('shipment_id', '') for d in st.session_state.documents if d.get('shipment_id'))
    st.markdown(f"📦 **Lô hàng:** `{len(shipment_ids)}`")

    st.divider()

    # Data management
    with st.expander("⚙️ Quản lý dữ liệu"):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📥 Xuất JSON", use_container_width=True, key="export_btn"):
                data = {
                    'documents': st.session_state.documents,
                    'comparisons': st.session_state.comparisons,
                    'exported_at': datetime.now().isoformat(),
                }
                json_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
                st.download_button(
                    "⬇️ Tải xuống",
                    data=json_str,
                    file_name=f"doccompare-backup-{datetime.now().strftime('%Y%m%d')}.json",
                    mime="application/json",
                    key="download_json",
                )
        with col2:
            uploaded_json = st.file_uploader("📤 Nhập JSON", type=['json'], key="import_json", label_visibility="collapsed")
            if uploaded_json:
                try:
                    data = json.loads(uploaded_json.read())
                    if 'documents' in data:
                        st.session_state.documents = data['documents']
                    if 'comparisons' in data:
                        st.session_state.comparisons = data['comparisons']
                    st.success("✅ Đã nhập dữ liệu!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Lỗi: {e}")

        if st.button("🗑️ Xóa tất cả", type="secondary", use_container_width=True, key="clear_all"):
            st.session_state.documents = []
            st.session_state.comparisons = []
            st.session_state.shipments = {}
            st.success("✅ Đã xóa!")
            st.rerun()

    st.divider()
    st.markdown("""
    <div class="security-badge">🔒 Xử lý 100% trên trình duyệt<br><small>Dữ liệu không gửi ra ngoài</small></div>
    """, unsafe_allow_html=True)


# ============================================================
# PAGE 1: Upload & Extract
# ============================================================
def page_upload():
    st.markdown("""
    <div class="main-header">
        <h1>📤 Tải lên & Trích xuất dữ liệu</h1>
        <p>Hỗ trợ Excel (.xlsx, .xls, .csv), PDF, Ảnh (OCR), Word (.docx)</p>
    </div>
    """, unsafe_allow_html=True)

    # OCR language selection
    col1, col2 = st.columns([3, 1])
    with col2:
        ocr_langs = st.multiselect(
            "🌐 Ngôn ngữ OCR (cho ảnh)",
            options=['vie', 'eng', 'chi_sim', 'chi_tra'],
            default=['vie', 'eng'],
            format_func=lambda x: {
                'vie': '🇻🇳 Tiếng Việt',
                'eng': '🇬🇧 English',
                'chi_sim': '🇨🇳 中文简体',
                'chi_tra': '🇹🇼 中文繁體',
            }.get(x, x),
            key="ocr_lang_select",
        )

    with col1:
        uploaded_files = st.file_uploader(
            "Kéo thả hoặc chọn file",
            type=['xlsx', 'xls', 'csv', 'pdf', 'jpg', 'jpeg', 'png', 'docx'],
            accept_multiple_files=True,
            key="file_uploader",
            help="Hỗ trợ: Excel, PDF, Ảnh (OCR), Word",
        )

    if uploaded_files:
        st.divider()
        progress_bar = st.progress(0, text="Đang xử lý...")

        for idx, file in enumerate(uploaded_files):
            # Check if already processed
            existing = [d for d in st.session_state.documents if d.get('file_name') == file.name]
            if existing:
                continue

            progress_bar.progress(
                (idx + 1) / len(uploaded_files),
                text=f"Đang xử lý: {file.name} ({idx + 1}/{len(uploaded_files)})"
            )

            with st.spinner(f"⏳ Đang trích xuất: **{file.name}**..."):
                # Extract data
                result = extract_file(file, ocr_languages=ocr_langs)

                if result.get('error'):
                    st.error(f"❌ Lỗi khi xử lý **{file.name}**: {result['error']}")
                    continue

                raw_text = result.get('raw_text', '')

                # Auto-detect document type
                detection = detect_document_type(raw_text)

                # Parse fields
                fields = parse_fields(raw_text, detection['type'])

                # Create document record
                doc = {
                    'id': str(uuid.uuid4()),
                    'file_name': file.name,
                    'file_type': result.get('file_type', 'unknown'),
                    'doc_type': detection['type'],
                    'doc_type_confidence': detection['confidence'],
                    'fields': fields,
                    'raw_text': raw_text[:5000],  # Limit stored raw text
                    'upload_date': datetime.now().isoformat(),
                    'shipment_id': '',
                }

                st.session_state.documents.append(doc)

        progress_bar.progress(1.0, text="✅ Hoàn tất!")
        st.rerun()

    # Show uploaded documents
    if st.session_state.documents:
        st.divider()
        st.subheader(f"📄 Chứng từ đã tải ({len(st.session_state.documents)})")

        for i, doc in enumerate(st.session_state.documents):
            doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})
            icon = doc_type_info.get('icon', '📄')
            type_name = doc_type_info.get('name', doc['doc_type'])
            field_count = len([f for f in doc['fields'].values() if f.get('value')])

            file_icons = {
                'excel': '📊', 'pdf': '📕', 'image': '🖼️', 'word': '📘', 'csv': '📊'
            }
            file_icon = file_icons.get(doc.get('file_type', ''), '📄')

            with st.expander(
                f"{file_icon} **{doc['file_name']}** — {icon} {type_name} — {field_count} trường",
                expanded=False,
            ):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    # Change document type
                    type_options = list(DOCUMENT_TYPES.keys())
                    type_labels = [f"{DOCUMENT_TYPES[t]['icon']} {DOCUMENT_TYPES[t]['name']}" for t in type_options]
                    current_idx = type_options.index(doc['doc_type']) if doc['doc_type'] in type_options else 0

                    new_type = st.selectbox(
                        "Loại chứng từ",
                        options=type_options,
                        index=current_idx,
                        format_func=lambda x: f"{DOCUMENT_TYPES[x]['icon']} {DOCUMENT_TYPES[x]['name']}",
                        key=f"type_{doc['id']}",
                    )

                    if new_type != doc['doc_type']:
                        doc['doc_type'] = new_type
                        doc['fields'] = parse_fields(doc.get('raw_text', ''), new_type)

                with col2:
                    # Shipment assignment
                    shipment = st.text_input(
                        "Mã lô hàng (Shipment ID)",
                        value=doc.get('shipment_id', ''),
                        key=f"ship_{doc['id']}",
                        placeholder="Ví dụ: SHIP-2024-001",
                    )
                    doc['shipment_id'] = shipment

                with col3:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Xóa", key=f"del_{doc['id']}", type="secondary"):
                        st.session_state.documents = [d for d in st.session_state.documents if d['id'] != doc['id']]
                        st.rerun()

                # Show extracted fields
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

                # Show raw text preview
                with st.expander("📝 Xem văn bản gốc", expanded=False):
                    st.text(doc.get('raw_text', '')[:2000])


# ============================================================
# PAGE 2: Document Management
# ============================================================
def page_documents():
    st.markdown("""
    <div class="main-header">
        <h1>📄 Quản lý Chứng từ</h1>
        <p>Xem, chỉnh sửa và quản lý các chứng từ đã tải lên</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.documents:
        st.info("📭 Chưa có chứng từ nào. Hãy tải lên ở trang **Tải lên & Trích xuất**.")
        return

    # Filters
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        search = st.text_input("🔍 Tìm kiếm", placeholder="Nhập tên file hoặc nội dung...", key="doc_search")
    with col2:
        type_filter = st.selectbox(
            "📁 Lọc theo loại",
            options=['all'] + list(DOCUMENT_TYPES.keys()),
            format_func=lambda x: "Tất cả" if x == 'all' else f"{DOCUMENT_TYPES[x]['icon']} {DOCUMENT_TYPES[x]['name']}",
            key="type_filter",
        )
    with col3:
        view_mode = st.radio("Xem theo", ["📋 Danh sách", "📦 Lô hàng"], horizontal=True, label_visibility="collapsed", key="view_mode_radio")

    st.divider()

    # Filter documents
    docs = st.session_state.documents
    if search:
        search_lower = search.lower()
        docs = [d for d in docs if search_lower in d.get('file_name', '').lower() or search_lower in d.get('raw_text', '').lower()]
    if type_filter != 'all':
        docs = [d for d in docs if d.get('doc_type') == type_filter]

    if not docs:
        st.warning("Không tìm thấy chứng từ phù hợp.")
        return

    if "📦" in view_mode:
        # Group by shipment
        grouped = {}
        no_shipment = []
        for doc in docs:
            sid = doc.get('shipment_id', '')
            if sid:
                grouped.setdefault(sid, []).append(doc)
            else:
                no_shipment.append(doc)

        for sid, group_docs in grouped.items():
            with st.expander(f"📦 Lô hàng: **{sid}** ({len(group_docs)} chứng từ)", expanded=True):
                _render_doc_table(group_docs)

        if no_shipment:
            with st.expander(f"📄 Chưa phân lô ({len(no_shipment)} chứng từ)", expanded=True):
                _render_doc_table(no_shipment)
    else:
        _render_doc_table(docs)


def _render_doc_table(docs):
    """Render a table of documents."""
    table_data = []
    for doc in docs:
        doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})
        icon = doc_type_info.get('icon', '📄')
        type_name = doc_type_info.get('name', doc['doc_type'])
        field_count = len([f for f in doc['fields'].values() if f.get('value')])
        upload_date = doc.get('upload_date', '')[:10]

        table_data.append({
            'Loại': f"{icon} {type_name}",
            'File': doc['file_name'],
            'Số trường': field_count,
            'Lô hàng': doc.get('shipment_id', '—'),
            'Ngày tải': upload_date,
        })

    df = pd.DataFrame(table_data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Detail view
    selected_doc_name = st.selectbox(
        "📝 Xem chi tiết chứng từ",
        options=[d['file_name'] for d in docs],
        key=f"detail_select_{docs[0]['id'] if docs else 'none'}",
    )

    if selected_doc_name:
        doc = next((d for d in docs if d['file_name'] == selected_doc_name), None)
        if doc:
            _render_doc_detail(doc)


def _render_doc_detail(doc):
    """Render document detail view with editable fields."""
    doc_type_info = DOCUMENT_TYPES.get(doc['doc_type'], {})

    st.markdown(f"### {doc_type_info.get('icon', '📄')} {doc['file_name']}")

    # Editable fields
    edited = False
    for key, field in doc['fields'].items():
        if field.get('value') or key in doc_type_info.get('fields', {}):
            label = field.get('label', key)
            current_val = str(field.get('value', ''))
            new_val = st.text_input(
                label,
                value=current_val,
                key=f"edit_{doc['id']}_{key}",
            )
            if new_val != current_val:
                doc['fields'][key]['value'] = new_val
                doc['fields'][key]['confidence'] = 1.0
                edited = True

    if edited:
        st.success("✅ Đã cập nhật!")


# ============================================================
# PAGE 3: Compare
# ============================================================
def page_compare():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 So sánh Chứng từ</h1>
        <p>So sánh tự do hoặc theo lô hàng — Tìm sai lệch tự động</p>
    </div>
    """, unsafe_allow_html=True)

    if len(st.session_state.documents) < 2:
        st.warning("⚠️ Cần ít nhất **2 chứng từ** để so sánh. Hãy tải lên thêm ở trang **Tải lên**.")
        return

    # Compare mode
    mode = st.radio(
        "Chế độ so sánh",
        ["🔀 So sánh tự do", "📦 So sánh theo lô hàng"],
        horizontal=True,
        key="compare_mode",
    )

    st.divider()

    selected_docs = []

    if "tự do" in mode:
        # Free compare - select documents
        st.markdown("**Chọn chứng từ để so sánh** (tối thiểu 2):")

        doc_options = {
            doc['id']: f"{DOCUMENT_TYPES.get(doc['doc_type'], {}).get('icon', '📄')} {doc['file_name']} ({DOCUMENT_TYPES.get(doc['doc_type'], {}).get('name', '')})"
            for doc in st.session_state.documents
        }

        selected_ids = st.multiselect(
            "Chọn chứng từ",
            options=list(doc_options.keys()),
            format_func=lambda x: doc_options[x],
            key="compare_select",
            label_visibility="collapsed",
        )

        selected_docs = [d for d in st.session_state.documents if d['id'] in selected_ids]

    else:
        # Shipment compare
        shipment_ids = sorted(set(
            d.get('shipment_id', '') for d in st.session_state.documents if d.get('shipment_id')
        ))

        if not shipment_ids:
            st.warning("⚠️ Chưa có lô hàng nào. Hãy gán mã lô hàng cho chứng từ ở trang **Tải lên**.")
            return

        selected_shipment = st.selectbox(
            "📦 Chọn lô hàng",
            options=shipment_ids,
            key="shipment_select",
        )

        if selected_shipment:
            selected_docs = [d for d in st.session_state.documents if d.get('shipment_id') == selected_shipment]
            st.info(f"Lô hàng **{selected_shipment}** có {len(selected_docs)} chứng từ")

    # Run comparison
    if len(selected_docs) >= 2:
        if st.button("🚀 So sánh ngay", type="primary", use_container_width=True, key="run_compare"):
            with st.spinner("⏳ Đang so sánh..."):
                if len(selected_docs) == 2:
                    result = compare_documents(selected_docs[0], selected_docs[1])
                    _render_comparison_result(result)
                else:
                    multi_result = compare_multiple(selected_docs)
                    _render_multi_comparison(multi_result, selected_docs)

                # Save comparison
                comp_record = {
                    'id': str(uuid.uuid4()),
                    'date': datetime.now().isoformat(),
                    'doc_ids': [d['id'] for d in selected_docs],
                    'doc_names': [d['file_name'] for d in selected_docs],
                }
                st.session_state.comparisons.append(comp_record)

    elif selected_docs:
        st.info("👆 Hãy chọn thêm chứng từ (tối thiểu 2)")

    # History
    if st.session_state.comparisons:
        st.divider()
        with st.expander("📜 Lịch sử so sánh", expanded=False):
            for comp in reversed(st.session_state.comparisons[-10:]):
                date_str = comp.get('date', '')[:16].replace('T', ' ')
                names = ", ".join(comp.get('doc_names', []))
                st.markdown(f"• **{date_str}** — {names}")


def _render_comparison_result(result):
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

        # Apply styling
        def highlight_status(row):
            status = row.get('Trạng thái', '')
            if 'Khớp' in status:
                return ['background-color: rgba(16,185,129,0.08)'] * len(row)
            elif 'Sai lệch' in status:
                return ['background-color: rgba(239,68,68,0.08)'] * len(row)
            elif 'Thiếu' in status:
                return ['background-color: rgba(245,158,11,0.08)'] * len(row)
            return [''] * len(row)

        styled_df = df.style.apply(highlight_status, axis=1)
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
                    key="export_excel",
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
                key="export_csv",
            )
    else:
        st.info("Không tìm thấy trường chung để so sánh giữa hai chứng từ.")


def _render_multi_comparison(multi_result, docs):
    """Render comparison result for 3+ documents."""
    st.divider()
    st.subheader("📊 Kết quả So sánh Nhiều Chứng từ")

    # Pair results
    pair_results = multi_result.get('pair_results', [])

    for pair_result in pair_results:
        doc1_name = pair_result.get('doc1_name', '')
        doc2_name = pair_result.get('doc2_name', '')
        summary = pair_result.get('summary', {})
        match_rate = summary.get('match_rate', 0)

        color = "#10b981" if match_rate >= 0.8 else "#f59e0b" if match_rate >= 0.5 else "#ef4444"

        with st.expander(
            f"📊 {doc1_name} ↔ {doc2_name} — Tỷ lệ khớp: {match_rate:.0%}",
            expanded=False,
        ):
            _render_comparison_result(pair_result)

    # Aggregate view
    aggregate = multi_result.get('aggregate', [])
    if aggregate:
        st.divider()
        st.subheader("📋 Tổng hợp tất cả chứng từ")

        agg_data = []
        for item in aggregate:
            row = {'Trường': item.get('label', '')}
            for doc in docs:
                val = item.get('values', {}).get(doc['id'], '—')
                row[doc['file_name'][:20]] = str(val) if val else '—'
            row['Tất cả khớp?'] = '✅' if item.get('all_match') else '❌'
            agg_data.append(row)

        if agg_data:
            agg_df = pd.DataFrame(agg_data)
            st.dataframe(agg_df, use_container_width=True, hide_index=True)


# ============================================================
# Router
# ============================================================
if "Tải lên" in page:
    page_upload()
elif "Chứng từ" in page:
    page_documents()
elif "So sánh" in page:
    page_compare()
