"""ส่งออก/นำเข้าประวัติแคปชั่นเป็น JSON (ผู้ใช้เก็บไฟล์เอง แอปไม่เก็บถาวร)"""
import json

MAX_ITEMS = 50


def export_history(hist):
    items = [{"t": t, "name": n, "caption": c} for t, n, c in hist]
    return json.dumps({"version": 1, "items": items}, ensure_ascii=False, indent=2)


def import_history(text, existing):
    """คืน (รายการรวมใหม่, จำนวนที่เพิ่ม) หรือ raise ValueError ถ้าไฟล์ไม่ถูกต้อง"""
    try:
        data = json.loads(text)
    except (TypeError, ValueError):
        raise ValueError("bad json")
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise ValueError("bad shape")
    merged = list(existing)
    seen = {c for _, _, c in merged}
    added = 0
    for it in items:
        if not isinstance(it, dict):
            continue
        t, n, c = it.get("t"), it.get("name"), it.get("caption")
        if not all(isinstance(x, str) for x in (t, n, c)) or not c.strip() or c in seen:
            continue
        merged.append((t[:20], n[:120], c[:6000]))
        seen.add(c)
        added += 1
    return merged[:MAX_ITEMS], added
