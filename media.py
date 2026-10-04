"""ดึงชื่อ/ราคา/รูป/คลิปจากหน้าสินค้า Lazada (ไม่พึ่ง streamlit เทสต์แยกได้)

หลักการ: ลองหลาย User-Agent, อ่านข้อมูลจากหลายแหล่ง (moduleData, JSON-LD, og:, สแกนทั้งหน้า),
และป้องกัน SSRF (บล็อก IP ภายใน + ต้องเป็นโดเมน Lazada สำหรับหน้าสินค้า)
"""
import ipaddress
import json
import re
import socket
from html import unescape
from urllib.parse import urljoin, urlparse

import requests

UA_MOBILE = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
)
UA_DESKTOP = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
UA_ANDROID = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Mobile Safari/537.36"
)

LAZADA_HOST_RE = re.compile(r"(^|\.)(lazada\.[a-z.]+|lzd\.co)$", re.I)
IMG_EXT = ("jpg", "jpeg", "png", "webp")
VID_EXT = ("mp4", "m3u8", "mov", "webm")
JUNK_WORDS = ("logo", "icon", "sprite", "badge", "placeholder", "blank", "template",
              "avatar", "emoji", "loading", "banner", "flag")
MAX_IMAGES = 30
MAX_VIDEOS = 8


class FetchError(Exception):
    """code: unsafe / not_lazada / conn / http / captcha / empty"""

    def __init__(self, code, detail=""):
        super().__init__(code)
        self.code = code
        self.detail = detail


# ---------------------------------------------------------------
# URL helpers + ความปลอดภัย
# ---------------------------------------------------------------
def extract_first_url(text):
    """ดึงลิงก์แรกจากข้อความแชร์ (วางทั้งก้อนได้)"""
    m = re.search(r"https?://[^\s<>\"'）)]+", text or "")
    return m.group(0).rstrip(".,;") if m else ""


def is_lazada_host(host):
    return bool(host) and bool(LAZADA_HOST_RE.search(host.lower()))


def check_public_url(url):
    """ปฏิเสธ scheme แปลกๆ และโฮสต์ที่ชี้ไป IP ภายใน/loopback/link-local"""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise FetchError("unsafe")
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        raise FetchError("conn")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved
                or ip.is_multicast or ip.is_unspecified):
            raise FetchError("unsafe")


def safe_get(url, headers, timeout=15, stream=False, max_redirects=5):
    """requests.get ที่ตามรีไดเรกต์เองและตรวจ IP ทุกทอด"""
    current = url
    for _ in range(max_redirects + 1):
        check_public_url(current)
        try:
            r = requests.get(current, headers=headers, timeout=timeout,
                             stream=stream, allow_redirects=False)
        except requests.RequestException:
            raise FetchError("conn")
        if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("Location"):
            current = urljoin(current, r.headers["Location"])
            r.close()
            continue
        r.final_url = current
        return r
    raise FetchError("conn")


# ---------------------------------------------------------------
# ดึงหน้าเว็บ (ลองหลาย UA)
# ---------------------------------------------------------------
def _headers(ua):
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
        "Referer": "https://www.lazada.co.th/",
    }


def _is_captcha(text):
    head = (text or "")[:6000].lower()
    return any(k in head for k in ("captcha", "x5secdata", "punish", "slide to verify"))


def normalize_page(page):
    """แปลง escape ที่พบบ่อยใน JSON ฝังหน้าเว็บให้เป็นข้อความอ่านได้"""
    return (page.replace("\\u002F", "/").replace("\\u002f", "/")
                .replace("\\/", "/").replace("&amp;", "&"))


def fetch_page(url):
    """คืน (html, final_url, error_code) ลอง UA ทีละแบบจนเจอหน้าที่มีข้อมูล"""
    host = urlparse(url).hostname or ""
    if not is_lazada_host(host):
        raise FetchError("not_lazada")
    last = ("", url, "empty")
    for ua in (UA_MOBILE, UA_DESKTOP, UA_ANDROID):
        try:
            r = safe_get(url, _headers(ua))
        except FetchError as e:
            if e.code in ("unsafe", "not_lazada"):
                raise
            last = ("", url, e.code)
            continue
        text = r.text or ""
        final = getattr(r, "final_url", url)
        if r.status_code != 200:
            last = (text, final, f"http_{r.status_code}")
            continue
        if _is_captcha(text):
            last = (text, final, "captcha")
            continue
        if len(text) < 500:
            last = (text, final, "empty")
            continue
        return text, final, ""
    return last


