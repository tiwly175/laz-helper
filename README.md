# LAZ HELPER v4.1

ไฟล์ใน GitHub (ต้องมีครบ ไว้ที่รากของ repo):

```
app.py            หน้าแอป
captions.py       สร้างแคปชั่น / ตรวจคำเสี่ยง / พรีเซ็ตแพลตฟอร์ม
media.py          ดึงชื่อ ราคา รูป คลิป
ai_helper.py      โหมด AI (ไม่บังคับ)
i18n.py           ข้อความ ไทย/อังกฤษ
theme.py          ธีมและแอนิเมชัน
guard.py          ตัวจำกัดการเรียก + เช็กรหัสผ่าน   (ใหม่)
library.py        ส่งออก/นำเข้าประวัติ JSON          (ใหม่)
batch.py          โหมดหลายสินค้า                      (ใหม่)
requirements.txt
.streamlit/config.toml
```

Secrets (Streamlit Cloud -> Settings -> Secrets) ทั้งหมดไม่บังคับ:

```toml
ANTHROPIC_API_KEY = "sk-ant-..."   # เปิดโหมด AI
AI_DAILY_LIMIT = 30                # โควตา AI ต่อวัน (นับรวมทุกคน)
APP_PASSWORD = "ตั้งรหัสของคุณ"     # ล็อกทั้งแอป
FETCH_HOURLY_LIMIT = 120           # จำกัดการดึงข้อมูล Lazada ต่อชั่วโมง (รวมทุกคน)
```

ค่าที่จำไว้ใน URL: ?lang=th|en&theme=auto|light|dark|dim|comfort&accent=orange&text_size=s|m|l&platform=general|facebook|instagram|tiktok|x
