import re

with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

# Replace the beginning of _render_multi_comparison
old_start = '''def _render_multi_comparison(multi_result, docs):
    """Render comparison result based on ECUS standard fields, split into tabs."""
    from utils.comparator import compare_ecus_centric
    
    st.divider()
    
    if not docs:
        st.info("Chưa có chứng từ nào để so sánh.")
        return

    ecus_output = compare_ecus_centric(docs)'''

new_start = '''def _render_multi_comparison(multi_result, docs):
    """Render comparison result based on ECUS standard fields, split into tabs."""
    from utils.comparator import compare_ecus_centric
    
    st.divider()
    
    if not docs:
        st.info("Chưa có chứng từ nào để so sánh.")
        return

    st.markdown("### 🔍 Màn hình Đối chiếu & Khai báo")
    
    doc_options = {doc['id']: f"[{doc.get('doc_type', 'Unknown')}] {doc['file_name']}" for doc in docs}
    
    # Tìm file có khả năng là Tờ khai nhất để làm mặc định
    default_idx = 0
    for idx, doc in enumerate(docs):
        if "customs_declaration" in doc.get('doc_type', '') or "excel" in doc['file_name'].lower() or "xls" in doc['file_name'].lower():
            default_idx = idx
            break

    master_doc_id = st.selectbox(
        "📝 Chọn chứng từ làm BẢN CHUẨN (Tờ khai nháp / Bản gốc để đối chiếu):",
        options=list(doc_options.keys()),
        format_func=lambda x: doc_options[x],
        index=default_idx
    )
    
    # Re-order docs so master_doc is first
    master_doc = next(d for d in docs if d['id'] == master_doc_id)
    other_docs = [d for d in docs if d['id'] != master_doc_id]
    docs = [master_doc] + other_docs

    ecus_output = compare_ecus_centric(docs)'''

app_content = app_content.replace(old_start, new_start)

# Now wait, since compare_ecus_centric hardcoded customs_declaration, if they upload an Excel file and it is NOT recognized as customs_declaration, the comparator might act weird.
# We should probably force the ecus_doc_type to match the master doc if possible, but that's a deeper change. For now, this UI change guarantees the Master is shown correctly in the Form.

with open("app.py", "w", encoding="utf-8") as f:
    f.write(app_content)
