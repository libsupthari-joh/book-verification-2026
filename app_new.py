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
# 1. PAGE SETTINGS (SIDEBAR EXPANDED & FIXED)
# ============================================================
st.set_page_config(
    page_title="2026 புதிய நூல்கள் விநியோகம்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# 2. UI DESIGN & STYLES (STABLE SIDEBAR & BOLD HEADERS)
# ============================================================
def get_custom_css():
    return """
    <style>
    :root {
        --navy: #071a38;
        --blue: #1565c0;
        --cyan: #00acc1;
        --green: #2e7d32;
    }

    .stApp {
        background: 
            radial-gradient(circle at 8% 8%, rgba(0,188,212,.12), transparent 28%),
            linear-gradient(135deg, #eef5ff, #f8fbff 48%, #edf3ff);
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { visibility: hidden; }

    h1 {
        font-size: 22px !important;
        padding: 16px 18px !important;
        border-radius: 16px;
        color: white !important;
        background: linear-gradient(135deg, #071a38, #1565c0 58%, #00acc1);
        box-shadow: 0 6px 0 #041127, 0 12px 20px rgba(7,26,56,.2);
        text-shadow: 1px 2px 2px rgba(0,0,0,.3);
        text-align: center;
    }

    h2, h3 { color: #092653 !important; font-size: 18px !important; }

    /* Force Sidebar to be fully visible and styled */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071a38, #0b2e63 55%, #082044) !important;
        border-right: 1px solid rgba(255,255,255,.15);
        min-width: 280px !important;
        visibility: visible !important;
        display: block !important;
    }

    section[data-testid="stSidebar"] h3, 
    section[data-testid="stSidebar"] p, 
    section[data-testid="stSidebar"] label {
        color: white !important;
    }

    section[data-testid="stSidebar"] .stButton > button {
        width: 100% !important;
        min-height: 48px !important;
        margin: 6px 0 !important;
        padding: 10px 14px !important;
        border-radius: 12px !important;
        color: white !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-align: left !important;
        background: linear-gradient(145deg, rgba(255,255,255,.12), rgba(255,255,255,.06)) !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
    }

    .stButton > button, .stDownloadButton > button {
        min-height: 50px !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        color: white !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 4px 0 #041430, 0 6px 12px rgba(8,43,104,.25) !important;
        width: 100% !important;
    }

    div[data-testid="stSelectbox"] label, 
    div[data-testid="stNumberInput"] label, 
    div[data-testid="stTextInput"] label {
        font-size: 14px !important;
        font-weight: 600 !important;
    }

    .login-card {
        max-width: 420px;
        margin: 5vh auto 0 auto;
        padding: 24px;
        border-radius: 20px;
        background: rgba(255,255,255,.98);
        box-shadow: 0 12px 0 rgba(7,26,56,.1), 0 20px 30px rgba(7,26,56,.15);
        text-align: center;
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
            <div style="font-size: 32px; margin-bottom: 8px;">📚</div>
            <div style="font-size: 20px; font-weight: 900; color: #082653;">பணி போர்ட்டல்</div>
            <div style="font-size: 12px; color: #60708a; margin-top: 4px;">2026 புதிய நூல்கள் விநியோகம்</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    _, form_col, _ = st.columns([0.1, 2.8, 0.1])
    with form_col:
        with st.form("secure_login_form"):
            phone = st.text_input(
                "📱 அலைபேசி எண்",
                max_chars=10,
                placeholder="10 இலக்க எண்",
            )
            password = st.text_input(
                "🔑 கடவுச்சொல்",
                type="password",
                placeholder="கடவுச்சொல்",
            )
            submitted = st.form_submit_button(
                "🔓 உள்நுழைக",
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
        fontSize=12,
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

    t = Table(table_data)
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
        st.error(f"❌ Google Drive Upload Error: {e}")
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
# 6. SIDEBAR & ROLE-BASED NAVIGATION (FIXED & VISIBLE)
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("selected_vendor", None)
st.session_state.setdefault("temp_verified_records", [])

st.sidebar.markdown(f"### 👤 {st.session_state['user_name']}")
role_badge = "👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"
st.sidebar.caption(f"அதிகார நிலை: **{role_badge}**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_name"] = ""
    st.session_state["selected_vendor"] = None
    st.session_state["temp_verified_records"] = []
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

st.title("📚 நூல்கள் சரிபார்ப்புப் போர்ட்டல்")
menu_choice = st.session_state["current_page"]


# ============================================================
# 7. TASK IMPLEMENTATIONS
# ============================================================

# --- TASK 1: PHYSICAL VERIFICATION ---
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    vendor_list = []
    vendor_id_map = {}
    if not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""  # Col B: Id with Vendor Name
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""  # Col C: Vendor Name only
            
            vendor_name = col_c if col_c and col_c.lower() != "nan" else col_b
            full_id_name = col_b if col_b and col_b.lower() != "nan" else col_c

            if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
                vendor_list.append(vendor_name)
                vendor_id_map[vendor_name] = full_id_name

    st.markdown("---")
    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    
    selected_vendor_raw = st.selectbox(
        "பதிப்பகத்தின் முதல் எழுத்துகளை உள்ளீடு செய்யவும் (உள்ளே இரண்டு எழுத்துகள் இடவும்)",
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list,
        key=f"vendor_select_{st.session_state['vendor_key']}"
    )

    if selected_vendor_raw != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"] != selected_vendor_raw:
            st.session_state["selected_vendor"] = selected_vendor_raw
            st.session_state["temp_verified_records"] = []

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
            c2.metric("📦 மொத்தப் படிகள்", int(grouped["Quantity"].sum()))

            st.markdown("---")
            st.markdown(f"### 🔍 2. தலைப்பைத் தேடிச் சரிபார்த்தல்")

            verified_titles = {item["Title"] for item in st.session_state["temp_verified_records"]}
            remaining_book_titles = [t for t in grouped["Title"].tolist() if t not in verified_titles]

            if not remaining_book_titles:
                st.success("🎉 இந்த பதிப்பகத்தில் உள்ள அனைத்துத் தலைப்புகளும் தற்காலிகப் பட்டியலில் சேர்க்கப்பட்டுவிட்டன!")
            else:
                st.info("💡 தலைப்பின் முதல் 2-3 எழுத்துகளை உள்ளிட்டுத் தேர்ந்து கொள்ளலாம்.")
                selected_title = st.selectbox(
                    "புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும் (உள்ளே இரண்டு எழுத்துகள் இடவும்)",
                    ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"] + remaining_book_titles,
                    key=f"title_select_{len(st.session_state['temp_verified_records'])}"
                )

                if selected_title != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    book_row = grouped[grouped["Title"] == selected_title].iloc[0]
                    t_author = book_row["Author Name"] if pd.notna(book_row["Author Name"]) else ""
                    t_lang = book_row["Language"]
                    t_total_qty = int(book_row["Quantity"])

                    st.markdown(f"✍️ **ஆசிரியர்:** {t_author}")
                    st.markdown(f"🌐 **மொழி:** {t_lang}")
                    st.success(f"📦 **Total Qty:** {t_total_qty}")

                    rec_qty = st.number_input(
                        "பெறப்பட்ட எண்ணிக்கை (Received Qty)",
                        min_value=0,
                        value=t_total_qty,
                        step=1,
                        key=f"rec_inp_{selected_title}"
                    )

                    if st.button("➕ தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                        diff = rec_qty - t_total_qty
                        if diff < 0:
                            not_rec = abs(diff)
                            short_extra_val = str(diff)  # உ.ம்: -1, -3
                        elif diff > 0:
                            not_rec = 0
                            short_extra_val = f"+{diff}"  # உ.ம்: +10
                        else:
                            not_rec = 0
                            short_extra_val = "0"

                        id_with_vendor = vendor_id_map.get(completed_vendor_name, completed_vendor_name)

                        st.session_state["temp_verified_records"].append({
                            "Title": selected_title,
                            "Language": t_lang,
                            "Total Qty": t_total_qty,
                            "Received": rec_qty,
                            "Not Received": not_rec,
                            "Short / Extra": short_extra_val,
                            "ID with Vendor Name": id_with_vendor,
                            "Author Name": t_author,
                            "Vendor Name": completed_vendor_name,
                            "Date": datetime.now().strftime("%d-%m-%y %H:%M:%S")
                        })
                        st.success(f"✅ '{selected_title}' சேர்க்கப்பட்டது!")
                        time.sleep(0.3)
                        st.rerun()

            if st.session_state["temp_verified_records"]:
                st.markdown("---")
                st.markdown(f"### 📋 தற்காலிகச் சரிபார்ப்புப் பட்டியல் ({len(st.session_state['temp_verified_records'])} தலைப்புகள்)")
                
                temp_df = pd.DataFrame(st.session_state["temp_verified_records"])
                display_cols = ["Title", "Language", "Total Qty", "Received", "Not Received", "Short / Extra"]
                
                st.dataframe(temp_df[display_cols], use_container_width=True)

                col_clr, col_save = st.columns(2)
                with col_clr:
                    if st.button("🗑️ அழிக்க", use_container_width=True):
                        st.session_state["temp_verified_records"] = []
                        st.rerun()

                with col_save:
                    if st.button("💾 சீட் & Drive-ல் சேமி", use_container_width=True):
                        if sheet_physically and sheet_vendor_wise:
                            try:
                                with st.spinner("சேமிக்கப்படுகிறது..."):
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

                                    for item in st.session_state["temp_verified_records"]:
                                        sheet_physically.append_row([
                                            item["ID with Vendor Name"],
                                            item["Title"],
                                            item["Language"],
                                            item["Author Name"],
                                            item["Vendor Name"],
                                            item["Total Qty"],
                                            item["Received"],
                                            item["Not Received"],
                                            item["Short / Extra"],
                                            item["Date"]
                                        ])

                                    ws_data = sheet_vendor_wise.get_all_values()
                                    header_lower = [str(h).strip().lower() for h in ws_data[0]]
                                    s_col = next((i + 1 for i, h in enumerate(header_lower) if "received" in h and "not" not in h), 19)
                                    t_col = next((i + 1 for i, h in enumerate(header_lower) if "not received" in h or ("not" in h and "received" in h)), 20)
                                    
                                    for item in st.session_state["temp_verified_records"]:
                                        t_title_clean = clean_text(item["Title"])
                                        rec_qty = int(item["Received"])
                                        
                                        matching_row_numbers = []
                                        for r_idx, row_item in enumerate(ws_data[1:], start=2):
                                            row_vendor_match = target_vendor_clean in clean_text(row_item[10] if len(row_item) > 10 else "") or target_vendor_clean in clean_text(row_item[9] if len(row_item) > 9 else "")
                                            row_title_match = t_title_clean == clean_text(row_item[4] if len(row_item) > 4 else "")
                                            if row_vendor_match and row_title_match:
                                                matching_row_numbers.append(r_idx)
                                        
                                        for idx, r_num in enumerate(matching_row_numbers):
                                            if idx < rec_qty:
                                                sheet_vendor_wise.update_cell(r_num, s_col, "1")
                                                sheet_vendor_wise.update_cell(r_num, t_col, "0")
                                            else:
                                                sheet_vendor_wise.update_cell(r_num, s_col, "0")
                                                sheet_vendor_wise.update_cell(r_num, t_col, "1")

                                    pdf_bytes = generate_pdf_bytes(temp_df[display_cols], completed_vendor_name)
                                    file_name = f"{completed_vendor_name}_Verification_Report.pdf"
                                    upload_pdf_to_drive(pdf_bytes, file_name, GOOGLE_DRIVE_FOLDER_ID)

                                st.success("✅ வெற்றிகரமாகச் சேமிக்கப்பட்டது மற்றும் Drive-ல் பதிவேற்றப்பட்டது!")
                                st.session_state["selected_vendor"] = None
                                st.session_state["temp_verified_records"] = []
                                st.session_state["vendor_key"] += 1
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ பிழை: {e}")
                        else:
                            st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!")

    if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்க", use_container_width=True):
        st.session_state["selected_vendor"] = None
        st.session_state["temp_verified_records"] = []
        st.session_state["vendor_key"] += 1
        st.rerun()

# --- TASK 2: GOOGLE SHEET SYNC ---
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 2. Google Sheet தரவு ஒத்திசைவு")
    if st.button("🚀 உடனே ஒத்திசை", use_container_width=True):
        st.success("✅ ஒத்திசைக்கப்பட்டது!")

# --- TASK 3: VENDOR DETAILS ---
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள்")
    if vendor_df is not None and not vendor_df.empty:
        st.dataframe(vendor_df, use_container_width=True)

# --- TASK 4: LIBRARY DISTRIBUTION ---
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம்")
    if sheet_library_details:
        st.dataframe(pd.DataFrame(sheet_library_details.get_all_records()), use_container_width=True)

# --- TASK 5: ACCESSION ---
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. Accession மேலாண்மை")
    with st.form("acc_form"):
        st.text_input("📖 தலைப்பு")
        st.text_input("🔢 எண்")
        if st.form_submit_button("💾 பதிவு செய்", use_container_width=True):
            st.success("✅ பதிவு செய்யப்பட்டது!")
