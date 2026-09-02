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

st.set_page_config(
    page_title="மாவட்ட நூலக ஆணைக்குழு, கிருஷ்ணகிரி",
    page_icon="📚",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans Tamil', sans-serif !important;
}

.stApp {
    background: linear-gradient(135deg, #064e3b, #022c22);
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

h1 {
    font-size: 24px !important;
    font-weight: 800 !important;
    padding: 14px 18px !important;
    border-radius: 12px;
    color: #fff !important;
    background: linear-gradient(135deg, #059669, #047857) !important;
    box-shadow: 0 4px 12px rgba(6,78,59,0.3);
    text-align: center;
    margin-bottom: 15px !important;
}

h2, h3 {
    color: #064e3b !important;
    font-weight: 700 !important;
}

p, span, label, div {
    font-size: 15px !important;
    color: #111827;
}

.profile-card, .book-info-card {
    background: #ffffff;
    border: 1.5px solid #a7f3d0;
    box-shadow: 0 4px 10px rgba(0,0,0,0.06);
}

.profile-card {
    padding: 12px 16px;
    border-radius: 10px;
    color: #064e3b;
    background: #ecfdf5;
}

.book-info-card {
    border-left: 6px solid #047857;
    border-radius: 10px;
    padding: 14px 16px;
    line-height: 2.0;
    margin: 12px 0 16px;
    background: #ffffff;
}

.login-card-wrapper {
    background: #ffffff;
    border-radius: 16px;
    padding: 30px 25px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    border: 1.5px solid #a7f3d0;
    max-width: 420px;
    margin: 40px auto;
}

.login-header-box {
    text-align: center;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    border: 1.5px solid #a7f3d0;
    border-radius: 12px;
    padding: 15px;
    margin-bottom: 20px;
}

.login-header-icon {
    font-size: 32px;
    margin-bottom: 4px;
}

.login-title {
    color: #064e3b;
    font-size: 18px;
    font-weight: 800;
    line-height: 1.4;
}

.stButton > button, .stDownloadButton > button {
    min-height: 44px !important;
    border-radius: 8px !important;
    font-size: 15px !important;
    font-weight: 700 !important;
    color: #ffffff !important;
    background: linear-gradient(135deg, #059669, #047857) !important;
    box-shadow: 0 3px 8px rgba(0,0,0,0.12) !important;
    border: none !important;
    width: 100% !important;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background: linear-gradient(135deg, #047857, #064e3b) !important;
    color: #fff !important;
}

button[kind="secondary"] {
    background: linear-gradient(135deg, #ecfdf5, #d1fae5) !important;
    color: #064e3b !important;
    box-shadow: 0 2px 6px rgba(6,78,59,0.1) !important;
    font-weight: 700 !important;
    border: 1.2px solid #a7f3d0 !important;
}
button[kind="secondary"]:hover {
    background: linear-gradient(135deg, #d1fae5, #a7f3d0) !important;
    color: #064e3b !important;
}
button[kind="primary"] {
    background: linear-gradient(135deg, #064e3b, #047857) !important;
    box-shadow: 0 3px 10px rgba(6,78,59,0.3) !important;
    border: 1.2px solid #064e3b !important;
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

def make_session_token(role):
    return hmac.new(app_secret().encode(), role.encode(), hashlib.sha256).hexdigest()

def verify_session_token(role, token):
    return bool(role and token) and hmac.compare_digest(make_session_token(role), str(token))

USERS_DATABASE = {
    "Admin": {"password_hash": hash_password("Hari@@1979"), "name": "முதன்மை நிர்வாகி (Admin)"},
    "DCL Staff": {"password_hash": hash_password("123456"), "name": "DCL Staff"},
    "Librarian": {"password_hash": hash_password("123456789"), "name": "Librarian"},
}

def authenticate_user(role_key, password):
    user = USERS_DATABASE.get(role_key)
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "",
    "current_page": "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", "verified_records": [],
}.items():
    st.session_state.setdefault(key, default)

if not st.session_state["logged_in"]:
    query_role = st.query_params.get("role")
    query_token = st.query_params.get("token")
    if query_role in USERS_DATABASE and verify_session_token(query_role, query_token):
        user = USERS_DATABASE[query_role]
        st.session_state.update(
            logged_in=True, user_role=query_role, user_name=user["name"]
        )

def show_login_page():
    st.markdown("""
    <div class="login-card-wrapper">
        <div class="login-header-box">
            <div class="login-header-icon">📚</div>
            <div class="login-title">மாவட்ட நூலக ஆணைக்குழு,<br>கிருஷ்ணகிரி</div>
        </div>
    """, unsafe_allow_html=True)
    
    with st.form("secure_login_form"):
        selected_role = st.selectbox("பயனர் வகை (User)", ["-- தேர்ந்தெடுக்கவும் --", "Admin", "DCL Staff", "Librarian"])
        password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
        submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        
    st.markdown("</div>", unsafe_allow_html=True)
    
    if submitted:
        if selected_role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
        else:
            user = authenticate_user(selected_role, password)
            if not user:
                st.error("❌ தவறான கடவுச்சொல்!")
            else:
                st.session_state.update(
                    logged_in=True, user_role=selected_role, user_name=user["name"]
                )
                st.query_params.update(role=selected_role, token=make_session_token(selected_role))
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

def get_col(df, possible_names):
    for col in df.columns:
        if str(col).strip() in possible_names:
            return col
    for col in df.columns:
        for name in possible_names:
            if name.lower() in str(col).lower():
                return col
    return possible_names[0]

def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"

def excel_bytes(frame, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name=str(sheet_name)[:31])
    return output.getvalue()

def csv_bytes(frame):
    return frame.to_csv(index=False).encode("utf-8-sig")

def download_excel_csv_panel(frame, prefix, sheet_name):
    st.markdown("### 📥 Excel / CSV அறிக்கை பதிவிறக்க வசதிகள்")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📊 Excel பதிவிறக்கம்", excel_bytes(frame, sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True, key=f"xlsx_{prefix}")
    with col2:
        st.download_button("📄 CSV பதிவிறக்கம் (Tamil Support)", csv_bytes(frame), f"{prefix}.csv", "text/csv", use_container_width=True, key=f"csv_{prefix}")

menu_items = [
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", 
    "🏢 2. சரிபார்க்கப்பட்ட பதிப்பாளர்"
]

if st.session_state["current_page"] not in menu_items:
    st.session_state["current_page"] = menu_items[0]

st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")

info, logout = st.columns([3.2, 0.8])
with info:
    st.markdown(f'<div class="profile-card">👤 <b>பயனர்:</b> {st.session_state["user_name"]} &nbsp;|&nbsp; <b>வகை:</b> {st.session_state["user_role"]}</div>', unsafe_allow_html=True)
with logout:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

st.markdown("---")

MENU_SHORT_LABELS = {
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு": "📥 சரிபார்ப்பு",
    "🏢 2. சரிபார்க்கப்பட்ட பதிப்பாளர்": "🏢 சரிபார்க்கப்பட்ட பதிப்பாளர்",
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

st.markdown("---")

if st.session_state["current_page"] == menu_items[0]:
    st.subheader("🔎 பதிப்பாளர் வாரியான நூல்கள் சரிபார்ப்பு")
    if df_summary is None or df_summary.empty or df_books is None or df_books.empty:
        st.error("❌ தரவுகள் கிடைக்கவில்லை!")
        st.stop()
        
    c_pub = get_col(df_books, ["Publication Name", "Publisher", "Vendor Name", "Publication Name / Vendor Name"])
    c_title = get_col(df_books, ["Title", "Book Title", "Book Name", "Name"])
    c_author = get_col(df_books, ["Author Name", "Author"])
    c_isbn = get_col(df_books, ["ISBN", "ISBN No", "ISBN Number"])
    c_lang = get_col(df_books, ["Language"])
    c_price = get_col(df_books, ["Price", "Amount"])
    c_qty = get_col(df_books, ["Quantity", "Qty", "Count", "No of Libraries", "Libraries Count"])

    if c_pub in df_books.columns:
        publishers = sorted(df_books[c_pub].dropna().unique().tolist())
        selected_publisher = st.selectbox(
            "1. பதிப்பாளரைத் தேர்ந்தெடுக்கவும் (Select Publisher):",
            ["-- தேர்ந்தெடுக்கவும் --"] + publishers,
            key="pub_select_dropdown"
        )
        
        if not selected_publisher.startswith("-- தேர்ந்தெடுக்கவும் --"):
            pub_filtered_books = df_books[df_books[c_pub] == selected_publisher]
        else:
            pub_filtered_books = df_books
    else:
        pub_filtered_books = df_books

    grouped_df = pub_filtered_books.groupby(c_title, as_index=False).agg({
        c_pub: "first",
        c_author: "first",
        c_isbn: "first" if c_isbn in pub_filtered_books.columns else lambda x: "N/Class",
        c_lang: "first",
        c_price: "first",
        c_qty: "sum"
    }).rename(columns={
        c_pub: "பதிப்பகம்", 
        c_title: "தலைப்பு", 
        c_author: "ஆசிரியர்",
        c_isbn: "ISBN",
        c_price: "விலை", 
        c_qty: "அனுமதிக்கப்பட்ட எண்ணிக்கை"
    })

    st.markdown("2. புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்:")
    
    if not grouped_df.empty:
        book_titles = ["-- தேர்ந்தெடுக்கவும் --"] + grouped_df["தலைப்பு"].tolist()
        selected_book_title = st.selectbox(
            "புத்தகத் தலைப்பு தேர்வு:",
            book_titles,
            label_visibility="collapsed",
            key="auto_book_title_select"
        )
        
        if selected_book_title != "-- தேர்ந்தெடுக்கவும் --":
            b_row = grouped_df[grouped_df["தலைப்பு"] == selected_book_title].iloc[0]
            orig_qty = int(b_row["அனுமதிக்கப்பட்ட எண்ணிக்கை"])
            author_val = b_row.get("ஆசிரியர்", "N/A")
            isbn_val = b_row.get("ISBN", "N/A")
            price_val = b_row.get("விலை", 0)
            
            st.markdown(f"""
            <div class="book-info-card">
                📖 <b>தலைப்பு:</b> {b_row['தலைப்பு']}<br>
                🏢 <b>பதிப்பகம்:</b> {b_row['பதிப்பகம்']}<br>
                ✍️ <b>ஆசிரியர்:</b> {author_val}<br>
                🏷️ <b>ISBN:</b> {isbn_val}<br>
                💰 <b>விலை/தொகை:</b> ₹{price_val}<br>
                📚 <b>நூலகங்களின் எண்ணிக்கை (அனுமதிக்கப்பட்டது):</b> {orig_qty}
            </div>
            """, unsafe_allow_html=True)
            
            with st.form("verify_single_form"):
                rec_qty = st.number_input("பெறப்பட்ட புத்தகங்களின் எண்ணிக்கை (Received Quantity)", min_value=0, max_value=orig_qty, value=orig_qty, step=1)
                submitted_rec = st.form_submit_button("💾 இந்தத் தலைப்பைச் சரிபார்த்துச் சேமி", use_container_width=True)
                
                if submitted_rec:
                    st.session_state["verified_records"].append({
                        "தலைப்பு": b_row["தலைப்பு"],
                        "பதிப்பகம்": b_row["பதிppகம்"] if "பதிppகம்" in b_row else b_row["பதிப்பகம்"],
                        "ஆசிரியர்": author_val,
                        "ISBN": isbn_val,
                        "மொழி": b_row[c_lang],
                        "விலை": price_val,
                        "அனுமதிக்கப்பட்ட எண்ணிக்கை": orig_qty,
                        "பெறப்பட்ட எண்ணிக்கை": rec_qty,
                        "பெறப்படாத எண்ணிக்கை": orig_qty - rec_qty,
                        "தேதி": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
                    })
                    st.success(f"✅ '{b_row['தலைப்பு']}' வெற்றிகரமாகச் சேமிக்கப்பட்டது!")
                    st.rerun()
    else:
        st.info("ℹ️ தேர்ந்தெடுக்கப்பட்ட பதிப்பகத்திற்குப் புத்தகங்கள் எதுவும் கிடைக்கவில்லை.")
        
    if st.session_state["verified_records"]:
        st.markdown("---")
        st.subheader("📋 இதுவரை சரிபார்க்கப்பட்ட நூல்களின் தற்காலிகப் பட்டியல்")
        v_df = pd.DataFrame(st.session_state["verified_records"])
        st.dataframe(v_df, use_container_width=True, hide_index=True)
        
        if st.button("🗑️ தற்காலிகப் பட்டியலை முழுமையாக அழிக்க", use_container_width=True):
            st.session_state["verified_records"] = []
            st.rerun()

elif len(menu_items) > 1 and st.session_state["current_page"] == menu_items[1]:
    st.subheader("🏢 சரிபார்க்கப்பட்ட பதிப்பாளர் வாரியான அறிக்கைகள்")
    if not st.session_state["verified_records"]:
        st.info("ℹ️ இதுவரை எந்தப் பதிப்பக நூல்களும் சரிபார்க்கப்பட்டுச் சேமிக்கப்படவில்லை. முதலாவது பக்கத்தில் சரிபார்க்கவும்.")
    else:
        v_df = pd.DataFrame(st.session_state["verified_records"])
        verified_publishers = sorted(v_df["பதிப்பகம்"].dropna().unique().tolist())
        
        selected_v_pub = st.selectbox(
            "🔎 சரிபார்க்கப்பட்ட பதிப்பாளரைத் தேர்ந்தெடுக்கவும்:",
            ["-- தேர்ந்தெடுக்கவும் --"] + verified_publishers,
            key="verified_pub_filter"
        )
        
        if selected_v_pub.startswith("-- தேர்ந்தெடுக்கவும் --"):
            filtered_v_df = v_df
            file_prefix = "All_Verified_Publishers"
        else:
            filtered_v_df = v_df[v_df["பதிப்பகம்"] == selected_v_pub]
            file_prefix = safe_name(selected_v_pub) + "_Verified_Report"
            
        st.markdown(f"**தேர்ந்தெடுக்கப்பட்ட பதிப்பகத்தின் சரிபார்க்கப்பட்ட விவரங்கள் ({len(filtered_v_df)} தலைப்புகள்):**")
        st.dataframe(filtered_v_df, use_container_width=True, hide_index=True)
        
        download_excel_csv_panel(filtered_v_df, file_prefix, "Verified Books Report")
