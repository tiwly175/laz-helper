import io
import json
import random
import re
import zipfile
from html import unescape

import requests
import streamlit as st

# ---------------------------------------------------------------
# ตั้งค่า
# ---------------------------------------------------------------
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    "Referer": "https://www.lazada.co.th/",
}

# แต่ละสไตล์มีหลายแบบ สุ่มใช้ เพื่อไม่ให้โพสต์หน้าตาซ้ำกันทุกครั้ง
CAPTION_STYLES = {
    "🔥 ป้ายยาจัดเต็ม (ภาษาเพื่อนกัน)": [
        "กระแสแรงจนต้องกดมาลอง! {name} 🔥\n\n"
        "บอกตรงๆ เล็งอยู่นานมากกก พอได้ลองแล้วโคตรประทับใจ ทำออกมาได้ดีเกินเรื่องมากว่ะมึง "
        "{point_embedded}"
        "ใครงบประมาณนี้แล้วกำลังลังเลอยู่ บอกเลยว่าจัดเหอะ ไม่ต้องคิดเยอะ คุ้มค่าตัวแน่นอน!\n\n"
        "{price_str}",
        "เจอของดีอีกแล้วมึง! {name} 🔥\n\n"
        "ตัวนี้ถูกพูดถึงเยอะมาก เลยต้องลองดูสักตั้ง "
        "{point_embedded}"
        "ใครกำลังหาอยู่ ตัวนี้น่าสนใจจริงๆ คุ้มราคาสุดๆ ไปดูกันก่อนได้เลย!\n\n"
        "{price_str}",
    ],
    "📝 สายรีวิวใช้งานจริง": [
        "แกะกล่องลองของ! {name} ✨\n\n"
        "ใครที่กำลังตามหาตัวนี้อยู่ ฟังทางนี้ก่อนมึง! "
        "{point_embedded}"
        "เนื้องานดี คุ้มราคา ควรมีติดบ้านไว้จริงๆ!\n\n"
        "{price_str}",
        "รีวิวสั้นๆ สำหรับ {name} ✨\n\n"
        "ภาพรวมถือว่าน่าสนใจมากสำหรับราคานี้ "
        "{point_embedded}"
        "ใครอยากได้ของคุ้มๆ ลองเช็กรายละเอียดตามลิงก์ได้เลย!\n\n"
        "{price_str}",
    ],
    "⚡ สายป้ายยาของมันต้องมี": [
        "🚨 ของมันต้องมีว่ะมึง! {name} 🛒✨\n\n"
        "ไปเจอตัวนี้มา ไม่ป้ายยาต่อไม่ได้จริงๆ! "
        "{point_embedded}"
        "ใครเล็งๆ ไว้อยู่ รีบกดใส่ตะกร้าก่อนโค้ดหมดหรือของหมดนะมึง คุ้มจัด!\n\n"
        "{price_str}",
        "🛒 ตัวนี้ห้ามพลาด! {name} ⚡\n\n"
        "{point_embedded}"
        "ของมันต้องมีจริงๆ ใครสนใจรีบเช็กโปรก่อนหมดเขต!\n\n"
        "{price_str}",
    ],
    "💡 สั้นกระชับ ติดเทรนด์": [
        "ตัวนี้โคตรเด็ดว่ะมึง! {name} 👍\n\n"
        "{point_embedded}"
        "คุ้มค่าตัวสุดๆ จิ้มพิกัดด้านล่างแล้วไปตำกันเลย 👇\n\n"
        "{price_str}",
        "ของดีบอกต่อ! {name} 👍\n\n"
        "{point_embedded}"
        "คุ้มจัด พิกัดอยู่ด้านล่างเลย 👇\n\n"
        "{price_str}",
    ],
}

