"""โหมดหลายสินค้า: แยกบรรทัดลิงก์ + ประมวลผลทีละรายการ (ฟังก์ชันจริงฉีดจากแอป เทสต์แยกได้)"""
import re

URL_RE = re.compile(r"https?://[^\s|<>\"'）)]+")
PROD_RE = re.compile(r"/products/|/pdp/|-i\d+(?:-s\d+)?\.html", re.I)


def _is_product(url):
    return bool(PROD_RE.search(url))


def parse_batch(text, max_items):
    """คืน (items, ข้ามเพราะเกินจำนวน, errors) errors = [(เลขบรรทัด, รหัส)]"""
    items, errors, skipped = [], [], 0
    for n, line in enumerate((text or "").splitlines(), 1):
        urls = [u.rstrip(".,;") for u in URL_RE.findall(line)]
        if not urls:
            if line.strip():
                errors.append((n, "no_url"))
            continue
        aff = prod = ""
        if len(urls) >= 2:
            a, b = urls[0], urls[1]
            if _is_product(a) and not _is_product(b):
                aff, prod = b, a
            else:
                aff, prod = a, b
        else:
            if _is_product(urls[0]):
                errors.append((n, "no_aff"))
            else:
                errors.append((n, "no_prod"))
            continue
        if len(items) >= max_items:
            skipped += 1
            continue
        items.append({"line": n, "aff": aff, "prod": prod})
    return items, skipped, errors


def process_item(item, fetch_fn, build_fn, validate_fn):
    """fetch_fn(prod)->info, build_fn(name, price, aff)->(caption, cat_key),
    validate_fn(aff, prod, name, price, cat_key)->checks"""
    info = fetch_fn(item["prod"]) or {}
    name = info.get("title", "")
    price = info.get("price", "")
    caption, cat_key = build_fn(name, price, item["aff"])
    return {
        "line": item["line"],
        "name": name,
        "caption": caption,
        "cat": cat_key,
        "images": len(info.get("images", [])),
        "fetch_error": info.get("error", ""),
        "http": info.get("http", ""),
        "checks": validate_fn(item["aff"], item["prod"], name, price, cat_key),
    }
