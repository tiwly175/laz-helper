import io
import zipfile
from datetime import date, datetime
from html import escape

import streamlit as st
import streamlit.components.v1 as components

import ai_helper as ai
import batch
import captions as cp
import guard
import library
import media
from i18n import STR, make_t
from theme import ACCENTS, build_css

st.set_page_config(page_title="LAZ HELPER", page_icon="⚡", layout="wide",
                   initial_sidebar_state="collapsed")

BATCH_MAX = 10
THEMES = ["auto", "light", "dark", "dim", "comfort"]
ACCENT_IDS = list(ACCENTS.keys())
SIZES = ["s", "m", "l"]
PLATFORM_IDS = list(cp.PLATFORMS.keys())


def secret(name, default=""):
    try:
        return st.secrets[name]
    except Exception:
        return default


# ---------------------------------------------------------------
# ตั้งค่าผู้ใช้ (จำไว้ใน URL เปิดใหม่/บุ๊กมาร์กแล้วยังอยู่)
# ---------------------------------------------------------------
def _init(key, default, allowed=None, cast=str):
    if key in st.session_state:
        return
    raw = st.query_params.get(key, default)
    try:
        val = cast(raw)
    except (TypeError, ValueError):
        val = default
    st.session_state[key] = val if (allowed is None or val in allowed) else default


_truthy = lambda v: str(v) in ("1", "True", "true")
_init("lang", "th", ["th", "en"])
_init("theme", "auto", THEMES)
_init("accent", "orange", ACCENT_IDS)
_init("brightness", 100, cast=lambda v: min(100, max(40, int(v))))
_init("warm", False, cast=_truthy)
_init("reduce_motion", False, cast=_truthy)
_init("text_size", "m", SIZES)
_init("platform", "general", PLATFORM_IDS)
_init("signature", "", cast=lambda v: str(v)[:120])

PREF_KEYS = ("lang", "theme", "accent", "brightness", "warm", "reduce_motion",
             "text_size", "platform", "signature", "authed")
t = make_t(st.session_state["lang"])


def notice(level, text):
    st.markdown(f"<div class='notice notice-{level}'>{escape(text)}</div>", unsafe_allow_html=True)


def reset_all():
    keep = {k: st.session_state[k] for k in PREF_KEYS if k in st.session_state}
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.session_state.update(keep)


def reason_text(code, http=""):
    if code == "http":
        return t("err_http", code=http)
    return t(f"err_{code}") if f"err_{code}" in STR["th"] else t("err_conn")


def render_checks(checks, levels=None):
    for level, code, params in checks:
        if levels and level not in levels:
            continue
        p = dict(params)
        if code == "v_cat_detected":
            p["label"] = cp.cat_label(p.pop("cat"), st.session_state["lang"])
        notice(level, t(code, **p))


# ---------------------------------------------------------------
# แคช + ตัวจำกัดการเรียก
# ---------------------------------------------------------------
class _NotCached(Exception):
    def __init__(self, info):
        super().__init__("not cached")
        self.info = info


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_ok(url_or_text):
    info = media.fetch_product(url_or_text)
    if info["error"] or not (info["images"] or info["videos"]):
        raise _NotCached(info)  # ล้มเหลว/ได้ไม่ครบ = ไม่แคช กดดึงใหม่แล้วลองจริงทันที
    return info


def cached_product(url_or_text):
    try:
        return _fetch_ok(url_or_text)
    except _NotCached as e:
        return e.info


@st.cache_data(ttl=900, show_spinner=False, max_entries=64)
def cached_bytes(url, max_bytes):
    return media.download_bytes(url, max_bytes)


@st.cache_resource
def _fetch_limiter():
    return guard.WindowLimiter(int(secret("FETCH_HOURLY_LIMIT", 120)), 3600)


@st.cache_resource
def _fail_limiter():
    return guard.WindowLimiter(5, 300)