# ---------------------------------------------------------------
# แยกข้อมูล
# ---------------------------------------------------------------
def clean_title(text):
    if not text:
        return ""
    text = unescape(str(text))
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"\s*[|｜]\s*Lazada.*$", "", text, flags=re.I)
    text = re.sub(r"\s+-\s+Lazada.*$", "", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip()


def _ext(u):
    path = urlparse(u).path.lower()
    m = re.search(r"\.([a-z0-9]{2,4})(?:_\.[a-z0-9]+)?$", path)
    return m.group(1) if m else ""


def norm_img(u):
    """ทำให้ URL รูปเป็นไฟล์ต้นฉบับขนาดใหญ่ คืน '' ถ้าเป็นรูปจิ๋ว/ขยะ"""
    u = (u or "").replace("\\/", "/").strip()
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith(("http://", "https://")):
        return ""
    low = u.lower()
    if any(w in low for w in JUNK_WORDS):
        return ""
    # รูปจิ๋ว เช่น _80x80
    m = re.search(r"_(\d+)x(\d+)", low)
    is_product_cdn = "slatic.net/p/" in low or "lazcdn.com/g/p/" in low
    if m and int(m.group(1)) <= 200 and int(m.group(2)) <= 200 and not is_product_cdn:
        return ""  # ไอคอนจิ๋วจากโดเมนอื่น; รูปสินค้าจาก CDN ของ Lazada จะถูกแปลงเป็นไฟล์ใหญ่ด้านล่าง
    u = re.sub(r"_\.(webp|avif)$", "", u, flags=re.I)  # xxx.jpg_.webp -> xxx.jpg
    stripped = re.sub(r"_\d+x\d+(?:q\d+)?\.(?:jpg|jpeg|png|webp)$", "", u, flags=re.I)
    if re.search(r"\.(?:jpg|jpeg|png|webp)$", stripped, re.I):
        u = stripped
    return u if _ext(u) in IMG_EXT else ""


def norm_video(u):
    u = (u or "").replace("\\/", "/").strip()
    if u.startswith("//"):
        u = "https:" + u
    if not u.startswith(("http://", "https://")):
        return ""
    return u if _ext(u) in VID_EXT else ""


def _walk_strings(obj, depth=0):
    """ไล่เก็บ (key, string) ทั้งหมดในโครง JSON"""
    if depth > 14:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str):
                yield k, v
            else:
                yield from _walk_strings(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            if isinstance(v, str):
                yield "", v
            else:
                yield from _walk_strings(v, depth + 1)


def _json_after(page, pattern):
    m = re.search(pattern, page)
    if not m:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(page[m.end():])
        return obj if isinstance(obj, (dict, list)) else {}
    except ValueError:
        return {}


def _jsonld_products(page):
    out = []
    for blk in re.findall(r'<script[^>]+application/ld\+json[^>]*>(.*?)</script>', page, re.S | re.I):
        try:
            data = json.loads(blk.strip())
        except ValueError:
            continue
        for it in data if isinstance(data, list) else [data]:
            if isinstance(it, dict) and it.get("@type") == "Product":
                out.append(it)
    return out


def _digits_price(v):
    s = re.sub(r"[^\d.]", "", str(v or ""))
    return s if re.fullmatch(r"\d+(\.\d+)?", s or "x") else ""


def _price_from_fields(fields):
    """พยายามอ่านราคาจาก moduleData (โครงอาจเปลี่ยน จึงห่อ try)"""
    try:
        infos = fields.get("skuInfos") or {}
        first = next(iter(infos.values())) if isinstance(infos, dict) else infos[0]
        sale = first.get("price", {}).get("salePrice", {})
        for key in ("value", "text"):
            p = _digits_price(sale.get(key))
            if p:
                return p
    except Exception:
        pass
    return ""


def _num(v):
    """'฿1,299.00' / 1299 -> float หรือ None"""
    d = _digits_price(str(v).replace(",", ""))
    try:
        return float(d) if d else None
    except ValueError:
        return None


def _fmt_plain(x):
    return str(int(x)) if x is not None and float(x).is_integer() else (f"{x:.2f}".rstrip("0").rstrip(".") if x is not None else "")


def _walk_dicts(obj, depth=0):
    if depth > 14:
        return
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_dicts(v, depth + 1)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_dicts(v, depth + 1)


def _price_facts(fields, page, sale_hint=""):
    """ราคาปกติ/ส่วนลด/คะแนนรีวิว จากโครงข้อมูล + regex สำรอง (โครงอาจเปลี่ยน จึงห่อ try ทุกจุด)
    คืน dict: price, orig_price, discount(int %), rating(float|''), reviews(int|'')"""
    out = {"price": "", "orig_price": "", "discount": 0, "rating": "", "reviews": ""}
    sale = _num(sale_hint)
    orig = None
    try:
        for d in _walk_dicts(fields):
            sp, op = d.get("salePrice"), d.get("originalPrice")
            if isinstance(sp, dict) or isinstance(op, dict):
                if sale is None and isinstance(sp, dict):
                    sale = _num(sp.get("value")) or _num(sp.get("text"))
                if orig is None and isinstance(op, dict):
                    orig = _num(op.get("value")) or _num(op.get("text"))
        if orig is None or sale is None:
            m = re.search(r'"originalPrice"\s*:\s*\{[^{}]*?"value"\s*:\s*"?([\d.]+)', page)
            if m and orig is None:
                orig = _num(m.group(1))
            m = re.search(r'"salePrice"\s*:\s*\{[^{}]*?"value"\s*:\s*"?([\d.]+)', page)
            if m and sale is None:
                sale = _num(m.group(1))
        if orig is None:
            m = re.search(r'"(?:pdt_)?(?:origin(?:al)?_?[pP]rice|price_before_discount|marketPrice)"\s*:\s*"?[^\d"]*([\d,]+(?:\.\d+)?)', page)
            if m:
                orig = _num(m.group(1))
    except Exception:
        pass
    pct = 0
    try:
        if orig and sale and orig > sale > 0:
            pct = int(round((1 - sale / orig) * 100))
        else:
            m = re.search(r'"(?:pdt_)?discount"\s*:\s*"-?\s*(\d{1,2})\s*%', page)
            if m:
                pct = int(m.group(1))
    except Exception:
        pct = 0
    if 0 < pct < 95:
        out["discount"] = pct
    if orig and sale and orig > sale:
        out["orig_price"] = _fmt_plain(orig)
    if sale:
        out["price"] = _fmt_plain(sale)
    try:
        for p in _jsonld_products(page):
            ar = p.get("aggregateRating")
            if isinstance(ar, dict):
                rv, rc = _num(ar.get("ratingValue")), _num(ar.get("reviewCount") or ar.get("ratingCount"))
                if rv and 0 < rv <= 5:
                    out["rating"] = round(rv, 1)
                if rc:
                    out["reviews"] = int(rc)
                break
        if not out["rating"]:
            m = re.search(r'"ratingScore"\s*:\s*"?([\d.]+)', page)
            if m and _num(m.group(1)) and 0 < _num(m.group(1)) <= 5:
                out["rating"] = round(_num(m.group(1)), 1)
    except Exception:
        pass
    return out


def item_id_from_url(url):
    m = re.search(r"-i(\d+)(?:-s(\d+))?\.html", url or "")
    return m.group(1) if m else ""


def extract_media(raw_html):
    """คืน dict: title, price, images(list), videos(list ของ {url, kind})"""
    page = normalize_page(raw_html or "")
    info = {"title": "", "price": "", "images": [], "videos": [],
            "orig_price": "", "discount": 0, "rating": "", "reviews": ""}
    imgs, vids = [], []

    mod = _json_after(page, r"window\.__moduleData__\s*=\s*")
    fields = {}
    if isinstance(mod, dict):
        fields = mod.get("data", {}).get("root", {}).get("fields", {}) or {}
    if isinstance(fields, dict):
        info["title"] = clean_title(fields.get("productTitle", ""))
        info["price"] = _price_from_fields(fields)
        gal = fields.get("skuGalleries", {})
        if isinstance(gal, dict):
            for items in gal.values():
                for it in items if isinstance(items, list) else []:
                    if isinstance(it, dict):
                        if it.get("src"):
                            imgs.append(norm_img(it["src"]))
                        for vk in ("videoUrl", "video_url", "videoSrc"):
                            if it.get(vk):
                                vids.append(norm_video(it[vk]))
        # ไล่หา string ที่เป็นสื่อทั้งก้อน (กันโครงเปลี่ยน)
        for key, val in _walk_strings(fields):
            if val.startswith(("http", "//")):
                v = norm_video(val)
                if v:
                    vids.append(v)
                elif "video" not in key.lower():
                    imgs.append(norm_img(val))

    for p in _jsonld_products(page):
        if not info["title"]:
            info["title"] = clean_title(p.get("name", ""))
        img = p.get("image")
        for i in img if isinstance(img, list) else [img]:
            if isinstance(i, str):
                imgs.append(norm_img(i))
        offers = p.get("offers")
        for o in offers if isinstance(offers, list) else [offers]:
            if isinstance(o, dict) and not info["price"]:
                info["price"] = _digits_price(o.get("price"))

    if not info["title"]:
        m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']', page, re.I)
        if m:
            info["title"] = clean_title(m.group(1))
    if not info["title"]:
        m = re.search(r"<title>(.*?)</title>", page, re.I | re.S)
        if m:
            info["title"] = clean_title(m.group(1))
    if not info["price"]:
        m = re.search(r'<meta[^>]+property=["\']product:price:amount["\'][^>]+content=["\'](.*?)["\']', page, re.I)
        if m:
            info["price"] = _digits_price(m.group(1))

    for u in re.findall(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']', page, re.I):
        imgs.append(norm_img(u))
    for u in re.findall(r'(?:https?:)?//[^"\'\s\\<>]+?\.(?:jpg|jpeg|png|webp)(?:_[^"\'\s\\<>]*)?', page, re.I):
        if ("slatic.net/p/" in u or "lazcdn.com/g/p/" in u) and "template" not in u:
            imgs.append(norm_img(u))
    for u in re.findall(r'(?:https?:)?//[^"\'\s\\<>]+?\.(?:mp4|m3u8)[^"\'\s\\<>]*', page, re.I):
        vids.append(norm_video(u))

    facts = _price_facts(fields if isinstance(fields, dict) else {}, page, info["price"])
    for k, v in facts.items():
        if v and not info.get(k):
            info[k] = v
    if not info["price"] and facts["price"]:
        info["price"] = facts["price"]

    info["images"] = _unique(i for i in imgs if i)[:MAX_IMAGES]
    uv = _unique(v for v in vids if v)
    uv.sort(key=lambda v: _ext(v) != "mp4")  # mp4 ก่อน (ดาวน์โหลดได้)
    info["videos"] = [{"url": v, "kind": "mp4" if _ext(v) in ("mp4", "mov", "webm") else "hls"}
                      for v in uv[:MAX_VIDEOS]]
    return info


