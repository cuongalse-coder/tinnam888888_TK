import streamlit as st
import io
import pandas as pd
import os
from utils.pdf_extractor import extract_text_from_pdf, parse_customs_declaration

st.set_page_config(
    page_title="Trích xuất Tờ Khai Hải Quan",
    page_icon="📄",
    layout="wide"
)

st.title("📄 Hệ Thống Trích Xuất Tờ Khai Hải Quan")
st.markdown("Hỗ trợ trích xuất tự động dữ liệu từ Tờ khai (nhận diện cả file scan).")

uploaded_files = st.file_uploader(
    "Tải lên các file PDF Tờ khai hải quan", 
    type=["pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    for uploaded_file in uploaded_files:
        st.write("---")
        st.subheader(f"📑 File: {uploaded_file.name}")
        
        with st.spinner(f"Đang xử lý và bóc tách dữ liệu từ {uploaded_file.name}..."):
            pdf_bytes = uploaded_file.read()
            
            # Trích xuất toàn bộ text & bảng
            result = extract_text_from_pdf(pdf_bytes)
            
            is_scanned_text = "Có (OCR)" if result['is_scanned'] else "Không (Text PDF gốc)"
            st.info(f"Loại file: **{is_scanned_text}** | Số trang: **{len(result['pages'])}**")
            
            # Phân tích các trường dữ liệu Tờ khai
            parsed_data = parse_customs_declaration(result['full_text'])
            
            col1, col2 = st.columns([1.5, 1])
            
            with col1:
                st.markdown("### 📊 Dữ liệu Tờ khai (Đã chuẩn hóa)")
                df_parsed = pd.DataFrame(list(parsed_data.items()), columns=['Trường Dữ Liệu', 'Giá Trị'])
                st.dataframe(df_parsed, use_container_width=True, height=450)
                
                # Nút tải xuống Excel
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df_parsed.to_excel(writer, index=False, sheet_name='ToKhai')
                
                st.download_button(
                    label="📥 Tải File Excel (Kết quả)",
                    data=excel_buffer.getvalue(),
                    file_name=f"ToKhai_{parsed_data.get('Số Tờ Khai', 'Unknown')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    key=f"dl_excel_{uploaded_file.name}"
                )
                
            with col2:
                st.markdown("### 📝 Nội dung thô đã đọc được")
                with st.expander("Bấm để xem toàn bộ nội dung text", expanded=False):
                    st.text(result['full_text'])
            
            # Nếu có bảng (với PDF text)
            if result['tables']:
                st.markdown("### 🗄️ Các bảng (Tables) tìm thấy")
                for i, table in enumerate(result['tables']):
                    if table:
                        with st.expander(f"Bảng {i+1}"):
                            try:
                                df_table = pd.DataFrame(table[1:], columns=table[0])
                                st.dataframe(df_table, use_container_width=True)
                            except Exception:
                                st.write(table)
