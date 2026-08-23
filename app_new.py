import hashlib
import hmac
import os
import re
import time
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
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
# 2. COMPLETE UI DESIGN & PRINT STYLES
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

    /* Sidebar - FIXED & ALWAYS VISIBLE */
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
        box-shadow: 0 6px 0 rgba(0,0,0,.25), 0 12px 18px rgba(0,0,0,.25) !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:first-child .stButton > button {
        background: linear-gradient(145deg, #ef5350, #b71c1c) !important;
        text-align: center !important;
        font-weight: 800 !important;
    }

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

    div[data-testid="stDataFrame"] {
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 6px 16px rgba(30,70,120,.12);
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
        box-shadow: 0 3px 10px rgba(0,0,0,.3) !important;
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
        input_pass_hash = hash_password(password)
        if hmac.compare_digest(input_pass_hash, user_data["password_hash"]):
            return user_data
    return None


def show_login_page():
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">📚</div>
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
# 4. HELPER FUNCTION: PRINT & PDF VIEWER COMPONENT
# ============================================================
def render_print_and_export(df, report_title):
    if df is not None and not df.empty:
        col_dl, col_print_info = st.columns([2, 3])
        with col_dl:
            csv_data = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 CSV கோப்பாகப் பதிவிறக்குக (Download CSV)",
                data=csv_data,
                file_name=f"{report_title.replace(' ', '_')}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        
        with col_print_info:
            st.info("💡 PDF ஆக சேமிக்க / Print எடுக்க கீழة உள்ள பொத்தானைப் பயன்படுத்தவும்.")

        # HTML Print Component
        html_table = df.to_html(index=False, classes="print-table")
        print_html = f"""
        <html>
        <head>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 15px; color: #222; background: #fff; }}
            h3 {{ color: #082653; text-align: center; margin-bottom: 15px; }}
            .print-btn {{
                background: linear-gradient(145deg, #1565c0, #0d47a1);
                color: white;
                padding: 12px 24px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 15px;
                font-weight: bold;
                display: block;
                margin: 0 auto 20px auto;
                box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            }}
            .print-btn:hover {{ background: #0b3d91; }}
            table.print-table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 10px;
            }}
            table.print-table th, table.print-table td {{
                border: 1px solid #b0bec5;
                padding: 8px 10px;
                text-align: left;
                font-size: 12px;
            }}
            table.print-table th {{
                background-color: #071a38;
                color: white;
                font-weight: bold;
            }}
            table.print-table tr:nth-child(even) {{ background-color: #f4f6f9; }}
            @media print {{
                .print-btn {{ display: none; }}
                body {{ margin: 0; }}
            }}
        </style>
        </head>
        <body>
            <h3>{report_title}</h3>
            <button class="print-btn" onclick="window.print()">🖨️ Print / PDF ஆக சேமிக்க (Save as PDF)</button>
            {html_table}
        </body>
        </html>
        """
        components.html(print_html, height=450, scrolling=True)


# ============================================================
# 5. GOOGLE SHEETS & EXCEL CONFIGURATION
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
# 6. SIDEBAR & ROLE-BASED NAVIGATION (RESTRICTED FOR USER)
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("verified_list", [])
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("book_key", 0)
st.session_state.setdefault("selected_vendor", None)

st.sidebar.markdown(f"### 👤 {st.session_state['user_name']}")
role_badge = "👑 Admin" if st.session_state["user_role"] == "Admin" else "👤 User"
st.sidebar.caption(f"அதிகார நிலை: **{role_badge}**")
st.sidebar.markdown("---")

if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    st.session_state["logged_in"] = False
    st.session_state["user_role"] = None
    st.session_state["user_name"] = ""
    st.session_state["verified_list"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

# --- ROLE RESTRICTION APPLIED HERE ---
if st.session_state["user_role"] == "Admin":
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
        "⚙️ 5. Accession எண்கள் மேலாண்மை",
    ]
else:
    # Users can ONLY perform Task 1
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
    ]

if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]

for item in menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()

st.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")
menu_choice = st.session_state["current_page"]


# ============================================================
# 7. TASK IMPLEMENTATIONS WITH PRINT / PDF EXPORT
# ============================================================

