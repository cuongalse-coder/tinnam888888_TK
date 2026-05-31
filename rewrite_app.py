with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_ui = """with st.sidebar:
    st.markdown('''
    <div style="text-align:center; padding: 1rem 0;">
        <div style="font-size: 3rem;">📋</div>
        <h1 style="background: linear-gradient(135deg, #3b82f6, #60a5fa, #93c5fd); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 1.5rem; font-weight: 800; margin: 0.5rem 0 0 0;">DocCompare</h1>
        <p style="color: #64748b; font-size: 0.75rem; letter-spacing: 2px; margin: 0;">SO SÁNH CHỨNG TỪ XNK</p>
    </div>
    ''', unsafe_allow_html=True)

    st.divider()
    st.markdown("🤖 **Cấu hình AI (Tùy chọn)**")
    default_api_key = ""
    try:
        default_api_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass
        
    api_key = st.text_input(
        "Gemini API Key",
        value=default_api_key,
        type="password",
        placeholder="Nhập API Key để AI phân tích...",
        help="Sử dụng Google Gemini AI để đọc chứng từ siêu chính xác."
    )
    st.session_state.gemini_api_key = api_key

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

if uploaded_files:
    st.divider()
    progress_bar = st.progress(0, text="Đang xử lý...")
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
    progress_bar.progress(1.0, text="✅ Hoàn tất!")
    st.rerun()

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
                multi_result = compare_multiple(docs)
            _render_multi_comparison(multi_result, docs)
            _render_ai_analyzer_section(multi_result, True, docs)
    else:
        st.info("👆 Hãy tải thêm ít nhất 1 chứng từ nữa để hệ thống tự động chạy bảng so sánh chéo nhé.")

"""

lines = lines[:187] + [new_ui + "\n"] + lines[684:]

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)
