import hashlib
import hmac
import os
import re
import time
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

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
# 2. COMPLETE UI DESIGN
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
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.2rem .85rem;
    }

    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: white !important;
    }

    /* Sidebar menu buttons - improved styling */
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
        box-shadow: 0 6px 0 rgba(0,0,0,.25), 0 12px 18px rgba(0,0,0,.25) !important;
    }

    section[data-testid="stSidebar"] .stButton > button:active {
        transform: translateY(1px) !important;
        box-shadow: 0 2px 0 rgba(0,0,0,.25), 0 4px 8px rgba(0,0,0,.2) !important;
    }

    /* Active page highlight */
    section[data-testid="stSidebar"] .stButton > button:focus {
        background: linear-gradient(145deg, #1565c0, #0d47a1) !important;
        border-color: rgba(255,255,255,.4) !important;
    }

    /* Logout button - red */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:first-child .stButton > button {
        background: linear-gradient(145deg, #ef5350, #b71c1c) !important;
        text-align: center !important;
        font-weight: 800 !important;
    }

    /* Input fields */
    div[data-testid="stSelectbox"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label {
        color: white !important;
        font-weight: 600 !important;
    }

    div[data-baseweb="select"] > div,
    input, textarea {
        border-radius: 12px !important;
        border: 1px solid #b7c9e5 !important;
        background: rgba(255,255,255,.95) !important;
    }

    /* Main buttons */
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

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-2px);
        filter: brightness(1.12);
        box-shadow: 0 6px 0 #061b42, 0 12px 20px rgba(8,43,104,.32) !important;
    }

    /* Metric cards */
    div[data-testid="stMetric"] {
        padding: 16px !important;
        border-radius: 16px;
        background: rgba(255,255,255,.9);
        border: 1px solid rgba(255,255,255,.8);
        box-shadow: 0 6px 16px rgba(30,70,120,.12);
    }

    div[data-testid="stMetricValue"] {
        color: #0b3d91 !important;
        font-weight: 900 !important;
    }

    /* Dataframe */
    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 6px 16px rgba(30,70,120,.12);
    }

    /* Alerts */
    div[data-testid="stAlert"] {
        border-radius: 14px !important;
        box-shadow: 0 4px 12px rgba(30,70,120,.1);
    }

    /* Login card */
    .login-card {
        max-width: 500px;
        margin: 8vh auto 0 auto;
        padding: 32px 32px 26px;
        border-radius: 24px;
        background: rgba(255,255,255,.95);
        box-shadow: 0 16px 0 rgba(7,26,56,.14), 0 24px 40px rgba(7,26,56,.18);
        text-align: center;
    }

    .login-logo {
        width: 72px;
        height: 72px;
        margin: 0 auto 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 36px;
        background: linear-gradient(145deg, #00acc1, #1565c0);
        box-shadow: inset 0 2px 6px rgba(255,255,255,.4), 0 6px 0 #07366c, 0 12px 20px rgba(7,54,108,.22);
    }

    .login-title {
        margin: 0;
        color: #082653;
        font-size: 24px;
        font-weight: 900;
    }

    .login-subtitle {
        margin: 6px 0 22px;
        color: #60708a;
        font-size: 13px;
    }

    /* Sidebar toggle button - FIXED */
    [data-testid="stSidebarCollapsedControl"] {
        background: linear-gradient(145deg, #1565c0, #0d47a1) !important;
        border-radius: 8px !important;
        padding: 6px !important;
        margin: 8px !important;
        box-shadow: 0 3px 8px rgba(0,0,0,.25) !important;
        opacity: 1 !important;
        visibility: visible !important;
    }
    [data-testid="stSidebarCollapsedControl"] svg {
        fill: white !important;
        width: 20px !important;
        height: 20px !important;
    }

    @media (max-width: 768px) {
        h1 { font-size: 1.3rem !important; padding: 16px !important; }
        section[data-testid="stSidebar"] { min-width: 260px !important; }
        section[data-testid="stSidebar"] .stButton > button { min-height: 48px !important; font-size: 13px !important; }
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
        "password_hash": hash_password("Hari@1979"),
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
        input_pass_hash = hash_password(password)
        if hmac.compare_digest(input_pass_hash, user_data["password_hash"]):
            return user_data
    return None


def show_login_page():
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">📚</div>
            <div class="login-title">பணி போர்ட்டல்</div>
            <div class="login-subtitle">2026 புதிய நூல்கள் விநியோகம்</div>
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
                st.session_state["login_attempts"] = 0
                st.rerun()
            else:
                st.session_state["login_attempts"] += 1
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_role", None)
st.session_state.setdefault("user_name", "")
st.session_state.setdefault("login_attempts", 0)

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# 4. GOOGLE SHEETS AND EXCEL CONFIGURATION
# ============================================================
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"


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
        sheet for sheet in excel_data.sheet_names
        if "Vendor Wise Book Data" in sheet
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
# 5. SIDEBAR & ROLE-BASED NAVIGATION
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("verified_list", [])
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("book_key", 0)
st.session_state.setdefault("selected_vendor", None)

# User info in sidebar
st.sidebar.markdown(f"### 👤 {st.session_state['user_name']}")
role_badge = "👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"
st.sidebar.caption(f"அதிகார நிலை: **{role_badge}**")
st.sidebar.markdown("---")

# Logout button
if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_name"] = ""
    st.session_state["verified_list"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

# Menu items based on role
if st.session_state["user_role"] == "Admin":
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
        "⚙️ 5. Accession எண்கள் மேலாண்மை",
    ]
else:
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
    ]

for item in menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()

st.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")
menu_choice = st.session_state["current_page"]


# ============================================================
# 6. TASK 1 - PHYSICAL VERIFICATION (ADMIN & USER)
# ============================================================
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல்")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    saved_entries = set()
    if sheet_physically:
        try:
            records = sheet_physically.get_all_values()
            for row in records[1:]:
                if len(row) >= 2:
                    saved_entries.add((clean_text(row[0]), clean_text(row[1])))
        except Exception:
            pass

    vendor_list = []
    if not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            vendor_name = col_b or col_c
            if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
                vendor_list.append(vendor_name)

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
            st.session_state["verified_list"] = []
            st.session_state["vendor_key"] += 1
            st.rerun()

    if selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"] != selected_vendor_raw:
            st.session_state["selected_vendor"] = selected_vendor_raw
            st.session_state["verified_list"] = []

    if st.session_state["selected_vendor"]:
        target_vendor_clean = clean_text(st.session_state["selected_vendor"])
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

            added_titles = [
                clean_text(item["Title"])
                for item in st.session_state["verified_list"]
            ]
            title_options = ["-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]

            for _, row in grouped.iterrows():
                title = str(row["Title"]).strip()
                title_clean = clean_text(title)
                if (
                    title_clean not in added_titles
                    and (target_vendor_clean, title_clean) not in saved_entries
                ):
                    author = str(row["Author Name"]).strip() if pd.notna(row["Author Name"]) else ""
                    title_options.append(f"{title} - {author}" if author else title)

            if len(title_options) == 1 and not st.session_state["verified_list"]:
                st.success("🎉 இந்த பதிப்பகத்தின் அனைத்துப் புத்தகங்களும் சரிபார்க்கப்பட்டுவிட்டன!")
            elif len(title_options) > 1:
                st.markdown("### 📖 2. புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்")
                col_book, col_book_change = st.columns([5, 1])

                with col_book:
                    selected_title = st.selectbox(
                        "புத்தகத்தைத் தேர்ந்தெடுக்கவும்",
                        title_options,
                        key=f"book_select_{st.session_state['book_key']}",
                        label_visibility="collapsed",
                    )

                with col_book_change:
                    if st.button("🔄 மாற்றுக", key="btn_b_change", use_container_width=True):
                        st.session_state["book_key"] += 1
                        st.rerun()

                if selected_title != "-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    matched_row = None
                    for _, row in grouped.iterrows():
                        title = str(row["Title"]).strip()
                        author = str(row["Author Name"]).strip() if pd.notna(row["Author Name"]) else ""
                        display = f"{title} - {author}" if author else title
                        if display == selected_title:
                            matched_row = row
                            break

                    if matched_row is not None:
                        total_quantity = int(matched_row["Quantity"])
                        with st.form("verify_form"):
                            st.write(f"📖 **புத்தகத் தலைப்பு:** {matched_row['Title']}")
                            st.write(f"✍️ **ஆசிரியர் பெயர்:** {matched_row['Author Name']}")
                            received_quantity = st.number_input(
                                "📦 பெறப்பட்ட படிகள்",
                                min_value=0,
                                max_value=1000,
                                value=total_quantity,
                            )
                            submitted = st.form_submit_button("➕ பட்டியலில் சேர்")

                        if submitted:
                            st.session_state["verified_list"].append({
                                "Vendor": st.session_state["selected_vendor"],
                                "Title": matched_row["Title"],
                                "Language": matched_row["Language"],
                                "Author": matched_row["Author Name"],
                                "TotalQty": total_quantity,
                                "ReceivedQty": received_quantity,
                                "NotReceivedQty": max(0, total_quantity - received_quantity),
                            })
                            st.session_state["book_key"] += 1
                            st.rerun()

    if st.session_state["verified_list"]:
        st.markdown("---")
        st.markdown("### 📋 சரிபார்க்கப்பட்ட தற்காலிகப் பட்டியல்")
        verified_df = pd.DataFrame(st.session_state["verified_list"])
        verified_df.index = range(1, len(verified_df) + 1)
        st.dataframe(
            verified_df[[
                "Vendor", "Title", "Language", "Author",
                "TotalQty", "ReceivedQty", "NotReceivedQty",
            ]],
            use_container_width=True,
        )

        col_save, col_clear = st.columns([3, 1])
        with col_save:
            if st.button("💾 Google Sheet-ல் சேமி", key="btn_save", use_container_width=True):
                try:
                    if not sheet_physically:
                        st.error("❌ Physically Verified sheet கிடைக்கவில்லை!")
                    else:
                        current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                        rows = [
                            [
                                item["Vendor"], item["Title"], item["Language"],
                                item["Author"], item["Vendor"], item["TotalQty"],
                                item["ReceivedQty"], item["NotReceivedQty"], current_date,
                            ]
                            for item in st.session_state["verified_list"]
                        ]
                        sheet_physically.append_rows(rows)
                        st.success("🎉 தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                        st.session_state["verified_list"] = []
                        st.rerun()
                except Exception as error:
                    st.error(f"❌ சேமிப்பு பிழை: {error}")

        with col_clear:
            if st.button("🗑️ பட்டியலை அழி", key="btn_clear", use_container_width=True):
                st.session_state["verified_list"] = []
                st.rerun()


# ============================================================
# 7. TASK 2 - SYNC (ADMIN ONLY)
# ============================================================
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    if st.session_state["user_role"] != "Admin":
        st.warning("🔒 இந்தப் பக்கத்தை அணுக **Admin** அனுமதி தேவை!")
        st.stop()

    st.subheader("🔄 2. பதிப்பகம் வாரியாக பெறப்பட்ட நூல்கள் ஒத்திசைவு")

    if not sheet_physically or not sheet_vendor_wise:
        st.error("❌ Google Sheet இணைப்புகள் சரியாக இல்லை!")
    else:
        try:
            physical_records = sheet_physically.get_all_values()
            vendor_data = sheet_vendor_wise.get_all_values()
            synced_vendors = set()

            for row in vendor_data[1:]:
                if len(row) > 18 and str(row[18]).strip() == "1":
                    synced_vendors.add(clean_text(row[10]))

            physical_vendors = []
            for row in physical_records[1:]:
                if len(row) >= 1:
                    vendor = row[0]
                    if (
                        vendor
                        and clean_text(vendor) not in synced_vendors
                        and vendor not in physical_vendors
                    ):
                        physical_vendors.append(vendor)

            if not physical_vendors:
                st.success("🟢 அனைத்துப் பதிப்பகங்களும் ஏற்கனவே ஒத்திசைக்கப்பட்டுள்ளன!")
            else:
                selected_vendor = st.selectbox(
                    "ஒத்திசைவு செய்ய வேண்டிய பதிப்பகம்",
                    ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + physical_vendors,
                )

                if selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    selected_clean = clean_text(selected_vendor)
                    vendor_books = [
                        row for row in physical_records[1:]
                        if clean_text(row[0]) == selected_clean
                    ]
                    display_df = pd.DataFrame(
                        vendor_books,
                        columns=[
                            "Vendor", "Title", "Lang", "Auth", "V2",
                            "Total", "Rec", "NotRec", "Date",
                        ],
                    )
                    st.dataframe(display_df[["Title", "Total", "Rec"]], use_container_width=True)

                    if st.button(
                        f"🚀 {selected_vendor} தரவை ஒத்திசைவு செய்",
                        key="btn_sync_single",
                        use_container_width=True,
                    ):
                        updates = []
                        for record in vendor_books:
                            target_title = clean_text(record[1])
                            received_quantity = int(record[6]) if str(record[6]).isdigit() else 0
                            matched_count = 0

                            for row_index, sheet_row in enumerate(vendor_data[1:], start=2):
                                if len(sheet_row) > 10:
                                    sheet_title = clean_text(sheet_row[4])
                                    sheet_publisher = clean_text(sheet_row[9])
                                    sheet_vendor = clean_text(sheet_row[10])
                                    if (
                                        selected_clean in {sheet_publisher, sheet_vendor}
                                        and target_title == sheet_title
                                        and matched_count < received_quantity
                                    ):
                                        updates.append({
                                            "range": f"S{row_index}:T{row_index}",
                                            "values": [[1, 0]],
                                        })
                                        matched_count += 1

                        if updates:
                            sheet_vendor_wise.batch_update(updates)
                            st.success("✅ தேர்ந்தெடுக்கப்பட்ட பதிப்பகம் ஒத்திசைக்கப்பட்டது!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning("⚠️ பொருந்தும் தரவுகள் கிடைக்கவில்லை!")
        except Exception as error:
            st.error(f"❌ ஒத்திசைவு பிழை: {error}")


# ============================================================
# 8. TASK 3 - VENDOR DETAILS (ADMIN & USER)
# ============================================================
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")

    if not sheet_vendor_wise:
        st.error("❌ Vendor Wise Book Data sheet கிடைக்கவில்லை!")
    else:
        with st.spinner("⏳ நேரலைத் தரவை ஏற்றுகிறது..."):
            data = sheet_vendor_wise.get_all_values()

        if len(data) > 1:
            live_df = pd.DataFrame(data[1:], columns=data[0])
            vendor_column = live_df.columns[10] if len(live_df.columns) > 10 else live_df.columns[9]
            vendors = sorted(set(live_df[vendor_column].astype(str).str.strip()))
            selected_vendor = st.selectbox(
                "🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",
                ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors,
            )

            if selected_vendor != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                filtered_df = live_df[
                    live_df[vendor_column].astype(str).str.strip() == selected_vendor
                ]
                st.markdown(f"### 📋 {selected_vendor} - மொத்தப் புத்தகங்கள் ({len(filtered_df)})")
                st.dataframe(filtered_df, use_container_width=True)


# ============================================================
# 9. TASK 4 - LIBRARY DELIVERY REPORT (ADMIN & USER)
# ============================================================
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. 103 நூலகங்கள் வாரியான விநியோக அறிக்கை")

    if not sheet_vendor_wise or not sheet_library_details:
        st.error("❌ தேவையான Google Sheet தரவுகள் கிடைக்கவில்லை!")
    else:
        with st.spinner("⏳ தரவுகளை ஏற்றுகிறது..."):
            vendor_data = sheet_vendor_wise.get_all_values()
            live_df = pd.DataFrame(vendor_data[1:], columns=vendor_data[0])
            library_records = sheet_library_details.get_all_values()

        library_map = {}
        library_names = []
        for row in library_records[1:]:
            if len(row) >= 3:
                code = str(row[1]).strip()
                name = str(row[2]).strip()
                if name and name.lower() != "nan":
                    library_map[code] = name
                    if name not in library_names:
                        library_names.append(name)

        selected_library = st.selectbox(
            "🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்",
            ["-- 🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + sorted(library_names),
        )

        if selected_library != "-- 🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            selected_code = next(
                (code for code, name in library_map.items() if name == selected_library),
                "",
            )
            name_clean = clean_text(selected_library)
            code_clean = clean_text(selected_code)
            column_o = live_df.columns[14] if len(live_df.columns) > 14 else None
            column_p = live_df.columns[15] if len(live_df.columns) > 15 else None

            def library_match(row):
                p_value = clean_text(row[column_p]) if column_p else ""
                o_value = clean_text(row[column_o]) if column_o else ""
                return (
                    name_clean in p_value
                    or p_value in name_clean
                    or (code_clean and (code_clean in o_value or o_value in code_clean))
                )

            filtered_df = live_df[live_df.apply(library_match, axis=1)]

            if filtered_df.empty:
                st.warning("⚠️ இந்த நூலகத்திற்கு ஒதுக்கீடு இல்லை!")
            else:
                received_column = live_df.columns[18] if len(live_df.columns) > 18 else None
                received_df = (
                    filtered_df[filtered_df[received_column].astype(str).str.strip() == "1"]
                    if received_column
                    else filtered_df
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("📖 மொத்த ஒதுக்கீடு", len(filtered_df))
                c2.metric("✅ பெறப்பட்ட புத்தகங்கள்", len(received_df))
                c3.metric("🏛️ நூலகக் குறியீடு", selected_code or "N/A")

                st.markdown(f"### 📋 {selected_library} - விநியோக அறிக்கை")
                st.dataframe(filtered_df, use_container_width=True)

                csv_data = filtered_df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    f"📄 {selected_library} - CSV பதிவிறக்கம்",
                    csv_data,
                    f"{selected_library}_Book_Delivery_Report.csv",
                    "text/csv",
                    use_container_width=True,
                )


# ============================================================
# 10. TASK 5 - ACCESSION MANAGEMENT (ADMIN ONLY)
# ============================================================
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    if st.session_state["user_role"] != "Admin":
        st.warning("🔒 இந்தப் பக்கத்தை அணுக **Admin** அனுமதி தேவை!")
        st.stop()

    st.subheader("⚙️ 5. Accession எண்கள் மற்றும் Batch ஒதுக்கீடு மேலாண்மை")
    st.info("💡 சரிபார்ப்பு மற்றும் ஒத்திசைவு பணிகள் முடிந்த பிறகு இந்தப் பணியைச் செய்யவும்.")

    if not sheet_vendor_wise:
        st.error("❌ Google Sheet இணைப்புகள் சரியாக இல்லை!")
    else:
        with st.spinner("⏳ Accession தரவுகளை ஏற்றுகிறது..."):
            try:
                vendor_data = sheet_vendor_wise.get_all_values()
                if len(vendor_data) > 1:
                    live_df = pd.DataFrame(vendor_data[1:], columns=vendor_data[0])

                    col_acc1, col_acc2 = st.columns(2)
                    with col_acc1:
                        prefix = st.text_input("Accession Prefix (எ.கா: LIB-2026-)", value="LIB-2026-")
                        start_num = st.number_input("தொடக்க Accession எண்", min_value=1, value=1001, step=1)
                    with col_acc2:
                        batch_name = st.text_input("தொகுதி / Batch பெயர்", value="Batch-01")

                    st.markdown("---")
                    st.markdown("### 📝 Accession எண்கள் ஒதுக்கீடு முன்னோட்டம்")

                    if st.button("🔢 Accession எண்களை உருவாக்கு / Generate", use_container_width=True):
                        live_df["Accession No"] = [
                            f"{prefix}{start_num + i}" for i in range(len(live_df))
                        ]
                        live_df["Batch Name"] = batch_name
                        st.session_state["acc_preview_df"] = live_df
                        st.success("✅ Accession எண்கள் வெற்றிகரமாக உருவாக்கப்பட்டன!")

                    if "acc_preview_df" in st.session_state:
                        st.dataframe(st.session_state["acc_preview_df"], use_container_width=True)

                        acc_csv = st.session_state["acc_preview_df"].to_csv(index=False).encode("utf-8-sig")
                        st.download_button(
                            "📄 Accession அறிக்கையைப் பதிவிறக்குக (CSV)",
                            acc_csv,
                            "Accession_Numbers_Report.csv",
                            "text/csv",
                            use_container_width=True,
                        )
                else:
                    st.warning("⚠️ தரவுகள் எதுவும் கிடைக்கவில்லை!")
            except Exception as error:
                st.error(f"❌ Accession மேலாண்மை பிழை: {error}")
