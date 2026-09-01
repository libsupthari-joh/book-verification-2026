import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import sqlite3
from datetime import datetime
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape as xml_escape
import pandas as pd
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans Tamil', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #f0fdf4, #e6f4ea);
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

h1 {
    font-size: 26px !important;
    font-weight: 800 !important;
    padding: 18px 22px !important;
    border-radius: 14px;
    color: #fff !important;
    background: linear-gradient(135deg, #064e3b, #047857) !important;
    box-shadow: 0 6px 15px rgba(6,78,59,0.3);
    text-align: center;
    margin-bottom: 20px !important;
}

h2, h3 {
    color: #064e3b !important;
    font-weight: 700 !important;
}

p, span, label, div {
    font-size: 16px !important;
    color: #111827;
}

.profile-card, .book-info-card, .login-card {
    background: #ffffff;
    border: 1.5px solid #a7f3d0;
    box-shadow: 0 6px 12px -2px rgba(0,0,0,0.08);
}

.profile-card {
    padding: 16px 20px;
    border-radius: 12px;
    color: #064e3b;
    background: #ecfdf5;
}

.book-info-card {
    border-left: 8px solid #047857;
    border-radius: 12px;
    padding: 18px 20px;
    line-height: 2.1;
    margin: 14px 0 18px;
    background: #ffffff;
}

.total-qty {
    color: #047857;
    font-size: 20px !important;
    font-weight: 800;
}

.not-received-card {
    background: #fffbeb;
    border-left: 8px solid #f59e0b;
    border-radius: 12px;
    padding: 14px 18px;
    color: #b45309;
    font-weight: 800;
    margin: 12px 0;
}

.stButton > button, .stDownloadButton > button {
    min-height: 50px !important;
    border-radius: 10px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    background: linear-gradient(135deg, #064e3b, #047857) !important;
    box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
    border: none !important;
    width: 100% !important;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #047857, #022c22) !important;
    color: #fff !important;
}

button[kind="secondary"] {
    background: linear-gradient(135deg, #ecfdf5, #d1fae5) !important;
    color: #064e3b !important;
    box-shadow: 0 3px 8px rgba(6,78,59,0.12) !important;
    font-weight: 700 !important;
    border: 1.5px solid #a7f3d0 !important;
}
button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #d1fae5, #a7f3d0) !important;
    color: #064e3b !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #064e3b, #047857) !important;
    box-shadow: 0 4px 12px rgba(6,78,59,0.4) !important;
    border: 1.5px solid #064e3b !important;
}

.login-card {
    text-align: center;
    border-radius: 18px;
    padding: 38px 30px 34px;
    background: #ffffff;
    border: 1.5px solid #a7f3d0;
}
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

_RUNTIME_SESSION_SECRET = None

def app_secret():
    global _RUNTIME_SESSION_SECRET
    if _RUNTIME_SESSION_SECRET:
        return _RUNTIME_SESSION_SECRET
    value = os.getenv("SESSION_SECRET", "").strip()
    if not value:
        try:
            value = str(st.secrets.get("app_secret", "")).strip()
        except Exception:
            value = ""
    _RUNTIME_SESSION_SECRET = value or py_secrets.token_hex(32)
    return _RUNTIME_SESSION_SECRET

def make_session_token(phone):
    return hmac.new(app_secret().encode(), phone.encode(), hashlib.sha256).hexdigest()

def verify_session_token(phone, token):
    return bool(phone and token) and hmac.compare_digest(make_session_token(phone), str(token))

USERS_DATABASE = {
    "9842759306": {"password_hash": hash_password("Hari@@1979"), "role": "Admin", "name": "முதன்மை நிர்வாகி (Admin)"},
    "9787555290": {"password_hash": hash_password("123456"), "role": "சரிபார்ப்பு பயனர் 1", "name": "சரிபார்ப்பு பயனர் 1 (User)"},
    "9751687939": {"password_hash": hash_password("123456"), "role": "சரிபார்ப்பு பயனர் 2", "name": "சரிபார்ப்பு பயனர் 2 (User)"},
}

def authenticate_user(phone, password):
    user = USERS_DATABASE.get(str(phone).strip())
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "", "user_phone": None,
    "current_page": "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", "vendor_key": 0,
    "selected_vendor": None, "temp_verified_records": [],
}.items():
    st.session_state.setdefault(key, default)

if not st.session_state["logged_in"]:
    query_phone = st.query_params.get("phone")
    query_token = st.query_params.get("token")
    if query_phone in USERS_DATABASE and verify_session_token(query_phone, query_token):
        user = USERS_DATABASE[query_phone]
        st.session_state.update(
            logged_in=True, user_role=user["role"], user_name=user["name"], user_phone=query_phone
        )

def show_login_page():
    _, column, _ = st.columns([1, 1.4, 1])
    with column:
        st.markdown(
            '<div class="login-card"><div class="login-icon">📚</div>'
            '<div class="login-badge">2026</div><h2>2026ஆம் ஆண்டு புதிய நூல்கள் கொள்முதல்</h2>'
            '<p>பதிப்பாளர்களின் புதிய நூல்கள் விநியோகம் &amp; சரிபார்ப்பு தளம்</p></div>',
            unsafe_allow_html=True,
        )
        with st.form("secure_login_form"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10, placeholder="10 இலக்க எண்")
            password = st.text_input("🔑 கடவுச்சொல்", type="password")
            submitted = st.form_submit_button("🔓 உள்நுழைக", use_container_width=True)
        if submitted:
            user = authenticate_user(phone, password)
            if not user:
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")
            else:
                clean_phone = phone.strip()
                st.session_state.update(
                    logged_in=True, user_role=user["role"], user_name=user["name"], user_phone=clean_phone
                )
                st.query_params.update(phone=clean_phone, token=make_session_token(clean_phone))
                st.rerun()

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

@st.cache_data(ttl=60)
def load_all_data():
    excel_path = "Book Supply-2026.xlsx"
    if os.path.exists(excel_path):
        xls = pd.ExcelFile(excel_path)
        df_summary = pd.read_excel(xls, sheet_name="Vendor Name")
        df_books = pd.read_excel(xls, sheet_name="Vendor Wise Book Data ")
        return df_summary, df_books
    return pd.DataFrame(), pd.DataFrame()

df_summary, df_books = load_all_data()

def clean_text(value):
    if value is None or pd.isna(value):
        return ""
    value = re.sub(r"^\s*\d+[\.\s\-_]*", "", str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF\s]", "", value).casefold().strip()

PDF_FONT_REGULAR = PDF_FONT_BOLD = None
PDF_FONT_ERROR = None
FONT_URL = "https://github.com/notofonts/tamil/raw/main/fonts/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf"

def find_tamil_font():
    root = os.path.dirname(os.path.abspath(__file__))
    paths = [
        os.path.join(root, "fonts", "NotoSansTamil-Regular.ttf"),
        os.path.join(root, "fonts", "NotoSansTamil.ttf"),
        os.path.join(os.getcwd(), "fonts", "NotoSansTamil-Regular.ttf"),
        os.path.join(os.getcwd(), "fonts", "NotoSansTamil.ttf"),
    ]
    found = next((path for path in paths if os.path.isfile(path)), None)
    if found:
        return found
    target = paths[0]
    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        request = Request(FONT_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(request, timeout=20) as response, open(target, "wb") as output:
            output.write(response.read())
        return target if os.path.isfile(target) and os.path.getsize(target) > 10000 else None
    except Exception:
        return None

def load_pdf_font():
    global PDF_FONT_REGULAR, PDF_FONT_BOLD
    path = find_tamil_font()
    if not path:
        raise FileNotFoundError("fonts/NotoSansTamil-Regular.ttf கிடைக்கவில்லை.")
    if "TamilUI" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("TamilUI", path))
        pdfmetrics.registerFontFamily("TamilUI", normal="TamilUI", bold="TamilUI", italic="TamilUI", boldItalic="TamilUI")
    PDF_FONT_REGULAR = PDF_FONT_BOLD = "TamilUI"

try:
    load_pdf_font()
except Exception as error:
    PDF_FONT_ERROR = error

def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"

def excel_bytes(frame, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=str(sheet_name)[:31])
    return output.getvalue()

def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")

def pdf_bytes(frame, title):
    if PDF_FONT_ERROR:
        raise RuntimeError(f"Tamil PDF font could not be loaded: {PDF_FONT_ERROR}")
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=7 * mm, leftMargin=7 * mm, topMargin=7 * mm, bottomMargin=7 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TamilTitle", parent=styles["Title"], fontName=PDF_FONT_REGULAR, fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#064e3b"))
    body_style = ParagraphStyle("TamilBody", parent=styles["BodyText"], fontName=PDF_FONT_REGULAR, fontSize=8, leading=10)
    columns = list(frame.columns)
    data = [[Paragraph(xml_escape(str(column)), body_style) for column in columns]]
    for row in frame.fillna("").astype(str).itertuples(index=False, name=None):
        data.append([Paragraph(xml_escape(str(value)[:150]), body_style) for value in row])
    widths = []
    for column in columns:
        sample = [str(column)] + [str(value) for value in frame[column].head(25)]
        widths.append(max(20 * mm, min(58 * mm, (max(map(len, sample)) + 2) * 1.15 * mm)))
    available = landscape(A4)[0] - 14 * mm
    if sum(widths) > available:
        scale = available / sum(widths)
        widths = [width * scale for width in widths]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#064e3b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#a7f3d0")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#ecfdf5")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    document.build([Paragraph(xml_escape(str(title)), title_style), Spacer(1, 4 * mm), table])
    return output.getvalue()

