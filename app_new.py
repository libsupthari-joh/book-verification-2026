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
    st.download_button("📊 Excel பதிவிறக்கம்", cached
