"""เติมจุดเด่นและโปรโมชันให้อัตโนมัติจากข้อมูลที่ดึงมา (ไม่ใช้ AI ไม่เสียเงิน)

หลักการ: ใช้เฉพาะข้อเท็จจริงที่อยู่ในข้อมูลสินค้าจริง ได้แก่ ส่วนลดที่คำนวณจากราคา, คะแนนรีวิวที่หน้าเว็บให้มา,
คำบอกสเปค/คุณสมบัติที่ "ปรากฏอยู่ในชื่อสินค้าเอง" ไม่แต่งคุณสมบัติที่ไม่มีในข้อมูล
ถ้าไม่มีข้อมูลพอ จะคืนค่าว่าง (ปล่อยให้ผู้ใช้กรอกเองหรือใช้ AI)
"""
import re

import captions as cp

# คำคุณสมบัติที่หยิบมาได้เมื่อ "อยู่ในชื่อสินค้า" (ตัวพิมพ์เล็กสำหรับภาษาอังกฤษ)
FEATURE_WORDS = [
    ("กันน้ำ", "กันน้ำ"), ("waterproof", "กันน้ำ"), ("กันฝน", "กันฝน"), ("กันลื่น", "กันลื่น"),
    ("พับได้", "พับได้"), ("foldable", "พับได้"), ("พกพา", "พกพาสะดวก"), ("portable", "พกพาสะดวก"),
    ("ไร้สาย", "ไร้สาย"), ("wireless", "ไร้สาย"), ("ชาร์จได้", "ชาร์จได้"), ("rechargeable", "ชาร์จได้"),
    ("usb", "ใช้ผ่าน USB"), ("ทนทาน", "ทนทาน"), ("น้ำหนักเบา", "น้ำหนักเบา"), ("ระบายอากาศ", "ระบายอากาศ"),
    ("สแตนเลส", "สแตนเลส"), ("ซิลิโคน", "ซิลิโคน"), ("ผ้าฝ้าย", "ผ้าฝ้าย"), ("อเนกประสงค์", "ใช้ได้หลายแบบ"),
    ("ประหยัดไฟ", "ประหยัดไฟ"), ("ล้างได้", "ล้างทำความสะอาดได้"), ("ซักได้", "ซักได้"),
    ("ปรับระดับ", "ปรับระดับได้"), ("แพ็คคู่", "แพ็คคู่"), ("แพ็ค 2", "แพ็คคู่"), ("เซ็ต", "ขายเป็นเซ็ต"),
    ("ชุดสุดคุ้ม", "ชุดสุดคุ้ม"), ("พร้อมส่ง", "พร้อมส่ง"),
]
SPEC_RE = re.compile(
    r"(\d+(?:[.,]\d+)?)\s*(ml|มล\.?|ลิตร|l|กรัม|g|kg|กก\.?|cm|ซม\.?|mm|มม\.?|w|วัตต์|v|mah|gb|tb|"
    r"ชิ้น|แพ็ค|ชุด|คู่|ซอง|ขวด|กล่อง|ใบ|เมตร|m|นิ้ว|inch)(?![a-zA-Zก-ฮ])", re.I)
SPEC_LABEL = {"มล": "มล.", "มล.": "มล.", "กก": "กก.", "กก.": "กก.", "ซม": "ซม.", "ซม.": "ซม.", "มม": "มม.", "มม.": "มม."}


def _plain(x):
    s = str(x or "").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


def promo_text(price, orig_price, discount):
    """'ลด 40% จาก 500 เหลือ 300 บาท' (ต้องมีส่วนลดอย่างน้อย 5% และมีตัวเลขราคาปกติ > ราคาขาย)"""
    try:
        d = int(discount or 0)
    except (TypeError, ValueError):
        d = 0
    if d < 5:
        return ""
    lo, hi = _plain(orig_price), _plain(price)
    if lo and hi and lo > hi:
        return f"ลด {d}% จาก {cp.fmt_price(orig_price)} เหลือ {cp.fmt_price(price)} บาท"
    return f"ลด {d}%"


def specs_from_title(title, limit=2):
    out = []
    for m in SPEC_RE.finditer(title or ""):
        num, unit = m.group(1), m.group(2)
        unit = SPEC_LABEL.get(unit.lower(), unit)
        item = f"{num} {unit}"
        if item not in out:
            out.append(item)
        if len(out) >= limit:
            break
    return out


def features_from_title(title, limit=3):
    low = (title or "").lower()
    out = []
    for key, label in FEATURE_WORDS:
        if key in low and label not in out:
            out.append(label)
        if len(out) >= limit:
            break
    return out


def point_text(info):
    """รวมจุดเด่น: คุณสมบัติจากชื่อ + สเปค + คะแนนรีวิว (ถ้ามีและดี) ตัดคำเสี่ยงโฆษณาเกินจริงทิ้ง"""
    title = (info or {}).get("title", "")
    parts = features_from_title(title, 2) + specs_from_title(title, 1)
    try:
        rating = float(info.get("rating") or 0)
        reviews = int(info.get("reviews") or 0)
    except (TypeError, ValueError):
        rating, reviews = 0.0, 0
    if rating >= 4.0 and reviews >= 10:
        parts.append(f"คะแนนรีวิว {rating:g}/5 จาก {reviews:,} รีวิว")
    parts = [p for p in parts if not cp.find_risky(p) and not cp.clean_profanity(p)[1]]
    text = " · ".join(parts[:4])
    return text[:100].rstrip(" ·")


def suggest(info):
    """คืน (จุดเด่น, โปรโมชัน) จากข้อมูลสินค้าที่ดึงมา (ว่างได้ ผู้ใช้แก้เองได้)"""
    info = info or {}
    return point_text(info), promo_text(info.get("price"), info.get("orig_price"), info.get("discount"))