def _unique(items):
    seen, out = set(), []
    for x in items:
        key = x.split("?")[0]
        if x and key not in seen:
            seen.add(key)
            out.append(x)
    return out


def iter_lazada_pages(url):
    """ดึงหน้าเดียวกันด้วย UA หลายแบบ ทีละแบบ (เดสก์ท็อปก่อน เพราะมักมีแกลเลอรีเต็มกว่าหน้ามือถือ)
    คืนทีละ (html, final_url, error_code) ไม่หยุดที่หน้าแรกที่ได้"""
    host = urlparse(url).hostname or ""
    if not is_lazada_host(host):
        raise FetchError("not_lazada")
    for ua in (UA_DESKTOP, UA_MOBILE, UA_ANDROID):
        try:
            r = safe_get(url, _headers(ua))
        except FetchError as e:
            if e.code in ("unsafe", "not_lazada"):
                raise
            yield "", url, e.code
            continue
        text = r.text or ""
        final = getattr(r, "final_url", url)
        if r.status_code != 200:
            yield text, final, f"http_{r.status_code}"
        elif _is_captcha(text):
            yield text, final, "captcha"
        elif len(text) < 500:
            yield text, final, "empty"
        else:
            yield text, final, ""


ENOUGH_IMAGES = 8  # ได้รูปถึงเท่านี้แล้วไม่ต้องลอง UA ถัดไป


