import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """    if uploaded_files:
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
            st.warning(f"🗑️ Đã loại bỏ {len(discarded_files)} file không phải chứng từ XNK hợp lệ (như báo giá, hợp đồng...): {', '.join(discarded_files)}")"""

pattern = re.compile(r'    if uploaded_files:\n        st.divider\(\)\n.*?progress_bar\.progress\(1\.0, text="✅ Hoàn tất!"\)', re.DOTALL)
content = pattern.sub(replacement, content)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated app.py")
