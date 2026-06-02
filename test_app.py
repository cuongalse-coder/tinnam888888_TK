import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import utils.parser
import json

raw_text = """
BOOKING CONFIRMATION
Booking No: BKG123456
Shipper: ABC Company
Consignee: XYZ Company
Vessel: OOCL HONGKONG
POL: Haiphong
POD: Los Angeles
"""

res = utils.parser.parse_fields(raw_text, "booking")
print(json.dumps(res, ensure_ascii=False, indent=2))