def fetch_allowed():
    """ผ่านทั้งโควตารวมของแอปและโควตาของผู้ใช้คนนี้ (กัน Lazada บล็อกเพราะยิงถี่)"""
    sess = st.session_state.setdefault("_fetch_sess", guard.WindowLimiter(30, 3600))
    return _fetch_limiter().allow() and sess.allow()


IMG_MAX = 15 * 1024 * 1024
VID_MAX = 40 * 1024 * 1024


def build_zip(images, videos, uploads, caption, progress):
    buf = io.BytesIO()
    n_img = n_vid = skipped = 0
    total = len(images) + len(videos)
    done = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("caption.txt", caption or "")
        for i, u in enumerate(images, 1):
            done += 1
            progress(done, total)
            try:
                data, ctype = cached_bytes(u, IMG_MAX)
                z.writestr(f"image_{i}{media.guess_ext(u, ctype, '.jpg')}", data)
                n_img += 1
            except Exception:
                skipped += 1
        for i, v in enumerate(videos, 1):
            done += 1
            progress(done, total)
            try:
                data, ctype = cached_bytes(v, VID_MAX)
                z.writestr(f"video_{i}{media.guess_ext(v, ctype, '.mp4')}", data)
                n_vid += 1
            except Exception:
                skipped += 1
        for j, f in enumerate(uploads or [], 1):
            z.writestr(f"upload_{j}_{f.name}", f.getvalue())
            n_img += 1
    return buf.getvalue(), n_img, n_vid, skipped


# ---------------------------------------------------------------
# ส่วนหัว + ตั้งค่า
# ---------------------------------------------------------------
st.markdown(
    build_css(st.session_state["theme"], st.session_state["accent"],
              st.session_state["brightness"], st.session_state["warm"],
              st.session_state["reduce_motion"], st.session_state["text_size"]),
    unsafe_allow_html=True,
)

h1, h2, h3, h4 = st.columns([5, 2, 2, 3], vertical_alignment="center")
with h1:
    st.markdown(
        f"<div class='laz-hero'><div class='laz-logo'>⚡</div>"
        f"<div class='laz-title'>{escape(t('app_title'))}</div></div>"
        f"<div class='laz-sub'>{escape(t('tagline'))}</div>",
        unsafe_allow_html=True,
    )
with h2:
    st.segmented_control("lang", ["th", "en"], key="lang_ctl",
                         default=st.session_state["lang"],
                         format_func=lambda x: "ไทย" if x == "th" else "EN",
                         label_visibility="collapsed")
    chosen_lang = st.session_state.get("lang_ctl")
    if chosen_lang and chosen_lang != st.session_state["lang"]:
        st.session_state["lang"] = chosen_lang
        st.rerun()
with h3:
    with st.popover(t("settings"), use_container_width=True):
        st.selectbox(t("theme"), THEMES, key="theme", format_func=lambda x: t(f"theme_{x}"))
        st.selectbox(t("accent"), ACCENT_IDS, key="accent", format_func=lambda x: t(f"accent_{x}"))
        st.selectbox(t("text_size"), SIZES, key="text_size", format_func=lambda x: t(f"size_{x}"))
        st.slider(t("brightness"), 40, 100, key="brightness", step=5, format="%d%%")
        st.checkbox(t("warm"), key="warm")
        st.checkbox(t("reduce_motion"), key="reduce_motion")
with h4:
    st.button(t("reset"), on_click=reset_all, use_container_width=True)

st.query_params.update({
    "lang": st.session_state["lang"], "theme": st.session_state["theme"],
    "accent": st.session_state["accent"], "brightness": str(st.session_state["brightness"]),
    "warm": "1" if st.session_state["warm"] else "0",
    "reduce_motion": "1" if st.session_state["reduce_motion"] else "0",
    "text_size": st.session_state["text_size"], "platform": st.session_state["platform"],
    "signature": st.session_state["signature"],
})

