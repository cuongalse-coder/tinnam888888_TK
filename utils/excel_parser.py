import pandas as pd
import re
import unicodedata
from typing import Dict, Any, List

COLUMN_MAPPINGS = {
    'declarationNo': ['declaration no', 'so to khai', 'số tờ khai', 'to khai', 'tk', 'tờ khai'],
    'type': ['mã loại hình', 'loại hình', 'type'],
    'date': ['ngày đăng ký', 'ngày đk', 'date'],
    'itemCode': ['mã hàng', 'mã phần tử', 'item code', 'part no', 'part number'],
    'hsCode': ['mã hs', 'hs code', 'customs code', 'mã số hàng hóa'],
    'description': ['mo ta', 'mô tả', 'ten hang', 'ecus name', 'ten tieng viet', 'name ecus', 'tên tiếng việt', 'tên hàng', 'description'],
    'origin': ['xuat xu', 'xuất xứ', 'mã nước xuất xứ', 'ma nuoc xuat xu', 'c/o', 'origin'],
    'quantity': ['tong so luong', 'số lượng', "q'ty", 'lượng', 'qty', 'luong', 'tổng số lượng', 'so luong', 'quantity'],
    'uom': ['đvt', 'unit', 'đon vi tinh', 'uom', 'đơn vị tính'],
    'unitPrice': ['đon gia', 'đơn giá tính thuế', 'đơn giá', 'unit price', 'đơn giá hóa đơn', 'đon gia tinh thue', 'đon gia hoa đon'],
    'itemValue': ['amount', 'trị giá nguyên tệ', 'trị giá', 'tri gia', 'tri gia nguyen te', 'value', 'tổng trị giá', 'tong tri gia'],
    'itemTax': ['thue xnk', 'tiền thuế nhập khẩu', 'import tax', 'tien thue xnk', 'tiền thuế xnk', 'tien thue nhap khau', 'thuế xnk'],
    'itemTaxVAT': ['tiền thuế gtgc', 'thuế vat', 'tien thue vat', 'thue vat', 'tien thue gtgc', 'tiền thuế vat']
}

GLOBAL_FIELD_MAPPINGS = {'declarationNo': ['declaration no', 'so to khai', 'số tờ khai', 'to khai', 'tờ khai'], 'type': ['loại hình', 'loai hinh', 'ma loai hinh', 'mã loại hình', 'mã lh', 'ma lh'], 'customsBranch': ['customs', 'co quan', 'co quan hai quan', 'hai quan', 'hải quan', 'cơ quan hải quan', 'cơ quan'], 'registrationDate': ['ngay đang ky', 'ngay', 'reg date', 'ngay đk', 'ngày đk', 'ngày đăng ký', 'ngày'], 'exporterName': ['nguoi xuat khau', 'người xuất khẩu', 'exporter', 'người gửi', 'nguoi gui'], 'importerName': ['importer', 'nguoi nhap khau', 'người nhập khẩu', 'nguoi nhan', 'người nhận'], 'blNo': ['b/l', 'van đon', 'so van đon', 'bill', 'vận đơn', 'bl', 'số vận đơn'], 'vessel': ['tên tàu', 'tau', 'vessel', 'tàu', 'ten tau', 'phương tiện', 'phuong tien', 'chuyen', 'chuyến'], 'portOfLoading': ['pol', 'cảng đi', 'cang xep', 'cảng xếp', 'cang đi'], 'portOfDischarge': ['cang đen', 'cảng đến', 'cang do', 'pod', 'cảng dỡ'], 'grossWeight': ['trọng lượng cả bì', 'gross weight', 'g.w', 'trong luong ca bi', 'g/w'], 'netWeight': ['trọng lượng tịnh', 'n.w', 'trong luong tinh', 'n/w', 'net weight'], 'packages': ['pkgs', 'so luong kien', 'số lượng kiện', 'kien', 'packages', 'kiện'], 'invoiceNo': ['hóa đơn', 'invoice', 'hoa đon', 'so hoa đon', 'inv', 'số hóa đơn'], 'invoiceDate': ['inv date', 'ngay hoa đon', 'ngày hóa đơn'], 'invoiceValue': ['tri gia hoa đon', 'trị giá hóa đơn', 'inv value', 'tổng trị giá', 'tong tri gia'], 'incoterm': ['đieu kien giao hang', 'incoterm', 'điều kiện', 'điều kiện giao hàng', 'đieu kien'], 'currency': ['mã đồng tiền', 'ma đong tien', 'đong tien', 'mã đt', 'ma đt', 'currency', 'đồng tiền']}

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
            
        # create an unaccented row string for very robust matching
        row_str_raw = ' '.join(str(x).lower() for x in row.values)
        row_str = "".join([c for c in unicodedata.normalize('NFKD', row_str_raw) if not unicodedata.combining(c)])
        
        matches = 0
        
        # Check for typical headers (unaccented)
        if 'stt' in row_str or 'so tt' in row_str:
            matches += 1
        if 'hs' in row_str or 'customs code' in row_str:
            matches += 1
        if 'ten hang' in row_str or 'description' in row_str or 'ecus name' in row_str:
            matches += 1
        if 'so luong' in row_str or 'luong' in row_str or 'quantity' in row_str or 'qty' in row_str:
            matches += 1
        if 'ma hang' in row_str or 'item code' in row_str or 'part no' in row_str:
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
                df = pd.read_excel(file, engine=engine, header=None)
            except Exception:
                # Fallback for fake .xls files (e.g. exported from ECUS as HTML or TSV)
                file.seek(0)
                try:
                    dfs = pd.read_html(file)
                    new_dfs = []
                    for d in dfs:
                        cols_as_row = pd.DataFrame([d.columns.values], columns=d.columns)
                        d = pd.concat([cols_as_row, d], ignore_index=True)
                        d.columns = range(d.shape[1])
                        new_dfs.append(d)
                    df = pd.concat(new_dfs, ignore_index=True) if new_dfs else pd.DataFrame()
                except Exception:
                    file.seek(0)
                    try:
                        df = pd.read_csv(file, sep='\t', encoding='utf-16', names=range(30), on_bad_lines='skip')
                    except Exception:
                        file.seek(0)
                        df = pd.read_csv(file, sep='\t', encoding='utf-8', names=range(30), on_bad_lines='skip')
            
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
            for field in ['itemCode', 'hsCode', 'description', 'origin', 'quantity', 'uom', 'unitPrice', 'itemValue', 'itemTax', 'itemTaxVAT']:
                if field in mapped_cols:
                    val = row[mapped_cols[field]]
                    if pd.notna(val) and str(val).strip():
                        item[field] = str(val).strip()
                        has_data = True
                        
            # Only add if we found a description, hs code, or item code
            if has_data and ('description' in item or 'hsCode' in item or 'itemCode' in item):
                items.append(item)
                
        if items:
            result['items'] = items
            
        return result
        
    except Exception as e:
        # Ignore print to avoid UnicodeEncodeError on Windows cp1252 terminal
        import logging
        logging.error("Excel parse error: %s", str(e).encode('ascii', 'ignore').decode('ascii'))
        return {}
