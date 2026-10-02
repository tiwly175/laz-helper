"""ตัวกันการใช้งานเกินเหตุ: จำกัดจำนวนครั้งต่อช่วงเวลา + เช็กรหัสผ่านแบบเวลาคงที่"""
import hmac
import threading
import time
from collections import deque


class WindowLimiter:
    """อนุญาตไม่เกิน limit ครั้งในช่วง window วินาที (นับแบบเลื่อนตามเวลา)"""

    def __init__(self, limit, window_s):
        self.limit = int(limit)
        self.window = float(window_s)
        self.hits = deque()
        self._lock = threading.Lock()

    def _prune(self, now):
        while self.hits and now - self.hits[0] >= self.window:
            self.hits.popleft()

    def allow(self, now=None):
        now = time.time() if now is None else now
        with self._lock:
            self._prune(now)
            if len(self.hits) >= self.limit:
                return False
            self.hits.append(now)
            return True

    def remaining(self, now=None):
        now = time.time() if now is None else now
        with self._lock:
            self._prune(now)
            return max(self.limit - len(self.hits), 0)


def check_password(supplied, expected):
    """เทียบรหัสแบบเวลาคงที่ ถ้าไม่ได้ตั้งรหัสไว้ (expected ว่าง) ถือว่าผ่าน"""
    if not expected:
        return True
    return hmac.compare_digest((supplied or "").encode("utf-8"), str(expected).encode("utf-8"))
