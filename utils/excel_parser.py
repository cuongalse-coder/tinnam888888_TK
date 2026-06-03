import pandas as pd
import re
from typing import Dict, Any, List

# Các từ khóa thường dùng trong các định dạng Excel khác nhau (Báo cáo chi tiết, file mẫu, file nội bộ)
COLUMN_MAPPINGS = {
    'declarationNo': ['số tk', 'số tờ khai', 'tk', 'declaration no'],
    'type': ['mã loại hình', 'loại hình', 'type'],
    'date': ['ngày đk', 'ngày đăng ký', 'date'],
    
    # Item level
    'hsCode': ['mã hs', 'hs code', 'customs code', 'mã số hàng hóa'],
    'description': ['tên hàng', 'mô tả', 'description', 'ecus name', 'name ecus', 'tên tiếng việt'],
    'origin': ['xuất xứ', 'origin', 'c/o', 'mã nước xuất xứ'],
    'quantity': ['lượng', 'số lượng', 'tổng số lượng', 'q\'ty', 'quantity', 'qty'],
    'uom': ['đvt', 'đơn vị tính', 'unit', 'uom'],
    'unitPrice': ['đơn giá', 'unit price', 'đơn giá hóa đơn', 'đơn giá tính thuế'],
    'itemValue': ['trị giá', 'tổng trị giá', 'trị giá nguyên tệ', 'amount', 'value'],
    'itemTax': ['tiền thuế xnk', 'thuế xnk', 'tiền thuế nhập khẩu', 'import tax'],
    'itemTaxVAT': ['tiền thuế vat', 'thuế vat', 'tiền thuế gtgc']
}

def clean_column_name(col_name) -> str:
    if not isinstance(col_name, str):
        return ""
    # Normalize to lowercase and remove extra spaces
    return " ".join(col_name.lower().strip().split())

def find_header_row(df: pd.DataFrame) -> int:
    """Scan rows to find the most likely header row"""
    best_row_idx = -1
    max_matches = 0
    
    # Check first 30 rows
    for i, row in df.iterrows():
        if i > 30:
            break
            
        row_str = ' '.join(str(x).lower() for x in row.values)
        matches = 0
        
        # Check for typical headers
        if 'stt' in row_str or 'số tt' in row_str:
            matches += 1
        if 'hs' in row_str or 'customs code' in row_str:
            matches += 1
        if 'tên hàng' in row_str or 'description' in row_str or 'ecus name' in row_str:
            matches += 1
        if 'số lượng' in row_str or 'quantity' in row_str or 'q\'ty' in row_str:
            matches += 1
            
        if matches > max_matches:
            max_matches = matches
            best_row_idx = i
            
    # If we found a row with at least 2 key indicators, it's likely the header
    if max_matches >= 2:
        return best_row_idx
    return 0 # Fallback to first row

def parse_excel_fields_directly(file) -> Dict[str, Any]:
    """Parse Excel file directly into standard JSON format without AI"""
    try:
        # Determine engine
        ext = file.name.lower()
        if ext.endswith('.csv'):
            df = pd.read_csv(file)
        else:
            engine = "openpyxl" if ext.endswith('.xlsx') or ext.endswith('.xlsm') else "xlrd"
            df = pd.read_excel(file, engine=engine)
            
        if df.empty:
            return {}
            
        header_idx = find_header_row(df)
        
        # Set the columns and drop preceding rows
        df.columns = [clean_column_name(col) for col in df.iloc[header_idx].values]
        df = df.iloc[header_idx+1:].reset_index(drop=True)
        
        # Map columns
        mapped_cols = {}
        for std_field, keywords in COLUMN_MAPPINGS.items():
            for col in df.columns:
                if any(kw == col for kw in keywords):
                    mapped_cols[std_field] = col
                    break
                # Partial match fallback if no exact match
                if std_field not in mapped_cols:
                    if any(kw in col for kw in keywords):
                        mapped_cols[std_field] = col
                        
        result = {}
        
        # Extract document-level info from the first row that has data
        for field in ['declarationNo', 'type', 'date']:
            if field in mapped_cols:
                # Find first non-null value
                valid_vals = df[mapped_cols[field]].dropna()
                if not valid_vals.empty:
                    result[field] = str(valid_vals.iloc[0]).strip()
                    
        # Extract items
        items = []
        for idx, row in df.iterrows():
            item = {}
            has_data = False
            for field in ['hsCode', 'description', 'origin', 'quantity', 'uom', 'unitPrice', 'itemValue', 'itemTax', 'itemTaxVAT']:
                if field in mapped_cols:
                    val = row[mapped_cols[field]]
                    if pd.notna(val) and str(val).strip():
                        item[field] = str(val).strip()
                        has_data = True
                        
            # Only add if we found a description or hs code
            if has_data and ('description' in item or 'hsCode' in item):
                items.append(item)
                
        if items:
            result['items'] = items
            
        return result
        
    except Exception as e:
        print(f"Lỗi đọc Excel trực tiếp: {e}")
        return {}
