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

.profile-card, .book-info-card {
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

.login-main-container {
    background: #ffffff;
    border-radius: 20px;
    padding: 40px 35px;
    box-shadow: 0 12px 30px rgba(6, 78, 59, 0.12);
    border: 2px solid #a7f3d0;
    max-width: 500px;
    margin: 40px auto;
}

.login-header-icon {
    font-size: 45px;
    text-align: center;
    margin-bottom: 10px;
}

.login-title {
    text-align: center;
    color: #064e3b;
    font-size: 24px;
    font-weight: 800;
    margin-bottom: 8px;
}

.login-subtitle {
    text-align: center;
    color: #047857;
    font-size: 15px;
    font-weight: 600;
    margin-bottom: 30px;
}

.stButton > button, .stDownloadButton > button {
    min-height: 50px !important;
    border-radius: 10px !important;
    font-size: 16px !important;
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
    "current_page": "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", "verified_records": [],
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
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown("""
        <div class="login-main-container">
            <div class="login-header-icon">📚</div>
            <div class="login-title">2026ஆம் ஆண்டு புதிய நூல்கள் கொள்முதல்</div>
            <div class="login-subtitle">பதிப்பாளர்களின் புதிய நூல்கள் விநியோகம் & சரிபார்ப்பு தளம்</div>
        """, unsafe_allow_html=True)
        
        with st.form("secure_login_form"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10, placeholder="10 இலக்க எண்")
            password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
            submitted = st.form_submit_button("🔓 உள்நுழைக", use_container_width=True)
            
        st.markdown("</div>", unsafe_allow_html=True)
        
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
            output.read()
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
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📊 Excel பதிவிறக்கம்", excel_bytes(frame, sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{prefix}")
    with col2:
        st.download_button("📄 CSV பதிவிறக்கம்", csv_bytes(frame), f"{prefix}.csv", "text/csv", use_container_width=True, key=f"csv_{prefix}")
    with col3:
        try:
            pdf = pdf_bytes(frame, pdf_title or sheet_name)
            st.download_button("🧾 PDF பதிவிறக்கம்", pdf, f"{prefix}.pdf", "application/pdf", use_container_width=True, key=f"pdf_{prefix}")
        except Exception as error:
            st.error(f"❌ PDF உருவாக்க முடியவில்லை: {error}")

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

st.markdown("---python" if False else "")

if st.session_state["current_page"] == menu_items[0]:
    st.subheader("🔎 பதிப்பாளர் வாரியான நூல்கள் சரிபார்ப்பு")
    if df_summary is None or df_summary.empty or df_books is None or df_books.empty:
        st.error("❌ தரவுகள் கிடைக்கவில்லை!")
        st.stop()
        
    # 1. பதிப்பாளரைத் தேர்ந்தெடுக்கும் பகுதி
    if "Publication Name" in df_books.columns:
        publishers = sorted(df_books["Publication Name"].dropna().unique().tolist())
        selected_publisher = st.selectbox(
            "1. பதிப்பாளரைத் தேர்ந்தெடுக்கவும் (Select Publisher):",
            ["-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"] + publishers,
            key="pub_select_dropdown"
        )
        
        if not selected_publisher.startswith("-- அனைத்து"):
            pub_filtered_books = df_books[df_books["Publication Name"] == selected_publisher]
        else:
            pub_filtered_books = df_books
    else:
        pub_filtered_books = df_books

    # 2. தலைப்பு மூலம் தேடும் பகுதி
    search_query = st.text_input("2. புத்தகத் தலைப்பு தட்டச்சு செய்யவும் (குறைந்தது 2 எழுத்துக்கள்)...", placeholder="புத்தகத்தின் தலைப்பை இங்கு தட்டச்சு செய்யவும்...")
    
    # Group books by Title
    grouped_df = pub_filtered_books.groupby("Title", as_index=False).agg({
        "Publication Name": "first",
        "Author Name": "first",
        "Language": "first",
        "Price": "first",
        "Quantity": "sum"
    }).rename(columns={"Publication Name": "பதிப்பகம்", "Title": "தலைப்பு", "Price": "விலை", "Quantity": "எண்ணிக்கை"})
    
    if search_query and len(search_query.strip()) >= 2:
        q_clean = clean_text(search_query)
        filtered_books = grouped_df[grouped_df["தலைப்பு"].apply(clean_text).str.contains(q_clean, na=False)]
    else:
        filtered_books = pd.DataFrame(columns=grouped_df.columns)
        
    if not filtered_books.empty:
        st.markdown(f"**தேடல் முடிவுகள் ({len(filtered_books)} தலைப்புகள் கண்டுபிடிக்கப்பட்டன):**")
        
        display_view = filtered_books[["தலைப்பு", "பதிப்பகம்", "விலை", "எண்ணிக்கை"]].reset_index(drop=True)
        display_view.index = display_view.index + 1
        st.dataframe(display_view, use_container_width=True)
        
        selected_book_title = st.selectbox("சரிபார்க்க வேண்டிய தலைப்பைத் தேர்ந்தெடுக்கவும்", ["-- தேர்ந்தெடுக்கவும் --"] + filtered_books["தலைப்பு"].tolist())
        
        if selected_book_title != "-- தேர்ந்தெடுக்கவும் --":
            b_row = filtered_books[filtered_books["தலைப்பு"] == selected_book_title].iloc[0]
            orig_qty = int(b_row["எண்ணிக்கை"])
            
            with st.form("verify_single_form"):
                st.markdown(f"📖 **தலைப்பு:** {b_row['தலைப்பு']} | 🏢 **பதிப்பகம்:** {b_row['பதிப்பகம்']}")
                rec_qty = st.number_input("பெறப்பட்ட புத்தகங்களின் எண்ணிக்கை (Received Quantity)", min_value=0, max_value=orig_qty, value=orig_qty, step=1)
                
                submitted_rec = st.form_submit_button("💾 இந்தத் தலைப்பைச் சரிபார்த்துச் சேமி", use_container_width=True)
                if submitted_rec:
                    st.session_state["verified_records"].append({
                        "தலைப்பு": b_row["தலைப்பு"],
                        "பதிப்பகம்": b_row["பதிப்பகம்"],
                        "ஆசிரியர்": b_row["Author Name"],
                        "மொழி": b_row["Language"],
                        "விலை": b_row["விலை"],
                        "கோரப்பட்ட எண்ணிக்கை": orig_qty,
                        "பெறப்பட்ட எண்ணிக்கை": rec_qty,
                        "பெறப்படாத எண்ணிக்கை": orig_qty - rec_qty,
                        "தேதி": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    })
                    st.success(f"✅ '{b_row['தலைப்பு']}' வெற்றிகரமாகச் சேமிக்கப்பட்டது!")
                    st.rerun()
    elif search_query and len(search_query.strip()) >= 2:
        st.info("ℹ️ எந்தப் புத்தகமும் கிடைக்கவில்லை. வேறு பெயரைக் முயற்சிக்கவும்.")
    else:
        st.markdown("*(தேடலைத் தொடங்க மேலே உள்ள பெட்டியில் குறைந்தபட்சம் 2 எழுத்துக்களைத் தட்டச்சு செய்யவும் அல்லது பதிப்பாளரை மாற்றவும்)*")
        
    # Show saved verified records table & download options
    if st.session_state["verified_records"]:
        st.markdown("---")
        st.subheader("📋 பதிப்பாளர் / தலைப்பு சரிபார்க்கப்பட்ட தற்காலிகப் பட்டியல்")
        v_df = pd.DataFrame(st.session_state["verified_records"])
        st.dataframe(v_df, use_container_width=True, hide_index=True)
        
        download_panel(v_df, "Verified_Books_Report", "Verified Books Report", "நூல்கள் சரிபார்ப்பு அறிக்கை")
        
        if st.button("🗑️ தற்காலிகப் பட்டியலை முழுமையாக அழிக்க", use_container_width=True):
            st.session_state["verified_records"] = []
            st.rerun()

elif len(menu_items) > 1 and st.session_state["current_page"] == menu_items[1]:
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள்")
    if df_summary is None or df_summary.empty:
        st.error("❌ தரவு கிடைக்கவில்லை!")
        st.stop()
    vendors = sorted(df_summary["Publication Name / Vendor Name"].dropna().unique().tolist())
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
```[cite: 11]