HASHTAG_GROUPS = [
    "#Lazada #LazadaAffiliate #ของดีบอกต่อ #ป้ายยา #พิกัดช้อป #รีวิวของดี #ของมันต้องมี",
    "#LazadaTH #โปรเด็ด #ใช้ดีบอกต่อ #ป้ายยาลาซาด้า #ของดีราคาถูก #รีวิวแน่น",
    "#Lazadaส่งฟรี #ช้อปปิ้งออนไลน์ #ป้ายยาวันนี้ #ของดีราคาคุ้ม",
]
DISCLOSURE_TAGS = "#โฆษณา #Affiliate"


# ---------------------------------------------------------------
# ดึงข้อมูลสินค้า
# ---------------------------------------------------------------
def unique_keep_order(items):
    seen, out = set(), []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def clean_title(text):
    if not text:
        return ""
    text = unescape(text)
    text = re.sub(r"https?://\S+", "", text)
    # ตัดท้ายพวก "| Lazada.co.th" โดยไม่ตัดขีดกลางในชื่อสินค้า
    text = re.sub(r"\s*[|｜]\s*Lazada.*$", "", text, flags=re.I)
    text = re.sub(r"\s+-\s+Lazada.*$", "", text, flags=re.I)
    return text.strip()


def norm_img(u):
    u = u.replace("\\/", "/").strip()
    if u.startswith("//"):
        u = "https:" + u
    # ตัดตัวย่อขนาด เช่น xxx.jpg_720x720q80.jpg -> xxx.jpg
    stripped = re.sub(r"_\d+x\d+(?:q\d+)?\.(?:jpg|jpeg|png|webp)$", "", u, flags=re.I)
    if re.search(r"\.(?:jpg|jpeg|png|webp)$", stripped, re.I):
        u = stripped
    return u


