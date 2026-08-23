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
    page_title="2026 புதிய நூல்கள் விநியோகம்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
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
        if hmac.compare_digest(hash_password(password), user_data["password_hash"]):
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
    st.markdown("<br>", unsafe_allow_html=True)
    _, form_col, _ = st.columns([1, 1.2, 1])
    with form_col:
        st.markdown(
            """
            <div style="text-align: center; padding: 10px 0;">
                <div style="font-size: 36px; margin-bottom: 6px;">📚</div>
                <div style="font-size: 22px; font-weight: 900; color: #082653;">பணி போர்ட்டல்</div>
                <div style="font-size: 13px; color: #60708a; margin-top: 4px; margin-bottom: 16px;">2026 புதிய நூல்கள் விநியோகம்</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("secure_login_form"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10, placeholder="10 இலக்க எண்")
            password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்")
            submitted = st.form_submit_button("🔓 உள்நுழைக", use_container_width=True)

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
    vendor_df = pd.read_excel(file_path, sheet_name="Vendor Name") if "Vendor Name" in excel_data.sheet_names else pd.DataFrame()
    book_sheet_names = [s for s in excel_data.sheet_names if "Vendor Wise Book Data" in s]
    book_df = pd.read_excel(file_path, sheet_name=book_sheet_names[0]) if book_sheet_names else pd.DataFrame()
    return vendor_df, book_df

@st.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials_dict = dict(st.secrets["gcp_service_account"])
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
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

try:
    client = init_gspread()
    spreadsheet = client.open_by_key(SPREADSHEET_ID)
    worksheets = {worksheet.title.strip().lower(): worksheet for worksheet in spreadsheet.worksheets()}
    for title, worksheet in worksheets.items():
        if "physically verified" in title:
            sheet_physically = worksheet
        elif "vendor wise book data" in title:
            sheet_vendor_wise = worksheet
except Exception as error:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")

# ============================================================
# 5. SIDEBAR & NAVIGATION
# ============================================================
st.session_state.setdefault("current_page", "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
st.session_state.setdefault("vendor_key", 0)
st.session_state.setdefault("selected_vendor", None)
st.session_state.setdefault("temp_verified_records", [])
st.session_state.setdefault("library_key", 0)
st.session_state.setdefault("selected_library", None)
st.session_state.setdefault("vendor_t3_key", 0)
st.session_state.setdefault("selected_vendor_t3", None)

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
    st.session_state["selected_library"] = None
    st.session_state["selected_vendor_t3"] = None
    st.query_params.clear()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

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

for item in menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()

st.title("📚 நூல்கள் சரிபார்ப்புப் போர்ட்டல்")
menu_choice = st.session_state["current_page"]

# ============================================================
# 6. TASKS IMPLEMENTATION
# ============================================================

# --- TASK 1: PHYSICAL VERIFICATION ---
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    already_verified_clean = set()
    if sheet_physically:
        try:
            p_rows = sheet_physically.get_all_values()
            for r in p_rows[1:]:
                if len(r) > 4 and r[4]:
                    already_verified_clean.add(clean_text(r[4]))
                elif len(r) > 0 and r[0]:
                    already_verified_clean.add(clean_text(r[0]))
        except Exception:
            pass

    vendor_list = []
    vendor_id_map = {}
    if not vendor_df.empty:
        for _, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            vendor_name = col_c if col_c and col_c.lower() != "nan" else col_b
            full_id_name = col_b if col_b and col_b.lower() != "nan" else col_c
            if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
                vendor_list.append(vendor_name)
                vendor_id_map[vendor_name] = full_id_name

    st.markdown("---")
    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    selected_vendor_raw = st.selectbox(
        "பதிப்பகத்தின் முதல் எழுத்துகளை உள்ளீடு செய்யவும்",
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list,
        key=f"vendor_select_{st.session_state['vendor_key']}",
    )

    if selected_vendor_raw != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"] != selected_vendor_raw:
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
                grouped = filtered_books.groupby(
                    ["Title", "Author Name", "Language"], as_index=False
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
                st.markdown("### 🔍 2. தலைப்பைத் தேடிச் சரிபார்த்தல்")

                verified_titles = {item["Title"] for item in st.session_state["temp_verified_records"]}
                remaining_book_titles = [t for t in grouped["Title"].tolist() if t not in verified_titles]

                if not remaining_book_titles:
                    st.success("🎉 இந்த பதிப்பகத்தில் உள்ள அனைத்துத் தலைப்புகளும் தற்காலிகப் பட்டியலில் சேர்க்கப்பட்டுவிட்டன!")
                else:
                    selected_title = st.selectbox(
                        "புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்",
                        ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"] + remaining_book_titles,
                        key=f"title_select_{len(st.session_state['temp_verified_records'])}",
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
                            key=f"rec_inp_{selected_title}",
                        )

                        if st.button("➕ தற்காலிகப் பட்டியலில் சேர்", use_container_width=True):
                            diff = rec_qty - t_total_qty
                            if diff < 0:
                                not_rec = abs(diff)
                                short_extra_val = str(diff)
                            elif diff > 0:
                                not_rec = 0
                                short_extra_val = f"+{diff}"
                            else:
                                not_rec = 0
                                short_extra_val = "0"

                            id_with_vendor = vendor_id_map.get(completed_vendor_name, completed_vendor_name)

                            st.session_state["temp_verified_records"].append({
                                "Title": selected_title,
                                "Author Name": t_author,
                                "Language": t_lang,
                                "Total Qty": t_total_qty,
                                "Received": rec_qty,
                                "Not Received": not_rec,
                                "Short / Extra": short_extra_val,
                                "ID with Vendor Name": id_with_vendor,
                                "Vendor Name": completed_vendor_name,
                                "Date": datetime.now().strftime("%d-%m-%y %H:%M:%S"),
                            })
                            st.success(f"✅ '{selected_title}' சேர்க்கப்பட்டது!")
                            time.sleep(0.3)
                            st.rerun()

                if st.session_state["temp_verified_records"]:
                    st.markdown("---")
                    st.markdown(f"### 📋 தற்காலிகச் சரிபார்ப்புப் பட்டியல் ({len(st.session_state['temp_verified_records'])} தலைப்புகள்)")
                    temp_df = pd.DataFrame(st.session_state["temp_verified_records"])
                    display_cols = ["Title", "Author Name", "Language", "Total Qty", "Received", "Not Received", "Short / Extra", "Date"]
                    st.dataframe(temp_df[display_cols], use_container_width=True, hide_index=True)

                    col_clr, col_save = st.columns(2)
                    with col_clr:
                        if st.button("🗑️ அனைத்தையும் அழி", use_container_width=True):
                            st.session_state["temp_verified_records"] = []
                            st.rerun()

                    with col_save:
                        if st.button("💾 சீட்டில் சேமி", use_container_width=True):
                            if sheet_physically:
                                try:
                                    with st.spinner("சீட்டில் சேமிக்கப்படுகிறது..."):
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
                                                item["Date"],
                                            ])
                                    st.success("✅ Google Sheet-ல் தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                                    time.sleep(1)
                                    st.session_state["selected_vendor"] = None
                                    st.session_state["temp_verified_records"] = []
                                    st.session_state["vendor_key"] += 1
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ பிழை: {e}")
                            else:
                                st.error("❌ Google Sheet இணைப்பு கிடைக்கவில்லை!")

# --- TASK 2: VENDOR WISE BOOK DATA SYNC ---
elif menu_choice == "🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்":
    st.subheader("🔄 Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை ஒத்திசைவு (Sync)")
    st.info("💡 Physically verified சீட்டில் உள்ள பதிப்பகங்களில், இன்னும் ஒத்திசைவு செய்யப்படாதவை மட்டுமே கீழே தோன்றும்.")

    if sheet_physically is None or sheet_vendor_wise is None:
        st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!")
        st.stop()

    try:
        phys_rows = sheet_physically.get_all_values()
        phys_headers = [str(h).strip().lower() for h in phys_rows[0]] if phys_rows else []
        v_name_idx = next((i for i, h in enumerate(phys_headers) if "vendor" in h), 4)

        ws_data = sheet_vendor_wise.get_all_values()
        ws_headers = [str(h).strip().lower() for h in ws_data[0]]
        s_col = next((i for i, h in enumerate(ws_headers) if "received" in h and "not" not in h), 18)

        vendor_records_map = {}
        for p_row in phys_rows[1:]:
            if len(p_row) > v_name_idx and p_row[v_name_idx].strip():
                v_name = p_row[v_name_idx].strip()
                vendor_records_map.setdefault(v_name, []).append(p_row)

        title_idx = next((i for i, h in enumerate(phys_headers) if "title" in h), 1)
        rec_idx = next((i for i, h in enumerate(phys_headers) if "received" in h and "not" not in h), 6)

        unsynced_vendors = []
        for v_name, records in vendor_records_map.items():
            v_clean = clean_text(v_name)
            all_synced = True
            for p_row in records:
                p_title = clean_text(p_row[title_idx] if len(p_row) > title_idx else "")
                matched_and_filled = False
                for w_row in ws_data[1:]:
                    w_v_clean = clean_text(w_row[10] if len(w_row) > 10 else (w_row[9] if len(w_row) > 9 else ""))
                    w_t_clean = clean_text(w_row[4] if len(w_row) > 4 else "")
                    if v_clean in w_v_clean and p_title == w_t_clean:
                        if len(w_row) > s_col and str(w_row[s_col]).strip() != "":
                            matched_and_filled = True
                            break
                if not matched_and_filled:
                    all_synced = False
                    break

            if not all_synced:
                unsynced_vendors.append(v_name)

        if not unsynced_vendors:
            st.warning("⚠️ ஒத்திசைவு செய்ய வேண்டிய புதிய பதிப்பகங்கள் எதுவும் இல்லை.")
        else:
            st.markdown("---")
            selected_vendor_t2 = st.selectbox(
                "ஒத்திசைவு செய்ய வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",
                ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + unsynced_vendors,
                key="vendor_select_t2",
            )

            if selected_vendor_t2 != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                target_v_clean_t2 = clean_text(selected_vendor_t2)
                lang_idx = next((i for i, h in enumerate(phys_headers) if "language" in h), 2)
                author_idx = next((i for i, h in enumerate(phys_headers) if "author" in h), 3)
                total_qty_idx = next((i for i, h in enumerate(phys_headers) if "total" in h or h == "quantity"), 5)
                not_rec_idx = next((i for i, h in enumerate(phys_headers) if "not received" in h), 7)
                short_extra_idx = next((i for i, h in enumerate(phys_headers) if "short" in h), 8)
                date_idx = next((i for i, h in enumerate(phys_headers) if "date" in h), 9)

                vendor_phys_records = []
                display_records = []
                for p_row in phys_rows[1:]:
                    if len(p_row) > max(v_name_idx, title_idx, rec_idx):
                        if target_v_clean_t2 in clean_text(p_row[v_name_idx]):
                            vendor_phys_records.append(p_row)
                            display_records.append({
                                "Title": p_row[title_idx] if len(p_row) > title_idx else "",
                                "Author Name": p_row[author_idx] if len(p_row) > author_idx else "",
                                "Language": p_row[lang_idx] if len(p_row) > lang_idx else "",
                                "Total Qty": p_row[total_qty_idx] if len(p_row) > total_qty_idx else "",
                                "Received": p_row[rec_idx] if len(p_row) > rec_idx else "",
                                "Not Received": p_row[not_rec_idx] if len(p_row) > not_rec_idx else "",
                                "Short / Extra": p_row[short_extra_idx] if len(p_row) > short_extra_idx else "",
                                "Date": p_row[date_idx] if len(p_row) > date_idx else "",
                            })

                if vendor_phys_records:
                    disp_df = pd.DataFrame(display_records)
                    st.dataframe(disp_df, use_container_width=True, hide_index=True)

                    if st.button("🚀 இந்த பதிப்பகத்திற்கு மட்டும் ஒத்திசைவு செய்க (Sync)", use_container_width=True):
                        with st.spinner("ஒத்திசைக்கப்படுகிறது..."):
                            ws_data = sheet_vendor_wise.get_all_values()
                            ws_headers = [str(h).strip().lower() for h in ws_data[0]]

                            s_col = next((i + 1 for i, h in enumerate(ws_headers) if "received" in h and "not" not in h), 19)
                            t_col = next((i + 1 for i, h in enumerate(ws_headers) if "not received" in h or ("not" in h and "received" in h)), 20)
                            qty_col = next((i + 1 for i, h in enumerate(ws_headers) if h == "quantity"), 18)

                            cell_list = []
                            for p_row in vendor_phys_records:
                                title_val = p_row[title_idx]
                                try:
                                    rec_qty = int(p_row[rec_idx])
                                except ValueError:
                                    rec_qty = 0

                                target_t_clean = clean_text(title_val)
                                matching_rows = []
                                for r_idx, row_item in enumerate(ws_data[1:], start=2):
                                    row_v_clean = clean_text(row_item[10] if len(row_item) > 10 else (row_item[9] if len(row_item) > 9 else ""))
                                    row_t_clean = clean_text(row_item[4] if len(row_item) > 4 else "")
                                    if target_v_clean_t2 in row_v_clean and target_t_clean == row_t_clean:
                                        matching_rows.append((r_idx, row_item))

                                remaining_rec = rec_qty
                                for r_num, row_item in matching_rows:
                                    try:
                                        row_qty = int(row_item[qty_col - 1]) if len(row_item) >= qty_col and row_item[qty_col - 1] != "" else 1
                                    except ValueError:
                                        row_qty = 1

                                    if remaining_rec >= row_qty:
                                        val_s = str(row_qty)
                                        val_t = "0"
                                        remaining_rec -= row_qty
                                    elif remaining_rec > 0:
                                        val_s = str(remaining_rec)
                                        val_t = str(row_qty - remaining_rec)
                                        remaining_rec = 0
                                    else:
                                        val_s = "0"
                                        val_t = str(row_qty)

                                    cell_list.append(Cell(row=r_num, col=s_col, value=val_s))
                                    cell_list.append(Cell(row=r_num, col=t_col, value=val_t))

                            if cell_list:
                                sheet_vendor_wise.update_cells(cell_list)

                            st.success(f"✅ **{selected_vendor_t2}** பதிப்பகத்தின் தரவுகள் வெற்றி பெற ஒத்திசைக்கப்பட்டன!")
                            time.sleep(1.5)
                            st.rerun()
    except Exception as e:
        st.error(f"❌ பிழை: {e}")

# --- TASK 3: TOTAL VENDOR DETAILS (480) ---
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")

    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு கிடைக்கவில்லை!")
    else:
        vendor_list = []
        for _, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            vendor_name = col_c if col_c and col_c.lower() != "nan" else col_b
            if vendor_name and vendor_name.lower() != "nan" and vendor_name not in vendor_list:
                vendor_list.append(vendor_name)

        vendor_list = sorted(vendor_list)

        st.markdown("---")
        st.markdown("### 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் (Select Publisher)")

        selected_vendor_raw_t3 = st.selectbox(
            "பதிப்பகத்தின் பெயரினை உள்ளீடு செய்யவும் அல்லது தேர்ந்தெடுக்கவும்",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --", "-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"] + vendor_list,
            key=f"vendor_select_t3_{st.session_state['vendor_t3_key']}",
        )

        if selected_vendor_raw_t3 != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            if st.session_state["selected_vendor_t3"] != selected_vendor_raw_t3:
                st.session_state["selected_vendor_t3"] = selected_vendor_raw_t3

        if st.session_state["selected_vendor_t3"]:
            selected_vendor_t3 = st.session_state["selected_vendor_t3"]

            if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்க", use_container_width=True):
                st.session_state["selected_vendor_t3"] = None
                st.session_state["vendor_t3_key"] += 1
                st.rerun()

            if selected_vendor_t3 == "-- அனைத்து பதிப்பாளர்களும் (All Publishers) --":
                st.markdown("### 📋 அனைத்து பதிப்பகங்களின் பொதுப் பட்டியல்")
                st.dataframe(vendor_df, use_container_width=True, hide_index=True)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    vendor_df.to_excel(writer, index=False, sheet_name="Vendor Summary")
                excel_data = output.getvalue()

                st.download_button(
                    label="📥 அனைத்து பதிப்பாளர் பட்டியலைப் பதிவிறக்குக (Excel)",
                    data=excel_data,
                    file_name="All_Vendors_Summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                target_vendor_clean_t3 = clean_text(selected_vendor_t3)
                vendor_mask = (book_df.iloc[:, 9].apply(clean_text) == target_vendor_clean_t3) | (book_df.iloc[:, 10].apply(clean_text) == target_vendor_clean_t3)
                filtered_books_t3 = book_df[vendor_mask]

                if filtered_books_t3.empty:
                    st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
                else:
                    total_titles = len(filtered_books_t3)
                    total_qty = int(filtered_books_t3["Quantity"].sum()) if "Quantity" in filtered_books_t3.columns else 0

                    lang_col_idx = next((i for i, col in enumerate(filtered_books_t3.columns) if "lang" in str(col).lower()), None)
                    tamil_count = 0
                    english_count = 0
                    if lang_col_idx is not None:
                        lang_series = filtered_books_t3.iloc[:, lang_col_idx].astype(str)
                        tamil_count = int(lang_series.str.contains("tamil", case=False, na=False).sum())
                        english_count = int(lang_series.str.contains("english", case=False, na=False).sum())

                    col1, col2, col3, col4 = st.columns(4)
                    col1.metric("📚 மொத்தத் தலைப்புகள்", total_titles)
                    col2.metric("📦 மொத்தப் படிகள்", total_qty)
                    col3.metric("🇮🇳 தமிழ் நூல்கள்", tamil_count)
                    col4.metric("🇬🇧 ஆங்கில நூல்கள்", english_count)

                    st.markdown("---")
                    st.markdown(f"### 📋 {selected_vendor_t3} - நூல்களின் முழு விவரங்கள்")
                    st.dataframe(filtered_books_t3, use_container_width=True)

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        filtered_books_t3.to_excel(writer, index=False, sheet_name="Vendor Details")
                    excel_data = output.getvalue()

                    st.download_button(
                        label=f"📥 '{selected_vendor_t3}' தரவைப் பதிவிறக்குக (Excel)",
                        data=excel_data,
                        file_name=f"{selected_vendor_t3}_Vendor_Details.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

# --- TASK 4: LIBRARY DISTRIBUTION (103) ---
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")

    if book_df is None or book_df.empty:
        st.error("❌ புத்தகத் தரவுகள் கிடைக்கவில்லை!")
    else:
        base_df = book_df.copy()
        drop_cols = [c for c in base_df.columns if any(k in str(c).lower() for k in ["v s.no", "temp no", "v.s.no", "temp"])]
        base_df = base_df.drop(columns=drop_cols, errors="ignore")

        col_map_lower = {str(c).lower().strip(): c for c in base_df.columns}
        lib_id_col = next((col_map_lower[c] for c in col_map_lower if "librarianid" in c or "lib id" in c or "librarian" in c), base_df.columns[11] if len(base_df.columns) > 11 else None)
        lib_name_col = next((col_map_lower[c] for c in col_map_lower if "library name" in c), base_df.columns[12] if len(base_df.columns) > 12 else None)
        lib_type_col = next((col_map_lower[c] for c in col_map_lower if "library type" in c), base_df.columns[10] if len(base_df.columns) > 10 else None)

        lib_dict = {}
        lib_name_list = []
        if lib_name_col and lib_id_col:
            for _, r in base_df.dropna(subset=[lib_name_col, lib_id_col]).iterrows():
                l_name = str(r[lib_name_col]).strip()
                l_id = str(r[lib_id_col]).strip()
                if l_name and l_name.lower() != "nan":
                    lib_dict[l_name] = l_id
                    if l_name not in lib_name_list:
                        lib_name_list.append(l_name)

        lib_name_list = sorted(lib_name_list)

        st.markdown("---")
        st.markdown("### 🏢 நூலகத்தைத் தேர்ந்தெடுக்கவும் (Select Library)")
        
        selected_library_raw = st.selectbox(
            "நூலகத்தின் பெயரினை உள்ளீடு செய்யவும் அல்லது தேர்ந்தெடுக்கவும்",
            ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --", "-- அனைத்து நூலகங்களும் (All Libraries) --"] + lib_name_list,
            key=f"library_select_{st.session_state['library_key']}",
        )

        if selected_library_raw != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            if st.session_state["selected_library"] != selected_library_raw:
                st.session_state["selected_library"] = selected_library_raw

        if st.session_state["selected_library"]:
            selected_library = st.session_state["selected_library"]
            
            if st.button("🔄 மற்றொரு நூலகத்தைத் தேர்ந்தெடுக்க", use_container_width=True):
                st.session_state["selected_library"] = None
                st.session_state["library_key"] += 1
                st.rerun()

            if selected_library == "-- அனைத்து நூலகங்களும் (All Libraries) --":
                filtered_lib_df = base_df.copy()
            else:
                target_lib_id = lib_dict.get(selected_library)
                if target_lib_id and lib_id_col:
                    filtered_lib_df = base_df[base_df[lib_id_col].astype(str).str.strip() == target_lib_id].copy()
                elif lib_name_col:
                    filtered_lib_df = base_df[base_df[lib_name_col].astype(str).str.strip() == selected_library].copy()
                else:
                    filtered_lib_df = base_df.copy()

            if not filtered_lib_df.empty:
                reordered_cols = []
                if lib_id_col in filtered_lib_df.columns: reordered_cols.append(lib_id_col)
                if lib_name_col in filtered_lib_df.columns: reordered_cols.append(lib_name_col)
                if lib_type_col in filtered_lib_df.columns and lib_type_col not in reordered_cols: reordered_cols.append(lib_type_col)
                
                other_cols = [c for c in filtered_lib_df.columns if c not in reordered_cols]
                filtered_lib_df = filtered_lib_df[reordered_cols + other_cols].copy()
                
                if "S.No" in filtered_lib_df.columns:
                    filtered_lib_df = filtered_lib_df.drop(columns=["S.No"])
                filtered_lib_df.insert(0, "S.No", range(1, len(filtered_lib_df) + 1))

                total_titles = len(filtered_lib_df)
                total_qty = int(filtered_lib_df["Quantity"].sum()) if "Quantity" in filtered_lib_df.columns else 0

                lang_col_idx = next((i for i, col in enumerate(filtered_lib_df.columns) if "lang" in str(col).lower()), None)
                tamil_count = 0
                english_count = 0
                if lang_col_idx is not None:
                    lang_series = filtered_lib_df.iloc[:, lang_col_idx].astype(str)
                    tamil_count = int(lang_series.str.contains("tamil", case=False, na=False).sum())
                    english_count = int(lang_series.str.contains("english", case=False, na=False).sum())

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("📚 மொத்தத் தலைப்புகள்", total_titles)
                col2.metric("📦 மொத்தப் படிகள்", total_qty)
                col3.metric("🇮🇳 தமிழ் நூல்கள்", tamil_count)
                col4.metric("🇬🇧 ஆங்கில நூல்கள்", english_count)

                st.markdown("---")
                title_header_text = f"📋 {selected_library} - நூலகத்தின் முழு விவரங்கள்" if selected_library != "-- அனைத்து நூலகங்களும் (All Libraries) --" else "📋 அனைத்து நூலகங்களின் விநியோக விவரங்கள்"
                st.markdown(f"### {title_header_text}")
                st.dataframe(filtered_lib_df, use_container_width=True, hide_index=True)

                st.markdown("---")
                st.markdown("### 📥 தரவிறக்கம் செய்யும் வசதி")
                btn_col1, btn_col2 = st.columns(2)

                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    filtered_lib_df.to_excel(writer, index=False, sheet_name="Library Distribution")
                excel_data = output.getvalue()

                file_prefix = re.sub(r"[^\w\s]", "", selected_library).strip() if selected_library != "-- அனைத்து நூலகங்களும் (All Libraries) --" else "All_Libraries"

                with btn_col1:
                    st.download_button(
                        label="📊 Excel கோப்பாக பதிவிறக்குக",
                        data=excel_data,
                        file_name=f"{file_prefix}_Distribution.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )

                csv_data = filtered_lib_df.to_csv(index=False).encode('utf-8-sig')
                with btn_col2:
                    st.download_button(
                        label="📄 CSV கோப்பாக பதிவிறக்குக",
                        data=csv_data,
                        file_name=f"{file_prefix}_Distribution.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
            else:
                st.warning("⚠️ தரவுகள் எதுவும் இல்லை.")

# --- TASK 5: ACCESSION NUMBERS MANAGEMENT ---
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ Accession எண்கள் மேலாண்மை")
    st.info("💡 நூலகளுக்கான Accession எண்களை நிர்வகிக்கும் பகுதி.")
    st.markdown("---")
    st.success("✅ இந்த பிரிவு பயன்பாட்டிற்குத் தயாராக உள்ளது. கூடுதல் விவரங்களை விரைவில் சேர்க்கலாம்.")
