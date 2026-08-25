import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import time
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape

import gspread
from gspread.cell import Cell
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ============================================================
# 0. TAMIL-CAPABLE PDF FONT
#    Use one known Tamil-capable font for every PDF text element.
#    NotoSansTamil.ttf must be placed in the sibling fonts/ directory.
# ============================================================
PDF_FONT_REGULAR = None
PDF_FONT_BOLD = None
PDF_FONT_ERROR = None


def _find_tamil_font():
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    candidates = [
        os.path.join(font_dir, "NotoSansTamil.ttf"),
        os.path.join(font_dir, "NotoSansTamil-Regular.ttf"),
        os.path.join(os.getcwd(), "fonts", "NotoSansTamil.ttf"),
        os.path.join(os.getcwd(), "fonts", "NotoSansTamil-Regular.ttf"),
    ]
    return next((path for path in candidates if os.path.isfile(path)), None)


def _load_pdf_fonts():
    global PDF_FONT_REGULAR, PDF_FONT_BOLD
    font_path = _find_tamil_font()
    if not font_path:
        raise FileNotFoundError(
            "Tamil font missing. Upload fonts/NotoSansTamil.ttf "
            "to the repository. Do not use FreeSans for this PDF."
        )

    pdfmetrics.registerFont(TTFont("TamilUI", font_path))
    PDF_FONT_REGULAR = "TamilUI"
    # Use the same verified Tamil font for bold roles too. This avoids
    # FreeSansBold/Helvetica fallback boxes in titles and table cells.
    PDF_FONT_BOLD = PDF_FONT_REGULAR
    pdfmetrics.registerFontFamily(
        "TamilUI",
        normal=PDF_FONT_REGULAR,
        bold=PDF_FONT_BOLD,
        italic=PDF_FONT_REGULAR,
        boldItalic=PDF_FONT_BOLD,
    )


try:
    _load_pdf_fonts()
except Exception as font_error:
    PDF_FONT_ERROR = font_error
# ============================================================
# 1. PAGE SETTINGS
# ============================================================
st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# 2. MOBILE-FIRST 3D COLOUR UI
# ============================================================
st.markdown(
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, maximum-scale=5\">\n"
    "<style>\n"
    ":root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--gold:#f59e0b}\n"
    "html, body, [class*=\"css\"]{-webkit-tap-highlight-color:transparent}\n"
    ".stApp{background:radial-gradient(circle at 8% 8%,rgba(0,188,212,.12),transparent 28%),linear-gradient(135deg,#eef5ff,#fbfdff 50%,#eaf2ff)}\n"
    "[data-testid=\"stHeader\"]{background:transparent}\n"
    "[data-testid=\"stToolbar\"]{visibility:hidden}\n"
    "h1{font-size:20px!important;padding:14px 16px!important;border-radius:16px;color:#fff!important;background:linear-gradient(135deg,#071a38,#1565c0 58%,#00acc1);box-shadow:0 6px 0 #041126,0 14px 24px #071a3833;text-shadow:2px 3px 3px #0006;text-align:center;margin-bottom:16px!important;line-height:1.4}\n"
    "h2,h3{color:#092653!important}\n"
    ".profile-card{background:linear-gradient(145deg,#fff,#eef5ff);padding:12px 16px;border-radius:14px;border:1px solid #cfe0f5;box-shadow:5px 5px 0 #c8d8ed,0 8px 18px #08265318;font-size:14px;line-height:1.7}\n"
    ".book-info-card{background:linear-gradient(145deg,#fff,#edf5ff);border-left:7px solid #1565c0;border-radius:14px;padding:14px 16px;line-height:1.9;box-shadow:5px 5px 0 #c8d8ed;margin:10px 0 16px;font-size:15px;word-break:break-word}\n"
    ".total-qty{color:#0b3d91;font-size:18px;font-weight:900}\n"
    ".not-received-card{background:linear-gradient(145deg,#fff8e1,#fff3c4);border-left:7px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#8a4b00;font-size:16px;font-weight:800;box-shadow:4px 4px 0 #ead69b;margin:10px 0}\n"
    ".stButton>button,.stDownloadButton>button{min-height:50px!important;border-radius:13px!important;font-size:15px!important;font-weight:800!important;color:#fff!important;background:linear-gradient(145deg,#1976d2,#082b68)!important;box-shadow:0 4px 0 #041b42,0 8px 15px #082b6830!important;border:0!important;transition:.2s!important;width:100%!important;white-space:normal!important}\n"
    ".stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);filter:brightness(1.1)}\n"
    ".stButton>button:active,.stDownloadButton>button:active{transform:translateY(1px);filter:brightness(0.95)}\n"
    "[data-testid=\"stMetric\"]{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;border-radius:14px;box-shadow:4px 4px 0 #c8d8ed;padding:10px}\n"
    "div[data-testid=\"stSelectbox\"] label,div[data-testid=\"stNumberInput\"] label,div[data-testid=\"stTextInput\"] label{font-size:14px!important;font-weight:700!important;color:#092653!important}\n"
    "div[data-baseweb=\"select\"] > div{min-height:48px!important;font-size:15px!important}\n"
    "input[type=\"number\"], input[type=\"text\"], input[type=\"password\"]{min-height:44px!important;font-size:15px!important}\n"
    "[data-testid=\"stDataFrame\"]{overflow-x:auto!important}\n"
    "@media (max-width: 640px){\n"
    "  h1{font-size:17px!important;padding:12px!important}\n"
    "  .block-container{padding-left:10px!important;padding-right:10px!important;padding-top:12px!important}\n"
    "  [data-testid=\"column\"]{width:100%!important;flex:1 1 100%!important;min-width:100%!important;margin-bottom:8px!important}\n"
    "  .stButton>button,.stDownloadButton>button{font-size:14px!important;min-height:52px!important}\n"
    "}\n"
    ".login-card{text-align:center;background:linear-gradient(160deg,#ffffff,#f4f9ff 70%);border-radius:26px;padding:34px 26px 30px;box-shadow:0 10px 0 #c8d8ed,0 22px 40px #08265322;border:1px solid #dbe8fa;position:relative;overflow:hidden}\n"
    ".login-card::before{content:'';position:absolute;top:-40px;left:-40px;width:140px;height:140px;background:radial-gradient(circle,rgba(0,172,193,.18),transparent 70%)}\n"
    ".login-card::after{content:'';position:absolute;bottom:-50px;right:-30px;width:160px;height:160px;background:radial-gradient(circle,rgba(21,101,192,.16),transparent 70%)}\n"
    ".login-card .login-icon{font-size:52px;line-height:1.1;filter:drop-shadow(0 6px 10px #08265333)}\n"
    ".login-card .login-badge{display:inline-block;margin-top:10px;padding:5px 16px;border-radius:999px;background:linear-gradient(135deg,#071a38,#1565c0 60%,#00acc1);color:#fff;font-size:13px;font-weight:800;letter-spacing:.3px;box-shadow:0 3px 0 #041126}\n"
    ".login-card h2{margin:16px 0 6px;color:#071a38;font-size:22px;font-weight:900;position:relative;z-index:1}\n"
    ".login-card p{margin:0;color:#5b7aa3;font-size:13.5px;font-weight:600;position:relative;z-index:1}\n"
    ".login-card hr{border:none;height:3px;width:56px;margin:16px auto 0;border-radius:99px;background:linear-gradient(90deg,#1565c0,#00acc1)}\n"
    "</style>",
    unsafe_allow_html=True,
)

