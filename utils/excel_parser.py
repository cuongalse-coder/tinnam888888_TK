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

GLOBAL_FIELD_MAPPINGS = {
    'declarationNo': ['số tờ khai', 'tờ khai', 'declaration no'],
    'type': ['mã loại hình', 'loại hình', 'mã lh'],
    'customsBranch': ['cơ quan hải quan', 'hải quan', 'cơ quan', 'customs'],
    'registrationDate': ['ngày đăng ký', 'ngày đk', 'reg date', 'ngày'],
    'exporterName': ['người xuất khẩu', 'exporter', 'người gửi'],
    'importerName': ['người nhập khẩu', 'importer', 'người nhận'],
    'blNo': ['số vận đơn', 'vận đơn', 'b/l', 'bill', 'bl'],
    'vessel': ['tên tàu', 'phương tiện', 'vessel', 'tàu', 'chuyến'],
    'portOfLoading': ['cảng xếp', 'pol', 'cảng đi'],
    'portOfDischarge': ['cảng dỡ', 'pod', 'cảng đến'],
    'grossWeight': ['trọng lượng cả bì', 'gross weight', 'g.w', 'g/w'],
    'netWeight': ['trọng lượng tịnh', 'net weight', 'n.w', 'n/w'],
    'packages': ['số lượng kiện', 'kiện', 'packages', 'pkgs'],
    'invoiceNo': ['số hóa đơn', 'hóa đơn', 'invoice', 'inv'],
    'invoiceDate': ['ngày hóa đơn', 'inv date'],
    'invoiceValue': ['trị giá hóa đơn', 'inv value', 'tổng trị giá'],
    'incoterm': ['điều kiện giao hàng', 'điều kiện', 'incoterm'],
    'currency': ['mã đồng tiền', 'đồng tiền', 'currency', 'mã đt'],
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
            try:
                df = pd.read_excel(file, engine=engine)
            except Exception:
                # Fallback for fake .xls files (e.g. exported from ECUS as HTML or TSV)
                file.seek(0)
                try:
                    dfs = pd.read_html(file)
                    df = dfs[0] if dfs else pd.DataFrame()
                except Exception:
                    file.seek(0)
                    try:
                        df = pd.read_csv(file, sep='\t', encoding='utf-16')
                    except Exception:
                        file.seek(0)
                        df = pd.read_csv(file, sep='\t', encoding='utf-8')
            
        if df.empty:
            return {}
            
        header_idx = find_header_row(df)
        
        result = {}
        
        # --- Extract Global Fields from the header section ---
        for i in range(header_idx):
            row_vals = [str(x) for x in df.iloc[i].values if pd.notna(x)]
            for j, cell_val in enumerate(row_vals):
                lower_cell = cell_val.lower().strip()
                for field_key, keywords in GLOBAL_FIELD_MAPPINGS.items():
                    if field_key in result:
                        continue
                    for kw in keywords:
                        if kw in lower_cell:
                            # If it has a colon inside
                            if ':' in cell_val:
                                val = cell_val.split(':', 1)[1].strip()
                                if val and val not in ['-', '/']:
                                    result[field_key] = val
                                    break
                            # Otherwise, take the next cell
                            elif j + 1 < len(row_vals):
                                val = str(row_vals[j+1]).strip()
                                # Ensure next cell isn't another header (no colon and not a keyword)
                                if val and val not in ['-', '/'] and ':' not in val:
                                    result[field_key] = val
                                    break
                                    
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
        # Ignore print to avoid UnicodeEncodeError on Windows cp1252 terminal
        import logging
        logging.error("Excel parse error: %s", str(e).encode('ascii', 'ignore').decode('ascii'))
        return {}