lang = st.session_state["lang"]

# ---------------------------------------------------------------
# ล็อกแอปด้วยรหัสผ่าน (ไม่บังคับ: ตั้ง APP_PASSWORD ใน Secrets)
# ---------------------------------------------------------------
app_pw = str(secret("APP_PASSWORD", ""))
if app_pw and not st.session_state.get("authed"):
    st.markdown(f"<div class='laz-sec'>{escape(t('pw_title'))}</div>", unsafe_allow_html=True)
    typed = st.text_input(t("pw_label"), type="password", key="pw_input")
    if st.button(t("pw_btn"), type="primary"):
        if _fail_limiter().remaining() == 0:
            notice("error", t("pw_locked"))
        elif guard.check_password(typed, app_pw):
            st.session_state["authed"] = True
            st.rerun()
        else:
            _fail_limiter().allow()  # บันทึกครั้งที่ผิด
            notice("error", t("pw_wrong"))
    st.stop()

# ตัวบอกขั้นตอน
has_aff = bool((st.session_state.get("aff_link") or "").strip())
has_caps = bool(st.session_state.get("captions"))
cur = 3 if has_caps else (2 if has_aff else 1)
steps = "".join(
    f"<div class='laz-step {'done' if n < cur else ('now' if n == cur else '')}'>"
    f"<b>{'✓' if n < cur else n}</b>{escape(t(f'step_{n}'))}</div>"
    for n in (1, 2, 3)
)
st.markdown(f"<div class='laz-steps'>{steps}</div>", unsafe_allow_html=True)

# ---------------------------------------------------------------
# AI (ไม่บังคับ): เปิดเมื่อมี ANTHROPIC_API_KEY ใน Secrets
# ---------------------------------------------------------------
ai_key = secret("ANTHROPIC_API_KEY", "")
try:
    ai_limit = int(secret("AI_DAILY_LIMIT", 30))
except (TypeError, ValueError):
    ai_limit = 30


@st.cache_resource
def _quota():
    return {"day": "", "n": 0}


def ai_left():
    q = _quota()
    today = date.today().isoformat()
    if q["day"] != today:
        q["day"], q["n"] = today, 0
    return max(ai_limit - q["n"], 0)


# ---------------------------------------------------------------
# เลย์เอาต์: PC = 2 คอลัมน์ / มือถือ = เรียงลง
# ---------------------------------------------------------------
left, right = st.columns([5, 6], gap="large")

