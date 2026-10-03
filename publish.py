"""ส่งต่อ/โพสต์: ลิงก์แชร์ (ไม่ต้องใช้รหัสใดๆ) + โพสต์ลงเพจ Facebook ผ่าน Graph API ทางการ

สถานะ: เขียนตามเอกสาร Graph API ที่ทราบ ยังไม่เคยทดสอบกับเพจจริง
 - ใช้ได้เฉพาะ "เพจ" ที่คุณเป็นแอดมิน (Facebook ไม่เปิด API โพสต์ลงโปรไฟล์ส่วนตัวหรือกลุ่ม)
 - รหัส (Page Access Token) ส่งแบบ POST body ไปที่ graph.facebook.com เท่านั้น ไม่ถูกบันทึก/แสดง
"""
import json
import re
from urllib.parse import quote

import requests

GRAPH_HOST = "https://graph.facebook.com"
DEFAULT_VERSION = "v23.0"  # ตั้งใหม่ได้ด้วย Secret FB_GRAPH_VERSION ถ้าเวอร์ชันนี้ถูกยกเลิก
VERSION_RE = re.compile(r"^v\d{1,2}\.\d{1,2}$")
PAGE_ID_RE = re.compile(r"^\d{5,25}$")
MAX_PHOTOS = 10
MAX_URL_LEN = 7000  # ลิงก์แชร์ยาวเกินนี้หลายแอปไม่รับ


def share_links(text):
    """คืน dict ชื่อ->URL (ไม่มีรายการที่ยาวเกินไป)"""
    enc = quote(text or "", safe="")
    out = {
        "line": "https://line.me/R/msg/text/?" + enc,
        "x": "https://x.com/intent/post?text=" + enc,
    }
    return {k: v for k, v in out.items() if len(v) <= MAX_URL_LEN}


def creds_ok(creds):
    return bool(creds and PAGE_ID_RE.match(str(creds.get("page_id", ""))) and creds.get("token"))


def _version(creds):
    v = str(creds.get("version") or DEFAULT_VERSION)
    return v if VERSION_RE.match(v) else DEFAULT_VERSION


def _redact(text, token):
    text = str(text or "")
    return text.replace(token, "***") if token else text


def _call(creds, path, data):
    """POST ไป Graph API คืน (ok, json|code, detail)"""
    token = creds["token"]
    url = f"{GRAPH_HOST}/{_version(creds)}/{path}"
    body = dict(data)
    body["access_token"] = token
    try:
        r = requests.post(url, data=body, timeout=45, allow_redirects=False)
    except requests.RequestException:
        return False, "conn", ""
    try:
        j = r.json()
    except ValueError:
        return False, "api", f"HTTP {r.status_code}"
    if isinstance(j, dict) and isinstance(j.get("error"), dict):
        e = j["error"]
        code = e.get("code")
        msg = _redact(e.get("message", ""), token)[:200]
        if code == 190:
            return False, "auth", msg
        if code in (10, 200, 283) or (isinstance(code, int) and 200 <= code <= 299):
            return False, "perm", msg
        if code in (4, 17, 32, 341, 368, 613):
            return False, "rate", msg
        return False, "api", msg
    if r.status_code != 200 or not isinstance(j, dict):
        return False, "api", f"HTTP {r.status_code}"
    return True, j, ""


def _https(u):
    return isinstance(u, str) and u.startswith("https://") and len(u) < 2000


def post_to_page(creds, message, image_urls=(), video_url=None):
    """โพสต์ข้อความ (+รูปหลายรูป หรือ +วิดีโอ 1 คลิป) ลงเพจ
    คืน {"ok": bool, "id", "photos", "photos_failed", "link"} หรือ {"ok": False, "code", "detail"}"""
    if not creds_ok(creds):
        return {"ok": False, "code": "creds", "detail": ""}
    message = (message or "").strip()
    if not message:
        return {"ok": False, "code": "empty", "detail": ""}
    page = str(creds["page_id"])

    if video_url:
        if not _https(video_url):
            return {"ok": False, "code": "video", "detail": ""}
        ok, res, detail = _call(creds, f"{page}/videos", {"file_url": video_url, "description": message})
        if not ok:
            return {"ok": False, "code": res, "detail": detail}
        vid = str(res.get("id", ""))
        return {"ok": True, "id": vid, "photos": 0, "photos_failed": 0,
                "link": f"https://www.facebook.com/{vid}" if vid else ""}

    imgs = [u for u in dict.fromkeys(image_urls or ()) if _https(u)][:MAX_PHOTOS]
    media_ids, failed, last = [], 0, ("", "")
    for u in imgs:
        ok, res, detail = _call(creds, f"{page}/photos", {"url": u, "published": "false"})
        if ok and res.get("id"):
            media_ids.append(str(res["id"]))
        else:
            failed += 1
            last = (res if not ok else "api", detail)
            if not ok and res in ("auth", "perm", "rate", "conn"):
                return {"ok": False, "code": res, "detail": detail}  # ปัญหาระดับบัญชี หยุดทันที
    if imgs and not media_ids:
        return {"ok": False, "code": "photo", "detail": last[1]}

    data = {"message": message}
    if media_ids:
        data["attached_media"] = json.dumps([{"media_fbid": i} for i in media_ids])
    ok, res, detail = _call(creds, f"{page}/feed", data)
    if not ok:
        return {"ok": False, "code": res, "detail": detail}
    pid = str(res.get("id", ""))
    return {"ok": True, "id": pid, "photos": len(media_ids), "photos_failed": failed,
            "link": f"https://www.facebook.com/{pid}" if pid else ""}
