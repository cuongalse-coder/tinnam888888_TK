import re

with open("app.py", "r", encoding="utf-8") as f:
    content = f.read()

new_tab_groups = '''    TAB_GROUPS = {
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
                "Mã số hàng hóa (HS)", "Mô tả hàng hóa", "Xuất xứ", "Lượng (Quantity)", "ĐVT", "Đơn giá", "Trị giá"
            ]
        }
    }
    
    tabs = st.tabs(list(TAB_GROUPS.keys()))
    
    for idx, (tab_name, sections) in enumerate(TAB_GROUPS.items()):
        with tabs[idx]:
            for section_name, keywords in sections.items():
                if tab_name == "Danh sách hàng":
                    # Lọc bằng .startswith để lấy được "[Hàng 1]", "[Hàng 2]"...
                    mask = df["Tiêu chí ECUS"].apply(lambda x: any(str(x).startswith(kw) for kw in keywords))
                    tab_df = df[mask].copy()
                    
                    if not tab_df.empty:
                        # Extract item index for sorting
                        def get_sort_key(label):
                            import re
                            m = re.search(r'\[Hàng (\d+)\]', str(label))
                            item_idx = int(m.group(1)) if m else 0
                            
                            # Find which keyword it matches to maintain field order
                            field_order = 99
                            for i, kw in enumerate(keywords):
                                if str(label).startswith(kw):
                                    field_order = i
                                    break
                            return (item_idx, field_order)
                            
                        tab_df["_sort_key"] = tab_df["Tiêu chí ECUS"].apply(get_sort_key)
                        tab_df = tab_df.sort_values("_sort_key").drop(columns=["_sort_key"])
                        
                        st.markdown(f"**{section_name}**")
                        
                        # Cải thiện UI: màu sắc và size
                        styled_df = tab_df.style.apply(highlight_match, axis=1)\\
                                          .set_properties(**{
                                              'font-size': '16px',
                                              'padding': '12px',
                                          })
                        
                        # Thêm màu nền sọc (nth-child) bằng CSS thông qua set_table_styles
                        styled_df = styled_df.set_table_styles([
                            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f9fafb')]},
                            {'selector': 'th', 'props': [('background-color', '#1e3a8a'), ('color', 'white'), ('font-size', '16px')]},
                            {'selector': 'td', 'props': [('border-bottom', '1px solid #e5e7eb')]}
                        ])
                        
                        st.dataframe(styled_df, use_container_width=True, hide_index=True, height=min(600, len(tab_df)*45 + 40))
                else:
                    tab_df = df[df["Tiêu chí ECUS"].isin(keywords)].copy()
                    if not tab_df.empty:
                        tab_df["Tiêu chí ECUS"] = pd.Categorical(tab_df["Tiêu chí ECUS"], categories=keywords, ordered=True)
                        tab_df = tab_df.sort_values("Tiêu chí ECUS")
                        st.markdown(f"**{section_name}**")
                        styled_df = tab_df.style.apply(highlight_match, axis=1)\\
                                          .set_properties(**{
                                              'font-size': '16px',
                                              'padding': '12px'
                                          })
                        
                        styled_df = styled_df.set_table_styles([
                            {'selector': 'tr:nth-child(even)', 'props': [('background-color', '#f9fafb')]},
                            {'selector': 'th', 'props': [('background-color', '#1e3a8a'), ('color', 'white'), ('font-size', '16px')]},
                            {'selector': 'td', 'props': [('border-bottom', '1px solid #e5e7eb')]}
                        ])
                        
                        st.dataframe(styled_df, use_container_width=True, hide_index=True)
'''

start_idx = content.find("    TAB_GROUPS = {")
end_idx = content.find("    # Các trường không thuộc 3 nhóm trên", start_idx)

if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + new_tab_groups + "\n" + content[end_idx:]
    with open("app.py", "w", encoding="utf-8") as f:
        f.write(content)
else:
    print("Could not find delimiters")