with left:
    st.markdown(f"<div class='laz-sec'>{escape(t('sec_inputs'))}</div>", unsafe_allow_html=True)
    aff_link = st.text_input(t("aff_label"), key="aff_link", placeholder=t("aff_ph"))
    prod_link = st.text_input(t("prod_label"), key="prod_link", placeholder=t("prod_ph"),
                              help=t("prod_help"))

    if st.button(t("fetch_btn"), use_container_width=True):
        if not prod_link.strip():
            notice("error", t("need_prod_link"))
        elif not fetch_allowed():
            notice("error", t("fetch_limited"))
        else:
            with st.spinner(t("fetching")):
                info = cached_product(prod_link.strip())
            st.session_state["info"] = info
            st.session_state["zip"] = None
            # สินค้าใหม่ = ล้างของเก่า กันก๊อปข้อความสินค้าก่อนหน้า
            st.session_state["product_name"] = info["title"]
            st.session_state["product_price"] = cp.fmt_price(info["price"])
            st.session_state["product_point"] = ""
            st.session_state["promo"] = ""
            st.session_state.pop("captions", None)
            st.session_state.pop("caption_meta", None)
            st.session_state.pop("checks", None)

    info = st.session_state.get("info")
    if info:
        reason = reason_text(info["error"], info.get("http", "")) if info["error"] else ""
        n_img, n_vid = len(info["images"]), len(info["videos"])
        if n_img or n_vid:
            notice("success", t("fetch_ok", n_img=n_img, n_vid=n_vid))
        elif info["title"]:
            notice("warning", t("fetch_partial", reason=reason or t("err_nodata")))
            st.caption(t("fetch_hint"))
        else:
            notice("warning", t("fetch_fail", reason=reason or t("err_nodata")))
            st.caption(t("fetch_hint"))

    product_name = st.text_input(t("name_label"), key="product_name")
    product_point = st.text_input(t("point_label"), key="product_point", placeholder=t("point_ph"))
    c1, c2 = st.columns(2)
    with c1:
        product_price = st.text_input(t("price_label"), key="product_price", placeholder=t("price_ph"))
    with c2:
        promo = st.text_input(t("promo_label"), key="promo", placeholder=t("promo_ph"))

    detected = cp.detect_category(f"{product_name} {product_point}")
    AUTO = "__auto__"
    cat_choice = st.selectbox(
        t("cat_label"), [AUTO] + list(cp.CATEGORIES.keys()), key="cat_choice",
        format_func=lambda k: t("cat_auto") if k == AUTO else cp.cat_label(k, lang))
    chosen_auto = cat_choice == AUTO
    cat_key = detected if chosen_auto else cat_choice
    if chosen_auto:
        st.caption(t("detected", label=cp.cat_label(cat_key, lang)))

    tone = st.selectbox(t("tone_label"), list(cp.TONES.keys()), key="tone",
                        format_func=lambda k: cp.tone_label(k, lang))
    platform = st.selectbox(t("platform_label"), PLATFORM_IDS, key="platform",
                            format_func=lambda k: t(f"pf_{k}"))
    link_header = st.text_input(t("header_label"), value=t("header_default"), key=f"hdr_{lang}")
    signature = st.text_input(t("signature_label"), key="signature", placeholder=t("signature_ph"),
                              max_chars=120)
    k1, k2 = st.columns(2)
    with k1:
        experienced = st.checkbox(t("experienced"), value=False, help=t("experienced_help"))
    with k2:
        disclose = st.checkbox(t("disclose"), value=True)

    def run_generation(use_ai):
        clean_name, f1 = cp.clean_profanity(product_name)
        clean_point, f2 = cp.clean_profanity(product_point)
        clean_promo, f3 = cp.clean_profanity(promo)
        clean_sig, f4 = cp.clean_profanity(signature)
        removed = f1 + f2 + f3 + f4
        checks = cp.validate_inputs(aff_link, prod_link, clean_name, product_price,
                                    clean_point, cat_key, chosen_auto)
        if removed:
            checks.append(("warning", "v_profanity", {"words": ", ".join(sorted(set(removed)))}))
        if any(level == "error" for level, _, _ in checks):
            st.session_state["captions"] = []
            st.session_state["checks"] = checks
            return

        popts = cp.platform_opts(platform)

        def make(body=None):
            return cp.build_caption(tone, cat_key, clean_name, clean_point, product_price,
                                    clean_promo, aff_link.strip(), link_header,
                                    experienced, disclose, body_override=body,
                                    signature=clean_sig, max_tags=popts["max_tags"],
                                    link_mode=popts["link_mode"])

        caps = []
        if use_ai:
            _quota()["n"] += 1
            with st.spinner(t("ai_spinner")):
                ok, text = ai.generate_body(ai_key, clean_name, clean_point,
                                            cp.CATEGORIES[cat_key]["label"], tone, experienced)
            if ok:
                caps = [make(text)]
                checks.append(("info", "ai_done_note", {}))
            else:
                checks.append(("warning", "ai_fallback", {"reason": t(f"ai_err_{text}")}))
        if not caps:
            tries = 0
            while len(caps) < 3 and tries < 15:
                tries += 1
                c = make()
                if c not in caps:
                    caps.append(c)

        # ตรวจคำเสี่ยงโฆษณาเกินจริงทั้งจากที่กรอกและที่ AI เขียน
        checks += cp.risky_checks("\n".join(caps))

        st.session_state["captions"] = caps
        st.session_state["checks"] = checks
        st.session_state["caption_meta"] = {
            "name": product_name, "aff": aff_link.strip(), "cat": cat_key,
            "price": cp.fmt_price(product_price), "platform": platform,
        }
        hist = st.session_state.setdefault("history", [])
        hist.insert(0, (datetime.now().strftime("%H:%M"), clean_name or "-", caps[0]))
        del hist[library.MAX_ITEMS:]
        st.session_state["scroll"] = True
        st.toast(t("toast_done"))

    if ai_key:
        g1, g2 = st.columns(2)
        with g1:
            go_free = st.button(t("gen_free"), type="primary", use_container_width=True)
        with g2:
            left_n = ai_left()
            go_ai = st.button(t("gen_ai", left=left_n), use_container_width=True, disabled=left_n <= 0)
        st.caption(t("ai_cost_note"))
    else:
        go_free = st.button(t("gen_free"), type="primary", use_container_width=True)
        go_ai = False

    if go_free:
        run_generation(False)
    if go_ai:
        run_generation(True)

