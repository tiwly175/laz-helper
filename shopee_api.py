"""ตัวเชื่อม Shopee Affiliate Open API (ทางการ: GraphQL + ลายเซ็น SHA256)

ต้องมีบัญชี Shopee Affiliate ที่ได้รับอนุมัติ แล้วเอา App ID / Secret จากเมนู Open API
ใส่ใน Secrets: SHOPEE_APP_ID, SHOPEE_APP_SECRET (ไม่บังคับ: SHOPEE_API_ENDPOINT)

สถานะ: เขียนตามเอกสารและ SDK ของบุคคลที่สามที่ค้นได้ ยังไม่เคยทดสอบกับ API จริง
 - ยืนยันจากแหล่งที่ค้น: รูปแบบลายเซ็น, ชื่อ productOfferV2 / generateShortLink, ฟิลด์ productName/imageUrl/priceMin/priceMax/offerLink
 - อนุมาน (ยังไม่ยืนยัน): endpoint ของไทย, ชื่ออาร์กิวเมนต์ itemId/shopId
"""
import hashlib
import json
import re
import time
from urllib.parse import urlparse

import requests

import media

# อนุมานจากรูปแบบของบราซิล (open-api.affiliate.shopee.com.br) ถ้าไม่ตรง ให้ตั้ง SHOPEE_API_ENDPOINT เอง
DEFAULT_ENDPOINT = "https://open-api.affiliate.shopee.co.th/graphql"
ENDPOINT_RE = re.compile(r"^https://open-api\.affiliate\.shopee\.[a-z.]+/graphql$", re.I)
SHOPEE_HOST_RE = re.compile(r"(^|\.)(shopee\.[a-z.]+|shope\.ee|shp\.ee)$", re.I)
SHORT_HOST_RE = re.compile(r"^(shope\.ee|shp\.ee|s\.shopee\.[a-z.]+)$", re.I)
ID_PATTERNS = [
    re.compile(r"/product/(\d+)/(\d+)"),
    re.compile(r"/opaanlp/(\d+)/(\d+)"),
    re.compile(r"-i\.(\d+)\.(\d+)"),
]


def is_shopee_host(host):
    return bool(host) and bool(SHOPEE_HOST_RE.search(host.lower()))


def parse_ids(url):
    """คืน (shop_id, item_id) หรือ None"""
    for p in ID_PATTERNS:
        m = p.search(url or "")
        if m:
            return int(m.group(1)), int(m.group(2))
    return None


def auth_header(app_id, secret, payload, ts):
    """Authorization: SHA256 Credential=..., Timestamp=..., Signature=SHA256(appId+timestamp+payload+secret)"""
    sig = hashlib.sha256(f"{app_id}{ts}{payload}{secret}".encode("utf-8")).hexdigest()
    return f"SHA256 Credential={app_id}, Timestamp={ts}, Signature={sig}"


