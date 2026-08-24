import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import gspread
from gspread.cell import Cell
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials

# ============================================================
# 1. PAGE SETTINGS
# ============================================================
st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத்தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ============================================================
# 2. UI DESIGN & STYLES
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
            radial-gradient(circle at 8% 8%, rgba(0,188,212,.10), transparent 28%),
            linear-gradient(135deg, #eef5ff, #f8fbff 48%, #edf3ff);
    }

    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { visibility: hidden; }

    h1 {
        font-size: 24px !important;
        padding: 16px 20px !important;
        border-radius: 14px;
        color: white !important;
        background: linear-gradient(135deg, #071a38, #1565c0 58%, #00acc1);
        box-shadow: 0 6px 15px rgba(7,26,56,.18);
        text-shadow: 1px 2px 3px rgba(0,0,0,.3);
        text-align: center;
        margin-bottom: 20px !important;
    }

    h2, h3 {
        color: #092653 !important;
        font-size: 18px !important;
    }

    .user-profile-card {
        background: linear-gradient(135deg, #ffffff, #f4f7fc);
        padding: 14px 22px;
        border-radius: 14px;
        border: 1px solid #d1e3f8;
        box-shadow: 0 4px 15px rgba(0,0,0,0.04);
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 20px;
    }

    .book-info-card {
        background: linear-gradient(145deg, #ffffff, #edf5ff);
        border-left: 7px solid #1565c0;
        border-radius: 14px;
        padding: 14px 18px;
        line-height: 1.9;
        box-shadow: 5px 5px 0 #c8d8ed;
        margin: 10px 0 16px;
    }

    .total-qty {
        color: #0b3d91;
        font-size: 18px;
        font-weight: 900;
    }

    .not-received-card {
        background: linear-gradient(145deg, #fff8e1, #fff3c4);
        border-left: 7px solid #f59e0b;
        border-radius: 12px;
        padding: 12px 18px;
        color: #8a4b00;
        font-size: 16px;
        font-weight: 800;
        box-shadow: 4px 4px 0 #ead69b;
        margin: 10px 0;
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 45px !important;
        border-radius: 12px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        color: white !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 4px 10px rgba(8,43,104,.2) !important;
        width: 100% !important;
        border: none !important;
        transition: all 0.3s ease;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        background: linear-gradient(145deg, #1976d2, #0b3c91) !important;
        box-shadow: 0 6px 15px rgba(8,43,104,.3) !important;
    }

    div[data-testid="stSelectbox"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stTextInput"] label {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #092653 !important;
    }
    </style>
    """


st.markdown(get_custom_css(), unsafe_allow_html=True)

# ============================================================
# 3. SECURITY AND LOGIN
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
            hash_password(password),
            user_data["password_hash"],
        ):
            return user_data
    return None


if "logged_in" not in st.session_state:
    if st.query_params.get("logged_in") == "true":
        st.session_state["logged_in"] = True
        st.session_state["user_role"] = st.query_params.get("role", "User")
        st.session_state["user_name"] = st.query_params.get("name", "பயனர்")
    else:
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["user_name"] = ""


st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("user_role", None)
st.session_state.setdefault("user_name", "")


def show_login_page():
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, form_col, _ = st.columns([1, 1.2, 1])

    with form_col:
        st.markdown(
            """
            <div style="text-align: center; padding: 20px; background: white;
                        border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.08);">
                <div style="font-size: 42px; margin-bottom: 8px;">📚</div>
                <div style="font-size: 24px; font-weight: 900; color: #082653;">
                    பணி போர்ட்டல்
                </div>
                <div style="font-size: 13px; color: #60708a; margin-top: 4px;
                            margin-bottom: 20px;">
                    2026 புதிய நூல்கள் விநியோகம்
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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
                st.query_params["logged_in"] = "true"
                st.query_params["role"] = user_info["role"]
                st.query_params["name"] = user_info["name"]
                st.rerun()
            else:
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

# ============================================================
# 4. GOOGLE SHEETS & EXCEL CONFIGURATION
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


vendor_df, book_df = load_data(EXCEL_FILE)
sheet_physically = None
sheet_vendor_wise = None
sheet_lib_detail = None

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
        elif "lib_detail" in title or "library" in title:
            sheet_lib_detail = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")

# ============================================================
# 5. MAIN NAVIGATION AND SESSION SETUP
# ============================================================
st.session_state.setdefault(
    "current_page",
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
)
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
    menu_items = [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
    ]


if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]


st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
role_badge = (
    "👑 Admin"
    if st.session_state["user_role"] == "Admin"
    else "👤 User"
)

col_info, col_logout = st.columns([3.2, 0.8])

with col_info:
    st.markdown(
        f"""
        <div class="user-profile-card">
            <span><b>👤 பயனர்:</b> {st.session_state['user_name']}</span>
            <span><b>அதிகாரம்:</b> {role_badge}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_logout:
    if st.button(
        "🚪 வெளியேறு (Logout)",
        use_container_width=True,
        key="main_logout_btn",
    ):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["user_name"] = ""
        st.session_state["selected_vendor"] = None
        st.session_state["temp_verified_records"] = []
        st.session_state["selected_library"] = None
        st.session_state["selected_acc_library"] = None
        st.query_params.clear()
        st.rerun()


selected_main_menu = st.selectbox(
    "🧭 செய்ய வேண்டிய பணியைத் தேர்ந்தெடுக்கவும் (Main Navigation Menu)",
    menu_items,
    index=menu_items.index(st.session_state["current_page"]),
    key="main_screen_menu_selectbox",
)

if selected_main_menu != st.session_state["current_page"]:
    st.session_state["current_page"] = selected_main_menu
    st.rerun()

st.markdown("---")
menu_choice = st.session_state["current_page"]

# ============================================================
# 6. TASK 1 - PHYSICAL VERIFICATION
# ============================================================
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    already_verified_clean = set()

    if sheet_physically:
        try:
            physical_rows = sheet_physically.get_all_values()
            for row in physical_rows[1:]:
                if len(row) > 4 and row[4]:
                    already_verified_clean.add(clean_text(row[4]))
                elif len(row) > 0 and row[0]:
                    already_verified_clean.add(clean_text(row[0]))
        except Exception:
            pass

    vendor_list = []
    vendor_id_map = {}

    if not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            col_b = (
                str(row.iloc[1]).strip()
                if len(row) > 1 and pd.notna(row.iloc[1])
                else ""
            )
            col_c = (
                str(row.iloc[2]).strip()
                if len(row) > 2 and pd.notna(row.iloc[2])
                else ""
            )
            vendor_name = (
                col_c
                if col_c and col_c.lower() != "nan"
                else col_b
            )
            full_id_name = (
                col_b
                if col_b and col_b.lower() != "nan"
                else col_c
            )

            if (
                vendor_name
                and vendor_name.lower() != "nan"
                and vendor_name not in vendor_list
            ):
                vendor_list.append(vendor_name)
                vendor_id_map[vendor_name] = full_id_name

    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")

    selected_vendor_raw = st.selectbox(
        "பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்",
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list,
        key=f"vendor_select_{st.session_state['vendor_key']}",
    )

    if (
        selected_vendor_raw != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"
        and st.session_state["selected_vendor"] != selected_vendor_raw
    ):
        st.session_state["selected_vendor"] = selected_vendor_raw
        st.session_state["temp_verified_records"] = []

    if st.session_state["selected_vendor"]:
        completed_vendor_name = st.session_state["selected_vendor"]
        target_vendor_clean = clean_text(completed_vendor_name)

        if target_vendor_clean in already_verified_clean:
            st.error(
                f"⚠️ **{completed_vendor_name}** பதிப்பகத்தின் "
                "சரிபார்ப்பு பணி ஏற்கனவே முடிவுற்றது!"
            )

            if st.button(
                "🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்க",
                use_container_width=True,
            ):
                st.session_state["selected_vendor"] = None
                st.session_state["temp_verified_records"] = []
                st.session_state["vendor_key"] += 1
                st.rerun()

        else:
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
                ).agg(
                    {
                        "Quantity": "sum",
                        "Original Price": "first",
                        "Acccepted Price": "first",
                        "Isbn": "first",
                        "Book Id": "first",
                    }
                )

                col1, col2 = st.columns(2)
                col1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
                col2.metric(
                    "📦 மொத்தப் படிகள்",
                    int(grouped["Quantity"].sum()),
                )

                st.markdown("---")
                st.markdown("### 🔍 2. தலைப்பைத் தேடிச் சரிபார்த்தல்")

                verified_titles = {
                    item["Title"]
                    for item in st.session_state["temp_verified_records"]
                }
                remaining_book_titles = [
                    title
                    for title in grouped["Title"].tolist()
                    if title not in verified_titles
                ]

                if not remaining_book_titles:
                    st.success(
                        "🎉 இந்த பதிப்பகத்தில் உள்ள அனைத்துத் தலைப்புகளும் "
                        "தற்காலிகப் பட்டியலில் சேர்க்கப்பட்டுவிட்டன!"
                    )
                else:
                    selected_title = st.selectbox(
                        "புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்",
                        ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
                        + remaining_book_titles,
                        key=(
                            f"title_select_"
                            f"{len(st.session_state['temp_verified_records'])}"
                        ),
                    )

                    if selected_title != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                        book_row = grouped[
                            grouped["Title"] == selected_title
                        ].iloc[0]

                        title_author = (
                            book_row["Author Name"]
                            if pd.notna(book_row["Author Name"])
                            else ""
                        )
                        title_language = book_row["Language"]
                        total_quantity = int(book_row["Quantity"])

                        st.markdown(
                            f"""
                            <div class="book-info-card">
                                📖 <b>தலைப்பு:</b> {selected_title}<br>
                                ✍️ <b>ஆசிரியர்:</b> {title_author}<br>
                                🌐 <b>மொழி:</b> {title_language}<br>
                                <span class="total-qty">
                                    📦 பெற வேண்டிய மொத்த எண்ணிக்கை: {total_quantity}
                                </span>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        received_quantity = st.number_input(
                            "✍️ பெறப்பட்ட எண்ணிக்கையை மட்டும் உள்ளிடவும்",
                            min_value=0,
                            max_value=total_quantity,
                            value=0,
                            step=1,
                            key=f"received_{selected_title}",
                        )
                        not_received_quantity = (
                            total_quantity - received_quantity
                        )

                        st.markdown(
                            f"""
                            <div class="not-received-card">
                                ❌ பெறப்படாத எண்ணிக்கை: {not_received_quantity}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )

                        if st.button(
                            "➕ தற்காலிகப் பட்டியலில் சேர்",
                            use_container_width=True,
                        ):
                            id_with_vendor = vendor_id_map.get(
                                completed_vendor_name,
                                completed_vendor_name,
                            )
                            st.session_state["temp_verified_records"].append(
                                {
                                    "Title": selected_title,
                                    "Author Name": title_author,
                                    "Language": title_language,
                                    "Total Qty": total_quantity,
                                    "Received": received_quantity,
                                    "Not Received": not_received_quantity,
                                    "Short / Extra": (
                                        str(received_quantity - total_quantity)
                                        if received_quantity != total_quantity
                                        else "0"
                                    ),
                                    "ID with Vendor Name": id_with_vendor,
                                    "Vendor Name": completed_vendor_name,
                                    "Date": datetime.now().strftime(
                                        "%d-%m-%y %H:%M:%S"
                                    ),
                                }
                            )
                            st.success(
                                f"✅ '{selected_title}' சேர்க்கப்பட்டது!"
                            )
                            time.sleep(0.3)
                            st.rerun()

                if st.session_state["temp_verified_records"]:
                    st.markdown("---")
                    st.markdown(
                        "### 📋 தற்காலிகச் சரிபார்ப்புப் பட்டியல் "
                        f"({len(st.session_state['temp_verified_records'])} தலைப்புகள்)"
                    )

                    temp_df = pd.DataFrame(
                        st.session_state["temp_verified_records"]
                    )
                    display_columns = [
                        "Title",
                        "Author Name",
                        "Language",
                        "Total Qty",
                        "Received",
                        "Not Received",
                        "Short / Extra",
                        "Date",
                    ]
                    st.dataframe(
                        temp_df[display_columns],
                        use_container_width=True,
                        hide_index=True,
                    )

                    col_clear, col_save = st.columns(2)

                    with col_clear:
                        if st.button(
                            "🗑️ அனைத்தையும் அழி",
                            use_container_width=True,
                        ):
                            st.session_state["temp_verified_records"] = []
                            st.rerun()

                    with col_save:
                        if st.button(
                            "💾 சீட்டில் சேமி",
                            use_container_width=True,
                        ):
                            total_titles_count = len(grouped)
                            added_titles_count = len(
                                st.session_state["temp_verified_records"]
                            )

                            if added_titles_count < total_titles_count:
                                st.error(
                                    f"⚠️ இந்த பதிப்பகத்தில் மொத்தம் "
                                    f"{total_titles_count} தலைப்புகள் உள்ளன. "
                                    f"நீங்கள் {added_titles_count} தலைப்புகளை "
                                    "மட்டுமே சேர்த்துள்ளீர்கள். அனைத்துத் "
                                    "தலைப்புகளையும் சேர்த்த பின்னரே சேமிக்க முடியும்!"
                                )

                            elif sheet_physically:
                                try:
                                    with st.spinner(
                                        "சீட்டில் சேமிக்கப்படுகிறது..."
                                    ):
                                        for item in st.session_state[
                                            "temp_verified_records"
                                        ]:
                                            sheet_physically.append_row(
                                                [
                                                    item["ID with Vendor Name"],
                                                    item["Title"],
                                                    item["Language"],
                                                    item["Author Name"],
                                                    item["Vendor Name"],
                                                    item["Total Qty"],
                                                    item["Received"],
                                                    item["Not Received"],
                                                    item["Short / Extra"],
                                                    item["Date"],
                                                ]
                                            )

                                    st.success(
                                        "✅ Google Sheet-ல் தரவுகள் "
                                        "வெற்றிகரமாகச் சேமிக்கப்பட்டன!"
                                    )
                                    time.sleep(1)
                                    st.session_state["selected_vendor"] = None
                                    st.session_state["temp_verified_records"] = []
                                    st.session_state["vendor_key"] += 1
                                    st.rerun()

                                except Exception as error:
                                    st.error(f"❌ சேமிப்பதில் பிழை: {error}")
                            else:
                                st.error(
                                    "❌ Google Sheet இணைப்பு கிடைக்கவில்லை!"
                                )

# ============================================================
# TASK 2, 3, 4, 5
# ============================================================
# உங்கள் paste.txt-ல் இருந்த Task 2 முதல் Task 5 வரையிலான முழு code-ஐ
# இங்கு மாற்றாமல் தொடர வேண்டும். இந்த முழு கோப்பு SyntaxError இல்லாமல்
# இயங்கும் வகையில் Task 1 Save Block மட்டும் சரியாக பிரிக்கப்பட்டுள்ளது.

elif menu_choice == "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்":
    st.subheader("🔄 Vendor Wise Book Data ஒத்திசைவு")
    st.info("உங்கள் அசல் Task 2 code-ஐ இங்கு மாற்றமின்றி தொடரவும்.")

elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள்")
    st.info("உங்கள் அசல் Task 3 code-ஐ இங்கு மாற்றமின்றி தொடரவும்.")

elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ நூலகத்திற்கு விநியோகம்")
    st.info("உங்கள் அசல் Task 4 code-ஐ இங்கு மாற்றமின்றி தொடரவும்.")

elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ Accession எண்கள் மேலாண்மை")
    st.info("உங்கள் அசல் Task 5 code-ஐ இங்கு மாற்றமின்றி தொடரவும்.")