# ---------------------------------------------------------------
# ผลลัพธ์
# ---------------------------------------------------------------
with right:
    st.markdown(f"<div id='results-anchor' class='laz-sec'>{escape(t('sec_results'))}</div>",
                unsafe_allow_html=True)
    checks = st.session_state.get("checks")
    caps = st.session_state.get("captions")
    meta = st.session_state.get("caption_meta")

    if not checks and not caps:
        st.markdown(f"<div class='laz-empty'>✨<br>{escape(t('empty_results'))}</div>",
                    unsafe_allow_html=True)

    if checks:
        st.markdown(f"**{t('checks_title')}**")
        render_checks(checks)

    if caps:
        if meta and (meta["name"] != product_name or meta["aff"] != aff_link.strip()
                     or meta["price"] != cp.fmt_price(product_price)):
            notice("error", t("stale_warn"))
        if any("{" in c or "}" in c for c in caps):
            notice("error", t("placeholder_warn"))

        meta_pf = (meta or {}).get("platform", "general")
        st.markdown(f"**{t('caption_title')}**")
        if meta:
            st.markdown(
                f"<div class='laz-card'><b>{escape(t('summary_name'))}:</b> "
                f"{escape(cp.short_name(meta['name']) or '-')}<br>"
                f"<b>{escape(t('summary_cat'))}:</b> {escape(cp.cat_label(meta['cat'], lang))}<br>"
                f"<b>{escape(t('summary_price'))}:</b> {escape(meta['price'] or '-')}</div>",
                unsafe_allow_html=True)
        st.caption(t("caption_hint"))
        tabs = st.tabs([t("variant", n=i) for i in range(1, len(caps) + 1)])
        for tab, c in zip(tabs, caps):
            with tab:
                st.code(c, language=None, wrap_lines=True)
                rep = cp.platform_report(c, meta_pf)
                if rep["over"]:
                    notice("error", t("pf_over", chars=rep["chars"], limit=rep["limit"]))
                else:
                    st.caption(t("pf_count_limit" if rep["limit"] else "pf_count_nolimit",
                                 chars=rep["chars"], limit=rep["limit"], tags=rep["tags"]))
        if meta_pf != "general":
            st.caption(t(f"pf_note_{meta_pf}"))
        if meta_pf == "instagram" and meta:
            st.markdown(f"**{t('link_box_title')}**")
            st.code(meta["aff"], language=None)
        st.download_button(t("download_txt"), data="\n\n-----\n\n".join(caps),
                           file_name="caption.txt", mime="text/plain", use_container_width=True)

    # ประวัติ: ส่งออก/นำเข้า JSON (แอปไม่เก็บถาวร ผู้ใช้เก็บไฟล์เอง)
    with st.expander(t("history_title")):
        up = st.file_uploader(t("hist_import"), type=["json"], key="hist_up")
        if up is not None:
            uid = getattr(up, "file_id", up.name)
            if st.session_state.get("hist_imported_id") != uid:
                st.session_state["hist_imported_id"] = uid
                try:
                    merged, added = library.import_history(
                        up.getvalue().decode("utf-8", "replace"), st.session_state.get("history", []))
                    st.session_state["history"] = merged
                    notice("success", t("hist_imported", n=added))
                except ValueError:
                    notice("error", t("hist_import_err"))
        hist = st.session_state.get("history") or []
        if hist:
            st.download_button(t("hist_export"), data=library.export_history(hist),
                               file_name="laz_history.json", mime="application/json",
                               use_container_width=True)
            for stamp, nm, cap in hist:
                st.caption(f"{stamp} · {cp.short_name(nm, 40)}")
                st.code(cap, language=None, wrap_lines=True)