def fetch_product(url_or_text, fetcher=None):
    """จุดเข้าหลัก คืน dict พร้อม error code ('' ถ้าสำเร็จ)
    fetcher: ฟังก์ชันดึงหน้าเว็บ (ค่าเริ่มต้น = Lazada: ลองหลาย UA แล้วรวมรูป/คลิปจากทุกหน้าที่ได้)"""
    info = {"title": "", "price": "", "images": [], "videos": [], "error": "", "http": "", "url": "",
            "orig_price": "", "discount": 0, "rating": "", "reviews": ""}
    url = extract_first_url(url_or_text)
    info["url"] = url
    if not url:
        info["error"] = "empty"
        return info

    def pages():
        if fetcher is not None:
            yield fetcher(url)
        else:
            yield from iter_lazada_pages(url)

    last_err, got_page = "", False
    seen_vid = set()
    try:
        for page, final, err in pages():
            if err:
                last_err = err
            if not page or err in ("captcha", "empty") or err.startswith("http_") and not page:
                continue
            got_page = True
            ex = extract_media(page)
            info["title"] = info["title"] or ex.get("title", "")
            info["price"] = info["price"] or ex.get("price", "")
            for k in ("orig_price", "discount", "rating", "reviews"):
                info[k] = info[k] or ex.get(k, info[k])
            info["images"] = _unique(info["images"] + ex.get("images", []))[:MAX_IMAGES]
            for v in ex.get("videos", []):
                if v["url"].split("?")[0] not in seen_vid:
                    seen_vid.add(v["url"].split("?")[0])
                    info["videos"].append(v)
            info["videos"] = info["videos"][:MAX_VIDEOS]
            if len(info["images"]) >= ENOUGH_IMAGES:
                break
    except FetchError as e:
        info["error"] = e.code
        return info

    has_data = bool(info["title"] or info["images"] or info["videos"])
    if not has_data and last_err:
        if last_err.startswith("http_"):
            info["error"], info["http"] = "http", last_err[5:]
        else:
            info["error"] = last_err
    elif not has_data and got_page:
        info["error"] = "nodata"
    return info