# ============================================================
# 3. LOGIN (with signed session token — fixes URL role-spoofing bug)
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

# A process-local fallback keeps the app usable on Streamlit Cloud when
# no secret has been configured. It changes after a restart, which safely
# invalidates old URL tokens and requires users to log in again.
_RUNTIME_SESSION_SECRET = None


def _app_secret():
    global _RUNTIME_SESSION_SECRET
    if _RUNTIME_SESSION_SECRET:
        return _RUNTIME_SESSION_SECRET

    secret = os.getenv("SESSION_SECRET", "").strip()
    if not secret:
        try:
            secret = str(st.secrets.get("app_secret", "")).strip()
        except Exception:
            secret = ""

    _RUNTIME_SESSION_SECRET = secret or py_secrets.token_hex(32)
    return _RUNTIME_SESSION_SECRET

def make_session_token(phone):
    return hmac.new(_app_secret().encode("utf-8"), phone.encode("utf-8"), hashlib.sha256).hexdigest()

def verify_session_token(phone, token):
    if not phone or not token:
        return False
    return hmac.compare_digest(make_session_token(phone), token)

USERS_DATABASE = {
    "9842759306": {"password_hash": hash_password("Hari@@1979"), "role": "Admin", "name": "முதன்மை நிர்வாகி (Admin)"},
    "9787555290": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 1 (User)"},
    "9751687939": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 2 (User)"},
}

def authenticate_user(phone, password):
    user = USERS_DATABASE.get(phone.strip())
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

if "logged_in" not in st.session_state:
    q_phone = st.query_params.get("phone")
    q_token = st.query_params.get("token")
    # IMPORTANT: role/name are ALWAYS looked up fresh from USERS_DATABASE using the
    # verified phone number — never trusted directly from the URL. This closes the
    # earlier bug where anyone could type ?role=Admin in the address bar to get
    # admin access without a password.
    if q_phone and q_phone in USERS_DATABASE and verify_session_token(q_phone, q_token):
        user = USERS_DATABASE[q_phone]
        st.session_state["logged_in"] = True
        st.session_state["user_role"] = user["role"]
        st.session_state["user_name"] = user["name"]
        st.session_state["user_phone"] = q_phone
    else:
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["user_name"] = ""
        st.session_state["user_phone"] = None

st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_role", None)
st.session_state.setdefault("user_name", "")
st.session_state.setdefault("user_phone", None)