@st.cache_data(ttl=600, show_spinner=False)
def fetch_page(url):
    """คืน (html, error_message)"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
    except requests.RequestException as e:
        return "", f"เชื่อมต่อไม่ได้: {type(e).__name__}"
    text = r.text or ""
    if r.status_code != 200:
        return text, f"Lazada ตอบกลับ HTTP {r.status_code}"
    head = text[:6000].lower()
    if any(k in head for k in ("captcha", "x5secdata", "punish", "slide to verify")):
        return text, "ติดระบบกันบอทของ Lazada (Captcha)"
    return text, ""


def parse_module_data(page):
    m = re.search(r"window\.__moduleData__\s*=\s*", page)
    if not m:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(page[m.end():])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}


def parse_jsonld_products(page):
    out = []
    blocks = re.findall(
        r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I
    )
    for blk in blocks:
        try:
            data = json.loads(blk.strip())
        except ValueError:
            continue
        for it in data if isinstance(data, list) else [data]:
            if isinstance(it, dict) and it.get("@type") == "Product":
                out.append(it)
    return out


def extract_lazada_media(url):
    info = {"images": [], "videos": [], "title": "", "price": "", "error": ""}
    page, err = fetch_page(url)
    info["error"] = err
    if not page:
        return info

    images = []

    # 1) window.__moduleData__
    fields = parse_module_data(page).get("data", {}).get("root", {}).get("fields", {})
    if isinstance(fields, dict):
        info["title"] = clean_title(fields.get("productTitle", ""))
        galleries = fields.get("skuGalleries", {})
        if isinstance(galleries, dict):
            for items in galleries.values():
                for it in items if isinstance(items, list) else []:
                    if isinstance(it, dict) and it.get("src"):
                        images.append(norm_img(it["src"]))

    # 2) JSON-LD (Product)
    for p in parse_jsonld_products(page):
        if not info["title"]:
            info["title"] = clean_title(p.get("name", ""))
        img = p.get("image")
        for i in img if isinstance(img, list) else [img]:
            if isinstance(i, str):
                images.append(norm_img(i))
        offers = p.get("offers")
        for o in offers if isinstance(offers, list) else [offers]:
            if isinstance(o, dict) and o.get("price") and not info["price"]:
                info["price"] = str(o["price"])

    # 3) og:title / <title>
    if not info["title"]:
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', page, re.I)
        if m:
            info["title"] = clean_title(m.group(1))
    if not info["title"]:
        m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
        if m:
            info["title"] = clean_title(m.group(1))

    # 4) ราคาจาก meta
    if not info["price"]:
        m = re.search(
            r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\'](.*?)["\']',
            page, re.I,
        )
        if m:
            info["price"] = m.group(1)

    # 5) รูปจาก og:image และสแกนทั้งหน้า
    for u in re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', page, re.I):
        images.append(norm_img(u))
    for u in re.findall(r'https?:(?:\\?/){2}[^"\'\s\\<>]+?\.(?:jpg|jpeg|png)', page, re.I):
        u = u.replace("\\/", "/")
        if ("slatic.net/p/" in u or "lazcdn.com/g/p/" in u) and "template" not in u:
            images.append(norm_img(u))

    # 6) วิดีโอ
    vids = re.findall(r'https?:(?:\\?/){2}[^"\'\s\\<>]+?\.mp4[^"\'\s\\<>]*', page, re.I)
    info["videos"] = unique_keep_order(v.replace("\\/", "/") for v in vids)[:3]
    info["images"] = unique_keep_order(images)[:9]
    return info


@st.cache_data(ttl=600, show_spinner=False, max_entries=64)
def fetch_bytes(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.content


def build_zip(images, caption):
    buf = io.BytesIO()
    ok = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("caption.txt", caption or "")
        for i, u in enumerate(images, 1):
            try:
                ext = "." + u.split("?")[0].rsplit(".", 1)[-1].lower()
                if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                    ext = ".jpg"
                z.writestr(f"image_{i}{ext}", fetch_bytes(u))
                ok += 1
            except Exception:
                pass
    return buf.getvalue(), ok


# ---------------------------------------------------------------
# สร้างแคปชั่น
# ---------------------------------------------------------------
def make_polite(text):
    text = text.replace("ว่ะมึง", "เลย").replace("ว่ะ", "").replace("มึง", "")
    return re.sub(r"[ ]{2,}", " ", text)


def build_caption(style, name, point, price, aff_link, link_header, polite=False, disclose=True):
    first_style = next(iter(CAPTION_STYLES))
    template = random.choice(CAPTION_STYLES.get(style, CAPTION_STYLES[first_style]))
    display_name = name if name and not name.startswith("http") else "สินค้าตัวนี้"
    point_embedded = f"จุดเด่นคือ {point} " if point else ""
    price_str = f"💰 ราคาตอนนี้ {price} บาท" if price else ""

    body = template.format(name=display_name, point_embedded=point_embedded, price_str=price_str)
    header_text = link_header or "📌 พิกัดสั่งซื้อราคาพิเศษ (Lazada):"
    tags = random.choice(HASHTAG_GROUPS)
    if disclose:
        tags = f"{DISCLOSURE_TAGS} {tags}"

    text = "\n".join([body.strip(), "", header_text, f"👉 {aff_link}", "", tags])
    return make_polite(text) if polite else text


# ---------------------------------------------------------------
# UI
# ---------------------------------------------------------------
st.set_page_config(page_title="LAZ HELPER v3.1", page_icon="⚡", layout="centered")
st.title("⚡ LAZ HELPER v3.1")
st.caption("ตัวช่วยทำโพสต์ Affiliate บนมือถือ (เจนแคปชั่น + ดึงรูป/คลิป)")

aff_link = st.text_input("1. ลิงก์ Affiliate ของคุณ (ลิงก์สั้น):", placeholder="https://s.lazada.co.th/s.xxx")
prod_link = st.text_input("2. ลิงก์สินค้าธรรมดา (ไว้ดึงรูป/คลิป/ชื่อ):", placeholder="https://www.lazada.co.th/products/...")

if st.button("🔍 ดึงข้อมูลสินค้าออโต้", use_container_width=True):
    if not prod_link.strip():
        st.error("กรุณาวางลิงก์สินค้าก่อนนะ")
    else:
        with st.spinner("กำลังดึงข้อมูล..."):
            info = extract_lazada_media(prod_link.strip())
        st.session_state["info"] = info
        st.session_state["zip"] = None
        # ตั้งค่าก่อนสร้างช่อง input ที่ผูก key เดียวกัน
        if info["title"]:
            st.session_state["product_name"] = info["title"]
        if info["price"]:
            st.session_state["product_price"] = info["price"]

info = st.session_state.get("info")
if info:
    if info["images"] or info["videos"]:
        st.success(f"พบรูป {len(info['images'])} รูป / คลิป {len(info['videos'])} ไฟล์")
    else:
        st.warning(
            f"⚠️ ดึงรูป/คลิปไม่ได้ ({info['error'] or 'ไม่พบข้อมูลในหน้าเว็บ'}) "
            "แต่ยังใช้เจนแคปชั่นได้ปกติ"
        )
        st.caption(
            "เซิร์ฟเวอร์ Streamlit อยู่ต่างประเทศ Lazada อาจบล็อก ลองใหม่อีกครั้ง "
            "หรือกรอกชื่อ/ราคาเองได้เลย"
        )

product_name = st.text_input("ชื่อสินค้า (แก้ได้):", key="product_name")

col1, col2 = st.columns(2)
with col1:
    product_point = st.text_input("จุดเด่นสินค้า:", placeholder="เช่น หอมอร่อยเคี้ยวกรุบๆ")
with col2:
    product_price = st.text_input("ราคา (บาท):", key="product_price", placeholder="เช่น 199")

link_header = st.text_input("ข้อความหัวข้อพิกัด:", value="📌 พิกัดสั่งซื้อราคาพิเศษ (Lazada):")
selected_style = st.selectbox("เลือกสไตล์แคปชั่น:", list(CAPTION_STYLES.keys()))
c1, c2 = st.columns(2)
with c1:
    polite = st.checkbox("ใช้คำสุภาพ (ไม่มี มึง/ว่ะ)", value=False)
with c2:
    disclose = st.checkbox("ใส่แท็ก #โฆษณา", value=True)

if st.button("✍️ สร้างแคปชั่นป้ายยา", type="primary", use_container_width=True):
    if not aff_link.strip():
        st.error("ใส่ลิงก์ Affiliate ในช่องแรกก่อนนะ!")
    else:
        st.session_state["final_caption"] = build_caption(
            selected_style, product_name, product_point, product_price,
            aff_link.strip(), link_header, polite, disclose,
        )
        st.session_state["zip"] = None

caption = st.session_state.get("final_caption")
if caption:
    st.subheader("📝 แคปชั่นของคุณ:")
    st.caption("กดไอคอนมุมขวาบนของกล่องเพื่อคัดลอก · กดปุ่มสร้างซ้ำเพื่อได้ข้อความแบบใหม่")
    st.code(caption, language=None, wrap_lines=True)

imgs = (info or {}).get("images", [])
vids = (info or {}).get("videos", [])

if imgs:
    st.subheader("🖼️ รูปภาพสินค้า")
    st.caption("กดค้างที่รูปเพื่อบันทึก หรือโหลดทั้งหมดเป็น ZIP ด้านล่าง")
    cols = st.columns(3)
    for idx, u in enumerate(imgs):
        with cols[idx % 3]:
            st.image(u, use_container_width=True)

    if st.button("📦 เตรียมไฟล์ ZIP (รูป + แคปชั่น)", use_container_width=True):
        with st.spinner("กำลังรวมไฟล์..."):
            data, ok = build_zip(imgs, caption or "")
        st.session_state["zip"] = (data, ok)
    if st.session_state.get("zip"):
        data, ok = st.session_state["zip"]
        st.download_button(
            f"⬇️ ดาวน์โหลด ZIP ({ok} รูป)", data=data,
            file_name="lazada_post.zip", mime="application/zip",
            use_container_width=True,
        )

if vids:
    st.subheader("🎬 คลิปวิดีโอสินค้า")
    for v in vids:
        st.video(v)
