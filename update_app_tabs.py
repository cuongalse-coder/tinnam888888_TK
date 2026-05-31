import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

replacement = """def _render_multi_comparison(multi_result, docs):
    \"\"\"Render comparison result based on ECUS standard fields, split into tabs.\"\"\"
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

pattern = re.compile(r"def _render_multi_comparison\(multi_result, docs\):.*?key=\"export_ecus_csv\",\n        \)", re.DOTALL)
content = pattern.sub(replacement, content)

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)
print("Updated app.py with 3-tab _render_multi_comparison for ECUS")
