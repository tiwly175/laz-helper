"""ตัวเชื่อมร้านค้า/แพลตฟอร์มสินค้า: Lazada, Shopee, เว็บทั่วไป
เพิ่มแพลตฟอร์มใหม่ = เพิ่ม 1 รายการใน STORES + ฟังก์ชันดึงข้อมูล 1 ตัว
"""
import re
from urllib.parse import urlparse

import media
import shopee_api

STORES = {
    "lazada": {
        "host_re": media.LAZADA_HOST_RE,
        "tags": ["#Lazada", "#LazadaTH", "#LazadaAffiliate"],
    },
    "shopee": {
        "host_re": shopee_api.SHOPEE_HOST_RE,
        "tags": ["#Shopee", "#ShopeeTH", "#ShopeeAffiliate"],
    },
    "generic": {
        "host_re": None,  # รับลิงก์เว็บใดก็ได้
        "tags": [],
    },
}
STORE_IDS = list(STORES)
AUTO = "auto"

# โดเมนลิงก์สั้น/ลิงก์ติดตามของ Affiliate (ใช้แยกว่าลิงก์ไหนคือ Affiliate ในโหมดหลายสินค้า)
AFF_HOST_RE = re.compile(
    r"^(s\.lazada\.[a-z.]+|c\.lazada\.[a-z.]+|lzd\.co|shope\.ee|shp\.ee|s\.shopee\.[a-z.]+)$", re.I)


def host_of(url):
    return (urlparse(url or "").hostname or "").lower()


def is_aff_host(url):
    return bool(AFF_HOST_RE.match(host_of(url)))


def detect_store(text):
    """เดาร้านจากลิงก์แรกในข้อความ คืน None ถ้าไม่มีลิงก์"""
    url = media.extract_first_url(text)
    if not url:
        return None
    host = host_of(url)
    for sid in ("lazada", "shopee"):
        if STORES[sid]["host_re"].search(host):
            return sid
    return "generic"


def link_matches(store, url):
    """ลิงก์นี้ดูเหมือนของร้านนี้ไหม (ใช้เตือนใน 'ตรวจก่อนโพสต์')"""
    u = (url or "").strip()
    if not re.match(r"^https?://", u, re.I):
        return False
    rx = (STORES.get(store) or STORES["generic"])["host_re"]
    return True if rx is None else bool(rx.search(host_of(u)))


def store_tags(store):
    return list((STORES.get(store) or STORES["generic"])["tags"])


def fetch_product(store, url_or_text, creds=None):
    """ดึงข้อมูลสินค้าตามร้าน คืน dict รูปแบบเดียวกันทุกร้าน"""
    if store == "shopee":
        return shopee_api.fetch_shopee(url_or_text, creds or {})
    if store == "generic":
        return media.fetch_product_generic(url_or_text)
    return media.fetch_product(url_or_text)