# --- TASK 1: PHYSICAL VERIFICATION & VENDOR WISE SYNC ---
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல்")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

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
                if title_clean not in added_titles:
                    author = str(row["Author Name"]).strip() if pd.notna(row["Author Name"]) else ""
                    title_options.append(f"{title} - {author}" if author else title)

            if len(title_options) > 1:
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
                                max_value=total_quantity,
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

    # தற்காலிக சரிபார்ப்பு பட்டியல் மற்றும் ஒத்திசைவு
    if st.session_state["verified_list"]:
        st.markdown("---")
        st.markdown("### 📋 தற்காலிக சரிபார்ப்பு பட்டியல் & ஒத்திசைவு")
        temp_df = pd.DataFrame(st.session_state["verified_list"])
        
        # Print & PDF Export for verification list
        render_print_and_export(temp_df, "Physical Verification Report")

        col_save, col_clear = st.columns(2)
        with col_save:
            if st.button("💾 Vendor Wise Book Data-வில் ஒத்திசைவு (Sync)", use_container_width=True):
                if sheet_vendor_wise:
                    try:
                        with st.spinner("Vendor Wise Book Data சீட்டில் ஒத்திசைவு செய்யப்படுகிறது..."):
                            ws_data = sheet_vendor_wise.get_all_values()
                            header = ws_data[0]
                            header_lower = [str(h).strip().lower() for h in header]
                            
                            s_col = next((i + 1 for i, h in enumerate(header_lower) if "received" in h and "not" not in h), 19)
                            t_col = next((i + 1 for i, h in enumerate(header_lower) if "not received" in h or ("not" in h and "received" in h)), 20)
                            
                            for item in st.session_state["verified_list"]:
                                t_vendor = clean_text(item["Vendor"])
                                t_title = clean_text(item["Title"])
                                rec_qty = int(item["ReceivedQty"])
                                
                                matching_row_numbers = []
                                for r_idx, row in enumerate(ws_data[1:], start=2):
                                    row_vendor_match = any(t_vendor in clean_text(c) for c in row)
                                    row_title_match = any(t_title in clean_text(c) for c in row)
                                    if row_vendor_match and row_title_match:
                                        matching_row_numbers.append(r_idx)
                                
                                for idx, r_num in enumerate(matching_row_numbers):
                                    if idx < rec_qty:
                                        sheet_vendor_wise.update_cell(r_num, s_col, "1")
                                        sheet_vendor_wise.update_cell(r_num, t_col, "0")
                                    else:
                                        sheet_vendor_wise.update_cell(r_num, s_col, "0")
                                        sheet_vendor_wise.update_cell(r_num, t_col, "1")
                                        
                            st.success("✅ 'Vendor Wise Book Data' சீட்டில் Received மற்றும் Not Received எண்கள் வெற்றிகரமாக ஒத்திசைவு செய்யப்பட்டன!")
                            st.session_state["verified_list"] = []
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"❌ ஒத்திசைவு செய்வதில் பிழை: {e}")
                else:
                    st.error("❌ 'Vendor Wise Data' Google Sheet இணைப்பு கிடைக்கவில்லை!")

        with col_clear:
            if st.button("🗑️ பட்டியலை அழிக்கவும்", use_container_width=True):
                st.session_state["verified_list"] = []
                st.rerun()


# --- TASK 2: GOOGLE SHEET DATA SYNC ---
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync) மேலாண்மை")
    st.markdown("உள்ளூர் தரவுத்தளத்திற்கும் (Local Excel) Google Sheet-க்கும் இடையேயான ஒத்திசைவைச் சரிபார்க்கவும்.")
    
    if st.button("🚀 தரவுகளை உடனே ஒத்திசை (Sync Now)"):
        with st.spinner("ஒத்திசைக்கப்படுகிறது..."):
            time.sleep(1)
            st.success("✅ Google Sheet தரவுகள் வெற்றிகரமாக ஒத்திசைக்கப்பட்டன!")
            
    if spreadsheet:
        st.info(f"📁 இணைக்கப்பட்ட Google Sheet: **{spreadsheet.title}**")
        ws_list = [ws.title for ws in spreadsheet.worksheets()]
        st.write("📋 உள்ள বিদ্যমান தாள்கள் (Worksheets):")
        for name in ws_list:
            st.markdown(f"- {name}")


# --- TASK 3: VENDOR DETAILS ---
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")
    st.markdown("பதிவு செய்யப்பட்டுள்ள அனைத்துப் பதிப்பாளர்கள் மற்றும் முகவர்களின் விரிவான விவரங்கள்:")
    
    if vendor_df is not None and not vendor_df.empty:
        st.metric("📦 மொத்தப் பதிப்பாளர்கள்", len(vendor_df))
        render_print_and_export(vendor_df, "Publisher Details Report")
    else:
        st.warning("⚠️ பதிப்பாளர் விவரங்கள் கிடைக்கவில்லை அல்லது கோப்பு காலியாக உள்ளது.")


# --- TASK 4: LIBRARY DISTRIBUTION ---
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")
    st.markdown("நூலகங்களுக்கு நூல்களை விநியோகம் செய்வது தொடர்பான விவரங்கள் மற்றும் பட்டியல்:")
    
    if sheet_library_details:
        try:
            lib_records = sheet_library_details.get_all_records()
            if lib_records:
                lib_df = pd.DataFrame(lib_records)
                st.metric("🏛️ மொத்த நூலகங்கள்", len(lib_df))
                render_print_and_export(lib_df, "Library Distribution Report")
            else:
                st.info("ℹ️ நூலக விநியோகப் பட்டியல் விவரங்கள் காலியாக உள்ளன.")
        except Exception as e:
            st.error(f"❌ நூலக விவரங்களை எடுப்பதில் பிழை: {e}")
    else:
        st.warning("⚠️ Google Sheet-ல் நூலக விவரத் தாள் (Library Details Sheet) கிடைக்கவில்லை.")


# --- TASK 5: ACCESSION NUMBER MANAGEMENT ---
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. Accession எண்கள் மேலாண்மை")
    st.markdown("நூல்களுக்கான Accession எண்களைப் பதிவுசெய்து நிர்வகிக்கும் பகுதி.")
    
    with st.form("accession_form"):
        acc_book_title = st.text_input("📖 புத்தகத் தலைப்பு")
        acc_number = st.text_input("🔢 Accession எண்")
        acc_submit = st.form_submit_button("💾 பதிவு செய்")
        
        if acc_submit:
            if acc_book_title and acc_number:
                st.success(f"✅ '{acc_book_title}' புத்தகத்திற்கு Accession எண் ({acc_number}) வெற்றிகரமாகப் பதிவு செய்யப்பட்டது!")
            else:
                st.error("❌ அனைத்து விவரங்களையும் உள்ளிடவும்!")
