# LAZ HELPER v5 (Lazada / Shopee / เว็บอื่น)

ไฟล์ที่ต้องอัปขึ้น GitHub (รากของ repo ทั้งหมด):

```
app.py  stores.py  shopee_api.py  media.py  captions.py  batch.py
i18n.py  theme.py  guard.py  library.py  ai_helper.py  publish.py  autopoint.py
requirements.txt  .streamlit/config.toml
```
ลบไฟล์เก่าที่ไม่อยู่ในรายการนี้ออก แล้ว Streamlit Cloud จะ deploy ใหม่เอง

## Secrets (Settings > Secrets) — ทั้งหมดเป็นตัวเลือก
```toml
APP_PASSWORD = "รหัสผ่านเข้าแอป"
FETCH_HOURLY_LIMIT = 30
ANTHROPIC_API_KEY = "..."      # ถ้าจะใช้ AI เขียนแคปชั่น
AI_DAILY_LIMIT = 20
FB_PAGE_ID = "เลขไอดีเพจ"      # ถ้าจะโพสต์ลงเพจ Facebook โดยตรง (ไม่บังคับ)
FB_PAGE_TOKEN = "Page Access Token"
POST_DAILY_LIMIT = 10          # จำนวนโพสต์สูงสุดต่อวัน
SHOPEE_APP_ID = "..."          # ต้องมีบัญชี Shopee Affiliate Open API ที่อนุมัติแล้ว
SHOPEE_APP_SECRET = "..."
SHOPEE_API_ENDPOINT = "https://open-api.affiliate.shopee.co.th/graphql"  # ไม่ใส่ก็ได้
```

## สถานะแต่ละร้าน
- Lazada: ดึงชื่อ/ราคา/รูป/วิดีโอจากหน้าเว็บ (อาจถูกบล็อกจาก IP ของ Cloud)
- Shopee: API ให้ชื่อ ราคา รูปหลัก 1 รูป + สร้างลิงก์ affiliate ได้ จากนั้นพยายามดึงรูป/วิดีโอเพิ่ม (สูงสุด 30 รูป 8 คลิป) จากหน้าสินค้า ถ้า Shopee กันบอทจะได้แค่รูปหลัก (ยังไม่ได้ทดสอบจริง)
  ** endpoint ไทยและชื่อ argument เป็นการอนุมาน ยังไม่เคยทดสอบกับ API จริง **
- เว็บอื่น: อ่าน og:/JSON-LD แบบทั่วไป ใช้ไม่ได้กับเว็บที่ใช้ JS/กันบอท
  แต่สร้างแคปชั่นได้เสมอ

## เพิ่มร้านใหม่
เพิ่มรายการใน `stores.STORES` (host_re + แท็ก) แล้วเพิ่มข้อความ `store_<id>` ใน `i18n.py`
(ถ้ามี API ให้เขียนตัวดึงแยกแบบ `shopee_api.py` แล้วเรียกใน `stores.fetch_product`)

## ส่งต่อ / โพสต์ (ใหม่)
- ปุ่มแชร์ LINE / X / เมนูแชร์ของมือถือ: ใช้ได้ทันที ไม่ต้องตั้งค่า
- โพสต์ลงเพจ Facebook โดยตรง (Graph API ทางการ) ใช้ได้เฉพาะเพจที่คุณเป็นแอดมิน ไม่รองรับโปรไฟล์ส่วนตัว/กลุ่ม
  ขั้นตอนคร่าวๆ (หน้าจอ Meta อาจเปลี่ยน ให้ยึดเอกสารของ Meta ล่าสุด):
  1. developers.facebook.com สร้างแอป แล้วเปิด Graph API Explorer
  2. ขอสิทธิ์ pages_show_list, pages_read_engagement, pages_manage_posts
  3. เรียก `me/accounts` จะได้ id และ access_token ของเพจ ใส่เป็น FB_PAGE_ID / FB_PAGE_TOKEN
  4. ถ้าใช้กับเพจที่ไม่ใช่ของคุณเอง แอปต้องผ่าน App Review
- ระบบกันพลาด: ต้องติ๊กยืนยันก่อนทุกครั้ง, กันโพสต์ซ้ำข้อความเดิม, จำกัดจำนวนต่อวัน, บล็อกถ้าแคปชั่นค้างปีกกา/ข้อมูลเปลี่ยนหลังสร้าง/มีคำไม่เหมาะสม
- ยังไม่ได้ทำ: Instagram, LINE OA broadcast, TikTok, ตั้งเวลาโพสต์ (Streamlit Cloud ไม่มีตัวตั้งเวลาในตัว)
- สถานะ: ยังไม่เคยทดสอบกับเพจ Facebook จริง ลองกับเพจทดสอบก่อน

## วางลิงก์แล้วจบ (ใหม่)
- ปุ่ม "⚡ ทำให้เลย": วางแค่ลิงก์ (ลิงก์ Affiliate อย่างเดียวก็ได้) กดปุ่มเดียว แอปดึงชื่อ ราคา ส่วนลด รูป เติมจุดเด่น/โปรโมชัน แล้วสร้างแคปชั่นต่อ
- ส่วนลด: คำนวณจากราคาปกติเทียบราคาขายที่พบในหน้าสินค้า (ลดอย่างน้อย 5% ถึงจะใส่)
- จุดเด่นอัตโนมัติ: ใช้เฉพาะคำคุณสมบัติ/สเปคที่มีในชื่อสินค้า และคะแนนรีวิวที่หน้าเว็บให้มา ไม่แต่งเพิ่ม ถ้าข้อมูลไม่พอจะเว้นว่างให้กรอกเอง
- โครงข้อมูลหน้าเว็บ Lazada/Shopee เปลี่ยนได้ตลอด ถ้าราคาหรือส่วนลดไม่ขึ้น แจ้งตัวอย่างลิงก์มาเพื่อปรับ
