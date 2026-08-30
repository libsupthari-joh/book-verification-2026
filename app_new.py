import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
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

st.markdown(
    """
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
<style>
:root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--gold:#f59e0b}
html,body,[class*="css"]{-webkit-tap-highlight-color:transparent}
.stApp{background:radial-gradient(circle at 8% 8%,rgba(0,188,212,.12),transparent 28%),linear-gradient(135deg,#eef5ff,#fbfdff 50%,#eaf2ff)}
[data-testid="stHeader"]{background:transparent}
[data-testid="stToolbar"]{visibility:hidden}
h1{font-size:20px!important;padding:14px 16px!important;border-radius:16px;color:#fff!important;background:linear-gradient(135deg,#071a38,#1565c0 58%,#00acc1);box-shadow:0 6px 0 #041126,0 14px 24px #071a3833;text-shadow:2px 3px 3px #0006;text-align:center;margin-bottom:16px!important;line-height:1.4}
h2,h3{color:#092653!important}
.profile-card,.book-info-card,.login-card{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;box-shadow:5px 5px 0 #c8d8ed,0 8px 18px #08265318}
.profile-card{padding:12px 16px;border-radius:14px;font-size:14px;line-height:1.7}
.book-info-card{border-left:7px solid #1565c0;border-radius:14px;padding:14px 16px;line-height:1.9;margin:10px 0 16px;font-size:15px;word-break:break-word}
.total-qty{color:#0b3d91;font-size:18px;font-weight:900}
.not-received-card{background:linear-gradient(145deg,#fff8e1,#fff3c4);border-left:7px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#8a4b00;font-size:16px;font-weight:800;box-shadow:4px 4px 0 #ead69b;margin:10px 0}
.stButton>button,.stDownloadButton>button{min-height:50px!important;border-radius:13px!important;font-size:15px!important;font-weight:800!important;color:#fff!important;background:linear-gradient(145deg,#1976d2,#082b68)!important;box-shadow:0 4px 0 #041b42,0 8px 15px #082b6830!important;border:0!important;transition:.2s!important;width:100%!important;white-space:normal!important}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);filter:brightness(1.1)}
[data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;border-radius:14px;box-shadow:4px 4px 0 #c8d8ed;padding:10px}
div[data-testid="stTextInput"] label,div[data-testid="stSelectbox"] label,div[data-testid="stNumberInput"] label{font-weight:700!important;color:#092653!important}
div[data-baseweb="select"]>div{min-height:48px!important;font-size:15px!important}
input[type="number"],input[type="text"],input[type="password"]{min-height:44px!important;font-size:15px!important}
.login-card{text-align:center;border-radius:26px;padding:34px 26px 30px;position:relative;overflow:hidden}
.login-card .login-icon{font-size:52px}
.login-card .login-badge{display:inline-block;margin-top:10px;padding:5px 16px;border-radius:999px;background:linear-gradient(135deg,#071a38,#1565c0 60%,#00acc1);color:#fff;font-weight:800}
.login-card h2{margin:16px 0 6px;font-size:22px}
.login-card p{margin:0;color:#5b7aa3;font-size:13.5px;font-weight:600}
/* ---- Improved emoji / icon rendering ---- */
html,body,.stApp,button,input,textarea,select,label,td,th,div[data-baseweb="select"]>div,[data-testid="stMetric"]{
  font-family:"Segoe UI","Noto Sans","Noto Sans Tamil","Noto Color Emoji","Segoe UI Emoji","Apple Color Emoji",sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
.stButton>button,.stDownloadButton>button{font-family:"Segoe UI","Noto Color Emoji","Segoe UI Emoji","Apple Color Emoji",sans-serif;letter-spacing:.2px}
button,label,td,th{font-variant-emoji:emoji}
.stButton>button span{display:inline-flex;align-items:center;gap:6px;justify-content:center}
@media(max-width:640px){h1{font-size:17px!important}.block-container{padding:12px 10px!important}[data-testid="column"]{width:100%!important;flex:1 1 100%!important;min-width:100%!important;margin-bottom:8px!important}}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------ Authentication ------------------------------
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


# ------------------------------- Data access --------------------------------
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
DRIVE_FOLDER_ID = "1T3HKPAExdNtC-LOCuh2cDXI-6Kf8dzyq"

_CLEAN_LEAD = re.compile(r"^\s*\d+[\.\s\-_]*")
_CLEAN_KEEP = re.compile(r"[^a-zA-Z0-9\u0B80-\u0BFF\s]")


def clean_text(value):
    if value is None or pd.isna(value):
        return ""
    value = _CLEAN_LEAD.sub("", str(value).strip())
    return _CLEAN_KEEP.sub("", value).casefold().strip()


def _pick_xlsx_engine():
    try:
        import calamine  # noqa: F401
        return "calamine"
    except Exception:
        return None


_EXCEL_ENGINE = _pick_xlsx_engine()


def _load_data_impl(file_path, engine):
    kwargs = {"engine": engine} if engine else {}
    excel = pd.ExcelFile(file_path, **kwargs)
    vendor = pd.read_excel(file_path, sheet_name="Vendor Name", **kwargs) if "Vendor Name" in excel.sheet_names else pd.DataFrame()
    sheets = [name for name in excel.sheet_names if "Vendor Wise Book Data" in name]
    books = pd.read_excel(file_path, sheet_name=sheets[0], **kwargs) if sheets else pd.DataFrame()
    return vendor, books


@st.cache_data(show_spinner=False)
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    try:
        return _load_data_impl(file_path, _EXCEL_ENGINE)
    except Exception:
        return _load_data_impl(file_path, None)


@st.cache_resource(show_spinner=False)
def get_sheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_drive_service():
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive", "v3", credentials=creds, cache_discovery=False)


@st.cache_resource(show_spinner=False)
def sheets():
    try:
        spreadsheet = get_sheet_client().open_by_key(SPREADSHEET_ID)
        worksheets = {w.title.strip().casefold(): w for w in spreadsheet.worksheets()}
    except Exception as error:
        return {"error": error}
    result = {}
    for title, worksheet in worksheets.items():
        if "physically verified" in title:
            result["physically"] = worksheet
        elif "vendor wise book data" in title:
            result["vendor_wise"] = worksheet
        elif "lib_detail" in title or "library" in title:
            result["lib_detail"] = worksheet
    return result


vendor_df, book_df = load_data(EXCEL_FILE)
_SHEETS = sheets()
sheet_physically = _SHEETS.get("physically")
sheet_vendor_wise = _SHEETS.get("vendor_wise")
sheet_lib_detail = _SHEETS.get("lib_detail")
if "error" in _SHEETS:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {_SHEETS['error']}")


# -------------------------------- PDF export --------------------------------
PDF_FONT_REGULAR = PDF_FONT_BOLD = None
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


def ensure_pdf_font():
    global PDF_FONT_REGULAR, PDF_FONT_BOLD
    if PDF_FONT_REGULAR and PDF_FONT_BOLD:
        return
    path = find_tamil_font()
    if not path:
        raise RuntimeError("fonts/NotoSansTamil-Regular.ttf கிடைக்கவில்லை; இணைய இணைப்புடன் PDF பதிவிறக்கத்தை மீண்டும் முயற்சிக்கவும்.")
    if "TamilUI" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("TamilUI", path))
        pdfmetrics.registerFontFamily("TamilUI", normal="TamilUI", bold="TamilUI", italic="TamilUI", boldItalic="TamilUI")
    PDF_FONT_REGULAR = PDF_FONT_BOLD = "TamilUI"


def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"


def get_vendor_number(vendor_id_name, vendor_name):
    match = re.search(r"\d+", str(vendor_id_name or vendor_name))
    return match.group(0) if match else "000"


def excel_bytes(frame, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output) as writer:
        frame.to_excel(writer, index=False, sheet_name=str(sheet_name)[:31])
    return output.getvalue()


def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")


def pdf_bytes(frame, title):
    ensure_pdf_font()
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=7 * mm, leftMargin=7 * mm, topMargin=7 * mm, bottomMargin=7 * mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TamilTitle", parent=styles["Title"], fontName=PDF_FONT_REGULAR, fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#071a38"))
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
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9db6d5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5ff")]),
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


@st.cache_data(show_spinner=False, max_entries=32)
def cached_excel(frame, sheet_name):
    return excel_bytes(frame, sheet_name)


@st.cache_data(show_spinner=False, max_entries=32)
def cached_csv(frame):
    return csv_bytes(frame)


@st.cache_data(show_spinner=False, max_entries=16)
def cached_pdf(frame, title):
    return pdf_bytes(frame, title)


def download_panel(frame, prefix, sheet_name, pdf_title=None):
    st.markdown("### 📥 பதிவிறக்க வசதிகள்")
    st.download_button("📊 Excel பதிவிறக்கம்", cached_excel(frame, sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{prefix}")
    st.download_button("📄 CSV பதிவிறக்கம்", cached_csv(frame), f"{prefix}.csv", "text/csv", use_container_width=True, key=f"csv_{prefix}")
    try:
        st.download_button("🧾 PDF பதிவிறக்கம்", cached_pdf(frame, pdf_title or sheet_name), f"{prefix}.pdf", "application/pdf", use_container_width=True, key=f"pdf_{prefix}")
    except Exception as error:
        st.error(f"❌ PDF உருவாக்க முடியவில்லை: {error}")


# --------------------------- Search and common UI ---------------------------
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


st.session_state.setdefault("search_reset", 0)
if st.session_state["user_role"] == "Admin":
    menu_items = ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்", "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)", "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)", "⚙️ 5. Accession எண்கள் மேலாண்மை"]
else:
    menu_items = ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"]
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
menu_choice = st.selectbox("🧭 செய்ய வேண்டிய பணியைத் தேர்ந்தெடுக்கவும்", menu_items, index=menu_items.index(st.session_state["current_page"]), key="main_menu")
if menu_choice != st.session_state["current_page"]:
    st.session_state["current_page"] = menu_choice
    st.rerun()
st.markdown("---")


# ---------------------------- Task 1: verification --------------------------
if menu_choice == menu_items[0]:
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
        vendor_id_by_name = {}
        for _, r in vendor_df.iterrows():
            if len(r) > 2 and pd.notna(r.iloc[2]):
                key = str(r.iloc[2]).strip()
                if key not in vendor_id_by_name:
                    vendor_id_by_name[key] = str(r.iloc[1]).strip()
        if clean_text(vendor_name) in already:
            st.error(f"⚠️ **{vendor_name}** பதிப்பகத்தின் சரிபார்ப்பு ஏற்கனவே முடிந்தது!")
            if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்", use_container_width=True):
                st.session_state.update(selected_vendor=None, temp_verified_records=[], vendor_key=st.session_state["vendor_key"] + 1)
                st.rerun()
        else:
            vcol9 = book_df.iloc[:, 9].map(clean_text)
            vcol10 = book_df.iloc[:, 10].map(clean_text)
            mask = (vcol9 == clean_text(vendor_name)) | (vcol10 == clean_text(vendor_name))
            filtered = book_df[mask]
            if filtered.empty:
                st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
            else:
                grouped = filtered.groupby(["Title", "Author Name", "Language"], as_index=False).agg({"Quantity": "sum", "Original Price": "first", "Acccepted Price": "first", "Isbn": "first", "Book Id": "first"})
                gby = grouped.set_index("Title")
                author_of = dict(zip(grouped["Title"], grouped["Author Name"]))
                c1, c2 = st.columns(2)
                c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
                c2.metric("📦 மொத்தப் படிகள்", int(grouped["Quantity"].sum()))
                done = {item["Title"] for item in st.session_state["temp_verified_records"]}
                remaining = [title for title in title_options(grouped) if title not in done]
                st.markdown("### 🔍 2. தலைப்பைத் தேடி சரிபார்க்கவும்")
                title_map = {f"{t} — {author_of.get(t, '')}": t for t in remaining}
                selected_title_display = st.selectbox(
                    "🔎 தலைப்பு / ஆசிரியர் தேடல்",
                    ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"] + list(title_map),
                    placeholder="தலைப்பு (அல்லது) ஆசிரியர் பெயரை தட்டச்சு செய்யவும்",
                    key=f"title_t1_{len(done)}",
                )
                selected_title = title_map.get(selected_title_display, "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --")
                if selected_title != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    book = gby.loc[selected_title]
                    if isinstance(book, pd.DataFrame):
                        book = book.iloc[0]
                    author, language, total = str(book["Author Name"] or ""), str(book["Language"] or ""), int(book["Quantity"])
                    st.markdown(f'<div class="book-info-card">📖 <b>தலைப்பு:</b> {xml_escape(selected_title)}<br>✍️ <b>ஆசிரியர்:</b> {xml_escape(author)}<br>🌐 <b>மொழி:</b> {xml_escape(language)}<br><span class="total-qty">📦 பெற வேண்டிய மொத்த எண்ணிக்கை: {total}</span></div>', unsafe_allow_html=True)
                    received = st.number_input("✍️ பெறப்பட்ட எண்ணிக்கை", min_value=0, max_value=total, value=0, step=1, key=f"received_{selected_title}")
                    st.markdown(f'<div class="not-received-card">❌ பெறப்படாத எண்ணிக்கை: {total - received}</div>', unsafe_allow_html=True)
                    if st.button("➕ தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                        vendor_id = vendor_id_by_name.get(vendor_name, vendor_name)
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
                                    rows = [[item["ID with Vendor Name"], item["Title"], item["Language"], item["Author Name"], item["Vendor Name"], item["Total Qty"], item["Received"], item["Not Received"], item["Short / Extra"], item["Date"]] for item in st.session_state["temp_verified_records"]]
                                    sheet_physically.append_rows(rows)
                                    try:
                                        upload_pdf_to_drive(pdf_bytes(temp[cols], f"{vendor_name} - Physical Verification"), vendor_name, vendor_name)
                                        st.success("✅ Google Sheet மற்றும் Drive PDF-ல் சேமிக்கப்பட்டது!")
                                    except Exception as error:
                                        st.warning(f"⚠️ Sheet சேமிக்கப்பட்டது; Drive PDF சேமிக்கப்படவில்லை: {error}")
                                    st.session_state.update(selected_vendor=None, temp_verified_records=[], vendor_key=st.session_state["vendor_key"] + 1)
                                    st.rerun()
                                except Exception as error:
                                    st.error(f"❌ சேமிப்பதில் பிழை: {error}")


# -------------------------- Task 2: vendor sync ------------------------------
elif menu_choice == menu_items[1]:
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
        vendor_index = {}
        for wrow_no, wrow in enumerate(vendor_sheet[1:], 2):
            wvendor = wrow[10] if len(wrow) > 10 else (wrow[9] if len(wrow) > 9 else "")
            wtitle = wrow[4] if len(wrow) > 4 else ""
            if wvendor and wtitle:
                vendor_index.setdefault(clean_text(wvendor), []).append((wrow_no, wrow, clean_text(wtitle)))
        st.info("ஒத்திசைவு செய்ய வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்.")
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
                target_key = clean_text(selected)
                for prow in records:
                    remaining = int(prow[ri]) if str(prow[ri]).isdigit() else 0
                    if remaining <= 0:
                        continue
                    ptitle = clean_text(prow[ti])
                    for wrow_no, wrow, wctitle in vendor_index.get(target_key, []):
                        if remaining <= 0:
                            break
                        if ptitle == wctitle:
                            qty = int(wrow[17]) if len(wrow) > 17 and str(wrow[17]).isdigit() else 1
                            got = min(remaining, qty)
                            cells += [Cell(row=wrow_no, col=si + 1, value=str(got)), Cell(row=wrow_no, col=si + 2, value=str(qty - got))]
                            remaining -= got
                if cells:
                    sheet_vendor_wise.update_cells(cells)
                st.success(f"✅ {selected} ஒத்திசைக்கப்பட்டது!")
                time.sleep(.5)
                st.rerun()
    except Exception as error:
        st.error(f"❌ பிழை: {error}")


# -------------------------- Task 3: vendor details ---------------------------
elif menu_choice == menu_items[2]:
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
        vcol9 = book_df.iloc[:, 9].map(clean_text)
        vcol10 = book_df.iloc[:, 10].map(clean_text)
        result = book_df[(vcol9 == clean_text(selected)) | (vcol10 == clean_text(selected))]
    st.dataframe(result, use_container_width=True, hide_index=True)
    if not result.empty:
        download_panel(result, safe_name(selected) + "_Vendor_Details", "Vendor Details")


# ---------------------- Tasks 4 and 5: library views -------------------------
elif menu_choice in menu_items[3:]:
    if book_df is None or book_df.empty:
        st.error("❌ புத்தகத் தரவு கிடைக்கவில்லை!")
        st.stop()
    base = book_df.copy()
    cmap = {str(c).casefold().strip(): c for c in base.columns}
    lib_name_col = next((cmap[k] for k in cmap if "library name" in k), base.columns[12] if len(base.columns) > 12 else None)
    lib_id_col = next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k), base.columns[11] if len(base.columns) > 11 else None)
    libraries = {}
    if lib_name_col and lib_id_col:
        keep = base.dropna(subset=[lib_name_col, lib_id_col])
        names = keep[lib_name_col].astype(str).str.strip()
        ids = keep[lib_id_col].astype(str).str.strip()
        libraries = dict(zip(names, ids))
    if menu_choice == menu_items[3]:
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
            st.error("❌ Vendor Wise Book Data இணைப்பு கிடைக்கவில்லை!")
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
            records = []
            for row_no, row in enumerate(rows[1:], 2):
                if len(row) > li and str(row[li]).strip() == libraries[selected]:
                    row_title = row[ti] if len(row) > ti else ""
                    if selected_book_title and row_title != selected_book_title:
                        continue
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
                    records.append({"Sheet Row": row_no, "Title": row[ti] if len(row) > ti else "", "Author Name": row[3] if len(row) > 3 else "", "Quantity": qty, "Received": received, "Central Accession No": ", ".join(x for x in c if x), "Branch Accession No": ", ".join(x for x in b if x), "_new": not old_c and not old_b})
            if records:
                visible = pd.DataFrame(records).drop(columns=["Sheet Row", "_new"])
                st.dataframe(visible, use_container_width=True, hide_index=True)
                                if st.button("💾 Google Sheet (U & V தூண்களில்) சேமி", use_container_width=True):
                    cells = []
                    for record in records:
                        if record["_new"]:
                            cells += [Cell(row=record["Sheet Row"], col=21, value=record["Central Accession No"]),
                                      Cell(row=record["Sheet Row"], col=22, value=record["Branch Accession No"])]
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