# มือถือ: เลื่อนไปที่ผลลัพธ์อัตโนมัติหลังสร้างแคปชั่น
if st.session_state.pop("scroll", False):
    components.html(
        "<script>try{const w=window.parent;if(w.innerWidth<800){"
        "const el=w.document.getElementById('results-anchor');"
        "if(el)el.scrollIntoView({behavior:'smooth',block:'start'});}}catch(e){}</script>",
        height=0)

# ---------------------------------------------------------------
# รูปและคลิป (เต็มความกว้าง)
# ---------------------------------------------------------------
info = st.session_state.get("info") or {}
auto_imgs = list(info.get("images", []))
vids = list(info.get("videos", []))

st.markdown(f"<div class='laz-sec'>{escape(t('sec_media'))}</div>", unsafe_allow_html=True)

with st.expander(t("manual_title"), expanded=not (auto_imgs or vids) and bool(info)):
    manual_text = st.text_area(t("manual_urls"), key="manual_urls", height=90)
    manual_imgs = [u for u in (media.norm_img(x.strip()) for x in manual_text.splitlines()) if u]
    if manual_imgs:
        st.caption(t("manual_added", n=len(manual_imgs)))
    uploads = st.file_uploader(t("manual_upload"), type=["jpg", "jpeg", "png", "webp"],
                               accept_multiple_files=True, key="uploads")

imgs = list(dict.fromkeys(auto_imgs + manual_imgs))
chosen_imgs = imgs

if imgs:
    st.caption(t("gallery_hint"))
    cells = "".join(
        f"<a class='g-item' href='{escape(u)}' target='_blank' rel='noopener noreferrer' "
        f"style='animation-delay:{min(i, 11) * 40}ms'>"
        f"<img src='{escape(u)}' loading='lazy' referrerpolicy='no-referrer' alt='{i + 1}'>"
        f"<span class='g-n'>{i + 1}</span></a>"
        for i, u in enumerate(imgs))
    st.markdown(f"<div class='gallery'>{cells}</div>", unsafe_allow_html=True)
    picked = st.multiselect(t("pick_imgs"), list(range(1, len(imgs) + 1)),
                            default=list(range(1, len(imgs) + 1)),
                            key=f"pick_{abs(hash(tuple(imgs)))}")
    chosen_imgs = [imgs[i - 1] for i in picked]

