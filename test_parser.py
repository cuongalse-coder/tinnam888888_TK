import traceback
import sys
try:
    import utils.parser
    print("Parser imported successfully")
    res = utils.parser.detect_document_type("tờ khai hàng hóa xuất khẩu")
    print(res)
except Exception as e:
    traceback.print_exc()
