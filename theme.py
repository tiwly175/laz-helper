"""ธีม + แอนิเมชัน (CSS) ปรับตามธีม/สีหลัก/ความสว่าง/โหมดลดแอนิเมชัน"""

PALETTES = {
    "light": dict(bg="#f6f7fb", card="#ffffff", text="#1b1d29", muted="#6b7080",
                  border="#e3e5ee", inp="#ffffff", code="#f0f2f8",
                  shadow="0 6px 22px rgba(20,24,40,.08)"),
    "dark": dict(bg="#0e1016", card="#181b24", text="#ebedf5", muted="#9aa0b4",
                 border="#2a2e3b", inp="#12151c", code="#10131a",
                 shadow="0 6px 22px rgba(0,0,0,.45)"),
    # หรี่แสง: คอนทราสต์ต่ำ สีนุ่ม ไม่จ้า เหมาะใช้ตอนกลางคืน
    "dim": dict(bg="#15161a", card="#1c1d22", text="#b0b4be", muted="#7d818c",
                border="#292b32", inp="#16171b", code="#131418",
                shadow="0 4px 14px rgba(0,0,0,.35)"),
    # ถนอมสายตา: โทนกระดาษอุ่น
    "comfort": dict(bg="#f2e9d8", card="#faf3e4", text="#4a4033", muted="#7d705d",
                    border="#e0d3b9", inp="#fbf6ea", code="#efe5cf",
                    shadow="0 6px 18px rgba(90,70,30,.12)"),
}

ACCENTS = {
    "orange": ("#ff6a2b", "#ff9a3c"),
    "blue": ("#2f6bff", "#45a0ff"),
    "green": ("#16a34a", "#3fcf7a"),
    "pink": ("#e63a8a", "#ff7ab6"),
    "purple": ("#7c4dff", "#b388ff"),
}


def _vars(p):
    return (f"--bg:{p['bg']};--card:{p['card']};--text:{p['text']};--muted:{p['muted']};"
            f"--border:{p['border']};--inp:{p['inp']};--code:{p['code']};--shadow:{p['shadow']};")


TEXT_SIZES = {"s": "93.75%", "m": "100%", "l": "112.5%"}