mp4s = [v["url"] for v in vids if v["kind"] == "mp4"]
if imgs or mp4s or uploads:
    inc_vid = st.checkbox(t("zip_include_videos"), value=False) if mp4s else False
    if st.button(t("zip_btn"), use_container_width=True):
        bar = st.progress(0.0, text="")
        data, n_img, n_vid, skipped = build_zip(
            chosen_imgs, mp4s if inc_vid else [], uploads, (caps or [""])[0],
            lambda d, tot: bar.progress(d / max(tot, 1), text=t("zip_progress", i=d, n=tot)))
        bar.empty()
        st.session_state["zip"] = (data, n_img, n_vid, skipped)
    z = st.session_state.get("zip")
    if z:
        data, n_img, n_vid, skipped = z
        if n_img or n_vid:
            st.download_button(t("zip_ready", n_img=n_img, n_vid=n_vid), data=data,
                               file_name="lazada_post.zip", mime="application/zip",
                               use_container_width=True)
        else:
            notice("warning", t("zip_none"))
        if skipped:
            notice("info", t("zip_skipped", n=skipped))

if vids:
    st.markdown(f"**{t('video_title')}**")
    vcols = st.columns(min(len(vids), 3))
    for col, v in zip(vcols, vids):
        with col:
            if v["kind"] == "mp4":
                st.video(v["url"])
            else:
                st.markdown(f"[{t('video_open')}]({v['url']})")
                st.caption(t("video_hls"))

# ---------------------------------------------------------------
# โหมดหลายสินค้า
# ---------------------------------------------------------------
st.markdown(f"<div class='laz-sec'>{escape(t('batch_title'))}</div>", unsafe_allow_html=True)
st.caption(t("batch_help", max=BATCH_MAX))
batch_text = st.text_area(t("batch_label"), key="batch_text", height=130, placeholder=t("batch_ph"))


def run_batch(text):
    items, skipped, errs = batch.parse_batch(text, BATCH_MAX)
    msgs = [("error", t(f"batch_err_{code}", line=line)) for line, code in errs]
    if skipped:
        msgs.append(("warning", t("batch_too_many", max=BATCH_MAX, n=skipped)))
    popts = cp.platform_opts(platform)
    clean_sig, _ = cp.clean_profanity(signature)

    def build_fn(name, price, aff):
        cname, _ = cp.clean_profanity(name)
        cat = cp.detect_category(cname)
        cap = cp.build_caption(tone, cat, cname, "", price, "", aff, link_header, False, disclose,
                               signature=clean_sig, max_tags=popts["max_tags"],
                               link_mode=popts["link_mode"])
        return cap, cat

    def validate_fn(aff, prod, name, price, cat):
        checks = cp.validate_inputs(aff, prod, name, price, "-", cat, True)
        return checks + cp.risky_checks(name)

    results = []
    bar = st.progress(0.0, text="") if items else None
    for i, item in enumerate(items, 1):
        bar.progress((i - 1) / len(items), text=t("batch_progress", i=i, n=len(items)))
        if not fetch_allowed():
            msgs.append(("warning", t("batch_stopped", i=i)))
            break
        results.append(batch.process_item(item, cached_product, build_fn, validate_fn))
    if bar:
        bar.empty()
    st.session_state["batch_results"] = {"msgs": msgs, "results": results}


if st.button(t("batch_btn"), key="batch_go", use_container_width=True):
    run_batch(batch_text)

br = st.session_state.get("batch_results")
if br:
    for level, msg in br["msgs"]:
        notice(level, msg)
    if br["results"]:
        notice("success", t("batch_done", n=len(br["results"])))
        notice("info", t("batch_review_hint"))
        export_lines = []
        for i, r in enumerate(br["results"], 1):
            title = cp.short_name(r["name"], 60) or t("batch_noname")
            st.markdown(f"**{t('batch_item', i=i, name=title)}**")
            if r["fetch_error"]:
                notice("warning", t("batch_fetch_err", reason=reason_text(r["fetch_error"], r["http"])))
            render_checks(r["checks"], levels=("error", "warning"))
            st.code(r["caption"], language=None, wrap_lines=True)
            export_lines.append(f"[{i}] {title}\n\n{r['caption']}")
        st.download_button(t("batch_download"), data="\n\n==========\n\n".join(export_lines),
                           file_name="captions_batch.txt", mime="text/plain",
                           use_container_width=True)