def show_login_page():
    _, form_col, _ = st.columns([1, 1.4, 1])
    with form_col:
        st.markdown(
            "<div class=\"login-card\">"
            "<div class=\"login-icon\">📚</div>"
            "<div class=\"login-badge\">2026</div>"
            "<h2>2026ஆம் ஆண்டு புதிய நூல்கள் கொள்முதல்</h2>"
            "<p>பதிப்பாளர்களின் புதிய நூல்கள் விநியோகம் &amp; சரிபார்ப்பு தளம்</p>"
            "<hr/>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.write("")
        with st.form("secure_login_form"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10, placeholder="10 இலக்க எண்")
            password = st.text_input("🔑 கடவுச்சொல்", type="password")
            submitted = st.form_submit_button("🔓 உள்நுழைக", use_container_width=True)
        if submitted:
            user = authenticate_user(phone, password)
            if user:
                clean_phone = phone.strip()
                st.session_state.update(
                    logged_in=True, user_role=user["role"], user_name=user["name"], user_phone=clean_phone
                )
                st.query_params["phone"] = clean_phone
                st.query_params["token"] = make_session_token(clean_phone)
                st.rerun()
            else:
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

# ============================================================
# 4. CONFIGURATION
# ============================================================
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
DRIVE_FOLDER_ID = "1T3HKPAExdNtC-LOCuh2cDXI-6Kf8dzyq"

# ============================================================
# 5. DATA CONNECTION
# ============================================================
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    # The workbook is .xlsx, so pandas must use the openpyxl engine.
    excel_data = pd.ExcelFile(file_path, engine="openpyxl")

    vendor_df = (
        pd.read_excel(
            file_path,
            sheet_name="Vendor Name",
            engine="openpyxl",
        )
        if "Vendor Name" in excel_data.sheet_names
        else pd.DataFrame()
    )

    book_sheets = [
        sheet for sheet in excel_data.sheet_names
        if "Vendor Wise Book Data" in sheet
    ]
    book_df = (
        pd.read_excel(
            file_path,
            sheet_name=book_sheets[0],
            engine="openpyxl",
        )
        if book_sheets
        else pd.DataFrame()
    )
    return vendor_df, book_df

@st.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(credentials)

@st.cache_resource
def get_drive_service():
    scopes = ["https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    return build("drive", "v3", credentials=credentials, cache_discovery=False)

def clean_text(value):
    if pd.isna(value) or value is None:
        return ""
    value = re.sub(r"^\d+[\.\s\-]*", "", str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF]", "", value).lower()

vendor_df, book_df = load_data(EXCEL_FILE)
sheet_physically = None
sheet_vendor_wise = None
sheet_lib_detail = None
try:
    worksheets = {w.title.strip().lower(): w for w in init_gspread().open_by_key(SPREADSHEET_ID).worksheets()}
    for title, worksheet in worksheets.items():
        if "physically verified" in title:
            sheet_physically = worksheet
        elif "vendor wise book data" in title:
            sheet_vendor_wise = worksheet
        elif "lib_detail" in title or "library" in title:
            sheet_lib_detail = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")
# ============================================================
# 6. FILE HELPERS
# ============================================================
def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"

def get_vendor_number(vendor_id_name, vendor_name):
    value = str(vendor_id_name or vendor_name).strip()
    match = re.search(r"\d+", value)
    return match.group(0) if match else "000"

def excel_bytes(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def pdf_bytes(df, title):
    if PDF_FONT_ERROR is not None:
        raise RuntimeError(f"Tamil PDF font could not be loaded: {PDF_FONT_ERROR}")

    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=7 * mm,
        leftMargin=7 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
    )
    styles = getSampleStyleSheet()

    # Use the regular Tamil font for the title. This prevents the publisher
    # name from becoming boxes when a bold font lacks Tamil glyph mapping.
    title_style = ParagraphStyle(
        "report_title",
        parent=styles["Title"],
        fontName=PDF_FONT_REGULAR,
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#071a38"),
    )
    body_style = ParagraphStyle(
        "report_body",
        parent=styles["BodyText"],
        fontName=PDF_FONT_REGULAR,
        fontSize=8,
        leading=10,
    )

    columns = list(df.columns)
    table_data = [[Paragraph(xml_escape(str(c)), body_style) for c in columns]]
    for row in df.fillna("").astype(str).values.tolist():
        table_data.append(
            [Paragraph(xml_escape(str(value)[:100]), body_style) for value in row]
        )

    widths = [
        max(
            20 * mm,
            min(
                58 * mm,
                (max([len(str(c))] + [len(str(v)) for v in df[c].head(25)]) + 2)
                * 1.15
                * mm,
            ),
        )
        for c in columns
    ]
    available_width = landscape(A4)[0] - 14 * mm
    total_width = sum(widths)
    if total_width > available_width:
        scale = available_width / total_width
        widths = [width * scale for width in widths]

    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9db6d5")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5ff")]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    document.build(
        [Paragraph(xml_escape(str(title)), title_style), Spacer(1, 4 * mm), table]
    )
    return output.getvalue()

def upload_pdf_to_drive(pdf_data, vendor_id_name, vendor_name):
    vendor_number = get_vendor_number(vendor_id_name, vendor_name)
    file_name = f"{vendor_number}_{safe_name(vendor_name).replace(' ', '_')}_Physical_Verification.pdf"
    metadata = {"name": file_name, "parents": [DRIVE_FOLDER_ID], "mimeType": "application/pdf"}
    media = MediaIoBaseUpload(io.BytesIO(pdf_data), mimetype="application/pdf", resumable=False)
    return get_drive_service().files().create(body=metadata, media_body=media, fields="id,name,webViewLink", supportsAllDrives=True).execute()

