import streamlit as st
import urllib.request
import re
import os
import json
import random
import datetime

# ---------------------------------------------------------------
# HEADERS สไตล์ Mobile App ให้ Lazada ปล่อยข้อมูล
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

CAPTION_STYLES = {
    "🔥 ป้ายยาจัดเต็ม (ภาษาเพื่อนกัน)": (
        "กระแสแรงจนต้องกดมาลอง! {name} 🔥\n\n"
        "บอกตรงๆ เล็งอยู่นานมากกก พอได้ลองแล้วโคตรประทับใจ คือทำออกมาได้ดีเกินเรื่องมากว่ะมึง "
        "{point_embedded}"
        "ใครงบประมาณนี้แล้วกำลังลังเลอยู่ บอกเลยว่าจัดเหอะ ไม่ต้องคิดเยอะ คุ้มค่าตัวทุกบาทแน่นอน!\n\n"
        "{price_str}"
    ),
    "📝 สายรีวิวใช้งานจริง": (
        "แกะกล่องลองของ! {name} ✨\n\n"
        "ใครที่กำลังตามหาตัวนี้อยู่ ฟังทางนี้ก่อนมึง! จากที่ลองใช้งานจริงคือยกให้เป็นตัวเด็ดเลย "
        "{point_embedded}"
        "เนื้องานดี คุ้มราคา ไม่จกตาแน่นอน ให้ 10/10 แบบไม่หักเลยมึง ควรมีติดบ้านไว้จริงๆ!\n\n"
        "{price_str}"
    ),
    "⚡ สายป้ายยาของมันต้องมี": (
        "🚨 ของมันต้องมีว่ะมึง! {name} 🛒✨\n\n"
        "ไปเจอตัวนี้มา บอกเลยว่าไม่ป้ายยาต่อไม่ได้จริงๆ! "
        "{point_embedded}"
        "ใครกำลังเล็งๆ ไว้อยู่ รีบกดใส่ตะกร้าด่วนๆ ก่อนโค้ดหมดหรือของจะขาดตลาดนะมึง คุ้มจัด!\n\n"
        "{price_str}"
    ),
    "💡 สั้นกระชับ ติดเทรนด์": (
        "ตัวนี้โคตรเด็ดว่ะมึง! {name} 👍\n\n"
        "{point_embedded}"
        "ของมันต้องมีจริงๆ คุ้มค่าตัวสุดๆ จิ้มพิกัดด้านล่างแล้วไปตำกันเลยมึง 👇\n\n"
        "{price_str}"
    )
}

HASHTAG_GROUPS = [
    "#Lazada #LazadaAffiliate #ของดีบอกต่อ #ป้ายยา #พิกัดช้อป #รีวิวของดี #ของมันต้องมี",
    "#LazadaTH #โปรเด็ด #ใช้ดีบอกต่อ #ป้ายยาลาซาด้า #ของดีราคาถูก #รีวิวแน่น",
    "#Lazadaส่งฟรี #ช้อปปิ้งออนไลน์ #ของอร่อยบอกต่อ #ป้ายยาวันนี้"
]

def clean_title(text):
    if not text or text.startswith("http://") or text.startswith("https://"):
        return ""
    text = re.sub(r'https?://\S+', '', text)
    return text.strip()

def unique_keep_order(items):
    seen = set()
    result = []
    for x in items:
        if x and x not in seen:
            seen.add(x)
            result.append(x)
    return result

def extract_lazada_media(url):
    images, videos, title = [], [], ""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            page = resp.read().decode('utf-8', errors='replace')
        
        # 1. ลองดึงจาก moduleData
        json_match = re.search(r'window\.__moduleData__\s*=\s*(\{.*?\});', page, re.S)
        if json_match:
            try:
                data = json.loads(json_match.group(1))
                fields = data.get("data", {}).get("root", {}).get("fields", {})
                title = clean_title(fields.get("productTitle", ""))
                sku_galleries = fields.get("skuGalleries", {})
                for key in sku_galleries:
                    for img_item in sku_galleries[key]:
                        if "src" in img_item:
                            src = img_item["src"]
                            if not src.startswith("http"):
                                src = "https:" + src
                            images.append(src)
            except Exception:
                pass

        # 2. ถ้าดึงชื่อไม่ได้ ดึงจาก Meta Title
        if not title:
            title_match = re.search(r'<title>(.*?)</title>', page, re.I | re.S)
            if title_match:
                raw_title = title_match.group(1).split('|')[0].split('-')[0].strip()
                title = clean_title(raw_title)

        # 3. Fallback ดึงรูปจาก og:image หรือ Regex สแกนทั้งหน้าเว็บ
        og_imgs = re.findall(r'<meta property="og:image" content="(.*?)"', page, re.I)
        for img in og_imgs:
            if img.startswith("//"):
                img = "https:" + img
            images.append(img)

        raw_imgs = re.findall(r'https?://[^"\'\s\\<>]+?\.(?:jpg|jpeg|png)', page, re.I)
        for u in raw_imgs:
            if ("slatic.net/p/" in u or "lazcdn.com/g/p/" in u) and "template" not in u:
                full_img = re.sub(r'_\d+x\d+\.(jpg|png|jpeg)', '', u)
                images.append(full_img)

        # 4. ดึงคลิปวิดีโอ
        raw_vids = re.findall(r'https?://[^"\'\s\\<>]+?\.mp4[^"\'\s\\<>]*', page, re.I)
        videos = [v.replace("\\/", "/") for v in raw_vids]

    except Exception:
        pass
    return unique_keep_order(images)[:9], unique_keep_order(videos)[:3], title