def build_css(theme="auto", accent="orange", brightness=100, warm=False, reduce_motion=False, text_size="m"):
    a1, a2 = ACCENTS.get(accent, ACCENTS["orange"])
    if theme == "auto":
        root = (f":root{{{_vars(PALETTES['light'])}color-scheme:light;}}"
                f"@media (prefers-color-scheme: dark){{:root{{{_vars(PALETTES['dark'])}color-scheme:dark;}}}}")
    else:
        p = PALETTES.get(theme, PALETTES["light"])
        scheme = "light" if theme in ("light", "comfort") else "dark"
        root = f":root{{{_vars(p)}color-scheme:{scheme};}}"

    dim_alpha = round(min(max((100 - int(brightness)) / 100, 0), 0.6), 2)
    motion = "" if not reduce_motion else (
        "*,*::before,*::after{animation:none!important;transition:none!important;scroll-behavior:auto!important}")

    css = f"""
{root}
:root{{--a1:{a1};--a2:{a2};}}
html{{font-size:{TEXT_SIZES.get(text_size, "100%")}}}
@media (prefers-reduced-motion: reduce){{*,*::before,*::after{{animation:none!important;transition:none!important}}}}
{motion}

/* ---------- โครงหน้า ---------- */
.stApp{{background:var(--bg)!important;color:var(--text)}}
[data-testid="stHeader"]{{background:transparent!important}}
footer,[data-testid="stDecoration"]{{visibility:hidden;height:0}}
.block-container{{max-width:1120px!important;padding:1.6rem 1.4rem 5rem!important}}
@media (max-width:640px){{.block-container{{padding:.8rem .75rem 4.5rem!important}}}}

.stApp,.stApp p,.stApp li,.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp label,
.stApp [data-testid="stWidgetLabel"] *,.stApp [data-testid="stMarkdownContainer"]{{color:var(--text)!important}}
.stApp [data-testid="stCaptionContainer"],.stApp [data-testid="stCaptionContainer"] *{{color:var(--muted)!important}}

/* ---------- ช่องกรอก ---------- */
.stApp [data-baseweb="input"],.stApp [data-baseweb="base-input"],.stApp [data-baseweb="textarea"]{{
  background:var(--inp)!important;border-color:var(--border)!important;border-radius:12px!important;transition:box-shadow .2s,border-color .2s}}
.stApp [data-baseweb="input"]:focus-within,.stApp [data-baseweb="textarea"]:focus-within{{
  border-color:var(--a1)!important;box-shadow:0 0 0 3px color-mix(in srgb,var(--a1) 25%,transparent)}}
.stApp input,.stApp textarea{{color:var(--text)!important;-webkit-text-fill-color:var(--text)!important}}
.stApp input::placeholder,.stApp textarea::placeholder{{color:var(--muted)!important;-webkit-text-fill-color:var(--muted)!important;opacity:.85}}
.stApp [data-baseweb="select"]>div{{background:var(--inp)!important;border-color:var(--border)!important;border-radius:12px!important}}
.stApp [data-baseweb="select"] *{{color:var(--text)!important}}
.stApp [data-baseweb="select"] svg{{fill:var(--muted)!important}}
[data-baseweb="popover"] [data-baseweb="menu"],[data-baseweb="popover"] ul,[data-testid="stPopoverBody"]{{
  background:var(--card)!important;color:var(--text)!important}}
[data-baseweb="popover"] li,[data-baseweb="popover"] li *{{color:var(--text)!important}}
[data-baseweb="popover"] li:hover,[data-baseweb="popover"] li[aria-selected="true"]{{background:var(--code)!important}}
[data-testid="stPopoverBody"] *{{color:var(--text)!important}}
[data-testid="stPopoverBody"]{{border:1px solid var(--border)!important;border-radius:14px!important}}
.stApp [data-baseweb="checkbox"] *{{color:var(--text)!important}}
.stApp [data-testid="stFileUploaderDropzone"]{{background:var(--inp)!important;border:1px dashed var(--border)!important;border-radius:12px}}
.stApp [data-testid="stFileUploaderDropzone"] *{{color:var(--muted)!important}}

/* ---------- ปุ่ม ---------- */
.stApp [data-testid^="stBaseButton"]{{border-radius:12px!important;font-weight:600;
  transition:transform .15s ease,box-shadow .2s ease,filter .2s ease}}
.stApp [data-testid^="stBaseButton"]:hover{{transform:translateY(-1px);box-shadow:var(--shadow)}}
.stApp [data-testid^="stBaseButton"]:active{{transform:translateY(0) scale(.97)}}
.stApp [data-testid="stBaseButton-secondary"],.stApp [data-testid="stBaseButton-segmented_control"]{{
  background:var(--card)!important;border:1px solid var(--border)!important;color:var(--text)!important}}
.stApp [data-testid="stBaseButton-primary"],.stApp [data-testid="stBaseButton-segmented_controlActive"],
.stApp button[kind="primary"]{{background:linear-gradient(135deg,var(--a1),var(--a2))!important;
  color:#fff!important;border:none!important;background-size:200% 200%}}
.stApp [data-testid="stBaseButton-primary"]:hover{{animation:laz-shift 2.2s ease infinite;filter:brightness(1.05)}}
.stApp [data-testid^="stBaseButton"] p{{color:inherit!important}}
.stApp [data-testid="stBaseButton-primary"] p,.stApp [data-testid="stBaseButton-segmented_controlActive"] p{{color:#fff!important}}
.stApp [data-testid^="stBaseButton"]:disabled{{opacity:.45;transform:none;box-shadow:none}}

/* ---------- แท็บ / โค้ด / expander ---------- */
.stApp button[data-baseweb="tab"] p{{color:var(--muted)!important;font-weight:600}}
.stApp button[data-baseweb="tab"][aria-selected="true"] p{{color:var(--text)!important}}
.stApp [data-baseweb="tab-highlight"]{{background:var(--a1)!important;height:3px;border-radius:3px}}
.stApp [data-baseweb="tab-border"]{{background:var(--border)!important}}
.stApp [data-testid="stCode"],.stApp [data-testid="stCode"] pre{{background:var(--code)!important;border-radius:14px!important}}
.stApp [data-testid="stCode"]{{border:1px solid var(--border);animation:laz-pop .35s ease both}}
.stApp [data-testid="stCode"] code,.stApp [data-testid="stCode"] code *{{color:var(--text)!important;font-size:.95rem;line-height:1.7}}
.stApp [data-testid="stExpander"]{{background:var(--card)!important;border:1px solid var(--border)!important;border-radius:14px!important}}
.stApp [data-testid="stExpander"] summary,.stApp [data-testid="stExpander"] summary *{{color:var(--text)!important}}
.stApp [data-testid="stProgress"] div[role="progressbar"]>div{{background:var(--a1)!important}}

/* ---------- แอนิเมชันเข้าจอ ---------- */
.element-container{{animation:laz-up .38s ease both}}
@keyframes laz-up{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
@keyframes laz-pop{{from{{opacity:0;transform:scale(.97)}}to{{opacity:1;transform:none}}}}
@keyframes laz-shift{{0%{{background-position:0% 50%}}50%{{background-position:100% 50%}}100%{{background-position:0% 50%}}}}
@keyframes laz-float{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-4px)}}}}
@keyframes laz-pulse{{0%,100%{{box-shadow:0 0 0 0 color-mix(in srgb,var(--a1) 45%,transparent)}}70%{{box-shadow:0 0 0 10px transparent}}}}

/* ---------- ส่วนประกอบของแอป ---------- */
.laz-hero{{display:flex;align-items:center;gap:.7rem;margin:.2rem 0 .1rem}}
.laz-logo{{font-size:2rem;animation:laz-float 3.2s ease-in-out infinite}}
.laz-title{{font-size:1.9rem;font-weight:800;letter-spacing:.3px;line-height:1.1;
  background:linear-gradient(90deg,var(--a1),var(--a2));-webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;color:transparent}}
.laz-sub{{color:var(--muted)!important;font-size:.92rem;margin:.1rem 0 .6rem}}
@media (max-width:640px){{.laz-title{{font-size:1.45rem}}.laz-logo{{font-size:1.6rem}}}}

.laz-steps{{display:flex;gap:.5rem;margin:.4rem 0 1rem;flex-wrap:wrap}}
.laz-step{{display:flex;align-items:center;gap:.45rem;padding:.35rem .8rem;border-radius:999px;
  background:var(--card);border:1px solid var(--border);color:var(--muted)!important;font-size:.85rem;transition:all .3s}}
.laz-step b{{display:inline-flex;width:1.35rem;height:1.35rem;border-radius:50%;align-items:center;justify-content:center;
  background:var(--code);color:var(--muted);font-size:.75rem}}
.laz-step.done{{color:var(--text)!important}}
.laz-step.done b{{background:var(--a1);color:#fff}}
.laz-step.now{{border-color:var(--a1);color:var(--text)!important}}
.laz-step.now b{{background:var(--a1);color:#fff;animation:laz-pulse 1.8s infinite}}

.laz-sec{{font-weight:700;font-size:1.05rem;margin:.9rem 0 .4rem;display:flex;align-items:center;gap:.5rem}}
.laz-sec::after{{content:"";flex:1;height:1px;background:var(--border)}}

.laz-card{{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:.8rem 1rem;
  box-shadow:var(--shadow);margin:.3rem 0 .8rem;animation:laz-pop .35s ease both;line-height:1.7}}
.laz-card b{{color:var(--text)}}
.laz-empty{{border:2px dashed var(--border);border-radius:16px;padding:1.6rem 1rem;text-align:center;
  color:var(--muted)!important}}

.notice{{border-radius:12px;padding:.6rem .85rem;margin:.35rem 0;font-size:.92rem;line-height:1.55;
  border-left:4px solid;animation:laz-up .3s ease both;color:var(--text)!important}}
.notice-info{{background:rgba(59,130,246,.12);border-color:#3b82f6}}
.notice-success{{background:rgba(34,197,94,.13);border-color:#22c55e}}
.notice-warning{{background:rgba(245,158,11,.15);border-color:#f59e0b}}
.notice-error{{background:rgba(239,68,68,.14);border-color:#ef4444}}

.gallery{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.6rem;margin:.4rem 0 .8rem}}
@media (max-width:640px){{.gallery{{grid-template-columns:repeat(2,1fr)}}}}
.g-item{{position:relative;display:block;border-radius:14px;overflow:hidden;border:1px solid var(--border);
  background:var(--code);aspect-ratio:1/1;animation:laz-pop .4s ease both;box-shadow:var(--shadow)}}
.g-item img{{width:100%;height:100%;object-fit:cover;display:block;transition:transform .35s ease}}
.g-item:hover img{{transform:scale(1.06)}}
.g-n{{position:absolute;left:.4rem;top:.4rem;background:rgba(0,0,0,.55);color:#fff;border-radius:999px;
  padding:.05rem .5rem;font-size:.72rem}}

/* ---------- ลดความสว่าง / กรองแสงสีฟ้า ---------- */
.laz-dim,.laz-warm{{position:fixed;inset:0;pointer-events:none;z-index:99999}}
.laz-dim{{background:#000;opacity:{dim_alpha}}}
.laz-warm{{background:rgba(255,150,40,.16);mix-blend-mode:multiply;display:{'block' if warm else 'none'}}}
"""
    return f"<style>{css}</style><div class='laz-dim'></div><div class='laz-warm'></div>"
