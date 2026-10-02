"""ระบบสร้างแคปชั่นแบบฉลาด: ตรวจหมวดสินค้า / กรองคำหยาบ / ตรวจก่อนโพสต์
ไฟล์นี้ไม่พึ่ง streamlit จึงเทสต์แยกได้
"""
import random
import re

# ---------------------------------------------------------------
# กรองคำไม่สุภาพ
# ---------------------------------------------------------------
# (คำ, ข้อยกเว้นที่ตามหลังแล้วเป็นคำปกติ, เป็นคำสั้นที่ต้องไม่มีพยัญชนะนำหน้า)
PROFANITY = [
    ("เหี้ย", "ม", False), ("ห่า", "งวน", True), ("ควย", "", False), ("สัส", "ดี", False),
    ("เชี่ย", "วน", False), ("แม่ง", "า", False), ("ฉิบหาย", "", False), ("ชิบหาย", "", False),
    ("ระยำ", "", False), ("ตอแหล", "", False), ("ส้นตีน", "", False), ("เย็ด", "", False),
    ("หี", "บ", True), ("มึง", "", False), ("กู", "รลเ", True), ("โคตร", "เวต", False),
]


def _pattern(word, exc, short):
    pre = r"(?<![ก-ฮเแโใไ])" if short else ""
    post = f"(?![{exc}])" if exc else ""
    return pre + re.escape(word) + post


_PROF_RE = re.compile(
    "|".join(_pattern(w, e, s) for w, e, s in sorted(PROFANITY, key=lambda x: -len(x[0])))
)


def clean_profanity(text):
    """คืน (ข้อความที่ตัดคำหยาบออกแล้ว, รายการคำที่เจอ)"""
    if not text:
        return "", []
    found = _PROF_RE.findall(text)
    cleaned = _PROF_RE.sub("", text)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned, found


