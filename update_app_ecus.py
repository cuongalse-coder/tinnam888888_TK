import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """def _render_multi_comparison(multi_result, docs):
    \"\"\"Render comparison result based on ECUS standard fields.\"\"\"
    from utils.comparator import compare_ecus_centric
    
    st.divider()
    st.subheader("📊 Bảng Đối Chiếu Chuẩn ECUS VNACCS")
    st.markdown("Bảng tổng hợp đối chiếu tất cả các chứng từ dựa trên bộ tiêu chí chuẩn của Tờ khai Hải quan (ECUS).")

    if not docs:
        st.info("Chưa có chứng từ nào để so sánh.")
        return

    ecus_results = compare_ecus_centric(docs)
    
    if not ecus_results:
        st.warning("Không thể tạo bảng đối chiếu ECUS. Vui lòng kiểm tra lại chứng từ tải lên.")
        return

    def highlight_match(row):
        val = row.get('Trạng thái', '')
        if isinstance(val, pd.Series):
            val = val.iloc[0] if not val.empty else ''
        val = str(val)
        if '✅' in val:
            return ['background-color: rgba(16,185,129,0.08)'] * len(row)
        else:
            return ['background-color: rgba(239,68,68,0.08)'] * len(row)

    # Đổi tên cột từ doc_id sang file_name
    display_data = []
    
    # Tạo map doc_id -> column_name (bao gồm icon để dễ nhìn)
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
    styled_df = df.style.apply(highlight_match, axis=1)
    
    st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Export ECUS comparison
    col1, col2 = st.columns(2)
    with col1:
        try:
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='ECUS_Compare')
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
"""

# Replace the existing _render_multi_comparison function
pattern = re.compile(r"def _render_multi_comparison\(multi_result, docs\):.*?st\.dataframe\(styled_df, use_container_width=True, hide_index=True\)", re.DOTALL)
content = pattern.sub(replacement, content)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated app.py with _render_multi_comparison for ECUS")