def download_panel(df, prefix, sheet_name):
    st.markdown("### 📥 பதிவிறக்க வசதிகள்")
    # Stacked full-width buttons instead of 3 cramped columns — much easier to
    # tap accurately on a phone screen than three squeezed-together buttons.
    st.download_button(
        "📊 Excel பதிவிறக்கம்", excel_bytes(df, sheet_name), f"{prefix}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True, key=f"dl_xlsx_{prefix}",
    )
    st.download_button(
        "📄 CSV பதிவிறக்கம்", csv_bytes(df), f"{prefix}.csv", "text/csv",
        use_container_width=True, key=f"dl_csv_{prefix}",
    )
    st.download_button(
        "🧾 PDF பதிவிறக்கம்", pdf_bytes(df, sheet_name), f"{prefix}.pdf", "application/pdf",
        use_container_width=True, key=f"dl_pdf_{prefix}",
    )

# ============================================================
# 7. NAVIGATION
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("selected_vendor", None)
st.session_state.setdefault("temp_verified_records", [])
st.session_state.setdefault("library_key", 0)
st.session_state.setdefault("selected_library", None)
st.session_state.setdefault("acc_library_key", 0)
st.session_state.setdefault("selected_acc_library", None)

if st.session_state["user_role"] == "Admin":
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
        "⚙️ 5. Accession எண்கள் மேலாண்மை",
    ]
else:
    menu_items = ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"]

if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]

st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
info_col, logout_col = st.columns([3.2, 0.8])
with info_col:
    st.markdown(
        f'<div class="profile-card">👤 <b>பயனர்:</b> {st.session_state["user_name"]} &nbsp;|&nbsp; '
        f'<b>அதிகாரம்:</b> {"👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"}</div>',
        unsafe_allow_html=True,
    )
with logout_col:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

selected_main_menu = st.selectbox(
    "🧭 செய்ய வேண்டிய பணியைத் தேர்ந்தெடுக்கவும்", menu_items,
    index=menu_items.index(st.session_state["current_page"]), key="main_screen_menu_selectbox",
)
if selected_main_menu != st.session_state["current_page"]:
    st.session_state["current_page"] = selected_main_menu
    st.rerun()
menu_choice = st.session_state["current_page"]
st.markdown("---")