# ---------------------------------------------------------------
# เว็บทั่วไป (ไม่ใช่ Lazada): อ่าน og:/JSON-LD แบบเบาๆ มีเพดานขนาดหน้า
# ---------------------------------------------------------------
def _generic_headers(ua):
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "th-TH,th;q=0.9,en;q=0.8",
    }


def fetch_page_generic(url, max_bytes=3_000_000):
    """คืน (html, final_url, error_code) บล็อก IP ภายใน อ่านไม่เกิน max_bytes"""
    last = ("", url, "empty")
    for ua in (UA_MOBILE, UA_DESKTOP):
        try:
            r = safe_get(url, _generic_headers(ua), stream=True)
        except FetchError as e:
            if e.code == "unsafe":
                raise
            last = ("", url, e.code)
            continue
        try:
            final = getattr(r, "final_url", url)
            if r.status_code != 200:
                last = ("", final, f"http_{r.status_code}")
                continue
            ctype = (r.headers.get("Content-Type") or "").lower()
            if ctype and "html" not in ctype and "xml" not in ctype:
                last = ("", final, "empty")
                continue
            buf = bytearray()
            for chunk in r.iter_content(64 * 1024):
                buf.extend(chunk)
                if len(buf) >= max_bytes:
                    break
            text = bytes(buf).decode(r.encoding or "utf-8", errors="replace")
        finally:
            r.close()
        if _is_captcha(text):
            last = (text, final, "captcha")
            continue
        if len(text) < 300:
            last = (text, final, "empty")
            continue
        return text, final, ""
    return last


def fetch_product_generic(url_or_text):
    return fetch_product(url_or_text, fetcher=fetch_page_generic)


# ---------------------------------------------------------------
# ดาวน์โหลดไฟล์ (มีเพดานขนาด)
# ---------------------------------------------------------------
class TooBig(Exception):
    pass


def download_bytes(url, max_bytes, timeout=30):
    r = safe_get(url, {"User-Agent": UA_DESKTOP, "Referer": "https://www.lazada.co.th/"},
                 timeout=timeout, stream=True)
    try:
        if r.status_code != 200:
            raise FetchError("http", str(r.status_code))
        length = r.headers.get("Content-Length")
        if length and length.isdigit() and int(length) > max_bytes:
            raise TooBig()
        buf, total = bytearray(), 0
        for chunk in r.iter_content(256 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise TooBig()
            buf.extend(chunk)
        return bytes(buf), r.headers.get("Content-Type", "")
    finally:
        r.close()


def guess_ext(url, content_type, default):
    e = _ext(url)
    if e in IMG_EXT + VID_EXT:
        return "." + e
    ct = (content_type or "").lower()
    for key, ext in (("jpeg", ".jpg"), ("png", ".png"), ("webp", ".webp"), ("mp4", ".mp4")):
        if key in ct:
            return ext
    return default