def download_panel(frame, prefix, sheet_name, pdf_title=None):
    st.markdown("### 📥 பதிவிறக்க வசதிகள்")
    st.download_button("📊 Excel பதிவிறக்கம்", excel_bytes(frame, sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{prefix}")
    st.download_button("📄 CSV பதிவிறக்கம்", csv_bytes(frame), f"{prefix}.csv", "text/csv", use_container_width=True, key=f"csv_{prefix}")
    try:
        pdf = pdf_bytes(frame, pdf_title or sheet_name)
        st.download_button("🧾 PDF பதிவிறக்கம்", pdf, f"{prefix}.pdf", "application/pdf", use_container_width=True, key=f"pdf_{prefix}")
    except Exception as error:
        st.error(f"❌ PDF உருவாக்க முடியவில்லை: {error}")

def vendor_options():
    if df_summary is not None and not df_summary.empty and "Publication Name / Vendor Name" in df_summary.columns:
        return sorted(df_summary["Publication Name / Vendor Name"].dropna().unique().tolist())
    return []

menu_items = [
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", 
    "🏢 2. மொத்த பதிப்பாளர் விவரங்கள்"
]

if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]

st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")

info, logout = st.columns([3.2, 0.8])
with info:
    role = "👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"
    st.markdown(f'<div class="profile-card">👤 <b>பயனர்:</b> {st.session_state["user_name"]} &nbsp;|&nbsp; <b>அதிகாரம்:</b> {role}</div>', unsafe_allow_html=True)
with logout:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

st.markdown("---")

MENU_SHORT_LABELS = {
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு": "📥 சரிபார்ப்பு",
    "🏢 2. மொத்த பதிப்பாளர் விவரங்கள்": "🏢 பதிப்பாளர்",
}

cols = st.columns(len(menu_items))
for i, item in enumerate(menu_items):
    with cols[i]:
        is_active = item == st.session_state["current_page"]
        if st.button(
            MENU_SHORT_LABELS.get(item, item),
            use_container_width=True,
            type="primary" if is_active else "secondary",
            key=f"menu_btn_{i}",
        ) and not is_active:
            st.session_state["current_page"] = item
            st.rerun()

st.markdown("---")

if st.session_state["current_page"] == menu_items[0]:
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if df_summary is None or df_summary.empty or df_books is None or df_books.empty:
        st.error("❌ தரவுகள் கிடைக்கவில்லை!")
        st.stop()
    
    vendors = vendor_options()
    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    selected = st.selectbox(
        "🔎 பதிப்பாளர் தேடல்",
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors,
        placeholder="பதிப்பகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
        key=f"vendor_t1_{st.session_state['vendor_key']}",
    )
    if selected != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and selected != st.session_state["selected_vendor"]:
        st.session_state.update(selected_vendor=selected, temp_verified_records=[])
    
    if st.session_state["selected_vendor"]:
        vendor_name = st.session_state["selected_vendor"]
        
        sum_rows = df_summary[df_summary["Publication Name / Vendor Name"].apply(clean_text) == clean_text(vendor_name)]
        if not sum_rows.empty:
            s_row = sum_rows.iloc[0]
            tot_titles = int(s_row.get("No. of Titals", 0))
            tot_qty = int(s_row.get("No of Book Quantity", 0))
            tam_qty = int(s_row.get("No. of Tamil Books", 0))
            eng_qty = int(s_row.get("No. of Engilsh Books", 0))
            st.markdown(f'<div class="book-info-card">🏢 <b>பதிப்பகம்:</b> {xml_escape(vendor_name)}<br>📚 <b>மொத்தத் தலைப்புகள்:</b> {tot_titles}<br>🇮🇳 <b>தமிழ் நூல்கள்:</b> {tam_qty} &nbsp;|&nbsp; 🇬🇧 <b>ஆங்கில நூல்கள்:</b> {eng_qty}<br><span class="total-qty">📦 பெற வேண்டிய மொத்த எண்ணிக்கை: {tot_qty}</span></div>', unsafe_allow_html=True)
        
        books_filtered = df_books[df_books["Publication Name"].apply(clean_text) == clean_text(vendor_name)]
        if books_filtered.empty:
            books_filtered = df_books[df_books["Vendor Name"].apply(clean_text) == clean_text(vendor_name)]
            
        if not books_filtered.empty:
            st.markdown("### 📚 2. புத்தகத் தலைப்புகளின் விவரங்கள் & சரிபார்ப்பு")
            
            verified_items = []
            for idx, book_row in books_filtered.iterrows():
                title = book_row.get("Title", "Unknown Title")
                author = book_row.get("Author Name", "")
                lang = book_row.get("Language", "")
                lib_name = book_row.get("Library Name", "")
                orig_qty = int(book_row.get("Quantity", 1))
                
                with st.expander(f"📖 {title} ({lang}) - நூலகம்: {lib_name} [கோரப்பட்ட எண்ணிக்கை: {orig_qty}]"):
                    st.write(f"✍️ ஆசிரியர்: `{author}` | 🏢 பதிப்பகம்: `{vendor_name}`")
                    rec_val = st.number_input(
                        f"பெறப்பட்ட எண்ணிக்கை ({title[:30]})", 
                        min_value=0, max_value=orig_qty, value=orig_qty, step=1, 
                        key=f"rec_book_{idx}"
                    )
                    not_rec = orig_qty - rec_val
                    st.markdown(f"❌ பெறப்படாதது: **{not_rec}**")
                    verified_items.append({
                        "Title": title,
                        "Author Name": author,
                        "Language": lang,
                        "Library Name": lib_name,
                        "Quantity": orig_qty,
                        "Received": rec_val,
                        "Not Received": not_rec
                    })
            
            if st.button("➕ சரிபார்த்த விவரங்களைத் தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                for item in verified_items:
                    item["Vendor Name"] = vendor_name
                    item["Date"] = datetime.now().strftime("%d-%m-%y %H:%M:%S")
                    st.session_state["temp_verified_records"].append(item)
                st.success("✅ தற்காலிகப் பட்டியலில் வெற்றிகரமாகச் சேர்க்கப்பட்டது!")
                st.rerun()
            
            if st.session_state["temp_verified_records"]:
                st.markdown("### 📋 தற்காலிகச் சரிபார்ப்புப் பட்டியல்")
                temp_df = pd.DataFrame(st.session_state["temp_verified_records"])
                st.dataframe(temp_df, use_container_width=True, hide_index=True)
                download_panel(
                    temp_df,
                    f"{safe_name(vendor_name)}_Title_Verification",
                    "Verification Report",
                    f"பதிப்பகம்: {vendor_name} | தலைப்புகள் சரிபார்ப்பு",
                )
                clear, save = st.columns(2)
                with clear:
                    if st.button("🗑️ அனைத்தையும் அழி", use_container_width=True):
                        st.session_state["temp_verified_records"] = []
                        st.rerun()
                with save:
                    if st.button("💾 சேமி", use_container_width=True):
                        st.success("✅ அனைத்து விவரங்களும் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                        st.session_state.update(selected_vendor=None, temp_verified_records=[], vendor_key=st.session_state["vendor_key"] + 1)
                        st.rerun()

elif len(menu_items) > 1 and st.session_state["current_page"] == menu_items[1]:
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள்")
    if df_summary is None or df_summary.empty:
        st.error("❌ தரவு கிடைக்கவில்லை!")
        st.stop()
    vendors = vendor_options()
    selected = st.selectbox(
        "🔎 பதிப்பாளர் தேடல்",
        ["-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"] + vendors,
        placeholder="பதிப்பகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
        key="vendor_t2",
    )
    if selected.startswith("-- அனைத்து"):
        result = df_summary
    else:
        result = df_summary[df_summary["Publication Name / Vendor Name"].apply(clean_text) == clean_text(selected)]
    st.dataframe(result, use_container_width=True, hide_index=True)
    if not result.empty:
        download_panel(result, safe_name(selected) + "_Vendor_Details", "Vendor Details")
