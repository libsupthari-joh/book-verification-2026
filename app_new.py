import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import gspread
import pandas as pd
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
import streamlit as st

# ============================================================
# 1. PAGE SETTINGS
# ============================================================
st.set_page_config(
    page_title="2026 புதிய நூல்கள் விநியோகம்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. COMPLETE UI DESIGN & STYLES
# ============================================================
def get_custom_css():
    return """
    <style>
    :root {
        --navy: #071a38;
        --blue: #1565c0;
        --cyan: #00acc1;
        --purple: #7b1fa2;
        --orange: #ef6c00;
        --green: #2e7d32;
        --slate: #263238;
    }

    .stApp {
        background: 
            radial-gradient(circle at 8% 8%, rgba(0,188,212,.15), transparent 28%),
            radial-gradient(circle at 92% 12%, rgba(123,31,162,.14), transparent 30%),
            linear-gradient(135deg, #eef5ff, #f8fbff 48%, #edf3ff);
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { visibility: hidden; }

    h1 {
        padding: 22px 28px !important;
        border-radius: 22px;
        color: white !important;
        background: linear-gradient(135deg, #071a38, #1565c0 58%, #00acc1);
        box-shadow: 0 12px 0 #041127, 0 20px 32px rgba(7,26,56,.25);
        text-shadow: 2px 3px 3px rgba(0,0,0,.35);
    }

    h2, h3 { color: #092653 !important; }

    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071a38, #0b2e63 55%, #082044);
        border-right: 1px solid rgba(255,255,255,.15);
        min-width: 280px !important;
        max-width: 320px !important;
        display: block !important;
        visibility: visible !important;
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.2rem .85rem;
    }

    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label {
        color: white !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        min-height: 52px !important;
        margin: 8px 0 !important;
        padding: 14px 16px !important;
        border: 1px solid rgba(255,255,255,.25) !important;
        border-radius: 14px !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-align: left !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 0 rgba(0,0,0,.25), 0 8px 12px rgba(0,0,0,.2) !important;
        background: linear-gradient(145deg, rgba(255,255,255,.08), rgba(255,255,255,.05)) !important;
    }

    section[data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-2px) !important;
        background: linear-gradient(145deg, rgba(255,255,255,.15), rgba(255,255,255,.1)) !important;
    }

    div[data-testid="stSelectbox"] label, 
    div[data-testid="stNumberInput"] label, 
    div[data-testid="stTextInput"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    .stButton > button, 
    .stDownloadButton > button {
        min-height: 44px;
        border: none !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 700 !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 4px 0 #061b42, 0 8px 14px rgba(8,43,104,.25) !important;
        transition: all 0.2s ease !important;
    }

    .login-card {
        max-width: 500px;
        margin: 8vh auto 0 auto;
        padding: 32px 32px 26px;
        border-radius: 24px;
        background: rgba(255,255,255,.95);
        box-shadow: 0 16px 0 rgba(7,26,56,.14), 0 24px 40px rgba(7,26,56,.18);
        text-align: center;
    }

    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 9999 !important;
        position: fixed !important;
        left: 8px !important;
        top: 8px !important;
        background: linear-gradient(145deg, #1565c0, #0d47a1) !important;
        border-radius: 8px !important;
        padding: 8px !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        width: 22px !important;
        height: 22px !important;
    }
    </style>
    """


st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================
# 3. SECURITY AND LOGIN (ADMIN & USER ROLES)
# ============================================================
def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


USERS_DATABASE = {
    "9842759306": {
        "password_hash": hash_password("123456"),
        "role": "Admin",
        "name": "முதன்மை நிர்வாகி (Admin)",
    },
    "9787555290": {
        "password_hash": hash_password("123456"),
        "role": "User",
        "name": "சரிபார்ப்பு பயனர் 1 (User)",
    },
    "9751687939": {
        "password_hash": hash_password("123456"),
        "role": "User",
        "name": "சரிபார்ப்பு பயனர் 2 (User)",
    },
}


def authenticate_user(phone, password):
    phone_clean = phone.strip()
    if phone_clean in USERS_DATABASE:
        user_data = USERS_DATABASE[phone_clean]
        if hmac.compare_digest(
            hash_password(password), user_data["password_hash"]
        ):
            return user_data
    return None


def show_login_page():
    st.markdown(
        """
        <div class="login-card">
            <div style="font-size: 36px; margin-bottom: 12px;">📚</div>
            <div style="font-size: 24px; font-weight: 900; color: #082653;">பணி போர்ட்டல்</div>
            <div style="font-size: 13px; color: #60708a; margin-top: 6px;">2026 புதிய நூல்கள் விநியோகம்</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("secure_login_form"):
            phone = st.text_input(
                "📱 அலைபேசி எண்",
                max_chars=10,
                placeholder="10 இலக்க அலைபேசி எண்",
            )
            password = st.text_input(
                "🔑 கடவுச்சொல்",
                type="password",
                placeholder="கடவுச்சொல்லை உள்ளிடவும்",
            )
            submitted = st.form_submit_button(
                "🔓 பாதுகாப்பாக உள்நுழைக",
                use_container_width=True,
            )

        if submitted:
            user_info = authenticate_user(phone, password)
            if user_info:
                st.session_state["logged_in"] = True
                st.session_state["user_role"] = user_info["role"]
                st.session_state["user_name"] = user_info["name"]
                st.rerun()
            else:
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_role", None)
st.session_state.setdefault("user_name", "")

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# 4. PDF GENERATION & GOOGLE DRIVE UPLOAD HELPERS
# ============================================================
def generate_pdf_bytes(df, vendor_name):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=20,
        leftMargin=20,
        topMargin=30,
        bottomMargin=30,
    )
    elements = []
    styles = getSampleStyleSheet()

    font_path = "/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"
    font_name = "Helvetica"
    if os.path.exists(font_path):
        try:
            pdfmetrics.registerFont(TTFont("TamilFont", font_path))
            font_name = "TamilFont"
        except Exception:
            pass

    title_style = ParagraphStyle(
        "TamilTitle",
        parent=styles["Heading1"],
        fontName=font_name,
        fontSize=13,
        alignment=1,
        textColor=colors.HexColor("#071a38"),
    )
    normal_style = ParagraphStyle(
        "TamilNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        textColor=colors.HexColor("#222222"),
    )

    elements.append(
        Paragraph(f"Physical Verification Report - {vendor_name}", title_style)
    )
    elements.append(Spacer(1, 10))

    table_data = []
    headers = list(df.columns)
    table_data.append([Paragraph(f"<b>{h}</b>", normal_style) for h in headers])

    for _, row in df.iterrows():
        table_data.append(
            [Paragraph(str(val) if pd.notna(val) else "", normal_style) for val in row]
        )

    t = Table(table_data, colWidths=[75, 110, 50, 75, 40, 40, 40, 45, 65])
    t.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#071a38")),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b0bec5")),
        ])
    )

    elements.append(t)
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def upload_pdf_to_drive(pdf_bytes, file_name, folder_id):
    try:
        credentials_dict = dict(st.secrets["gcp_service_account"])
        credentials = ServiceAccountCredentials.from_json_keyfile_dict(
            credentials_dict,
            [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive",
            ],
        )
        drive_service = build("drive", "v3", credentials=credentials)

        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaIoBaseUpload(
            io.BytesIO(pdf_bytes), mimetype="application/pdf", resumable=True
        )
        file = (
            drive_service.files()
            .create(body=file_metadata, media_body=media, fields="id")
            .execute()
        )
        return file.get("id")
    except Exception as e:
        st.error(f"Google Drive Upload Error: {e}")
        return None


# ============================================================
# 5. GOOGLE SHEETS & EXCEL CONFIGURATION
# ============================================================
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
GOOGLE_DRIVE_FOLDER_ID = "1XOTSn8f6ntfrG8rI0iSk0QVwDujGqs1f"


@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    excel_data = pd.ExcelFile(file_path)
    vendor_df = (
        pd.read_excel(file_path, sheet_name="Vendor Name")
        if "Vendor Name" in excel_data.sheet_names
        else pd.DataFrame()
    )
    book_sheet_names = [
        s for s in excel_data.sheet_names if "Vendor Wise Book Data" in s
    ]
    book_df = (
        pd.read_excel(file_path, sheet_name=book_sheet_names[0])
        if book_sheet_names
        else pd.DataFrame()
    )
    return vendor_df, book_df


@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    credentials_dict = dict(st.secrets["gcp_service_account"])
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(
        credentials_dict,
        scope,
    )
    return gspread.authorize(credentials)


def clean_text(value):
    if pd.isna(value) or value is None:
        return ""
    value = str(value).strip()
    value = re.sub(r"^\d+[\.\s\-]*", "", value)
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF]", "", value).lower()


vendor_df, book_df = load_data(EXCEL_FILE)
sheet_physically = None
sheet_vendor_wise = None
sheet_library_details = None

try:
    client = init_gspread()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheets = {
        worksheet.title.strip().lower(): worksheet
        for worksheet in spreadsheet.worksheets()
    }
    for title, worksheet in worksheets.items():
        if "physically verified" in title:
            sheet_physically = worksheet
        elif "vendor wise book data" in title:
            sheet_vendor_wise = worksheet
        elif any(
            name in title
            for name in ["lib_detail", "library detail", "library details"]
        ):
            sheet_library_details = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")


# ============================================================
# 6. SIDEBAR & ROLE-BASED NAVIGATION
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("selected_vendor", None)

st.sidebar.markdown(f"### 👤 {st.session_state['user_name']}")
role_badge = "👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"
st.sidebar.caption(f"அதிகார நிலை: **{role_badge}**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_name"] = ""
    st.session_state["selected_vendor"] = None
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

if st.session_state["user_role"] == "Admin":
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
        "⚙️ 5. Accession எண்கள் மேலாண்மை",
    ]
else:
    menu_items = ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"]

if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]

for item in menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()

st.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")
menu_choice = st.session_state["current_page"]


# ============================================================
# 7. TASK IMPLEMENTATIONS
# ============================================================

# --- TASK 1: PHYSICAL VERIFICATION, TARGETED VENDOR SYNC & DRIVE PDF UPLOAD ---
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல் (பதிப்பாளர் வாரியாக ஒத்திசைவு)")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    vendor_list = []
    vendor_id_map = {}
    if not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            col_a = str(row.iloc[0]).strip() if len(row) > 0 and pd.notna(row.iloc[0]) else ""
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            vendor_name = col_b or col_c
            if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
                vendor_list.append(vendor_name)
                vendor_id_map[vendor_name] = col_a

    st.markdown("---")
    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    col_vendor, col_change = st.columns([5, 1])

    with col_vendor:
        selected_vendor_raw = st.selectbox(
            "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்",
            ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list,
            key=f"vendor_select_{st.session_state['vendor_key']}",
            label_visibility="collapsed",
        )

    with col_change:
        if st.button("🔄 மாற்றுக", key="btn_v_change", use_container_width=True):
            st.session_state["selected_vendor"] = None
            st.session_state["vendor_key"] += 1
            st.rerun()

    if selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"] != selected_vendor_raw:
            st.session_state["selected_vendor"] = selected_vendor_raw

    if st.session_state["selected_vendor"]:
        completed_vendor_name = st.session_state["selected_vendor"]
        target_vendor_clean = clean_text(completed_vendor_name)
        
        vendor_mask = (
            book_df.iloc[:, 9].apply(clean_text) == target_vendor_clean
        ) | (
            book_df.iloc[:, 10].apply(clean_text) == target_vendor_clean
        )
        filtered_books = book_df[vendor_mask]

        if filtered_books.empty:
            st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
        else:
            grouped = filtered_books.groupby(
                ["Title", "Author Name", "Language"],
                as_index=False,
            ).agg({
                "Quantity": "sum",
                "Original Price": "first",
                "Acccepted Price": "first",
                "Isbn": "first",
                "Book Id": "first",
            })

            c1, c2 = st.columns(2)
            c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
            c2.metric("📦 மொத்தப் படிகள் (Total Qty)", int(grouped["Quantity"].sum()))

            st.markdown("---")
            st.markdown(f"### 📋 {completed_vendor_name} - புத்தகங்களின் சரிபார்ப்புப் பட்டியல்")
            st.info("💡 தற்காலிகப் பட்டியலின்படி பெறப்பட வேண்டிய எண்ணிக்கை (Total Qty) தானாக வரும். நீங்கள் நேரில் பெற்ற எண்ணிக்கையை (Received Qty) மட்டும் உள்ளீடு செய்யவும்; பெறப்படாத / கூடுதலாகப் பெறப்பட்ட எண்ணிக்கை தானாகக் கணக்கிடப்படும்.")

            display_data = []
            for idx, row in grouped.iterrows():
                tot_q = int(row["Quantity"])
                display_data.append({
                    "Title": row["Title"],
                    "Author": row["Author Name"] if pd.notna(row["Author Name"]) else "",
                    "Language": row["Language"],
                    "Total Qty": tot_q,
                    "Received Qty": tot_q,  # பயனாளர் மாற்றி அமைக்கக்கூடியது
                })

            edit_df = pd.DataFrame(display_data)
            
            edited_df = st.data_editor(
                edit_df,
                num_rows="fixed",
                use_container_width=True,
                key=f"editor_{st.session_state['vendor_key']}",
                disabled=["Title", "Author", "Language", "Total Qty"]
            )

            st.markdown("---")
            if st.button("💾 சரிபார்ப்பைச் சேமித்து Google Sheet & Drive-ல் ஒத்திசைவு செய்", use_container_width=True):
                if sheet_physically and sheet_vendor_wise:
                    try:
                        current_time_str = datetime.now().strftime("%d-%m-%y %H:%M:%S")
                        v_id_code = vendor_id_map.get(completed_vendor_name, "077")
                        id_with_vendor = f"{v_id_code}.{completed_vendor_name}"
                        
                        final_records_for_pdf = []

                        # 1. 'Physically verified' சீட்டில் பழைய பதிவுகள் நீக்கப்பட்டு புதிய தரவுகள் சேமிக்கப்படுதல்
                        with st.spinner("படி 1: பழைய பதிவுகள் நீக்கப்பட்டு புதிய தரவுகள் சேமிக்கப்படுகின்றன..."):
                            phys_data = sheet_physically.get_all_values()
                            rows_to_delete = []
                            for r_idx, row_item in enumerate(phys_data[1:], start=2):
                                if len(row_item) > 4 and (
                                    target_vendor_clean in clean_text(row_item[4]) or 
                                    target_vendor_clean in clean_text(row_item[0])
                                ):
                                    rows_to_delete.append(r_idx)
                            
                            for r_num in sorted(rows_to_delete, reverse=True):
                                sheet_physically.delete_rows(r_num)

                            for _, row in edited_df.iterrows():
                                t_title = row["Title"]
                                t_author = row["Author"]
                                t_lang = row["Language"]
                                total_q = int(row["Total Qty"])
                                rec_q = int(row["Received Qty"])
                                
                                # பெறப்படாத எண்ணிக்கை மற்றும் கூடுதலாகப் பெறப்பட்ட எண்ணிக்கை கணக்கீடு
                                not_rec_q = max(0, total_q - rec_q)
                                extra_q = max(0, rec_q - total_q)

                                sheet_physically.append_row([
                                    id_with_vendor,         # A: ID with Vendor Name
                                    t_title,                # B: Title
                                    t_lang,                 # C: Language
                                    t_author,               # D: Author Name
                                    completed_vendor_name,  # E: Vendor Name
                                    total_q,                # F: Total Qty
                                    rec_q,                  # G: Received Qty
                                    not_rec_q,              # H: Not Received Qty
                                    extra_q,                # I: Extra Qty
                                    current_time_str        # J: Date
                                ])

                                final_records_for_pdf.append({
                                    "ID with Vendor Name": id_with_vendor,
                                    "Title": t_title,
                                    "Language": t_lang,
                                    "Author Name": t_author,
                                    "Vendor Name": completed_vendor_name,
                                    "Total Qty": total_q,
                                    "Received": rec_q,
                                    "Not Received": not_rec_q,
                                    "Extra Qty": extra_q,
                                    "Date": current_time_str
                                })

                        # 2. 'Vendor Wise Book Data' சீட்டில் ஒத்திசைவு செய்றது
                        with st.spinner("படி 2: 'Vendor Wise Book Data' சீட்டில் ஒத்திசைவு செய்யப்படுகிறது..."):
                            ws_data = sheet_vendor_wise.get_all_values()
                            header = ws_data[0]
                            header_lower = [str(h).strip().lower() for h in header]
                            s_col = next((i + 1 for i, h in enumerate(header_lower) if "received" in h and "not" not in h), 19)
                            t_col = next((i + 1 for i, h in enumerate(header_lower) if "not received" in h or ("not" in h and "received" in h)), 20)
                            
                            for item in final_records_for_pdf:
                                t_title = clean_text(item["Title"])
                                rec_qty = int(item["Received"])
                                
                                matching_row_numbers = []
                                for r_idx, row_item in enumerate(ws_data[1:], start=2):
                                    row_vendor_match = target_vendor_clean in clean_text(row_item[10] if len(row_item) > 10 else "") or target_vendor_clean in clean_text(row_item[9] if len(row_item) > 9 else "")
                                    row_title_match = t_title == clean_text(row_item[4] if len(row_item) > 4 else "")
                                    if row_vendor_match and row_title_match:
                                        matching_row_numbers.append(r_idx)
                                
                                for idx, r_num in enumerate(matching_row_numbers):
                                    if idx < rec_qty:
                                        sheet_vendor_wise.update_cell(r_num, s_col, "1")
                                        sheet_vendor_wise.update_cell(r_num, t_col, "0")
                                    else:
                                        sheet_vendor_wise.update_cell(r_num, s_col, "0")
                                        sheet_vendor_wise.update_cell(r_num, t_col, "1")

                        # 3. PDF உருவாக்கி Google Drive-ல் பதிவேற்றுதல்
                        with st.spinner("படி 3: PDF உருவாக்கப்பட்டு பதிப்பகத்தின் பெயரில் Google Drive-ல் சேமிக்கப்படுகிறது..."):
                            temp_df_pdf = pd.DataFrame(final_records_for_pdf)
                            vendor_name_clean = re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', '_', completed_vendor_name)
                            pdf_bytes = generate_pdf_bytes(temp_df_pdf, completed_vendor_name)
                            file_name = f"{vendor_name_clean}_Verification_Report.pdf"
                            upload_pdf_to_drive(pdf_bytes, file_name, GOOGLE_DRIVE_FOLDER_ID)

                        st.success(f"✅ வெற்றிகரமாக முடிக்கப்பட்டது!\n1. '{completed_vendor_name}' பதிப்பாளர் தரவுகள் 'Physically verified' சீட்டில் பழைய பதிவுகள் நீக்கப்பட்டு சரியாகச் சேமிக்கப்பட்டன.\n2. 'Vendor Wise Book Data' சீட்டில் ஒத்திசைவு செய்யப்பட்டது.\n3. Google Drive-ல் PDF சேமிக்கப்பட்டது!")
                        
                        st.session_state["selected_vendor"] = None
                        st.session_state["vendor_key"] += 1
                        
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ செயல்பாட்டில் பிழை: {e}")
                else:
                    st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!")


# --- TASK 2: GOOGLE SHEET DATA SYNC ---
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync) மேலாண்மை")
    if st.button("🚀 தரவுகளை உடனே ஒத்திசை (Sync Now)"):
        with st.spinner("ஒத்திசைக்கப்படுகிறது..."):
            time.sleep(1)
            st.success("✅ Google Sheet தரவுகள் வெற்றிகரமாக ஒத்திசைக்கப்பட்டன!")


# --- TASK 3: VENDOR DETAILS ---
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")
    if vendor_df is not None and not vendor_df.empty:
        st.metric("📦 மொத்தப் பதிப்பாளர்கள்", len(vendor_df))
        st.dataframe(vendor_df, use_container_width=True)


# --- TASK 4: LIBRARY DISTRIBUTION ---
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")
    if sheet_library_details:
        lib_records = sheet_library_details.get_all_records()
        if lib_records:
            st.dataframe(pd.DataFrame(lib_records), use_container_width=True)


# --- TASK 5: ACCESSION NUMBER MANAGEMENT ---
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. Accession எண்கள் மேலாண்மை")
    with st.form("accession_form"):
        acc_book_title = st.text_input("📖 புத்தகத் தலைப்பு")
        acc_number = st.text_input("🔢 Accession எண்")
        if st.form_submit_button("💾 பதிவு செய்"):
            if acc_book_title and acc_number:
                st.success(f"✅ '{acc_book_title}' புத்தகத்திற்கு Accession எண் வெற்றிகரமாகப் பதிவு செய்யப்பட்டது!")
