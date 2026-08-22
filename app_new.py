import os
import re
import time
import hashlib
import hmac
from datetime import datetime

import pandas as pd
import streamlit as st
import gspread
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
# 2. UI DESIGN
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
    }

    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.2rem .85rem;
    }

    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stCaption {
        color: white !important;
    }

    section[data-testid="stSidebar"] button {
        width: 100% !important;
        min-height: 56px !important;
        margin: 9px 0 !important;
        padding: 12px 15px !important;
        border: 1px solid rgba(255,255,255,.28) !important;
        border-radius: 16px !important;
        color: white !important;
        font-weight: 800 !important;
        text-align: left !important;
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.38), 0 6px 0 rgba(0,0,0,.32), 0 12px 18px rgba(0,0,0,.25) !important;
    }

    section[data-testid="stSidebar"] button p {
        color: white !important;
        font-weight: 800 !important;
    }

    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(1) button {
        background: linear-gradient(145deg, #ef5350, #b71c1c) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(2) button {
        background: linear-gradient(145deg, #2e7d32, #124d17) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(3) button {
        background: linear-gradient(145deg, #8e24aa, #4a148c) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(4) button {
        background: linear-gradient(145deg, #ef6c00, #b23c00) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(5) button {
        background: linear-gradient(145deg, #0288d1, #01579b) !important;
    }
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(6) button {
        background: linear-gradient(145deg, #546e7a, #263238) !important;
    }

    section[data-testid="stSidebar"] button:hover {
        transform: translateY(-4px) scale(1.015) !important;
        filter: brightness(1.16) saturate(1.12) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,.48), 0 9px 0 rgba(0,0,0,.30), 0 18px 25px rgba(0,0,0,.32) !important;
    }

    section[data-testid="stSidebar"] button:active {
        transform: translateY(4px) !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,.35), 0 2px 0 rgba(0,0,0,.3) !important;
    }

    div[data-baseweb="select"] > div,
    input, textarea {
        border-radius: 13px !important;
        border: 1px solid #b7c9e5 !important;
        background: rgba(255,255,255,.92) !important;
    }

    .stButton > button,
    .stDownloadButton > button {
        min-height: 46px;
        border: none !important;
        border-radius: 13px !important;
        color: white !important;
        font-weight: 800 !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 5px 0 #061b42, 0 9px 15px rgba(8,43,104,.25) !important;
        transition: all .18s ease !important;
    }

    .stButton > button:hover,
    .stDownloadButton > button:hover {
        transform: translateY(-3px);
        filter: brightness(1.12);
        box-shadow: 0 8px 0 #061b42, 0 14px 22px rgba(8,43,104,.32) !important;
    }

    div[data-testid="stMetric"] {
        padding: 18px !important;
        border-radius: 18px;
        background: rgba(255,255,255,.84);
        border: 1px solid rgba(255,255,255,.72);
        box-shadow: 0 8px 20px rgba(30,70,120,.12);
    }

    div[data-testid="stMetricValue"] {
        color: #0b3d91 !important;
        font-weight: 900 !important;
    }

    div[data-testid="stDataFrame"] {
        border-radius: 15px;
        overflow: hidden;
        box-shadow: 0 8px 20px rgba(30,70,120,.13);
    }

    div[data-testid="stAlert"] {
        border-radius: 15px !important;
        box-shadow: 0 5px 14px rgba(30,70,120,.10);
    }

    .login-card {
        max-width: 520px;
        margin: 7vh auto 0 auto;
        padding: 30px 30px 24px;
        border-radius: 26px;
        background: rgba(255,255,255,.92);
        box-shadow: 0 18px 0 rgba(7,26,56,.16), 0 28px 45px rgba(7,26,56,.20);
        text-align: center;
    }

    .login-logo {
        width: 78px;
        height: 78px;
        margin: 0 auto 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        font-size: 38px;
        background: linear-gradient(145deg, #00acc1, #1565c0);
        box-shadow: inset 0 3px 7px rgba(255,255,255,.4), 0 8px 0 #07366c, 0 14px 23px rgba(7,54,108,.25);
    }

    .login-title {
        margin: 0;
        color: #082653;
        font-size: 26px;
        font-weight: 900;
    }

    .login-subtitle {
        margin: 7px 0 24px;
        color: #60708a;
        font-size: 14px;
    }

    @media (max-width: 768px) {
        h1 { font-size: 1.35rem !important; padding: 17px !important; }
        section[data-testid="stSidebar"] button { min-height: 52px !important; font-size: 13px !important; }
    }
    </style>
    """


st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================
# 3. MULTI-USER LOGIN AND ACCESS CONTROL
# ============================================================
# Admin      : 9842759306 / Basswood 123456 / All pages
# User 1     : 9787555290 / Basswood 123456 / Task 1 only
# User 2     : 9751687939 / Basswood 123456 / Task 1 only
#
# Password code-ல் நேரடியாக compare செய்யப்படாது.
# SHA-256 hash + hmac.compare_digest பயன்படுத்தப்படுகிறது.

ALL_PAGES = [
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
    "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
    "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
    "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
    "⚙️ 5. Accession எண்கள் மேலாண்மை",
]

TASK_1_ONLY = [
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
]


def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# Password: Basswood 123456
BASSWOOD_PASSWORD_HASH = hash_password(
    "Basswood 123456"
)

USERS = {
    "9842759306": {
        "name": "Admin",
        "role": "admin",
        "password_hash": BASSWOOD_PASSWORD_HASH,
        "allowed_pages": ALL_PAGES,
    },
    "9787555290": {
        "name": "Task 1 User 1",
        "role": "task1",
        "password_hash": BASSWOOD_PASSWORD_HASH,
        "allowed_pages": TASK_1_ONLY,
    },
    "9751687939": {
        "name": "Task 1 User 2",
        "role": "task1",
        "password_hash": BASSWOOD_PASSWORD_HASH,
        "allowed_pages": TASK_1_ONLY,
    },
}


def authenticate_user(phone, password):
    phone = str(phone).strip()
    password = str(password)
    user = USERS.get(phone)

    if not user:
        return None

    entered_hash = hash_password(password)
    if hmac.compare_digest(
        entered_hash,
        user["password_hash"],
    ):
        return user

    return None


def show_login_page():
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">📚</div>
            <div class="login-title">பணி போர்ட்டல்</div>
            <div class="login-subtitle">
                2026 புதிய நூல்கள் விநியோகம்
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        with st.form("secure_multi_user_login"):
            phone = st.text_input(
                "📱 அலைபேசி எண்",
                max_chars=10,
                placeholder="10 இலக்க எண்ணை உள்ளிடவும்",
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

        if not submitted:
            return

        clean_phone = phone.strip()

        if not clean_phone:
            st.warning("⚠️ அலைபேசி எண்ணை உள்ளிடவும்.")
            return

        if not clean_phone.isdigit() or len(clean_phone) != 10:
            st.warning("⚠️ 10 இலக்க சரியான எண்ணை உள்ளிடவும்.")
            return

        if not password:
            st.warning("⚠️ கடவுச்சொல்லை உள்ளிடவும்.")
            return

        user = authenticate_user(clean_phone, password)

        if user:
            st.session_state["logged_in"] = True
            st.session_state["user_phone"] = clean_phone
            st.session_state["user_name"] = user["name"]
            st.session_state["user_role"] = user["role"]
            st.session_state["allowed_pages"] = user["allowed_pages"]
            st.session_state["login_attempts"] = 0
            st.session_state["current_page"] = user["allowed_pages"][0]
            st.rerun()
        else:
            st.session_state["login_attempts"] = (
                st.session_state.get("login_attempts", 0) + 1
            )
            st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("login_attempts", 0)

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# 4. DATA CONFIGURATION
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
        pd.read_excel(
            file_path,
            sheet_name=book_sheet_names[0],
        )
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

    credentials_dict = dict(
        st.secrets["gcp_service_account"]
    )

    credentials = (
        ServiceAccountCredentials
        .from_json_keyfile_dict(
            credentials_dict,
            scope,
        )
    )

    return gspread.authorize(credentials)


def clean_text(value):
    if pd.isna(value) or value is None:
        return ""

    value = str(value).strip()
    value = re.sub(r"^\d+[\.\s\-]*", "", value)
    return re.sub(
        r"[^a-zA-Z0-9\u0B80-\u0BFF]",
        "",
        value,
    ).lower()


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
            keyword in title
            for keyword in [
                "lib_detail",
                "library detail",
                "library details",
            ]
        ):
            sheet_library_details = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")


# ============================================================
# 5. SIDEBAR
# ============================================================
st.session_state.setdefault(
    "current_page",
    ALL_PAGES[0],
)
st.session_state.setdefault("verified_list", [])
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("book_key", 0)
st.session_state.setdefault("selected_vendor", None)

st.sidebar.markdown(
    f"### 👤 {st.session_state.get('user_name', 'User')}"
)
st.sidebar.caption(
    f"Role: {st.session_state.get('user_role', 'user')}"
)

if st.sidebar.button(
    "🚪 வெளியேறு (Logout)",
    use_container_width=True,
):
    for key in [
        "logged_in",
        "user_phone",
        "user_name",
        "user_role",
        "allowed_pages",
    ]:
        st.session_state.pop(key, None)

    st.session_state["logged_in"] = False
    st.session_state["verified_list"] = []
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

allowed_pages = st.session_state.get(
    "allowed_pages",
    TASK_1_ONLY,
)

for page in allowed_pages:
    if st.sidebar.button(page, use_container_width=True):
        st.session_state["current_page"] = page
        st.rerun()

st.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")
menu_choice = st.session_state["current_page"]


# ============================================================
# 6. TASK 1 - PHYSICAL VERIFICATION
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
                    saved_entries.add(
                        (
                            clean_text(row[0]),
                            clean_text(row[1]),
                        )
                    )
        except Exception:
            pass

    vendor_list = []
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
            vendor_name = col_b or col_c

            if (
                vendor_name
                and vendor_name.lower() != "nan"
                and vendor_name not in vendor_list
            ):
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
        if st.button(
            "🔄 மாற்றுக",
            key="btn_v_change",
            use_container_width=True,
        ):
            st.session_state["selected_vendor"] = None
            st.session_state["verified_list"] = []
            st.session_state["vendor_key"] += 1
            st.rerun()

    if selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"] != selected_vendor_raw:
            st.session_state["selected_vendor"] = selected_vendor_raw
            st.session_state["verified_list"] = []

    if st.session_state["selected_vendor"]:
        target_vendor_clean = clean_text(
            st.session_state["selected_vendor"]
        )

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
            c2.metric(
                "📦 மொத்தப் படிகள்",
                int(grouped["Quantity"].sum()),
            )

            added_titles = [
                clean_text(item["Title"])
                for item in st.session_state["verified_list"]
            ]
            title_options = [
                "-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"
            ]

            for _, row in grouped.iterrows():
                title = str(row["Title"]).strip()
                title_clean = clean_text(title)

                if (
                    title_clean not in added_titles
                    and (
                        target_vendor_clean,
                        title_clean,
                    ) not in saved_entries
                ):
                    author = (
                        str(row["Author Name"]).strip()
                        if pd.notna(row["Author Name"])
                        else ""
                    )
                    title_options.append(
                        f"{title} - {author}"
                        if author
                        else title
                    )

            if (
                len(title_options) == 1
                and not st.session_state["verified_list"]
            ):
                st.success(
                    "🎉 இந்த பதிப்பகத்தின் அனைத்துப் புத்தகங்களும் "
                    "சரிபார்க்கப்பட்டுவிட்டன!"
                )
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
                    if st.button(
                        "🔄 மாற்றுக",
                        key="btn_b_change",
                        use_container_width=True,
                    ):
                        st.session_state["book_key"] += 1
                        st.rerun()

                if selected_title != "-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    matched_row = None

                    for _, row in grouped.iterrows():
                        title = str(row["Title"]).strip()
                        author = (
                            str(row["Author Name"]).strip()
                            if pd.notna(row["Author Name"])
                            else ""
                        )
                        display = (
                            f"{title} - {author}"
                            if author
                            else title
                        )

                        if display == selected_title:
                            matched_row = row
                            break

                    if matched_row is not None:
                        total_quantity = int(matched_row["Quantity"])

                        with st.form("verify_form"):
                            st.write(
                                f"📖 **புத்தகத் தலைப்பு:** "
                                f"{matched_row['Title']}"
                            )
                            st.write(
                                f"✍️ **ஆசிரியர் பெயர்:** "
                                f"{matched_row['Author Name']}"
                            )

                            received_quantity = st.number_input(
                                "📦 பெறப்பட்ட படிகள்",
                                min_value=0,
                                max_value=1000,
                                value=total_quantity,
                            )

                            submitted = st.form_submit_button(
                                "➕ பட்டியலில் சேர்"
                            )

                        if submitted:
                            st.session_state["verified_list"].append({
                                "Vendor": st.session_state["selected_vendor"],
                                "Title": matched_row["Title"],
                                "Language": matched_row["Language"],
                                "Author": matched_row["Author Name"],
                                "TotalQty": total_quantity,
                                "ReceivedQty": received_quantity,
                                "NotReceivedQty": max(
                                    0,
                                    total_quantity - received_quantity,
                                ),
                            })
                            st.session_state["book_key"] += 1
                            st.rerun()

    if st.session_state["verified_list"]:
        st.markdown("---")
        st.markdown("### 📋 சரிபார்க்கப்பட்ட தற்காலிகப் பட்டியல்")
        verified_df = pd.DataFrame(
            st.session_state["verified_list"]
        )
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
            if st.button(
                "💾 Google Sheet-ல் சேமி",
                key="btn_save",
                use_container_width=True,
            ):
                try:
                    if not sheet_physically:
                        st.error(
                            "❌ Physically Verified sheet கிடைக்கவில்லை!"
                        )
                    else:
                        current_date = datetime.now().strftime(
                            "%d/%m/%Y %H:%M:%S"
                        )

                        rows = [
                            [
                                item["Vendor"],
                                item["Title"],
                                item["Language"],
                                item["Author"],
                                item["Vendor"],
                                item["TotalQty"],
                                item["ReceivedQty"],
                                item["NotReceivedQty"],
                                current_date,
                            ]
                            for item in st.session_state["verified_list"]
                        ]

                        sheet_physically.append_rows(rows)
                        st.success(
                            "🎉 தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!"
                        )
                        st.session_state["verified_list"] = []
                        st.rerun()
                except Exception as error:
                    st.error(f"❌ சேமிப்பு பிழை: {error}")

        with col_clear:
            if st.button(
                "🗑️ பட்டியலை அழி",
                key="btn_clear",
                use_container_width=True,
            ):
                st.session_state["verified_list"] = []
                st.rerun()


# ============================================================
# 7. TASK 2 - SYNC
# ============================================================
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
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
                st.success(
                    "🟢 அனைத்துப் பதிப்பகங்களும் ஏற்கனவே "
                    "ஒத்திசைக்கப்பட்டுள்ளன!"
                )
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
                    st.dataframe(
                        display_df[["Title", "Total", "Rec"]],
                        use_container_width=True,
                    )

                    if st.button(
                        f"🚀 {selected_vendor} தரவை ஒத்திசைவு செய்",
                        key="btn_sync_single",
                        use_container_width=True,
                    ):
                        updates = []

                        for record in vendor_books:
                            target_title = clean_text(record[1])
                            received_quantity = (
                                int(record[6])
                                if str(record[6]).isdigit()
                                else 0
                            )
                            matched_count = 0

                            for row_index, sheet_row in enumerate(
                                vendor_data[1:],
                                start=2,
                            ):
                                if len(sheet_row) > 10:
                                    sheet_title = clean_text(sheet_row[4])
                                    sheet_publisher = clean_text(sheet_row[9])
                                    sheet_vendor = clean_text(sheet_row[10])

                                    if (
                                        selected_clean in {
                                            sheet_publisher,
                                            sheet_vendor,
                                        }
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
                            st.success(
                                "✅ தேர்ந்தெடுக்கப்பட்ட பதிப்பகம் "
                                "ஒத்திசைக்கப்பட்டது!"
                            )
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.warning(
                                "⚠️ பொருந்தும் தரவுகள் கிடைக்கவில்லை!"
                            )
        except Exception as error:
            st.error(f"❌ ஒத்திசைவு பிழை: {error}")


# ============================================================
# 8. TASK 3 - VENDOR DETAILS
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
            vendor_column = (
                live_df.columns[10]
                if len(live_df.columns) > 10
                else live_df.columns[9]
            )
            vendors = sorted(
                set(
                    live_df[vendor_column]
                    .astype(str)
                    .str.strip()
                )
            )

            selected_vendor = st.selectbox(
                "🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",
                ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors,
            )

            if selected_vendor != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                filtered_df = live_df[
                    live_df[vendor_column]
                    .astype(str)
                    .str.strip()
                    == selected_vendor
                ]
                st.markdown(
                    f"### 📋 {selected_vendor} - "
                    f"மொத்தப் புத்தகங்கள் ({len(filtered_df)})"
                )
                st.dataframe(filtered_df, use_container_width=True)


# ============================================================
# 9. TASK 4 - LIBRARY DELIVERY REPORT
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
                (
                    code
                    for code, name in library_map.items()
                    if name == selected_library
                ),
                "",
            )

            name_clean = clean_text(selected_library)
            code_clean = clean_text(selected_code)
            column_o = (
                live_df.columns[14]
                if len(live_df.columns) > 14
                else None
            )
            column_p = (
                live_df.columns[15]
                if len(live_df.columns) > 15
                else None
            )

            def library_match(row):
                p_value = clean_text(row[column_p]) if column_p else ""
                o_value = clean_text(row[column_o]) if column_o else ""

                return (
                    name_clean in p_value
                    or p_value in name_clean
                    or (
                        code_clean
                        and (
                            code_clean in o_value
                            or o_value in code_clean
                        )
                    )
                )

            filtered_df = live_df[
                live_df.apply(library_match, axis=1)
            ]

            if filtered_df.empty:
                st.warning("⚠️ இந்த நூலகத்திற்கு ஒதுக்கீடு இல்லை!")
            else:
                received_column = (
                    live_df.columns[18]
                    if len(live_df.columns) > 18
                    else None
                )

                received_df = (
                    filtered_df[
                        filtered_df[received_column]
                        .astype(str)
                        .str.strip()
                        == "1"
                    ]
                    if received_column
                    else filtered_df
                )

                c1, c2, c3 = st.columns(3)
                c1.metric("📖 மொத்த ஒதுக்கீடு", len(filtered_df))
                c2.metric("✅ பெறப்பட்ட புத்தகங்கள்", len(received_df))
                c3.metric(
                    "🏛️ நூலகக் குறியீடு",
                    selected_code or "N/A",
                )

                st.markdown(
                    f"### 📋 {selected_library} - விநியோக அறிக்கை"
                )
                st.dataframe(filtered_df, use_container_width=True)

                csv_data = filtered_df.to_csv(
                    index=False
                ).encode("utf-8-sig")

                st.download_button(
                    f"📄 {selected_library} - CSV பதிவிறக்கம்",
                    csv_data,
                    f"{selected_library}_Book_Delivery_Report.csv",
                    "text/csv",
                    use_container_width=True,
                )


# ============================================================
# 10. TASK 5 - ACCESSION MANAGEMENT
# ============================================================
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. Accession எண்கள் மற்றும் Batch ஒதுக்கீடு மேலாண்மை")
    st.info(
        "💡 சரிபார்ப்பு மற்றும் ஒத்திசைவு பணிகள் முடிந்த பிறகு "
        "இந்தப் பணியைச் செய்யவும்."
    )

    if not sheet_library_details or not sheet_vendor_wise or not sheet_physically:
        st.error("❌ Google Sheet தரவுகள் முழுமையாகக் கிடைக்கவில்லை!")
    else:
        library_records = sheet_library_details.get_all_values()
        vendor_data = sheet_vendor_wise.get_all_values()
        physical_records = sheet_physically.get_all_values()

        if len(library_records) > 1:
            central_value = (
                library_records[1][5]
                if len(library_records[1]) > 5
                and str(library_records[1][5]).strip()
                else "1001"
            )

            st.markdown("---")
            st.markdown("### 🏷️ 1. Last Central Accession Number")
            c1, c2 = st.columns([2, 3])
            c1.metric("தற்போதைய Central Number", central_value)

            with c2:
                new_central = st.number_input(
                    "புதிய Central Accession Number",
                    min_value=1,
                    value=(
                        int(central_value)
                        if str(central_value).isdigit()
                        else 1001
                    ),
                )

                if st.button(
                    "💾 Central Number புதுப்பி",
                    key="btn_update_central",
                ):
                    sheet_library_details.update_cell(
                        2,
                        6,
                        new_central,
                    )
                    st.success(
                        "✅ Central Accession Number புதுப்பிக்கப்பட்டது!"
                    )
                    st.rerun()

            st.markdown("---")
            st.markdown("### 🚀 2. Final Accession Allocation")
            st.warning(
                "⚠️ இந்த செயல் Google Sheet-ல் நிரந்தரமாகத் தரவை மாற்றும்."
            )

            if st.button(
                "⚡ Final Allocation தொடங்கு",
                key="btn_final_sync",
                use_container_width=True,
            ):
                with st.spinner(
                    "⏳ Accession எண்கள் ஒதுக்கப்படுகின்றன..."
                ):
                    current_central = (
                        int(central_value)
                        if str(central_value).isdigit()
                        else 1001
                    )
                    library_accessions = {}

                    for row_index, row in enumerate(
                        library_records[1:،],
                        start=2,
                    ):
                        if len(row) >= 7:
                            code = str(row[1]).strip()
                            last_accession = (
                                int(row[6])
                                if str(row[6]).isdigit()
                                else 1000
                            )

                            if code:
                                library_accessions[code] = {
                                    "last_acc": last_accession,
                                    "row_idx": row_index,
                                }

                    updates = []
                    updated_count = 0

                    for physical in physical_records[1:]:
                        if len(physical) < 8:
                            continue

                        vendor_clean = clean_text(physical[0])
                        title_clean = clean_text(physical[1])
                        required_quantity = (
                            int(physical[6])
                            if str(physical[6]).isdigit()
                            else 0
                        )
                        matched_count = 0

                        for row_index, vendor_row in enumerate(
                            vendor_data[1:],
                            start=2,
                        ):
                            if len(vendor_row) <= 14:
                                continue

                            row_title = clean_text(vendor_row[4])
                            row_publisher = clean_text(vendor_row[9])
                            row_vendor = clean_text(vendor_row[10])
                            library_code = str(vendor_row[14]).strip()

                            vendor_match = vendor_clean in {
                                row_publisher,
                                row_vendor,
                            }
                            title_match = (
                                title_clean in row_title
                                or row_title in title_clean
                            )

                            if vendor_match and title_match:
                                if matched_count < required_quantity:
                                    current_central += 1

                                    if library_code in library_accessions:
                                        library_accessions[library_code]["last_acc"] += 1
                                        library_accession = library_accessions[library_code]["last_acc"]
                                    else:
                                        library_accession = 1001

                                    updates.append({
                                        "range": f"S{row_index}:V{row_index}",
                                        "values": [[
                                            1,
                                            0,
                                            current_central,
                                            library_accession,
                                        ]],
                                    })
                                    matched_count += 1
                                    updated_count += 1
                                else:
                                    updates.append({
                                        "range": f"S{row_index}:V{row_index}",
                                        "values": [[0, 1, "", ""]],
                                    })

                    if updates:
                        sheet_vendor_wise.batch_update(updates)

                    library_updates = [{
                        "range": "F2",
                        "values": [[current_central]],
                    }]

                    for code, item in library_accessions.items():
                        library_updates.append({
                            "range": f"G{item['row_idx']}",
                            "values": [[item["last_acc"]]],
                        })

                    sheet_library_details.batch_update(library_updates)
                    st.success(
                        f"🎉 {updated_count} புத்தகங்களுக்கு Accession "
                        "எண்கள் ஒதுக்கப்பட்டன!"
                    )
                    time.sleep(1)
                    st.rerun()

            st.markdown("---")
            st.markdown("### 🏛️ 3. நூலக வாரியான Last Accession Number")

            extracted = []
            for row_index, row in enumerate(
                library_records[1:],
                start=2,
            ):
                if len(row) >= 3:
                    code = str(row[1]).strip()
                    name = str(row[2]).strip()
                    accession = (
                        str(row[6]).strip()
                        if len(row) > 6
                        else ""
                    )

                    if code and code.lower() != "nan":
                        extracted.append({
                            "row_idx": row_index,
                            "Lib Code": code,
                            "Library Name": name,
                            "Last Accession Number": accession,
                        })

            library_df = pd.DataFrame(extracted)
            category = st.radio(
                "நூலக வகை",
                [
                    "அனைத்தும் (All 103)",
                    "DCL",
                    "FTB",
                    "BL",
                    "VL",
                ],
                horizontal=True,
            )

            filtered_df = library_df.copy()
            if category != "அனைத்தும் (All 103)":
                filtered_df = filtered_df[
                    filtered_df["Lib Code"]
                    .astype(str)
                    .str.upper()
                    .str.contains(
                        category.upper(),
                        na=False,
                    )
                ]

            st.dataframe(
                filtered_df[[
                    "Lib Code",
                    "Library Name",
                    "Last Accession Number",
                ]],
                use_container_width=True,
            )

            options = [
                f"{row['Lib Code']} - {row['Library Name']}"
                for _, row in filtered_df.iterrows()
            ]

            if options:
                selected_option = st.selectbox(
                    "நூலகத்தைத் தேர்ந்தெடுக்கவும்",
                    ["-- தேர்ந்தெடுக்கவும் --"] + options,
                )

                if selected_option != "-- தேர்ந்தெடுக்கவும் --":
                    selected_code = selected_option.split(
                        " - ",
                        1,
                    )[0].strip()

                    selected_row = filtered_df[
                        filtered_df["Lib Code"] == selected_code
                    ].iloc[0]

                    row_index = int(selected_row["row_idx"])
                    current_accession = str(
                        selected_row["Last Accession Number"]
                    ).strip()
                    current_accession = (
                        int(current_accession)
                        if current_accession.isdigit()
                        else 1000
                    )

                    new_accession = st.number_input(
                        f"{selected_code} - புதிய Accession Number",
                        min_value=1,
                        value=current_accession,
                    )

                    if st.button(
                        "💾 நூலக Accession Number புதுப்பி",
                        key="btn_update_lib",
                        use_container_width=True,
                    ):
                        sheet_library_details.update_cell(
                            row_index,
                            7,
                            new_accession,
                        )
                        st.success(
                            "✅ நூலக Accession Number புதுப்பிக்கப்பட்டது!"
                        )
                        st.rerun()
            else:
                st.warning("⚠️ இந்த வகையில் நூலகங்கள் கிடைக்கவில்லை!")