# ============================================================
# 8. TASK 1 - PHYSICAL VERIFICATION + PDF + DRIVE
# ============================================================
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    already_verified_clean = set()
    if sheet_physically:
        try:
            rows = sheet_physically.get_all_values()
            for row in rows[1:]:
                if len(row) > 4 and row[4]:
                    already_verified_clean.add(clean_text(row[4]))
                elif row and row[0]:
                    already_verified_clean.add(clean_text(row[0]))
        except Exception:
            pass

    vendor_list = []
    vendor_id_map = {}
    for _, row in vendor_df.iterrows():
        col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
        col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
        vendor_name = col_c if col_c and col_c.lower() != "nan" else col_b
        full_id_name = col_b if col_b and col_b.lower() != "nan" else col_c
        if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
            vendor_list.append(vendor_name)
            vendor_id_map[vendor_name] = full_id_name

    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    selected_vendor_raw = st.selectbox("பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list, key=f"vendor_select_{st.session_state['vendor_key']}")
    if selected_vendor_raw != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and st.session_state["selected_vendor"] != selected_vendor_raw:
        st.session_state["selected_vendor"] = selected_vendor_raw
        st.session_state["temp_verified_records"] = []

    if st.session_state["selected_vendor"]:
        completed_vendor_name = st.session_state["selected_vendor"]
        target_vendor_clean = clean_text(completed_vendor_name)
        if target_vendor_clean in already_verified_clean:
            st.error(f"⚠️ **{completed_vendor_name}** பதிப்பகத்தின் சரிபார்ப்பு பணி ஏற்கனவே முடிவுற்றது!")
            if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்க", use_container_width=True):
                st.session_state["selected_vendor"] = None
                st.session_state["temp_verified_records"] = []
                st.session_state["vendor_key"] += 1
                st.rerun()
        else:
            vendor_mask = (book_df.iloc[:, 9].apply(clean_text) == target_vendor_clean) | (book_df.iloc[:, 10].apply(clean_text) == target_vendor_clean)
            filtered_books = book_df[vendor_mask]
            if filtered_books.empty:
                st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
            else:
                grouped = filtered_books.groupby(["Title", "Author Name", "Language"], as_index=False).agg({"Quantity":"sum", "Original Price":"first", "Acccepted Price":"first", "Isbn":"first", "Book Id":"first"})
                c1, c2 = st.columns(2)
                c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
                c2.metric("📦 மொத்தப் படிகள்", int(grouped["Quantity"].sum()))
                st.markdown("### 🔍 2. ஒவ்வொரு தலைப்பாகத் தேர்வு செய்து சரிபார்க்கவும்")

                verified_titles = {item["Title"] for item in st.session_state["temp_verified_records"]}
                remaining_titles = [title for title in grouped["Title"].tolist() if title not in verified_titles]
                if not remaining_titles:
                    st.success("🎉 இந்த பதிப்பகத்தில் உள்ள அனைத்துத் தலைப்புகளும் தற்காலிகப் பட்டியலில் சேர்க்கப்பட்டுவிட்டன!")
                else:
                    selected_title = st.selectbox("புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்", ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"] + remaining_titles, key=f"title_select_{len(st.session_state['temp_verified_records'])}")
                    if selected_title != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                        book_row = grouped[grouped["Title"] == selected_title].iloc[0]
                        t_author = book_row["Author Name"] if pd.notna(book_row["Author Name"]) else ""
                        t_lang = book_row["Language"]
                        t_total_qty = int(book_row["Quantity"])
                        st.markdown(f'<div class="book-info-card">📖 <b>தலைப்பு:</b> {selected_title}<br>✍️ <b>ஆசிரியர்:</b> {t_author}<br>🌐 <b>மொழி:</b> {t_lang}<br><span class="total-qty">📦 பெற வேண்டிய மொத்த எண்ணிக்கை: {t_total_qty}</span></div>', unsafe_allow_html=True)

                        rec_qty = st.number_input("✍️ பெறப்பட்ட எண்ணிக்கையை மட்டும் உள்ளிடவும் (Received Qty)", min_value=0, max_value=t_total_qty, value=0, step=1, key=f"rec_inp_{selected_title}")
                        not_rec = t_total_qty - rec_qty
                        st.markdown(f'<div class="not-received-card">❌ பெறப்படாத எண்ணிக்கை: {not_rec}</div>', unsafe_allow_html=True)
                        st.caption("பெற வேண்டிய மொத்த எண்ணிக்கை தானாக வரும். மேலே உள்ள பெறப்பட்ட எண்ணிக்கை பெட்டியில் மட்டும் உள்ளிடவும்.")

                        if st.button("➕ தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                            id_with_vendor = vendor_id_map.get(completed_vendor_name, completed_vendor_name)
                            st.session_state["temp_verified_records"].append({"Title":selected_title,"Author Name":t_author,"Language":t_lang,"Total Qty":t_total_qty,"Received":rec_qty,"Not Received":not_rec,"Short / Extra":str(rec_qty-t_total_qty) if rec_qty != t_total_qty else "0","ID with Vendor Name":id_with_vendor,"Vendor Name":completed_vendor_name,"Date":datetime.now().strftime("%d-%m-%y %H:%M:%S")})
                            st.success(f"✅ '{selected_title}' சேர்க்கப்பட்டது!")
                            time.sleep(0.3)
                            st.rerun()

                if st.session_state["temp_verified_records"]:
                    st.markdown(f"### 📋 தற்காலிகச் சரிபார்ப்புப் பட்டியல் ({len(st.session_state['temp_verified_records'])} தலைப்புகள்)")
                    temp_df = pd.DataFrame(st.session_state["temp_verified_records"])
                    display_cols = ["Title", "Author Name", "Language", "Total Qty", "Received", "Not Received", "Short / Extra", "Date"]
                    st.dataframe(temp_df[display_cols], use_container_width=True, hide_index=True)
                    st.markdown("### 📥 தற்போதைய பதிப்பக அறிக்கை")
                    vendor_pdf = pdf_bytes(temp_df[display_cols], f"{completed_vendor_name} - Physical Verification")
                    vendor_prefix = f"{get_vendor_number(vendor_id_map.get(completed_vendor_name), completed_vendor_name)}_{safe_name(completed_vendor_name).replace(' ', '_')}_Physical_Verification"
                    st.download_button("🧾 PDF பதிவிறக்கம்", vendor_pdf, f"{vendor_prefix}.pdf", "application/pdf", use_container_width=True, key="task1_pdf_download")

                    clr_col, save_col = st.columns(2)
                    with clr_col:
                        if st.button("🗑️ அனைத்தையும் அழி", use_container_width=True):
                            st.session_state["temp_verified_records"] = []
                            st.rerun()
                    with save_col:
                        if st.button("💾 சீட்டில் சேமி", use_container_width=True):
                            if len(st.session_state["temp_verified_records"]) < len(grouped):
                                st.error(f"⚠️ இந்த பதிப்பகத்தில் மொத்தம் {len(grouped)} தலைப்புகள் உள்ளன. அனைத்துத் தலைப்புகளையும் சேர்த்த பின்னரே சேமிக்க முடியும்!")
                            elif not sheet_physically:
                                st.error("❌ Google Sheet இணைப்பு கிடைக்கவில்லை!")
                            else:
                                try:
                                    with st.spinner("சீட்டில் சேமிக்கப்படுகிறது..."):
                                        for item in st.session_state["temp_verified_records"]:
                                            sheet_physically.append_row([item["ID with Vendor Name"],item["Title"],item["Language"],item["Author Name"],item["Vendor Name"],item["Total Qty"],item["Received"],item["Not Received"],item["Short / Extra"],item["Date"]])
                                    try:
                                        drive_pdf = pdf_bytes(temp_df[display_cols], f"{completed_vendor_name} - Physical Verification")
                                        uploaded = upload_pdf_to_drive(drive_pdf, vendor_id_map.get(completed_vendor_name), completed_vendor_name)
                                        st.success(f"✅ Google Sheet-ல் சேமிக்கப்பட்டது. PDF Drive-ல் சேமிக்கப்பட்டது: {uploaded.get('name', '')}")
                                    except Exception as drive_error:
                                        st.warning(f"⚠️ Sheet சேமிக்கப்பட்டது; ஆனால் Drive PDF சேமிக்கப்படவில்லை: {drive_error}")
                                    time.sleep(1)
                                    st.session_state["selected_vendor"] = None
                                    st.session_state["temp_verified_records"] = []
                                    st.session_state["vendor_key"] += 1
                                    st.rerun()
                                except Exception as error:
                                    st.error(f"❌ சேமிப்பதில் பிழை: {error}")

# ============================================================
# 9. TASK 2 - VENDOR WISE SYNC
# ============================================================
elif menu_choice == "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்":
    st.subheader("🔄 Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை ஒத்திசைவு (Sync)")
    if sheet_physically is None or sheet_vendor_wise is None:
        st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!")
        st.stop()
    try:
        phys_rows = sheet_physically.get_all_values(); phys_headers = [str(h).strip().lower() for h in phys_rows[0]] if phys_rows else []
        v_name_idx = next((i for i,h in enumerate(phys_headers) if "vendor" in h),4); title_idx = next((i for i,h in enumerate(phys_headers) if "title" in h),1); rec_idx = next((i for i,h in enumerate(phys_headers) if "received" in h and "not" not in h),6)
        ws_data = sheet_vendor_wise.get_all_values(); ws_headers = [str(h).strip().lower() for h in ws_data[0]]; s_col = next((i for i,h in enumerate(ws_headers) if "received" in h and "not" not in h),18)
        vendor_records = {}
        for row in phys_rows[1:]:
            if len(row)>v_name_idx and row[v_name_idx].strip(): vendor_records.setdefault(row[v_name_idx].strip(),[]).append(row)
        unsynced=[]
        for vendor_name,records in vendor_records.items():
            complete=True
            for p_row in records:
                found=False; p_title=clean_text(p_row[title_idx])
                for w_row in ws_data[1:]:
                    w_vendor=clean_text(w_row[10] if len(w_row)>10 else (w_row[9] if len(w_row)>9 else "")); w_title=clean_text(w_row[4] if len(w_row)>4 else "")
                    if clean_text(vendor_name) in w_vendor and p_title==w_title and len(w_row)>s_col and str(w_row[s_col]).strip(): found=True; break
                if not found: complete=False; break
            if not complete: unsynced.append(vendor_name)
        if not unsynced: st.warning("⚠️ ஒத்திசைவு செய்ய வேண்டிய புதிய பதிப்பகங்கள் எதுவும் இல்லை.")
        else:
            selected_vendor=st.selectbox("ஒத்திசைவு செய்ய வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"]+unsynced,key="vendor_select_t2")
            if selected_vendor!="-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                target=clean_text(selected_vendor); records=[r for r in phys_rows[1:] if len(r)>max(v_name_idx,title_idx,rec_idx) and target in clean_text(r[v_name_idx])]; view=pd.DataFrame([{"Title":r[title_idx],"Received":r[rec_idx]} for r in records]); st.dataframe(view,use_container_width=True,hide_index=True)
                if st.button("🚀 இந்த பதிப்பகத்திற்கு மட்டும் ஒத்திசைவு செய்க",use_container_width=True):
                    ws_data=sheet_vendor_wise.get_all_values(); ws_headers=[str(h).strip().lower() for h in ws_data[0]]; s_col=next((i+1 for i,h in enumerate(ws_headers) if "received" in h and "not" not in h),19); t_col=next((i+1 for i,h in enumerate(ws_headers) if "not received" in h or ("not" in h and "received" in h)),20); qty_col=next((i+1 for i,h in enumerate(ws_headers) if h=="quantity"),18); cells=[]
                    for p_row in records:
                        try: remaining=int(p_row[rec_idx])
                        except: remaining=0
                        matches=[]
                        for row_num,row in enumerate(ws_data[1:],start=2):
                            if target in clean_text(row[10] if len(row)>10 else (row[9] if len(row)>9 else "")) and clean_text(p_row[title_idx])==clean_text(row[4] if len(row)>4 else ""): matches.append((row_num,row))
                        for row_num,row in matches:
                            try: qty=int(row[qty_col-1]) if len(row)>=qty_col and row[qty_col-1] else 1
                            except: qty=1
                            got=min(remaining,qty); cells.extend([Cell(row=row_num,col=s_col,value=str(got)),Cell(row=row_num,col=t_col,value=str(qty-got))]); remaining-=got
                    if cells: sheet_vendor_wise.update_cells(cells)
                    st.success(f"✅ {selected_vendor} ஒத்திசைக்கப்பட்டது!"); time.sleep(1); st.rerun()
    except Exception as error: st.error(f"❌ பிழை: {error}")

# ============================================================
# 10. TASK 3 - VENDOR DETAILS
# ============================================================
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")
    if vendor_df is None or book_df is None: st.error("❌ தரவு கிடைக்கவில்லை!"); st.stop()
    vendors=[]
    for _,row in vendor_df.iterrows():
        b=str(row.iloc[1]).strip() if len(row)>1 and pd.notna(row.iloc[1]) else ""; c=str(row.iloc[2]).strip() if len(row)>2 and pd.notna(row.iloc[2]) else ""; name=c if c and c.lower()!="nan" else b
        if name and name not in vendors: vendors.append(name)
    selected=st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",["-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"]+vendors,key="vendor_select_t3")
    if selected=="-- அனைத்து பதிப்பாளர்களும் (All Publishers) --": result=vendor_df
    else:
        mask=(book_df.iloc[:,9].apply(clean_text)==clean_text(selected))|(book_df.iloc[:,10].apply(clean_text)==clean_text(selected)); result=book_df[mask]
    st.dataframe(result,use_container_width=True,hide_index=True)
    if not result.empty: download_panel(result,safe_name(selected)+"_Vendor_Details","Vendor Details")

# ============================================================
# 11. TASK 4 - LIBRARY DISTRIBUTION
# ============================================================
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")
    if book_df is None or book_df.empty: st.error("❌ புத்தகத் தரவு கிடைக்கவில்லை!"); st.stop()
    base_df=book_df.copy(); drop_cols=[c for c in base_df.columns if any(k in str(c).lower() for k in ["v s.no","temp no","v.s.no","temp"])]; base_df=base_df.drop(columns=drop_cols,errors="ignore"); cmap={str(c).lower().strip():c for c in base_df.columns}; lib_id_col=next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k or "librarian" in k),base_df.columns[11] if len(base_df.columns)>11 else None); lib_name_col=next((cmap[k] for k in cmap if "library name" in k),base_df.columns[12] if len(base_df.columns)>12 else None)
    lib_dict={}; names=[]
    if lib_name_col and lib_id_col:
        for _,r in base_df.dropna(subset=[lib_name_col,lib_id_col]).iterrows():
            name=str(r[lib_name_col]).strip(); lib_dict[name]=str(r[lib_id_col]).strip()
            if name and name not in names:names.append(name)
    selected=st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்",["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --","-- அனைத்து நூலகங்களும் (All Libraries) --"]+sorted(names),key=f"library_select_{st.session_state['library_key']}")
    if selected!="-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --": st.session_state["selected_library"]=selected
    if st.session_state["selected_library"]:
        selected=st.session_state["selected_library"]; result=base_df.copy() if selected=="-- அனைத்து நூலகங்களும் (All Libraries) --" else base_df[base_df[lib_id_col].astype(str).str.strip()==lib_dict.get(selected)].copy()
        if not result.empty:
            result=result.drop(columns=["S.No"],errors="ignore"); result.insert(0,"S.No",range(1,len(result)+1)); st.dataframe(result,use_container_width=True,hide_index=True); download_panel(result,safe_name(selected)+"_Distribution","Library Distribution")
        else: st.warning("⚠️ தரவுகள் எதுவும் இல்லை.")

