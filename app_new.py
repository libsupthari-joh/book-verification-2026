import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import sqlite3
import time
from datetime import datetime
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape as xml_escape
import gspread
import pandas as pd
import streamlit as st
from gspread.cell import Cell
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
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

/* Menu tab-bar: active task highlighted, inactive tasks muted — so the
   current page is obvious at a glance instead of every button looking
   identical. */
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

.login-card .login-icon { font-size: 60px; }
.login-card .login-badge {
    display: inline-block;
    margin-top: 12px;
    padding: 6px 18px;
    border-radius: 999px;
    background: #064e3b;
    color: #fff;
    font-weight: 800;
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
    "9787555290": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 1 (User)"},
    "9751687939": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 2 (User)"},
}

def authenticate_user(phone, password):
    user = USERS_DATABASE.get(str(phone).strip())
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "", "user_phone": None,
    "current_page": "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", "vendor_key": 0,
    "selected_vendor": None, "temp_verified_records": [], "library_key": 0,
    "selected_library": None, "acc_library_key": 0, "selected_acc_library": None,
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

EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
DRIVE_FOLDER_ID = "1T3HKPAExdNtC-LOCuh2cDXI-6Kf8dzyq"

# SQLite உள்ளூர் டேட்டாபேஸ் அமைப்பு
def init_local_db():
    conn = sqlite3.connect("local_books.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            author TEXT,
            language TEXT,
            quantity INTEGER,
            vendor_name TEXT,
            lib_id TEXT,
            lib_name TEXT
        )
    """)
    conn.commit()
    conn.close()

init_local_db()

@st.cache_data(ttl=3600)
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    excel = pd.ExcelFile(file_path, engine="openpyxl")
    vendor = pd.read_excel(file_path, sheet_name="Vendor Name", engine="openpyxl") if "Vendor Name" in excel.sheet_names else pd.DataFrame()
    sheets = [name for name in excel.sheet_names if "Vendor Wise Book Data" in name]
    books = pd.read_excel(file_path, sheet_name=sheets[0], engine="openpyxl") if sheets else pd.DataFrame()
    return vendor, books

@st.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

@st.cache_resource
def get_drive_service():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def clean_text(value):
    if value is None or pd.isna(value):
        return ""
    value = re.sub(r"^\s*\d+[\.\s\-_]*", "", str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF\s]", "", value).casefold().strip()

vendor_df, book_df = load_data(EXCEL_FILE)
sheet_physically = sheet_vendor_wise = sheet_lib_detail = None
try:
    worksheets = {w.title.strip().casefold(): w for w in init_gspread().open_by_key(SPREADSHEET_ID).worksheets()}
    for title, worksheet in worksheets.items():
        if "physically verified" in title:
            sheet_physically = worksheet
        elif "vendor wise book data" in title:
            sheet_vendor_wise = worksheet
        elif "lib_detail" in title or "library" in title:
            sheet_lib_detail = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")

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

def get_vendor_number(vendor_id_name, vendor_name):
    match = re.search(r"\d+", str(vendor_id_name or vendor_name))
    return match.group(0) if match else "000"

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

def upload_pdf_to_drive(pdf_data, vendor_id, vendor_name):
    name = f"{get_vendor_number(vendor_id, vendor_name)}_{safe_name(vendor_name).replace(' ', '_')}_Physical_Verification.pdf"
    media = MediaIoBaseUpload(io.BytesIO(pdf_data), mimetype="application/pdf", resumable=False)
    return get_drive_service().files().create(
        body={"name": name, "parents": [DRIVE_FOLDER_ID], "mimeType": "application/pdf"},
        media_body=media, fields="id,name,webViewLink", supportsAllDrives=True,
    ).execute()

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
    values = []
    if vendor_df is not None and not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            name = c if c and c.casefold() != "nan" else b
            if name and name.casefold() != "nan" and name not in values:
                values.append(name)
    return values

def title_options(frame):
    return list(dict.fromkeys(str(value) for value in frame["Title"].dropna().tolist()))

if st.session_state["user_role"] == "Admin":
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", 
        "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்", 
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)", 
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)", 
        "⚙️ 5. Accession எண்கள் மேலாண்மை"
    ]
else:
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"
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

# Short labels for the tab-bar (the full descriptive text is still shown as
# the st.subheader inside each task page). The currently-open task is
# rendered as a "primary" button (solid, highlighted) and the rest as
# "secondary" (muted) — so it's obvious at a glance which task you're on,
# instead of five identical-looking buttons.
MENU_SHORT_LABELS = {
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு": "📥 சரிபார்ப்பு",
    "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்": "🔄 Sync",
    "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)": "🏢 பதிப்பாளர்",
    "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)": "🏛️ விநியோகம்",
    "⚙️ 5. Accession எண்கள் மேலாண்மை": "⚙️ Accession",
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
    if vendor_df is None or book_df is None or book_df.empty:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு அல்லது புத்தகத் தரவு கிடைக்கவில்லை!")
        st.stop()
    already = set()
    if sheet_physically:
        try:
            for row in sheet_physically.get_all_values()[1:]:
                if len(row) > 4 and row[4]:
                    already.add(clean_text(row[4]))
                elif row and row[0]:
                    already.add(clean_text(row[0]))
        except Exception:
            pass
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
        if clean_text(vendor_name) in already:
            st.error(f"⚠️ **{vendor_name}** பதிப்பகத்தின் சரிபார்ப்பு ஏற்கனவே முடிந்தது!")
            if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்", use_container_width=True):
                st.session_state.update(selected_vendor=None, temp_verified_records=[], vendor_key=st.session_state["vendor_key"] + 1)
                st.rerun()
        else:
            mask = (book_df.iloc[:, 9].apply(clean_text) == clean_text(vendor_name)) | (book_df.iloc[:, 10].apply(clean_text) == clean_text(vendor_name))
            filtered = book_df[mask]
            if filtered.empty:
                st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
            else:
                grouped = filtered.groupby(["Title", "Author Name", "Language"], as_index=False).agg({"Quantity": "sum", "Original Price": "first", "Acccepted Price": "first", "Isbn": "first", "Book Id": "first"})
                c1, c2 = st.columns(2)
                c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
                c2.metric("📦 மொத்தப் படிகள்", int(grouped["Quantity"].sum()))
                done = {item["Title"] for item in st.session_state["temp_verified_records"]}
                remaining = [title for title in title_options(grouped) if title not in done]
                st.markdown("### 🔍 2. தலைப்பைத் தேடி சரிபார்க்கவும்")
                title_lookup = {
                    f"{title} — {str(grouped.loc[grouped['Title'] == title, 'Author Name'].iloc[0])}": title
                    for title in remaining
                }
                selected_title_display = st.selectbox(
                    "🔎 தலைப்பு / ஆசிரியர் தேடல்",
                    ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"] + list(title_lookup),
                    placeholder="தலைப்பு (அல்லது) ஆசிரியர் பெயரை தட்டச்சு செய்யவும்",
                    key=f"title_t1_{len(done)}",
                )
                selected_title = title_lookup.get(selected_title_display, "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --")
                if selected_title != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    book = grouped[grouped["Title"] == selected_title].iloc[0]
                    author, language, total = str(book["Author Name"] or ""), str(book["Language"] or ""), int(book["Quantity"])
                    st.markdown(f'<div class="book-info-card">📖 <b>தலைப்பு:</b> {xml_escape(selected_title)}<br>✍️ <b>ஆசிரியர்:</b> {xml_escape(author)}<br>🌐 <b>மொழி:</b> {xml_escape(language)}<br><span class="total-qty">📦 பெற வேண்டிய மொத்த எண்ணிக்கை: {total}</span></div>', unsafe_allow_html=True)
                    received = st.number_input("✍️ பெறப்பட்ட எண்ணிக்கை", min_value=0, max_value=total, value=0, step=1, key=f"received_{selected_title}")
                    st.markdown(f'<div class="not-received-card">❌ பெறப்படாத எண்ணிக்கை: {total - received}</div>', unsafe_allow_html=True)
                    if st.button("➕ தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                        vendor_id = next((str(r.iloc[1]).strip() for _, r in vendor_df.iterrows() if len(r) > 2 and str(r.iloc[2]).strip() == vendor_name), vendor_name)
                        st.session_state["temp_verified_records"].append({"Title": selected_title, "Author Name": author, "Language": language, "Total Qty": total, "Received": received, "Not Received": total - received, "Short / Extra": str(received - total) if received != total else "0", "ID with Vendor Name": vendor_id, "Vendor Name": vendor_name, "Date": datetime.now().strftime("%d-%m-%y %H:%M:%S")})
                        st.rerun()
                if st.session_state["temp_verified_records"]:
                    temp = pd.DataFrame(st.session_state["temp_verified_records"])
                    cols = ["Title", "Author Name", "Language", "Total Qty", "Received", "Not Received", "Short / Extra", "Date"]
                    st.dataframe(temp[cols], use_container_width=True, hide_index=True)
                    download_panel(
                        temp[cols],
                        f"{get_vendor_number(vendor_name, vendor_name)}_{safe_name(vendor_name)}_Physical_Verification",
                        "Physical Verification",
                        f"பதிப்பகம்: {vendor_name} | Physical Verification",
                    )
                    clear, save = st.columns(2)
                    with clear:
                        if st.button("🗑️ அனைத்தையும் அழி", use_container_width=True):
                            st.session_state["temp_verified_records"] = []
                            st.rerun()
                    with save:
                        if st.button("💾 சீட்டில் சேமி", use_container_width=True):
                            if len(temp) < len(grouped):
                                st.error(f"⚠️ மொத்தம் {len(grouped)} தலைப்புகள் உள்ளன. அனைத்தையும் சேர்க்கவும்!")
                            elif not sheet_physically:
                                st.error("❌ Google Sheet இணைப்பு கிடைக்கவில்லை!")
                            else:
                                try:
                                    for item in st.session_state["temp_verified_records"]:
                                        sheet_physically.append_row([item["ID with Vendor Name"], item["Title"], item["Language"], item["Author Name"], item["Vendor Name"], item["Total Qty"], item["Received"], item["Not Received"], item["Short / Extra"], item["Date"]])
                                    try:
                                        upload_pdf_to_drive(pdf_bytes(temp[cols], f"{vendor_name} - Physical Verification"), vendor_name, vendor_name)
                                        st.success("✅ Google Sheet மற்றும் Drive PDF-ல் சேமிக்கப்பட்டது!")
                                    except Exception as error:
                                        st.warning(f"⚠️ Sheet சேமிக்கப்பட்டது; Drive PDF சேமிக்கப்படவில்லை: {error}")
                                    st.session_state.update(selected_vendor=None, temp_verified_records=[], vendor_key=st.session_state["vendor_key"] + 1)
                                    st.rerun()
                                except Exception as error:
                                    st.error(f"❌ சேமிப்பதில் பிழை: {error}")

elif len(menu_items) > 1 and st.session_state["current_page"] == menu_items[1]:
    st.subheader("🔄 பெறப்பட்ட எண்ணிக்கை ஒத்திசைவு (Sync)")
    if not sheet_physically or not sheet_vendor_wise:
        st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!")
        st.stop()
    try:
        physical = sheet_physically.get_all_values()
        vendor_sheet = sheet_vendor_wise.get_all_values()
        ph = [str(x).strip().casefold() for x in physical[0]]
        wh = [str(x).strip().casefold() for x in vendor_sheet[0]]
        vi = next((i for i, x in enumerate(ph) if "vendor" in x), 4)
        ti = next((i for i, x in enumerate(ph) if "title" in x), 1)
        ri = next((i for i, x in enumerate(ph) if "received" in x and "not" not in x), 6)
        si = next((i for i, x in enumerate(wh) if "received" in x and "not" not in x), 18)
        vendors = sorted({row[vi].strip() for row in physical[1:] if len(row) > vi and row[vi].strip()})
        selected = st.selectbox(
            "🔎 பதிப்பகம் தேடல்",
            ["-- தேர்ந்தெடுக்கவும் --"] + vendors,
            placeholder="பதிப்பகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
            key="sync_vendor",
        )
        if selected != "-- தேர்ந்தெடுக்கவும் --":
            records = [row for row in physical[1:] if len(row) > max(vi, ti, ri) and clean_text(row[vi]) == clean_text(selected)]
            title_lookup = {
                f"{row[ti]} — {row[3] if len(row) > 3 else ''}": row[ti]
                for row in records
            }
            selected_book = st.selectbox(
                "🔎 தலைப்பு / ஆசிரியர் தேடல்",
                ["-- அனைத்து தலைப்புகளும் --"] + list(title_lookup),
                placeholder="தலைப்பு (அல்லது) ஆசிரியர் பெயரை தட்டச்சு செய்யவும்",
                key="sync_book",
            )
            if selected_book != "-- அனைத்து தலைப்புகளும் --":
                records = [row for row in records if row[ti] == title_lookup.get(selected_book)]
            st.dataframe(pd.DataFrame([{"Title": r[ti], "Received": r[ri]} for r in records]), use_container_width=True, hide_index=True)
            if st.button("🚀 இந்த பதிப்பகத்திற்கு மட்டும் ஒத்திசைவு செய்க", use_container_width=True):
                cells = []
                for prow in records:
                    remaining = int(prow[ri]) if str(prow[ri]).isdigit() else 0
                    for row_no, wrow in enumerate(vendor_sheet[1:], 2):
                        wvendor = wrow[10] if len(wrow) > 10 else (wrow[9] if len(wrow) > 9 else "")
                        wtitle = wrow[4] if len(wrow) > 4 else ""
                        if clean_text(selected) in clean_text(wvendor) and clean_text(prow[ti]) == clean_text(wtitle) and remaining:
                            qty = int(wrow[17]) if len(wrow) > 17 and str(wrow[17]).isdigit() else 1
                            got = min(remaining, qty)
                            cells += [Cell(row=row_no, col=si + 1, value=str(got)), Cell(row=row_no, col=si + 2, value=str(qty - got))]
                            remaining -= got
                if cells:
                    sheet_vendor_wise.update_cells(cells)
                st.success(f"✅ {selected} ஒத்திசைக்கப்பட்டது!")
                time.sleep(.5)
                st.rerun()
    except Exception as error:
        st.error(f"❌ பிழை: {error}")

elif len(menu_items) > 2 and st.session_state["current_page"] == menu_items[2]:
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள் (480)")
    if vendor_df is None or book_df is None:
        st.error("❌ தரவு கிடைக்கவில்லை!")
        st.stop()
    vendors = vendor_options()
    selected = st.selectbox(
        "🔎 பதிப்பாளர் தேடல்",
        ["-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"] + vendors,
        placeholder="பதிப்பகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
        key="vendor_t3",
    )
    if selected.startswith("-- அனைத்து"):
        result = vendor_df
    else:
        result = book_df[(book_df.iloc[:, 9].apply(clean_text) == clean_text(selected)) | (book_df.iloc[:, 10].apply(clean_text) == clean_text(selected))]
    st.dataframe(result, use_container_width=True, hide_index=True)
    if not result.empty:
        download_panel(result, safe_name(selected) + "_Vendor_Details", "Vendor Details")

elif len(menu_items) > 3 and st.session_state["current_page"] in menu_items[3:]:
    if book_df is None or book_df.empty:
        st.error("❌ புத்தகத் தரவு கிடைக்கவில்லை!")
        st.stop()
    base = book_df.copy()
    cmap = {str(c).casefold().strip(): c for c in base.columns}
    lib_name_col = next((cmap[k] for k in cmap if "library name" in k), base.columns[12] if len(base.columns) > 12 else None)
    lib_id_col = next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k), base.columns[11] if len(base.columns) > 11 else None)
    libraries = {}
    if lib_name_col and lib_id_col:
        for _, row in base.dropna(subset=[lib_name_col, lib_id_col]).iterrows():
            libraries[str(row[lib_name_col]).strip()] = str(row[lib_id_col]).strip()
    if st.session_state["current_page"] == menu_items[3]:
        st.subheader("🏛️ நூலகத்திற்கு விநியோகம் (103)")
        selected = st.selectbox(
            "🔎 நூலகம் தேடல்",
            ["-- தேர்ந்தெடுக்கவும் --", "-- அனைத்து நூலகங்களும் --"] + sorted(libraries),
            placeholder="நூலகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
            key=f"library_{st.session_state['library_key']}",
        )
        if selected != "-- தேர்ந்தெடுக்கவும் --":
            result = base if selected.startswith("-- அனைத்து") else base[base[lib_id_col].astype(str).str.strip() == libraries[selected]]
            result = result.drop(columns=["S.No"], errors="ignore")
            result.insert(0, "S.No", range(1, len(result) + 1))
            title_lookup = {
                f"{row.get('Title', '')} — {row.get('Author Name', '')}": row.get("Title", "")
                for _, row in result.iterrows()
            }
            selected_book = st.selectbox(
                "🔎 தலைப்பு / ஆசிரியர் தேடல்",
                ["-- அனைத்து தலைப்புகளும் --"] + list(title_lookup),
                placeholder="தலைப்பு (அல்லது) ஆசிரியர் பெயரை தட்டச்சு செய்யவும்",
                key="library_book_t4",
            )
            if selected_book != "-- அனைத்து தலைப்புகளும் --":
                result = result[result["Title"] == title_lookup.get(selected_book)]
            st.dataframe(result, use_container_width=True, hide_index=True)
            if not result.empty:
                download_panel(result, safe_name(selected) + "_Distribution", "Library Distribution")
    else:
        st.subheader("⚙️ தானியங்கி மைய மற்றும் கிளை நூல் சேர்க்கை எண்கள் மேலாண்மை")
        st.error("🚨 பெறப்பட்ட நூல்களுக்கு (Received Qty) மட்டுமே சேர்க்கை எண்கள் உருவாக்கப்படும்.")
        if not sheet_vendor_wise:
            st.error("❌ Vendor Wise Data இணைப்பு கிடைக்கவில்லை!")
            st.stop()
        selected = st.selectbox(
            "🔎 நூலகம் தேடல்",
            ["-- தேர்ந்தெடுக்கவும் --"] + sorted(libraries),
            placeholder="நூலகத்தின் பெயரை தட்டச்சு செய்து தேர்ந்தெடுக்கவும்",
            key=f"acc_{st.session_state['acc_library_key']}",
        )
        if selected != "-- தேர்ந்தெடுக்கவும் --":
            rows = sheet_vendor_wise.get_all_values()
            headers = [str(x).strip().casefold() for x in rows[0]]
            li = next((i for i, x in enumerate(headers) if "librarianid" in x or "lib id" in x), 11)
            ti = next((i for i, x in enumerate(headers) if "title" in x), 4)
            qi = next((i for i, x in enumerate(headers) if x == "quantity"), 17)
            ri = next((i for i, x in enumerate(headers) if "received" in x and "not" not in x), 18)
            
            central = branch = 0
            central_row = branch_row = None
            if sheet_lib_detail:
                try:
                    detail_rows = sheet_lib_detail.get_all_values()
                    for detail_row_no, detail in enumerate(detail_rows[1:], 2):
                        if central_row is None and len(detail) > 5 and str(detail[5]).strip().isdigit():
                            central = int(detail[5])
                            central_row = detail_row_no
                        if len(detail) > 1 and str(detail[1]).strip() == libraries[selected]:
                            if len(detail) > 6 and str(detail[6]).strip().isdigit():
                                branch = int(detail[6])
                            branch_row = detail_row_no
                except Exception as error:
                    st.warning(f"⚠️ Lib_Detail பிழை: {error}")
                    
            library_rows = [
                row for row in rows[1:]
                if len(row) > li and str(row[li]).strip() == libraries[selected]
            ]
            title_lookup = {
                f"{row[ti] if len(row) > ti else ''} — {row[3] if len(row) > 3 else ''}":
                (row[ti] if len(row) > ti else "")
                for row in library_rows
            }
            selected_book = st.selectbox(
                "🔎 தலைப்பு / ஆசிரியர் தேடல்",
                ["-- அனைத்து தலைப்புகளும் --"] + list(title_lookup),
                placeholder="தலைப்பு (அல்லது) ஆசிரியர் பெயரை தட்டச்சு செய்யவும்",
                key="library_book_t5",
            )
            selected_book_title = title_lookup.get(selected_book)
            
            all_library_records = []
            for row_no, row in enumerate(rows[1:], 2):
                if len(row) > li and str(row[li]).strip() == libraries[selected]:
                    row_title = row[ti] if len(row) > ti else ""
                    qty = int(row[qi]) if len(row) > qi and str(row[qi]).isdigit() else 1
                    received = int(row[ri]) if len(row) > ri and str(row[ri]).isdigit() else 0
                    old_c = row[20].strip() if len(row) > 20 else ""
                    old_b = row[21].strip() if len(row) > 21 else ""
                    
                    if not old_c and not old_b:
                        c = [str(central + n) for n in range(1, received + 1)]
                        b = [str(branch + n) for n in range(1, received + 1)]
                        central += received
                        branch += received
                    else:
                        c, b = [old_c], [old_b]
                        
                    all_library_records.append({
                        "Sheet Row": row_no, 
                        "Title": row_title, 
                        "Author Name": row[3] if len(row) > 3 else "", 
                        "Quantity": qty, 
                        "Received": received, 
                        "Central Accession No": ", ".join(x for x in c if x), 
                        "Branch Accession No": ", ".join(x for x in b if x), 
                        "_new": not old_c and not old_b
                    })
            
            records = [
                r for r in all_library_records 
                if not selected_book_title or r["Title"] == selected_book_title
            ]
            
            if records:
                visible = pd.DataFrame(records).drop(columns=["Sheet Row", "_new"])
                st.dataframe(visible, use_container_width=True, hide_index=True)
                if st.button("💾 Google Sheet (U & V தூண்களில்) சேமி", use_container_width=True):
                    cells = []
                    for record in records:
                        if record["_new"]:
                            cells += [Cell(row=record["Sheet Row"], col=21, value=record["Central Accession No"]), Cell(row=record["Sheet Row"], col=22, value=record["Branch Accession No"])]
                    if cells:
                        sheet_vendor_wise.update_cells(cells)
                    if sheet_lib_detail and central_row and branch_row:
                        try:
                            sheet_lib_detail.update_cells([
                                Cell(row=central_row, col=6, value=str(central)),
                                Cell(row=branch_row, col=7, value=str(branch)),
                            ])
                        except Exception as error:
                            st.warning(f"⚠️ Lib_Detail எண்ணிக்கை புதுப்பிக்கப்படவில்லை: {error}")
                    st.success("✅ சேர்க்கை எண்கள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    st.rerun()
                download_panel(visible, safe_name(selected) + "_Accession_Register", "Accession Register")
            else:
                st.warning("⚠️ இந்த நூலகத்திற்கு புத்தகங்கள் எதுவும் இல்லை.")
