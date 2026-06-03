import re

with open("app.py", "r", encoding="utf-8") as f:
    app_content = f.read()

# Replace the TAB_GROUPS to end of tab rendering block

new_ui_logic = '''    TAB_GROUPS = {
        "Thông tin chung": {
            "Cơ bản": [
                "Số tờ khai", "Số tờ khai đầu tiên", "Số nhánh", "Số tờ khai tạm nhập tái xuất tương ứng", "Mã loại hình", "Mã phân loại hàng hóa", "Cơ quan Hải quan", "Mã bộ phận xử lý tờ khai", "Phân loại cá nhân/tổ chức", "Ngày đăng ký", "Ngày khai báo", "Thời hạn tái xuất/tái nhập", "Phương thức vận chuyển"
            ],
            "Đơn vị xuất nhập khẩu": [
                "Mã người xuất khẩu", "Người xuất khẩu", "Tên người xuất khẩu", "Mã bưu chính (Người XK)", "Địa chỉ người xuất khẩu", "Điện thoại (Người XK)", "Mã nước (Người XK)", "Mã người nhập khẩu", "Người nhập khẩu", "Tên người nhập khẩu", "Mã bưu chính (Người NK)", "Địa chỉ người nhập khẩu", "Điện thoại (Người NK)", "Mã nước (Người NK)", "Mã người ủy thác", "Tên người ủy thác", "Mã đại lý / NV Hải quan"
            ],
            "Vận đơn & Vận tải": [
                "Số Vận đơn (B/L)", "Số lượng kiện", "Loại kiện", "Tổng trọng lượng", "ĐVT Trọng lượng", "Địa điểm lưu kho", "Địa điểm nhận hàng cuối cùng (POD)", "Cảng dỡ hàng (POD)", "Địa điểm xếp hàng (POL)", "Cảng xếp hàng (POL)", "Tên tàu / Phương tiện VC", "Phương tiện vận chuyển dự kiến", "Ngày hàng đi dự kiến", "Số container", "Số seal", "Trọng lượng tịnh (N/W)"
            ]
        },
        "Thông tin chung 2": {
            "Hóa đơn thương mại": [
                "Giấy phép xuất nhập khẩu", "Số Hóa đơn (Invoice)", "Số hóa đơn", "Ngày phát hành hóa đơn", "Ngày Hóa đơn", "Số tiếp nhận hóa đơn điện tử", "Phương thức thanh toán", "Điều kiện giao hàng", "Mã đồng tiền hóa đơn", "Mã đồng tiền", "Tổng trị giá hóa đơn", "Trị giá hóa đơn", "Tổng trị giá tính thuế", "Mã đồng tiền tính thuế", "Tỷ giá tính thuế", "Tỷ giá"
            ],
            "Thuế & Phí": [
                "Mã xác định thời hạn nộp thuế", "Thuế", "Tổng tiền thuế xuất/nhập khẩu", "Tổng số tiền lệ phí", "Số tiền bảo lãnh", "Phí vận chuyển", "Phí bảo hiểm"
            ],
            "Chứng từ khác": [
                "Số quản lý nội bộ doanh nghiệp", "Tổng số trang", "Tổng số dòng hàng", "Số C/O", "Số L/C"
            ]
        },
        "Danh sách hàng": {
            "Chi tiết mặt hàng": [
                "Mã số hàng hóa (HS)", "Mô tả hàng hóa", "Xuất xứ", "Lượng (Quantity)", "ĐVT", "Đơn giá", "Trị giá", "Thuế mặt hàng"
            ]
        }
    }
    
    master_col_name = col_map[docs[0]['id']]
    compare_col_names = [col_map[doc['id']] for doc in docs[1:]] if len(docs) > 1 else []
    
    # Custom HTML/CSS Generator for Form UI
    def generate_form_html(section_name, keywords, df_section):
        html = f"""
        <div style="background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 20px; margin-bottom: 20px; border: 1px solid #e5e7eb;">
            <h4 style="color: #1e3a8a; border-bottom: 2px solid #3b82f6; padding-bottom: 8px; margin-top: 0; font-family: sans-serif;">{section_name}</h4>
            <div style="display: flex; flex-wrap: wrap; gap: 15px; font-family: sans-serif;">
        """
        for kw in keywords:
            row = df_section[df_section["Tiêu chí ECUS"] == kw]
            if row.empty: continue
            row = row.iloc[0]
            
            master_val = str(row.get(master_col_name, "—"))
            if master_val.strip() in ["", "nan", "None", "—"]:
                master_val = ""
                
            has_diff = row.get("Trạng thái") == "❌ Lệch"
            
            border_color = "#ef4444" if has_diff else "#d1d5db"
            bg_color = "#fef2f2" if has_diff else "#f9fafb"
            
            html += f"""
            <div style="flex: 1 1 220px; min-width: 220px; display: flex; flex-direction: column;">
                <label style="font-size: 13px; font-weight: 600; color: #4b5563; margin-bottom: 4px;">{kw}</label>
                <div style="border: 1px solid {border_color}; border-radius: 4px; padding: 8px 10px; background: {bg_color}; font-size: 14px; color: #111827; min-height: 38px; word-break: break-word;">
                    {master_val}
                </div>
            """
            
            if has_diff:
                html += f'<div style="font-size: 12px; color: #dc2626; margin-top: 6px; font-weight: 500;">'
                for cmp_col in compare_col_names:
                    cmp_val = str(row.get(cmp_col, "—"))
                    if cmp_val != master_val and cmp_val not in ["", "nan", "None", "—"]:
                        doc_short = cmp_col.split(" ")[-1]
                        html += f'<div><span style="font-weight:bold;">{doc_short}:</span> {cmp_val}</div>'
                html += f'</div>'
                
            html += "</div>"
            
        html += "</div></div>"
        return html

    def generate_item_cards_html(keywords, tab_df):
        html = ""
        # Find unique item indices
        import re
        items = {}
        for idx, row in tab_df.iterrows():
            label = row["Tiêu chí ECUS"]
            m = re.search(r'\[Hàng (\d+)\]', str(label))
            if m:
                item_idx = int(m.group(1))
                if item_idx not in items:
                    items[item_idx] = []
                # Clean keyword name
                clean_kw = re.sub(r'\s*\[Hàng \d+\]\s*', '', str(label))
                items[item_idx].append((clean_kw, row))
                
        for item_idx in sorted(items.keys()):
            html += f"""
            <div style="background: #f8fafc; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); padding: 15px; margin-bottom: 15px; border: 1px solid #cbd5e1; border-left: 4px solid #3b82f6;">
                <h5 style="color: #0f172a; margin-top: 0; margin-bottom: 12px; font-family: sans-serif; font-size: 15px;">📦 Mặt hàng thứ {item_idx}</h5>
                <div style="display: flex; flex-wrap: wrap; gap: 15px; font-family: sans-serif;">
            """
            
            for clean_kw, row in items[item_idx]:
                master_val = str(row.get(master_col_name, "—"))
                if master_val.strip() in ["", "nan", "None", "—"]:
                    master_val = ""
                    
                has_diff = row.get("Trạng thái") == "❌ Lệch"
                border_color = "#ef4444" if has_diff else "#d1d5db"
                bg_color = "#fef2f2" if has_diff else "#ffffff"
                
                # Assign width based on field type
                flex_basis = "300px" if "Mô tả" in clean_kw else "150px"
                
                html += f"""
                <div style="flex: 1 1 {flex_basis}; min-width: 150px; display: flex; flex-direction: column;">
                    <label style="font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 4px;">{clean_kw}</label>
                    <div style="border: 1px solid {border_color}; border-radius: 4px; padding: 6px 10px; background: {bg_color}; font-size: 13.5px; color: #1e293b; min-height: 34px; word-break: break-word;">
                        {master_val}
                    </div>
                """
                
                if has_diff:
                    html += f'<div style="font-size: 11px; color: #dc2626; margin-top: 4px;">'
                    for cmp_col in compare_col_names:
                        cmp_val = str(row.get(cmp_col, "—"))
                        if cmp_val != master_val and cmp_val not in ["", "nan", "None", "—"]:
                            doc_short = cmp_col.split(" ")[-1]
                            html += f'<div><b>{doc_short}:</b> {cmp_val}</div>'
                    html += f'</div>'
                    
                html += "</div>"
            html += "</div></div>"
        return html

    tabs = st.tabs(list(TAB_GROUPS.keys()))
    
    for idx, (tab_name, sections) in enumerate(TAB_GROUPS.items()):
        with tabs[idx]:
            for section_name, keywords in sections.items():
                if tab_name == "Danh sách hàng":
                    mask = df["Tiêu chí ECUS"].apply(lambda x: any(str(x).startswith(kw) for kw in keywords))
                    tab_df = df[mask].copy()
                    
                    if not tab_df.empty:
                        html_out = generate_item_cards_html(keywords, tab_df)
                        if html_out:
                            st.components.v1.html(html_out, scrolling=True, height=700)
                        else:
                            st.info("Chưa lấy được danh sách hàng hóa.")
                else:
                    tab_df = df[df["Tiêu chí ECUS"].isin(keywords)].copy()
                    if not tab_df.empty:
                        html_out = generate_form_html(section_name, keywords, tab_df)
                        st.markdown(html_out, unsafe_allow_html=True)
'''

start_idx = app_content.find("    TAB_GROUPS = {")
end_idx = app_content.find("    # Các trường không thuộc 3 nhóm trên", start_idx)

if start_idx != -1 and end_idx != -1:
    new_content = app_content[:start_idx] + new_ui_logic + "\n" + app_content[end_idx:]
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Patched successfully!")
else:
    print("Could not find delimiters")