# ---------------------------------------------------------------
# หมวดสินค้า
# ---------------------------------------------------------------
CATEGORIES = {
    "food": {
        "label": "🍜 อาหาร / ขนม / เครื่องดื่ม",
        "emoji": "😋",
        "keywords": [
            "ขนม", "อาหาร", "กาแฟ", "ชาเขียว", "ชานม", "ชาไข่มุก", "เครื่องดื่ม", "น้ำผลไม้",
            "น้ำอัดลม", "น้ำพริก", "น้ำปลา", "ซอส", "ข้าว", "เส้นก๋วยเตี๋ยว", "เส้นหมี่", "เส้นบุก",
            "บะหมี่", "มาม่า", "สาหร่าย", "ช็อกโกแลต", "ช็อคโกแลต", "คุกกี้", "เยลลี่", "ลูกอม",
            "ถั่ว", "มันฝรั่ง", "หมูกรอบ", "หมูหยอง", "ปลาแห้ง", "ปลาทู", "ไก่ทอด", "ขนมปัง",
            "เค้ก", "อบกรอบ", "ปรุงรส", "โปรตีนบาร์", "โกโก้", "ผงชงดื่ม", "ไอศกรีม", "ซีเรียล",
            "ขนมขบเคี้ยว", "วุ้น", "snack", "coffee", "cookie", "chocolate", "noodle",
        ],
        "lines": [
            "เหมาะกินเล่น ซื้อติดบ้านไว้ หรือเป็นของฝากก็ได้",
            "ใครชอบของกินแนวนี้ น่าลองเลย",
            "ตัวช่วยเพิ่มความอร่อยให้วันนี้",
        ],
        "exp": "ชิมแล้วถูกปากสำหรับเรา",
        "note": "แนะนำเช็กส่วนผสมและวันหมดอายุก่อนสั่งนะ",
        "tags": ["#ของกิน", "#ขนมอร่อย", "#ป้ายยาของกิน", "#ของกินเล่น"],
    },
    "beauty": {
        "label": "💄 บิวตี้ / สกินแคร์",
        "emoji": "✨",
        "keywords": [
            "ครีม", "เซรั่ม", "โฟมล้างหน้า", "กันแดด", "ลิปสติก", "ลิปทินท์", "ลิปมัน", "ลิปบาล์ม",
            "ลิปกลอส", "แป้งพัฟ", "แป้งฝุ่น", "แป้งรองพื้น", "มาสคารา", "อายไลเนอร์", "สกินแคร์",
            "แชมพู", "ครีมนวด", "สบู่", "ทรีทเมนท์", "น้ำหอม", "มาส์ก", "รองพื้น", "คุชชั่น",
            "โลชั่น", "โทนเนอร์", "เมคอัพ", "บำรุงผิว", "serum", "sunscreen", "lipstick",
            "cleanser", "shampoo", "perfume", "makeup",
        ],
        "lines": [
            "เหมาะกับคนที่ชอบดูแลตัวเองและอยากลองของใหม่ๆ",
            "ใครกำลังมองหาตัวช่วยสายบิวตี้ ลองดูตัวนี้ได้",
        ],
        "exp": "ลองใช้แล้วชอบสำหรับเรา",
        "note": "ผลลัพธ์แต่ละคนอาจไม่เหมือนกัน ดูส่วนผสมก่อนใช้ทุกครั้งนะ",
        "tags": ["#บิวตี้", "#สกินแคร์", "#ป้ายยาบิวตี้", "#ดูแลผิว"],
    },
    "supplement": {
        "label": "💊 อาหารเสริม / วิตามิน",
        "emoji": "🌿",
        "keywords": [
            "วิตามิน", "อาหารเสริม", "คอลลาเจน", "โปรตีน", "เวย์", "ไฟเบอร์", "แคปซูล", "ซอฟท์เจล",
            "น้ำมันปลา", "กลูต้า", "โพรไบโอติก", "vitamin", "supplement", "collagen", "whey",
            "probiotic",
        ],
        "lines": [
            "เหมาะกับคนที่ใส่ใจสุขภาพและอยากหาตัวช่วยเสริมในแต่ละวัน",
        ],
        "exp": "ลองทานแล้วสบายใจสำหรับเรา",
        "note": "ไม่ใช่ยา ผลลัพธ์แต่ละคนไม่เหมือนกัน ควรอ่านฉลาก และปรึกษาแพทย์หากมีโรคประจำตัว",
        "tags": ["#อาหารเสริม", "#สุขภาพดี", "#วิตามิน", "#ดูแลสุขภาพ"],
    },
    "fashion": {
        "label": "👗 แฟชั่น / เครื่องแต่งกาย",
        "emoji": "👗",
        "keywords": [
            "เสื้อ", "กางเกง", "กระโปรง", "เดรส", "ชุดนอน", "ชุด", "รองเท้า", "กระเป๋า", "แว่นตา",
            "นาฬิกา", "หมวก", "ถุงเท้า", "เข็มขัด", "ผ้าพันคอ", "เครื่องประดับ", "สร้อย", "ต่างหู",
            "แหวน", "dress", "shirt", "jeans", "sneaker",
        ],
        "lines": [
            "ใครกำลังมองหาไอเทมใหม่ไว้เติมตู้ ตัวนี้น่าสนใจ",
            "ลองดูรูปจริงจากผู้ซื้อประกอบการตัดสินใจได้เลย",
        ],
        "exp": "ลองใส่แล้วชอบสำหรับเรา",
        "note": "เช็กตารางไซซ์และรูปจริงจากผู้ซื้อก่อนสั่งนะ",
        "tags": ["#แฟชั่น", "#ไอเทมเด็ด", "#แต่งตัว", "#ป้ายยาแฟชั่น"],
    },
    "electronics": {
        "label": "🎧 ไอที / อุปกรณ์อิเล็กทรอนิกส์",
        "emoji": "🔌",
        "keywords": [
            "หูฟัง", "สายชาร์จ", "ที่ชาร์จ", "พาวเวอร์แบงค์", "โทรศัพท์", "เคสมือถือ", "ลำโพง",
            "บลูทูธ", "กล้อง", "คีย์บอร์ด", "เมาส์", "หน้าจอ", "แท็บเล็ต", "สมาร์ทวอทช์", "ไมโครโฟน",
            "ไมค์", "ไฟฉาย", "เราเตอร์", "แฟลชไดรฟ์", "การ์ดความจำ", "usb", "wireless",
            "bluetooth", "charger", "earbuds", "headphone",
        ],
        "lines": [
            "ใครกำลังมองหาอุปกรณ์เสริมไว้ใช้งานทุกวัน ตัวนี้น่าลอง",
            "เหมาะกับสายไอทีที่ชอบของใช้คู่ใจ",
        ],
        "exp": "ลองใช้แล้วพอใจสำหรับเรา",
        "note": "เช็กรุ่นที่รองรับกับอุปกรณ์ของคุณก่อนสั่งนะ",
        "tags": ["#ไอที", "#แกดเจ็ต", "#อุปกรณ์เสริม", "#ป้ายยาแกดเจ็ต"],
    },
    "home": {
        "label": "🏠 ของใช้ในบ้าน / เครื่องใช้ไฟฟ้า",
        "emoji": "🏠",
        "keywords": [
            "หม้อ", "กระทะ", "ชั้นวาง", "ผ้าปูที่นอน", "หมอน", "ผ้านวม", "ไม้ถู", "ถังขยะ",
            "กล่องเก็บ", "ตะกร้า", "พัดลม", "หม้อทอดไร้น้ำมัน", "เครื่องดูดฝุ่น", "เครื่องซักผ้า",
            "เครื่องฟอกอากาศ", "เครื่องปั่น", "กาต้มน้ำ", "ผงซักฟอก", "น้ำยาล้างจาน",
            "น้ำยาปรับผ้านุ่ม", "ผ้าขนหนู", "แก้วน้ำ", "กระติกน้ำ", "ที่นอน", "โคมไฟ", "พรม",
            "ไม้แขวน", "โต๊ะ", "เก้าอี้", "มีด", "ขวด",
        ],
        "lines": [
            "ตัวช่วยเพิ่มความสะดวกให้บ้านและงานประจำวัน",
            "ใครกำลังจัดบ้านหรือหาของใช้เข้าบ้าน ตัวนี้น่าสนใจ",
        ],
        "exp": "ใช้แล้วสะดวกดีสำหรับเรา",
        "note": "เช็กขนาดและวัสดุก่อนสั่งให้เหมาะกับพื้นที่ของคุณนะ",
        "tags": ["#ของใช้ในบ้าน", "#จัดบ้าน", "#ป้ายยาของใช้", "#ไอเทมคู่บ้าน"],
    },
    "baby_pet": {
        "label": "🍼 แม่และเด็ก / สัตว์เลี้ยง",
        "emoji": "🐾",
        "keywords": [
            "ผ้าอ้อม", "นมผง", "ของเล่น", "ทารก", "เด็กอ่อน", "เด็ก", "ลูกน้อย", "อาหารสุนัข",
            "อาหารแมว", "อาหารสัตว์", "ทรายแมว", "สุนัข", "น้องหมา", "น้องแมว", "แมว", "หมา",
            "สัตว์เลี้ยง", "baby",
        ],
        "lines": [
            "ใครมีเด็กหรือสัตว์เลี้ยงที่บ้าน ลองดูตัวนี้ได้",
        ],
        "exp": "ใช้แล้วสบายใจสำหรับเรา",
        "note": "เลือกให้เหมาะกับวัยหรือสายพันธุ์ และอ่านรายละเอียดความปลอดภัยก่อนสั่งนะ",
        "tags": ["#แม่และเด็ก", "#สัตว์เลี้ยง", "#ของใช้เด็ก", "#ป้ายยาแม่และเด็ก"],
    },
    "auto_tools": {
        "label": "🔧 รถยนต์ / เครื่องมือช่าง",
        "emoji": "🔧",
        "keywords": [
            "สว่าน", "ประแจ", "เครื่องมือช่าง", "ชุดเครื่องมือ", "น้ำมันเครื่อง", "ยางรถ",
            "มอเตอร์ไซค์", "รถยนต์", "กล้องหน้ารถ", "ที่ปัดน้ำฝน", "ผ้าคลุมรถ", "หมวกกันน็อค",
            "ไขควง", "คีม", "ปืนกาว",
        ],
        "lines": [
            "เหมาะกับคนที่ชอบดูแลรถหรือลงมือซ่อมเองที่บ้าน",
        ],
        "exp": "ใช้แล้วคุ้มสำหรับเรา",
        "note": "เช็กรุ่นรถหรือสเปกให้ตรงก่อนสั่งนะ",
        "tags": ["#รถยนต์", "#เครื่องมือช่าง", "#DIY", "#ป้ายยาเครื่องมือ"],
    },
    "general": {
        "label": "🛍️ ทั่วไป",
        "emoji": "🛍️",
        "keywords": [],
        "lines": [
            "ใครกำลังมองหาของแนวนี้ ลองดูรายละเอียดได้",
            "ตัวเลือกน่าสนใจสำหรับคนที่อยากได้ของคุ้มๆ",
        ],
        "exp": "ลองแล้วพอใจสำหรับเรา",
        "note": "",
        "tags": ["#ของดีบอกต่อ", "#ช้อปออนไลน์", "#พิกัดช้อป"],
    },
}