# ============================================================
# 12. TASK 5 - ACCESSION MANAGEMENT
#     FIX: previously, re-opening the same library re-generated brand-new
#     accession numbers every time (the "last used" counters in Lib_Detail
#     were never written back after saving), which could silently create
#     duplicate accession numbers across runs. Now:
#       (a) rows that already have a saved accession number are detected
#           and shown as-is, never re-numbered;
#       (b) after a successful save, the running counters are written back
#           to Lib_Detail so the next run continues from the correct point.
# ============================================================
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. தானியங்கி மைய மற்றும் கிளை நூல் சேர்க்கை எண்கள் மேலாண்மை")
    st.error("🚨 பெறப்பட்ட நூல்களுக்கு (Received Qty) மட்டுமே சேர்க்கை எண்கள் உருவாக்கப்படும்.")
    if book_df is None or book_df.empty or sheet_vendor_wise is None:
        st.error("❌ தரவு அல்லது Google Sheet இணைப்பு கிடைக்கவில்லை!"); st.stop()

    base_df = book_df.copy()
    cmap = {str(c).lower().strip(): c for c in base_df.columns}
    lib_name_col = next((cmap[k] for k in cmap if "library name" in k), base_df.columns[12] if len(base_df.columns) > 12 else None)
    lib_id_col = next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k), base_df.columns[11] if len(base_df.columns) > 11 else None)
    lib_dict = {str(r[lib_name_col]).strip(): str(r[lib_id_col]).strip() for _, r in base_df.dropna(subset=[lib_name_col, lib_id_col]).iterrows()}
    names = sorted(lib_dict)

    selected = st.selectbox("சேர்க்கை எண்களைப் பதிவு செய்ய நூலகத்தைத் தேர்ந்தெடுக்கவும்", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + names, key=f"acc_library_select_{st.session_state['acc_library_key']}")
    if selected != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
        st.session_state["selected_acc_library"] = selected

    if st.session_state["selected_acc_library"]:
        selected = st.session_state["selected_acc_library"]
        target_id = lib_dict.get(selected)
        central_start = branch_start = None
        central_row_num = branch_row_num = None

        if sheet_lib_detail:
            try:
                lib_rows = sheet_lib_detail.get_all_values()
                for idx, row in enumerate(lib_rows[1:], start=2):
                    if central_start is None and len(row) > 5 and str(row[5]).strip().isdigit():
                        central_start = int(row[5])
                        central_row_num = idx
                    if len(row) > 1 and str(row[1]).strip() == target_id and len(row) > 6 and str(row[6]).strip().isdigit():
                        branch_start = int(row[6])
                        branch_row_num = idx
            except Exception as error:
                st.warning(f"⚠️ Lib_Detail பிழை: {error}")

        if central_row_num is None or branch_row_num is None:
            st.warning("⚠️ Lib_Detail சீட்டில் இந்த நூலகத்திற்கான தொடக்க எண் கிடைக்கவில்லை. சேமித்தவுடன் அடுத்த முறை எண் மேலெழுதப்படலாம் — Lib_Detail சீட்டைச் சரிபார்க்கவும்.")

        try:
            rows = sheet_vendor_wise.get_all_values()
            headers = [str(h).strip().lower() for h in rows[0]]
            lib_idx = next((i for i, h in enumerate(headers) if "librarianid" in h or "lib id" in h), 11)
            title_idx = next((i for i, h in enumerate(headers) if "title" in h), 4)
            qty_idx = next((i for i, h in enumerate(headers) if h == "quantity"), 17)
            rec_idx = next((i for i, h in enumerate(headers) if "received" in h and "not" not in h), 18)
            central_col_idx = 20  # column U (0-based)
            branch_col_idx = 21   # column V (0-based)

            records = []
            for row_num, row in enumerate(rows[1:], start=2):
                if len(row) > lib_idx and str(row[lib_idx]).strip() == target_id:
                    try:
                        q = int(row[qty_idx]) if str(row[qty_idx]).strip().isdigit() else 1
                    except Exception:
                        q = 1
                    try:
                        r = int(row[rec_idx]) if str(row[rec_idx]).strip().isdigit() else 0
                    except Exception:
                        r = 0
                    existing_central = row[central_col_idx].strip() if len(row) > central_col_idx and row[central_col_idx] else ""
                    existing_branch = row[branch_col_idx].strip() if len(row) > branch_col_idx and row[branch_col_idx] else ""
                    records.append({
                        "Sheet Row": row_num,
                        "Title": row[title_idx],
                        "Quantity": q,
                        "Received": r,
                        "Author Name": row[3] if len(row) > 3 else "",
                        "Language": row[2] if len(row) > 2 else "",
                        "Existing Central": existing_central,
                        "Existing Branch": existing_branch,
                    })

            if records:
                curr_c = central_start or 0
                curr_b = branch_start or 0
                display = []
                for item in records:
                    if item["Existing Central"] or item["Existing Branch"]:
                        # Already assigned earlier — show as-is, do NOT re-number.
                        display.append({
                            **item,
                            "Central Accession No": item["Existing Central"],
                            "Branch Accession No": item["Existing Branch"],
                            "_is_new": False,
                        })
                        continue
                    central, branch = [], []
                    for _ in range(item["Received"]):
                        curr_c += 1
                        central.append(str(curr_c))
                        curr_b += 1
                        branch.append(str(curr_b))
                    display.append({
                        **item,
                        "Central Accession No": ", ".join(central),
                        "Branch Accession No": ", ".join(branch),
                        "_is_new": True,
                    })

                preview = pd.DataFrame(display)
                visible = preview.drop(columns=["Sheet Row", "Existing Central", "Existing Branch", "_is_new"])
                st.dataframe(visible, use_container_width=True, hide_index=True)

                new_count = sum(1 for item in display if item["_is_new"] and item["Received"] > 0)
                if new_count == 0:
                    st.info("ℹ️ இந்த நூலகத்திற்கு ஏற்கனவே அனைத்து சேர்க்கை எண்களும் ஒதுக்கப்பட்டுள்ளன.")

                if st.button("💾 Google Sheet (U & V தூண்களில்) சேமி", use_container_width=True):
                    cells = []
                    for item in display:
                        if item["_is_new"]:
                            cells.extend([
                                Cell(row=item["Sheet Row"], col=21, value=item["Central Accession No"]),
                                Cell(row=item["Sheet Row"], col=22, value=item["Branch Accession No"]),
                            ])
                    if cells:
                        sheet_vendor_wise.update_cells(cells)
                    # Persist the running counters back to Lib_Detail so the NEXT
                    # time this library (or the shared central pool) is opened,
                    # numbering continues on instead of restarting — this is
                    # the fix for the duplicate-accession-number bug.
                    if sheet_lib_detail and central_row_num and branch_row_num:
                        try:
                            sheet_lib_detail.update_cells([
                                Cell(row=central_row_num, col=6, value=str(curr_c)),
                                Cell(row=branch_row_num, col=7, value=str(curr_b)),
                            ])
                        except Exception as counter_error:
                            st.warning(f"⚠️ Lib_Detail எண்ணிக்கை (counter) புதுப்பிக்கப்படவில்லை: {counter_error}")
                    st.success("✅ சேர்க்கை எண்கள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    time.sleep(1)
                    st.rerun()

                download_panel(visible, safe_name(selected) + "_Accession_Register", "Accession Register")
            else:
                st.warning("⚠️ இந்த நூலகத்திற்குப் புத்தகங்கள் எதுவும் இல்லை.")
        except Exception as error:
            st.error(f"❌ பிழை ஏற்பட்டது: {error}")