def build_caption(style, name, point, price, aff_link, link_header):
    template = CAPTION_STYLES.get(style, CAPTION_STYLES["🔥 ป้ายยาจัดเต็ม (ภาษาเพื่อนกัน)"])
    display_name = name if name and not name.startswith("http") else "สินค้าตัวนี้"
    point_embedded = f"จุดเด่นคือ {point} บอกเลยว่าโคตรเพลิน! " if point else ""
    price_str = f"💰 ค่าตัวน้องตอนนี้อัปเดตที่: {price} บาทเท่านั้นมึง" if price else ""
    
    body = template.format(name=display_name, point_embedded=point_embedded, price_str=price_str)
    header_text = link_header if link_header else "📌 พิกัดสั่งซื้อราคาพิเศษ (Lazada):"
    
    lines = [
        body.strip(),
        "",
        header_text,
        f"👉 {aff_link}",
        "",
        random.choice(HASHTAG_GROUPS)
    ]
    return "\n".join(lines)

# ---------------------------------------------------------------
# Streamlit Web UI (ปรับให้ใช้บนมือถือง่ายขึ้น)
# ---------------------------------------------------------------
st.set_page_config(page_title="LAZ HELPER v3.0", page_icon="⚡", layout="centered")

st.title("⚡ LAZ HELPER v3.0 (Mobile Ready)")
st.caption("ตัวช่วยทำโพสต์ Affiliate บนมือถือ (เจนแคปชั่น + แสดงรูปให้บันทึก)")

aff_link = st.text_input("1. ลิงก์ Affiliate ของคุณ (ลิงก์สั้น):", placeholder="https://s.lazada.co.th/s.xxx")
prod_link = st.text_input("2. ลิงก์สินค้าธรรมดา (ไว้ดึงรูป/คลิป/ชื่อ):", placeholder="https://www.lazada.co.th/products/...")

if st.button("🔍 ดึงข้อมูลสินค้าออโต้", use_container_width=True):
    if prod_link:
        with st.spinner("กำลังดึงข้อมูล..."):
            imgs, vids, extracted_title = extract_lazada_media(prod_link)
            st.session_state["fetched_imgs"] = imgs
            st.session_state["fetched_vids"] = vids
            if extracted_title:
                st.session_state["product_name"] = extracted_title
            
            if imgs or vids:
                st.success(f"ดึงข้อมูลสำเร็จ! พบรูปภาพ {len(imgs)} รูป / คลิปวิดีโอ {len(vids)} ไฟล์")
            else:
                st.warning("⚠️ ไม่พบรูปออโต้จากเซิร์ฟเวอร์ (อาจติด Anti-Bot ของ Lazada) แต่มึงยังสามารถใช้ระบบเจนแคปชั่นได้ปกติครับ")
    else:
        st.error("กรุณาวางลิงก์สินค้าก่อนมึง")

default_name = st.session_state.get("product_name", "")
product_name = st.text_input("ชื่อสินค้า (พิมพ์เปลี่ยนตรงนี้ได้):", value=default_name)

col1, col2 = st.columns(2)
with col1:
    product_point = st.text_input("จุดเด่นสินค้า:", placeholder="เช่น หอมอร่อยเคี้ยวกรุบๆ")
with col2:
    product_price = st.text_input("ราคา (บาท):", placeholder="เช่น 199 หรือ 1,300")

link_header = st.text_input("ข้อความหัวข้อพิกัด:", value="📌 พิกัดสั่งซื้อราคาพิเศษ (Lazada):")
selected_style = st.selectbox("เลือกสไตล์แคปชั่น:", list(CAPTION_STYLES.keys()))

if st.button("✍️ สร้างแคปชั่นป้ายยา", type="primary", use_container_width=True):
    if not aff_link:
        st.error("ใส่ลิงก์ Affiliate ในช่องแรกก่อนนะมึง!")
    else:
        caption_result = build_caption(selected_style, product_name, product_point, product_price, aff_link, link_header)
        st.session_state["final_caption"] = caption_result

if "final_caption" in st.session_state:
    st.subheader("📝 แคปชั่นของคุณ:")
    st.text_area("ก๊อปปี้ข้อความไปโพสต์ได้เลย:", value=st.session_state["final_caption"], height=200)

# แสดงรูปภาพให้กดเซฟลงมือถือ
imgs = st.session_state.get("fetched_imgs", [])
if imgs:
    st.subheader("🖼️ รูปภาพสินค้า (กดค้างที่รูปเพื่อบันทึกลงมือถือ):")
    cols = st.columns(3)
    for idx, img_url in enumerate(imgs):
        with cols[idx % 3]:
            st.image(img_url, use_column_width=True)

# แสดงคลิปวิดีโอ
vids = st.session_state.get("fetched_vids", [])
if vids:
    st.subheader("🎬 คลิปวิดีโอสินค้า:")
    for v_url in vids:
        st.video(v_url)