AUTO_LABEL = "🤖 ตรวจอัตโนมัติจากชื่อสินค้า"


def _match(kw, text):
    if kw.isascii():
        return re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", text) is not None
    return kw in text


def detect_category(text):
    """ให้คะแนนตามความยาวคำที่เจอ (คำยาวเฉพาะกว่าชนะ) คืน key ของหมวด"""
    text = (text or "").lower()
    best, best_score = "general", 0
    for key, cat in CATEGORIES.items():
        score = sum(len(kw) for kw in cat["keywords"] if _match(kw, text))
        if score > best_score:
            best, best_score = key, score
    return best


def label_to_key(label):
    for k, c in CATEGORIES.items():
        if c["label"] == label:
            return k
    return None


# ---------------------------------------------------------------
# ตัวช่วยจัดข้อมูล
# ---------------------------------------------------------------
def short_name(name, limit=60):
    """ตัดวงเล็บโปรโมชั่น และย่อชื่อยาวๆ ให้อ่านง่าย"""
    if not name:
        return ""
    name = re.sub(r"[【\[\(（][^】\]\)）]*[】\]\)）]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) <= limit:
        return name
    out = ""
    for part in name.split(" "):
        if len(out) + len(part) + 1 > limit:
            break
        out = f"{out} {part}".strip()
    return out or name[:limit].rstrip() + "…"


def _fmt_num(s):
    v = float(s)
    return f"{int(v):,}" if v == int(v) else f"{v:,.2f}"


def fmt_price(text):
    """'1300' -> '1,300' / '199.00' -> '199' / '199-299' -> '199-299' ไม่ใช่ตัวเลข -> ''"""
    s = re.sub(r"(บาท|฿|,|\s)", "", str(text or ""))
    if re.fullmatch(r"\d+(\.\d+)?", s):
        return _fmt_num(s)
    if re.fullmatch(r"\d+(\.\d+)?-\d+(\.\d+)?", s):
        a, b = s.split("-")
        return f"{_fmt_num(a)}-{_fmt_num(b)}"
    return ""


# ---------------------------------------------------------------
# สร้างแคปชั่น
# ---------------------------------------------------------------
TONES = {
    "😊 เป็นกันเอง": {
        "hooks": [
            "เจอของน่าสนใจมาฝาก! {name} {e}",
            "ใครกำลังมองหา {name} ดูทางนี้ {e}",
            "แนะนำของดีวันนี้ {name} {e}",
        ],
        "ctas": [
            "สนใจกดดูรายละเอียดตามลิงก์ได้เลย 👇",
            "ใครอยากได้ ลองเช็กราคาในลิงก์ด้านล่างนะ 👇",
        ],
        "full": True,
    },
    "📝 สรุปข้อมูลสินค้า": {
        "hooks": [
            "สรุปข้อมูลสินค้า {name} {e}",
            "ส่องรายละเอียด {name} {e}",
        ],
        "ctas": [
            "ดูรายละเอียดและรีวิวจากผู้ซื้อได้ที่ลิงก์ 👇",
            "เช็กรีวิวจริงจากผู้ซื้อในลิงก์ด้านล่างได้เลย 👇",
        ],
        "full": True,
    },
    "⚡ ป้ายยาสายด่วน": {
        "hooks": [
            "🚨 ห้ามพลาด! {name} 🛒",
            "⚡ ตัวนี้น่าโดนมาก {name} 🛒",
            "🔥 มาแรงตอนนี้ {name} 🛒",
        ],
        "ctas": [
            "เช็กโปรล่าสุดได้ที่ลิงก์ด้านล่าง 👇",
            "กดดูโปรและราคาล่าสุดที่ลิงก์ 👇",
        ],
        "full": True,
    },
    "💡 สั้นกระชับ": {
        "hooks": [
            "{name} {e}",
            "ของดีบอกต่อ! {name} {e}",
        ],
        "ctas": ["พิกัดอยู่ด้านล่าง 👇", "กดดูรายละเอียด 👇"],
        "full": False,
    },
}

BASE_TAGS = ["#Lazada", "#LazadaTH", "#LazadaAffiliate", "#ป้ายยา", "#ของดีบอกต่อ", "#พิกัดช้อป"]
DISCLOSURE_TAGS = "#โฆษณา #Affiliate"
BIO_LINK_LINE = "👉 ลิงก์สั่งซื้ออยู่ที่ไบโอ (หรือคอมเมนต์แรก)"


def build_caption(tone, cat_key, name, point, price, promo, aff_link, link_header,
                  experienced=False, disclose=True, rng=random, body_override=None,
                  signature="", max_tags=None, link_mode="inline"):
    tone_cfg = TONES.get(tone) or next(iter(TONES.values()))
    cat = CATEGORIES.get(cat_key) or CATEGORIES["general"]

    display_name = short_name(name) or "สินค้าตัวนี้"
    price = fmt_price(price)
    if body_override:
        # ข้อความจาก AI: ตัดลิงก์/แฮชแท็กที่ AI อาจแถมมา เพื่อไม่ให้แตะลิงก์ Affiliate
        ai_text = re.sub(r"https?://\S+|#\S+", "", body_override).strip()
        parts = [ai_text or display_name]
    else:
        parts = [rng.choice(tone_cfg["hooks"]).format(name=display_name, e=cat["emoji"])]
        body = []
        if point:
            body.append(f"จุดเด่นคือ {point}")
        if tone_cfg["full"]:
            body.append(rng.choice(cat["lines"]))
            if experienced:
                body.append(cat["exp"])
        if body:
            parts.append("\n".join(body))
    if cat["note"]:
        parts.append(f"ℹ️ {cat['note']}")

    extras = []
    if promo:
        extras.append(f"🎁 โปร: {promo}")
    if price:
        extras.append(f"💰 ราคา {price} บาท (ราคาอาจเปลี่ยนตามโปรโมชั่น)")
    if extras:
        parts.append("\n".join(extras))

    parts.append(rng.choice(tone_cfg["ctas"]))
    if link_mode == "bio":
        parts.append(BIO_LINK_LINE)  # แพลตฟอร์มที่ลิงก์ในแคปชั่นกดไม่ได้ (เช่น Instagram)
    else:
        parts.append(f"{link_header or '📌 พิกัดสั่งซื้อ (Lazada):'}\n👉 {aff_link}")
    if signature and signature.strip():
        parts.append(signature.strip())

    tag_list = (["#โฆษณา", "#Affiliate"] if disclose else []) \
        + rng.sample(BASE_TAGS, 2) + rng.sample(cat["tags"], min(3, len(cat["tags"])))
    if max_tags is not None:
        tag_list = tag_list[:max_tags]  # แท็กโฆษณาอยู่หน้าสุดเสมอ จึงไม่ถูกตัดก่อน
    if tag_list:
        parts.append(" ".join(tag_list))

    text = "\n\n".join(parts)
    text, _ = clean_profanity(text)  # ด่านสุดท้ายกันคำไม่สุภาพหลุด
    return text


# ---------------------------------------------------------------
# ตรวจก่อนโพสต์
# ---------------------------------------------------------------
LAZADA_LINK_RE = re.compile(r"^https?://([a-z0-9-]+\.)*(lazada\.[a-z.]+|lzd\.co)(/|$)", re.I)
BAD_NAMES = ("lazada", "lazada.co.th", "captcha", "access denied", "just a moment", "404", "error")


CAT_LABEL_EN = {
    "food": "🍜 Food / snacks / drinks",
    "beauty": "💄 Beauty / skincare",
    "supplement": "💊 Supplements / vitamins",
    "fashion": "👗 Fashion / apparel",
    "electronics": "🎧 Electronics / gadgets",
    "home": "🏠 Home / appliances",
    "baby_pet": "🍼 Baby / pets",
    "auto_tools": "🔧 Auto / tools",
    "general": "🛍️ General",
}
TONE_LABEL_EN = {
    "😊 เป็นกันเอง": "😊 Friendly",
    "📝 สรุปข้อมูลสินค้า": "📝 Product summary",
    "⚡ ป้ายยาสายด่วน": "⚡ Hype",
    "💡 สั้นกระชับ": "💡 Short & snappy",
}


def cat_label(key, lang="th"):
    if lang == "en":
        return CAT_LABEL_EN.get(key, key)
    return CATEGORIES.get(key, CATEGORIES["general"])["label"]


def tone_label(key, lang="th"):
    return TONE_LABEL_EN.get(key, key) if lang == "en" else key


def validate_inputs(aff_link, prod_link, name, price_raw, point, cat_key, chosen_auto):
    """คืนลิสต์ (ระดับ, รหัสข้อความ, พารามิเตอร์) ให้แอปแปลภาษาเอง
    ระดับ = error / warning / info
    """
    out = []
    aff = (aff_link or "").strip()
    if not aff:
        out.append(("error", "v_no_aff", {}))
    elif "xxx" in aff.lower():
        out.append(("error", "v_aff_placeholder", {}))
    elif not LAZADA_LINK_RE.match(aff):
        out.append(("warning", "v_aff_not_lazada", {}))
    if aff and prod_link and aff == prod_link.strip():
        out.append(("warning", "v_same_link", {}))

    n = (name or "").strip()
    if not n:
        out.append(("warning", "v_no_name", {}))
    elif n.lower() in BAD_NAMES:
        out.append(("warning", "v_bad_name", {"name": n}))
    elif len(n) > 120:
        out.append(("info", "v_long_name", {}))

    if not (price_raw or "").strip():
        out.append(("info", "v_no_price", {}))
    elif not fmt_price(price_raw):
        out.append(("warning", "v_bad_price", {"price": price_raw}))

    if not (point or "").strip():
        out.append(("info", "v_no_point", {}))

    if cat_key == "general":
        out.append(("info", "v_cat_general", {}))
    elif chosen_auto:
        out.append(("info", "v_cat_detected", {"cat": cat_key}))
    return out


# ---------------------------------------------------------------
# ตรวจคำเสี่ยงโฆษณาเกินจริง (อิงคำเตือนของ สคบ. เรื่องอวดยอดขาย/โฆษณาเกินจริง)
# ---------------------------------------------------------------
RISKY = {
    "medical": [
        "รักษา", "หายขาด", "หายเร็ว", "ป้องกันโรค", "ผอมเร็ว", "ขาวไว", "ขาวใน",
        "ไม่มีผลข้างเคียง", "ลดความอ้วน", "ลดน้ำหนักได้",
    ],
    "absolute": [
        "ดีที่สุด", "ถูกที่สุด", "อันดับ 1", "อันดับ1", "อันดับหนึ่ง", "100%", "การันตี",
        "รับประกันผล", "เห็นผลทันที", "ไม่มีใครเหมือน", "no.1", "no 1",
    ],
    "sales": [
        "ขายดี", "ถล่มทลาย", "ของหมด", "สินค้าหมด", "ขายหมด", "เหลือน้อย", "ยอดขายล้าน",
        "ล้านชิ้น", "หมดแล้ว",
    ],
}


def find_risky(text):
    """คืน dict หมวด -> รายการคำที่พบ (ไม่ซ้ำ)"""
    low = (text or "").lower()
    found = {}
    for cat, terms in RISKY.items():
        hits = [t for t in terms if t in low]
        if hits:
            found[cat] = hits
    return found


def risky_checks(text):
    """คืนลิสต์ (ระดับ, รหัสข้อความ, พารามิเตอร์) รูปแบบเดียวกับ validate_inputs"""
    return [("warning", f"v_risky_{cat}", {"terms": ", ".join(hits)})
            for cat, hits in find_risky(text).items()]


# ---------------------------------------------------------------
# พรีเซ็ตแพลตฟอร์ม (ตัวเลขจากแหล่งที่ค้นเมื่อ ต.ค. 2026 ตรวจซ้ำก่อนใช้จริงได้)
# ---------------------------------------------------------------
PLATFORMS = {
    "general": {"limit": None, "max_tags": None, "link_mode": "inline"},
    "facebook": {"limit": None, "max_tags": None, "link_mode": "inline"},
    "instagram": {"limit": 2200, "max_tags": 5, "link_mode": "bio"},
    "tiktok": {"limit": 2200, "max_tags": 5, "link_mode": "inline"},
    "x": {"limit": 280, "max_tags": 3, "link_mode": "inline"},
}
URL_IN_TEXT = re.compile(r"https?://\S+")
X_URL_WEIGHT = 23  # X นับลิงก์เป็น 23 ตัวอักษรเสมอ


def platform_opts(platform):
    p = PLATFORMS.get(platform) or PLATFORMS["general"]
    return {"max_tags": p["max_tags"], "link_mode": p["link_mode"]}


def platform_report(caption, platform):
    """นับตัวอักษร/แฮชแท็ก เทียบเพดานของแพลตฟอร์ม (ตัวเลขประมาณการ)"""
    p = PLATFORMS.get(platform) or PLATFORMS["general"]
    text = caption or ""
    counted = URL_IN_TEXT.sub("x" * X_URL_WEIGHT, text) if platform == "x" else text
    chars = len(counted)
    limit = p["limit"]
    return {
        "chars": chars,
        "limit": limit,
        "tags": len(re.findall(r"#\S+", text)),
        "over": bool(limit and chars > limit),
    }
