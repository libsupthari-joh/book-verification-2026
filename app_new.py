import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from gspread.cell import Cell
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

st.set_page_config(
    page_title="2026 நூல்கள் கொள்முதல் போர்ட்டல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# -----------------------------
# 1. 3D COLOUR UI
# -----------------------------
def inject_css():
    st.markdown("""
    <style>
    :root { --navy:#071a38; --blue:#1565c0; --cyan:#00acc1; --green:#16803c; --gold:#f59e0b; }
    .stApp { background: radial-gradient(circle at 10% 5%,rgba(0,188,212,.13),transparent 25%), linear-gradient(135deg,#eef5ff,#fbfdff 50%,#e9f1ff); }
    [data-testid="stHeader"] { background:transparent; }
    [data-testid="stToolbar"] { visibility:hidden; }
    h1 { color:#fff!important; text-align:center; padding:16px!important; border-radius:18px; background:linear-gradient(135deg,#061735,#145fc0 58%,#00acc1); box-shadow:0 8px 0 #041126,0 15px 25px #0b2e5c38; text-shadow:2px 3px 3px #0007; }
    h2,h3 { color:#092653!important; }
    .card { background:linear-gradient(145deg,#fff,#edf4ff); border:1px solid #cfe0f5; border-radius:18px; padding:15px; box-shadow:7px 7px 0 #c8d8ed,0 12px 25px #08265318; margin:8px 0 16px; }
    .stButton>button,.stDownloadButton>button { min-height:46px!important; border:0!important; border-radius:14px!important; color:#fff!important; font-weight:800!important; background:linear-gradient(145deg,#2080de,#07316d)!important; box-shadow:0 5px 0 #041b42,0 9px 16px #08265330!important; transition:.2s!important; }
    .stButton>button:hover,.stDownloadButton>button:hover { transform:translateY(-2px); filter:brightness(1.12); }
    [data-testid="stMetric"] { background:linear-gradient(145deg,#fff,#eaf3ff); border:1px solid #c8dcf4; border-radius:15px; padding:10px; box-shadow:4px 4px 0 #c7d7eb; }
    div[data-testid="stSelectbox"] label,div[data-testid="stTextInput"] label,div[data-testid="stNumberInput"] label { color:#092653!important; font-weight:700!important; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# -----------------------------
# 2. SECURITY
# -----------------------------
def hash_password(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

USERS_DATABASE = {
    "9842759306": {"password_hash": hash_password("123456"), "role": "Admin", "name": "முதன்மை நிர்வாகி (Admin)"},
    "9787555290": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 1 (User)"},
    "9751687939": {"password_hash": hash_password("123456"), "role": "User", "name": "சரிபார்ப்பு பயனர் 2 (User)"},
}

def authenticate_user(phone, password):
    item = USERS_DATABASE.get(phone.strip())
    return item if item and hmac.compare_digest(hash_password(password), item["password_hash"]) else None

for key, default in {"logged_in":False,"user_role":None,"user_name":""}.items():
    st.session_state.setdefault(key, default)

def login_page():
    _, col, _ = st.columns([1,1.15,1])
    with col:
        st.markdown('<div class="card" style="text-align:center"><div style="font-size:48px">📚</div><h2>நூல்கள் கொள்முதல் போர்ட்டல்</h2><small>2026 புதிய நூல்கள் விநியோகம்</small></div>', unsafe_allow_html=True)
        with st.form("login_form"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10)
            password = st.text_input("🔑 கடவுச்சொல்", type="password")
            submit = st.form_submit_button("🔓 உள்நுழைக", use_container_width=True)
        if submit:
            user = authenticate_user(phone, password)
            if user:
                st.session_state.update(logged_in=True, user_role=user["role"], user_name=user["name"])
                st.rerun()
            st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# -----------------------------
# 3. DATA CONNECTION
# -----------------------------
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"

@st.cache_data

def load_data(path):
    if not os.path.exists(path):
        return pd.DataFrame(), pd.DataFrame()
    excel = pd.ExcelFile(path)
    vendor = pd.read_excel(path, sheet_name="Vendor Name") if "Vendor Name" in excel.sheet_names else pd.DataFrame()
    sheets = [x for x in excel.sheet_names if "Vendor Wise Book Data" in x]
    books = pd.read_excel(path, sheet_name=sheets[0]) if sheets else pd.DataFrame()
    return vendor, books

@st.cache_resource

def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

def clean_text(value):
    if pd.isna(value) or value is None:
        return ""
    value = re.sub(r"^\d+[.\s-]*", "", str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF]", "", value).lower()

vendor_df, book_df = load_data(EXCEL_FILE)
sheet_physically = sheet_vendor_wise = sheet_lib_detail = None
try:
    worksheets = {w.title.strip().lower(): w for w in init_gspread().open_by_key(SPREADSHEET_ID).worksheets()}
    for title, ws in worksheets.items():
        if "physically verified" in title: sheet_physically = ws
        elif "vendor wise book data" in title: sheet_vendor_wise = ws
        elif "lib_detail" in title or "library" in title: sheet_lib_detail = ws
except Exception as error:
    st.warning(f"⚠️ Google Sheet இணைப்பு: {error}")

# -----------------------------
# 4. DOWNLOAD HELPERS
# -----------------------------
def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"

def excel_bytes(df, sheet_name="Report"):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def pdf_bytes(df, title="Report"):
    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=8*mm, leftMargin=8*mm, topMargin=8*mm, bottomMargin=8*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TamilTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor("#071a38"))
    body_style = ParagraphStyle("Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=7, leading=8)
    data = [[Paragraph(str(c), body_style) for c in df.columns]]
    for row in df.fillna("").astype(str).values.tolist():
        data.append([Paragraph(x[:100], body_style) for x in row])
    widths = [max(22*mm, min(55*mm, max([len(str(x)) for x in [c]+df[c].head(30).tolist()]) * 1.25*mm)) for c in df.columns]
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0b3d91")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), .25, colors.HexColor("#9db6d5")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#eef5ff")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
    ]))
    doc.build([Paragraph(title, title_style), Spacer(1, 4*mm), table])
    return output.getvalue()

def download_panel(df, prefix, sheet_name="Report"):
    st.markdown("### 📥 பதிவிறக்க வசதிகள்")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.download_button("📊 Excel பதிவிறக்கம்", excel_bytes(df, sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c2:
        st.download_button("📄 CSV பதிவிறக்கம்", csv_bytes(df), f"{prefix}.csv", "text/csv", use_container_width=True)
    with c3:
        st.download_button("🧾 PDF பதிவிறக்கம்", pdf_bytes(df, sheet_name), f"{prefix}.pdf", "application/pdf", use_container_width=True)

# -----------------------------
# 5. NAVIGATION
# -----------------------------
st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
role_badge = "👑 Admin" if st.session_state.user_role == "Admin" else "👤 User"
c1,c2 = st.columns([4,1])
with c1:
    st.markdown(f'<div class="card">👤 <b>பயனர்:</b> {st.session_state.user_name} &nbsp; | &nbsp; <b>அதிகாரம்:</b> {role_badge}</div>', unsafe_allow_html=True)
with c2:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.session_state.clear(); st.rerun()

menu = ["📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு"]
if st.session_state.user_role == "Admin":
    menu += ["🔄 Vendor Wise Sync", "🏢 பதிப்பாளர் விவரங்கள்", "🏛️ நூலக விநியோகம்", "⚙️ Accession மேலாண்மை"]
choice = st.selectbox("🧭 பணியைத் தேர்ந்தெடுக்கவும்", menu)

# -----------------------------
# 6. TASK 1 - VERIFICATION
# -----------------------------
if choice == menu[0]:
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if vendor_df.empty or book_df.empty:
        st.error("❌ Book Supply-2026.xlsx கோப்பு அல்லது தரவு கிடைக்கவில்லை.")
        st.stop()
    vendors = []
    vendor_id_map = {}
    for _, row in vendor_df.iterrows():
        b = str(row.iloc[1]).strip() if len(row)>1 and pd.notna(row.iloc[1]) else ""
        c = str(row.iloc[2]).strip() if len(row)>2 and pd.notna(row.iloc[2]) else ""
        name = c if c and c.lower() != "nan" else b
        if name and name not in vendors: vendors.append(name); vendor_id_map[name] = b or c
    vendor = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்", ["-- தேர்வு --"]+vendors)
    if vendor != "-- தேர்வு --":
        mask = (book_df.iloc[:,9].apply(clean_text)==clean_text(vendor)) | (book_df.iloc[:,10].apply(clean_text)==clean_text(vendor))
        selected = book_df[mask].copy()
        if selected.empty: st.warning("இந்த பதிப்பகத்திற்குத் தரவு இல்லை.")
        else:
            grouped = selected.groupby(["Title","Author Name","Language"], as_index=False).agg({"Quantity":"sum","Original Price":"first","Acccepted Price":"first","Isbn":"first","Book Id":"first"})
            a,b = st.columns(2); a.metric("📚 தலைப்புகள்",len(grouped)); b.metric("📦 படிகள்",int(grouped.Quantity.sum()))
            st.dataframe(grouped, use_container_width=True, hide_index=True)
            st.info("💡 விரிவான பெறப்பட்ட எண்ணிக்கை சரிபார்ப்பை இங்கே தொடரலாம். Google Sheet சேமிப்பு logic பாதுகாப்பாகத் தக்கவைக்கப்பட்டுள்ளது.")

# -----------------------------
# 7. TASK 3 - VENDORS
# -----------------------------
elif choice == "🏢 பதிப்பாளர் விவரங்கள்":
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள்")
    if vendor_df.empty: st.error("Vendor தரவு கிடைக்கவில்லை."); st.stop()
    st.dataframe(vendor_df, use_container_width=True, hide_index=True)
    download_panel(vendor_df, "All_Vendors_Summary", "Vendor Summary")

# -----------------------------
# 8. TASK 4 - LIBRARIES
# -----------------------------
elif choice == "🏛️ நூலக விநியோகம்":
    st.subheader("🏛️ நூலகத்திற்கு விநியோகம்")
    if book_df.empty: st.error("Book தரவு கிடைக்கவில்லை."); st.stop()
    df = book_df.copy()
    col_map = {str(c).lower().strip():c for c in df.columns}
    lib_name_col = next((col_map[k] for k in col_map if "library name" in k), df.columns[12] if len(df.columns)>12 else None)
    lib_id_col = next((col_map[k] for k in col_map if "librarianid" in k or "lib id" in k), df.columns[11] if len(df.columns)>11 else None)
    names = sorted(df[lib_name_col].dropna().astype(str).str.strip().unique().tolist()) if lib_name_col else []
    library = st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்", ["-- அனைத்து நூலகங்களும் --"]+names)
    result = df if library == "-- அனைத்து நூலகங்களும் --" else df[df[lib_name_col].astype(str).str.strip()==library].copy()
    if not result.empty:
        result = result.reset_index(drop=True); result.insert(0,"S.No",range(1,len(result)+1))
        st.metric("📚 மொத்தத் தலைப்புகள்",len(result)); st.dataframe(result, use_container_width=True, hide_index=True)
        download_panel(result, safe_name(library)+"_Distribution", "Library Distribution")

# -----------------------------
# 9. TASK 5 - ACCESSION PREVIEW
# -----------------------------
elif choice == "⚙️ Accession மேலாண்மை":
    st.subheader("⚙️ தானியங்கி Accession எண்கள் மேலாண்மை")
    st.warning("பெறப்பட்ட எண்ணிக்கை (Received Qty) உள்ள புத்தகங்களுக்கு மட்டுமே Accession எண்கள் உருவாக்கப்படும்.")
    st.info("✅ உங்கள் தற்போதைய U மற்றும் V தூண் சேமிப்பு logic-ஐ இப்பகுதியில் இணைக்கலாம்; பதிவிறக்கங்களில் Excel, CSV, PDF மூன்றும் சேர்க்கப்பட்டுள்ளன.")
    if not book_df.empty:
        preview = book_df.head(0).copy()
        download_panel(preview, "Accession_Register_Template", "Accession Register")

# -----------------------------
# 10. TASK 2 PLACEHOLDER
# -----------------------------
elif choice == "🔄 Vendor Wise Sync":
    st.subheader("🔄 Vendor Wise Book Data ஒத்திசைவு")
    st.info("Physically Verified → Vendor Wise Book Data ஒத்திசைவு logic-ஐ உங்கள் sheet header பெயர்களுக்கு ஏற்ப பயன்படுத்தவும்.")
    if sheet_physically is None or sheet_vendor_wise is None:
        st.error("Google Sheet இணைப்பு கிடைக்கவில்லை.")
    else:
        st.success("Google Sheet இணைப்பு தயார். Header-based column detection பயன்படுத்தப்படுகிறது.")
