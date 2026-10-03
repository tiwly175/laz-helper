"""โหมดหลายสินค้า: แยกบรรทัดลิงก์ + ประมวลผลทีละรายการ (ฟังก์ชันจริงฉีดจากแอป เทสต์แยกได้)"""
import re

import stores

URL_RE = re.compile(r"https?://[^\s|<>\"'）)]+")
PROD_RE = re.compile(r"/products/|/pdp/|-i\d+(?:-s\d+)?\.html|/product/\d+/\d+|/opaanlp/\d+/\d+|-i\.\d+\.\d+", re.I)


def _is_product(url):
    return (not stores.is_aff_host(url)) and bool(PROD_RE.search(url))


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
    """item มี store (ร้านของรายการนี้)
    fetch_fn(prod, store)->info, build_fn(name, price, aff, store)->(caption, cat_key),
    validate_fn(aff, prod, name, price, cat_key, store)->checks"""
    store = item.get("store", "lazada")
    info = fetch_fn(item["prod"], store) or {}
    name = info.get("title", "")
    price = info.get("price", "")
    caption, cat_key = build_fn(name, price, item["aff"], store)
    return {
        "line": item["line"],
        "name": name,
        "caption": caption,
        "cat": cat_key,
        "images": len(info.get("images", [])),
        "fetch_error": info.get("error", ""),
        "http": info.get("http", ""),
        "store": store,
        "checks": validate_fn(item["aff"], item["prod"], name, price, cat_key, store),
    }