def graphql(creds, query, timeout=15, now=None):
    """คืน dict: ok, data, code ('conn'/'auth'/'api'/'unsafe'), detail"""
    endpoint = (creds.get("endpoint") or DEFAULT_ENDPOINT).strip()
    if not ENDPOINT_RE.match(endpoint):
        return {"ok": False, "code": "unsafe", "detail": "endpoint"}  # กันส่งรหัสไปผิดปลายทาง
    payload = json.dumps({"query": query}, ensure_ascii=False, separators=(",", ":"))
    ts = int(time.time() if now is None else now)
    headers = {
        "Authorization": auth_header(creds["app_id"], creds["secret"], payload, ts),
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(endpoint, data=payload.encode("utf-8"), headers=headers, timeout=timeout)
    except requests.RequestException:
        return {"ok": False, "code": "conn", "detail": ""}
    try:
        body = r.json()
    except ValueError:
        return {"ok": False, "code": "auth" if r.status_code in (401, 403) else "api",
                "detail": f"HTTP {r.status_code}"}
    errors = body.get("errors") if isinstance(body, dict) else None
    if errors:
        first = errors[0] if isinstance(errors, list) and errors else {}
        msg = str(first.get("message", "")) if isinstance(first, dict) else str(first)
        low = msg.lower()
        looks_auth = r.status_code in (401, 403) or any(k in low for k in ("signature", "credential", "auth", "app id", "appid"))
        return {"ok": False, "code": "auth" if looks_auth else "api", "detail": msg[:200]}
    return {"ok": True, "data": (body.get("data") if isinstance(body, dict) else None) or {}}


def _creds_ok(creds):
    return bool(creds and creds.get("app_id") and creds.get("secret"))


def _resolve_ids(url):
    """หา shopId/itemId จากลิงก์ ถ้าเป็นลิงก์สั้นให้ตามรีไดเรกต์ก่อน"""
    ids = parse_ids(url)
    if ids:
        return ids
    host = urlparse(url).hostname or ""
    if SHORT_HOST_RE.match(host):
        try:
            r = media.safe_get(url, {"User-Agent": media.UA_MOBILE}, stream=True)
            final = getattr(r, "final_url", url)
            r.close()
            return parse_ids(final)
        except media.FetchError:
            return None
    return None


def _price(node):
    lo = media._digits_price(node.get("priceMin"))
    hi = media._digits_price(node.get("priceMax"))
    if lo and hi and lo != hi:
        return f"{lo}-{hi}"
    return lo or hi


# ---------------------------------------------------------------
# รูป/วิดีโอเพิ่มเติม (พยายามให้เต็มที่ ล้มเหลวได้ไม่กระทบผลหลัก)
#  API ทางการให้รูปหลักแค่รูปเดียว จึงลองอ่านจากข้อมูลสาธารณะของหน้าสินค้าเพิ่ม
#  Shopee มีระบบกันบอท อาจถูกปฏิเสธจาก IP ของ Cloud ซึ่งยังไม่ได้ทดสอบจริง
# ---------------------------------------------------------------
CC_BY_TLD = {"th": "th", "sg": "sg", "my": "my", "vn": "vn", "ph": "ph", "id": "id", "br": "br", "tw": "tw"}
CDN_RE = re.compile(r"https?://[a-z0-9-]+\.img\.susercontent\.com/file/[A-Za-z0-9_\-]{8,90}", re.I)


def _site_host(url):
    host = (urlparse(url).hostname or "").lower()
    m = re.search(r"(shopee\.[a-z.]+)$", host)
    return m.group(1) if m else "shopee.co.th"


def _cc(host):
    return CC_BY_TLD.get(host.rsplit(".", 1)[-1], "th")


def _clean_cdn(u):
    u = re.sub(r"_tn$", "", u.strip())  # ตัดรูปย่อ
    return u


def _hash_to_url(h, cc):
    h = (h or "").strip()
    if h.startswith("https://") and CDN_RE.match(h):
        return _clean_cdn(h)
    if re.fullmatch(r"[A-Za-z0-9_\-]{8,90}", h):
        return f"https://down-{cc}.img.susercontent.com/file/{_clean_cdn(h)}"
    return ""


def _walk(o):
    if isinstance(o, dict):
        yield o
        for v in o.values():
            yield from _walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from _walk(v)


def parse_item_json(data, cc="th"):
    """ดึง title/price/images/videos จาก JSON ของหน้าสินค้า (โครงสร้างยืดหยุ่น)"""
    out = {"title": "", "price": "", "images": [], "videos": []}
    for d in _walk(data):
        if not out["title"] and isinstance(d.get("name"), str) and ("itemid" in d or "item_id" in d):
            out["title"] = media.clean_title(d["name"])
        if not out["price"]:
            raw = d.get("price_min") or d.get("price")
            if isinstance(raw, (int, float)) and raw > 1000:
                out["price"] = str(int(round(raw / 100000)))
        for key in ("image", "images"):
            v = d.get(key)
            for h in ([v] if isinstance(v, str) else v if isinstance(v, list) else []):
                if isinstance(h, str):
                    u = _hash_to_url(h, cc)
                    if u:
                        out["images"].append(u)
    blob = json.dumps(data, ensure_ascii=False).replace("\\/", "/")
    for u in re.findall(r"https://[^\"\s\\<>]+?\.(?:mp4|m3u8)[^\"\s\\<>]*", blob):
        out["videos"].append(u)
    return out


def _json_get(url, referer):
    headers = {"User-Agent": media.UA_DESKTOP, "Accept": "application/json",
               "Accept-Language": "th-TH,th;q=0.9", "Referer": referer,
               "x-api-source": "pc", "x-requested-with": "XMLHttpRequest"}
    try:
        r = media.safe_get(url, headers, timeout=12, stream=True)
    except media.FetchError:
        return None
    try:
        if r.status_code != 200:
            return None
        raw = b"".join(c for _, c in zip(range(40), r.iter_content(64 * 1024)))
        return json.loads(raw.decode("utf-8", errors="replace"))
    except ValueError:
        return None
    finally:
        r.close()


def fetch_public_extras(shop_id, item_id, url):
    """คืน dict {title, price, images, videos(list of url)} เท่าที่ได้ ไม่โยน error"""
    host = _site_host(url)
    cc = _cc(host)
    page_url = f"https://{host}/product/{shop_id}/{item_id}"
    out = {"title": "", "price": "", "images": [], "videos": []}

    def merge(part):
        out["title"] = out["title"] or part.get("title", "")
        out["price"] = out["price"] or part.get("price", "")
        out["images"] += part.get("images", [])
        out["videos"] += part.get("videos", [])

    for ep in (f"https://{host}/api/v4/pdp/get_pc?item_id={item_id}&shop_id={shop_id}&tz_offset_minutes=420&detail_level=0",
               f"https://{host}/api/v4/item/get?itemid={item_id}&shopid={shop_id}"):
        try:
            data = _json_get(ep, page_url)
        except Exception:
            data = None
        if data:
            merge(parse_item_json(data, cc))
            if out["images"]:
                break
    if len(out["images"]) < 3:  # ยังน้อย: ลองอ่านหน้าเว็บ
        try:
            html, _final, err = media.fetch_page_generic(page_url)
        except Exception:
            html, err = "", "x"
        if html and not err:
            html = media.normalize_page(html)
            found = [_clean_cdn(u) for u in CDN_RE.findall(html)]
            part = {"images": found}
            try:
                ex = media.extract_media(html)
                part["title"] = ex.get("title", "")
                part["price"] = ex.get("price", "")
                part["videos"] = [v["url"] for v in ex.get("videos", [])]
            except Exception:
                pass
            merge(part)
    return out


def _dedupe(items):
    seen, res = set(), []
    for x in items:
        k = x.split("?")[0]
        if x and k not in seen:
            seen.add(k)
            res.append(x)
    return res


def fetch_shopee(url_or_text, creds):
    """รูปแบบผลลัพธ์เหมือน media.fetch_product (title, price, images, videos, error, http, url)
    API ทางการให้รูปหลักรูปเดียว: เสริมรูป/วิดีโออีกจากข้อมูลสาธารณะของหน้าสินค้าเท่าที่ดึงได้
    ไม่มี Secrets ก็ยังลองดึงจากข้อมูลสาธารณะได้ (ไม่ได้รับประกัน)"""
    info = {"title": "", "price": "", "images": [], "videos": [], "error": "", "http": "", "url": ""}
    url = media.extract_first_url(url_or_text)
    info["url"] = url
    if not url:
        info["error"] = "empty"
        return info
    if not is_shopee_host(urlparse(url).hostname or ""):
        info["error"] = "not_shopee"
        return info
    ids = _resolve_ids(url)
    if not ids:
        info["error"] = "no_ids"
        return info
    shop_id, item_id = ids

    api_err = ""
    api_images = []
    if _creds_ok(creds):
        query = ("query { productOfferV2(itemId: %d, shopId: %d, limit: 1) { nodes { "
                 "itemId productName imageUrl priceMin priceMax offerLink productLink } } }") % (item_id, shop_id)
        res = graphql(creds, query)
        if not res["ok"]:
            api_err = res["code"]
        else:
            nodes = ((res["data"].get("productOfferV2") or {}).get("nodes")) or []
            if not nodes:
                api_err = "notfound"  # สินค้าอาจไม่เข้าร่วมโปรแกรม Affiliate
            else:
                n = nodes[0]
                info["title"] = media.clean_title(n.get("productName", ""))
                info["price"] = _price(n)
                img = n.get("imageUrl")
                if isinstance(img, str) and img.startswith("https://"):
                    api_images = [img]
    else:
        api_err = "no_creds"

    try:
        extra = fetch_public_extras(shop_id, item_id, url)
    except Exception:
        extra = {"title": "", "price": "", "images": [], "videos": []}

    info["title"] = info["title"] or extra["title"]
    info["price"] = info["price"] or extra["price"]
    info["images"] = _dedupe(api_images + extra["images"])[:media.MAX_IMAGES]
    vids = _dedupe(extra["videos"])[:media.MAX_VIDEOS]
    info["videos"] = [{"url": v, "kind": "mp4" if media._ext(v) in ("mp4", "mov", "webm") else "hls"} for v in vids]
    if not (info["title"] or info["images"] or info["videos"]):
        info["error"] = api_err or "empty"
    return info


def generate_short_link(url_or_text, creds):
    """สร้างลิงก์ Affiliate จากลิงก์สินค้า คืน (ok, shortLink | รหัสข้อผิดพลาด)"""
    url = media.extract_first_url(url_or_text)
    if not url or not is_shopee_host(urlparse(url).hostname or ""):
        return False, "not_shopee"
    if not _creds_ok(creds):
        return False, "no_creds"
    query = "mutation { generateShortLink(input: {originUrl: %s}) { shortLink } }" % json.dumps(url)
    res = graphql(creds, query)
    if not res["ok"]:
        return False, res["code"]
    link = ((res["data"].get("generateShortLink") or {}).get("shortLink"))
    if isinstance(link, str) and link.startswith("http"):
        return True, link
    return False, "notfound"
