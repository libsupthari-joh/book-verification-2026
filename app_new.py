import hashlib
import hmac
from datetime import datetime
import pandas as pd
import streamlit as st
import psycopg2

st.set_page_config(
    page_title="மாவட்ட மைய நூலகம், கிருஷ்ணகிரி",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_URL = "postgresql://neondb_owner:npg_vA4w9qUFJheu@ep-odd-pine-b39tu9yu-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans Tamil', sans-serif !important; }
.stApp { background: #f8fafc; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

.top-header-container {
    background: linear-gradient(135deg, #064e3b, #022c22);
    padding: 16px 22px;
    border-radius: 12px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 15px rgba(6,78,59,0.2);
    margin-bottom: 20px;
}
.header-title { font-size: 20px; font-weight: 800; color: #ffffff; }
.header-subtitle { font-size: 13px; color: #a7f3d0; font-weight: 600; }
.login-top-container { display: flex; justify-content: center; align-items: flex-start; padding-top: 30px; }
.login-card-wrapper { background: #ffffff; border-radius: 16px; padding: 22px 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); border: 1.5px solid #a7f3d0; width: 100%; max-width: 380px; }
.login-header-box { text-align: center; background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #a7f3d0; border-radius: 10px; padding: 10px; margin-bottom: 12px; }
.login-title { color: #064e3b; font-size: 15px; font-weight: 800; }

.ticker-container { 
    background: linear-gradient(135deg, #f0fdf4, #dcfce7); 
    border: 1.5px solid #86efac; 
    padding: 8px 12px; 
    border-radius: 10px; 
    color: #065f46; 
    font-weight: 700; 
    font-size: 13px; 
    display: flex; 
    align-items: center; 
    box-shadow: 0 2px 8px rgba(6, 95, 70, 0.08); 
    margin-bottom: 20px; 
    overflow: hidden; 
    white-space: nowrap; 
}
.ticker-badge { 
    background: #065f46; 
    color: white; 
    padding: 3px 10px; 
    border-radius: 6px; 
    font-size: 12px; 
    margin-right: 15px; 
    display: flex; 
    align-items: center; 
    gap: 5px; 
    flex-shrink: 0; 
    z-index: 2;
}
.marquee-text {
    display: inline-block;
    white-space: nowrap;
    animation: marquee 25s linear infinite;
}
.marquee-text:hover {
    animation-play-state: paused;
}
@keyframes marquee {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

/* ---- Beautified menu / general buttons ---- */
.stButton>button {
    border-radius: 12px !important;
    border: 1.5px solid #a7f3d0 !important;
    background: #ffffff !important;
    color: #065f46 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    white-space: pre-line !important;
    line-height: 1.4 !important;
    padding: 10px 6px !important;
    min-height: 62px !important;
    box-shadow: 0 2px 6px rgba(6,95,70,0.07) !important;
    transition: all 0.18s ease-in-out !important;
}
.stButton>button:hover {
    background: #ecfdf5 !important;
    border-color: #10b981 !important;
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(6,95,70,0.18) !important;
    color: #047857 !important;
}
.stButton>button:active {
    transform: translateY(0px);
}
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #059669, #047857) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 6px 14px rgba(5,150,105,0.35) !important;
}
.stButton>button[kind="primary"]:hover {
    background: linear-gradient(135deg, #047857, #065f46) !important;
    color: #ffffff !important;
}
.menu-row-label {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 4px 0 6px 2px;
}
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

USERS_DATABASE = {
    "Admin": {"password_hash": hash_password("Hari@@1979"), "name": "முதன்மை நிர்வாகி (Admin)"},
    "DCL Staff": {"password_hash": hash_password("123456"), "name": "DCL Staff"},
    "Librarian": {"password_hash": hash_password("123456789"), "name": "Librarian"},
}

# ---------------------------------------------------------------------------
# ROLE-WISE MENU ACCESS CONTROL
# Admin -> அனைத்து மெனுக்களும் (full access)
# DCL Staff -> "பிரிக்க" மற்றும் "அறிக்கைகள்" மட்டும்
# Librarian -> "நூலகர் பார்வை ஆண்டு" மட்டும்
# ---------------------------------------------------------------------------
ROLE_MENU_ACCESS = {
    "Admin": None,  # None => எல்லா மெனுக்களுக்கும் அனுமதி
    "DCL Staff": ["பிரிக்க", "அறிக்கைகள்"],
    "Librarian": ["நூலகர் பார்வை ஆண்டு"],
}

def authenticate_user(role_key, password):
    user = USERS_DATABASE.get(role_key)
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

# Database Initialization for Submitted Reports
def init_submitted_table():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS submitted_reports (
                id SERIAL PRIMARY KEY,
                publisher TEXT,
                title TEXT,
                author TEXT,
                price TEXT,
                accepted_price TEXT,
                isbn TEXT,
                required_qty INT,
                received_qty INT,
                date TEXT
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"❌ Table creation error: {e}")

init_submitted_table()

def load_submitted_reports_from_db():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT id as \"Id\", publisher as \"Publisher\", title as \"Title\", author as \"Author\", price as \"Price\", accepted_price as \"Accepted Price\", isbn as \"ISBN\", required_qty as \"Required Qty\", received_qty as \"Received Qty\", date as \"Date\" FROM submitted_reports;", con=conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        return []

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "",
    "current_menu": None, "temp_distributed_list": [], 
    "submitted_reports": load_submitted_reports_from_db(),
    "dispatch_records": [], "librarian_records": []
}.items():
    st.session_state.setdefault(key, default)

def show_login_page():
    st.markdown("""
    <style>.stApp { background: linear-gradient(135deg, #064e3b, #022c22) !important; }</style>
    <div class="login-top-container">
        <div class="login-card-wrapper">
            <div class="login-header-box">
                <div style="font-size: 22px; margin-bottom: 2px;">📚</div>
                <div class="login-title">மாவட்ட மைய நூலகம்<br>கிருஷ்ணகிரி</div>
            </div>
    """, unsafe_allow_html=True)
    
    with st.form("secure_login_form"):
        selected_role = st.selectbox("பயனர் வகை (User)", ["-- தேர்ந்தெடுக்கவும் --", "Admin", "DCL Staff", "Librarian"])
        password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
        submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if submitted:
        if selected_role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
        else:
            user = authenticate_user(selected_role, password)
            if not user:
                st.error("❌ தவறான கடவுச்சொல்!")
            else:
                st.session_state.update(logged_in=True, user_role=selected_role, user_name=user["name"])
                st.session_state["current_menu"] = None
                st.rerun()

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

st.markdown("""
<div class="top-header-container">
    <div>
        <div class="header-title">📚 மாவட்ட மைய நூலகம்</div>
        <div class="header-subtitle">கிருஷ்ணகிரி — புதிய நூல்கள் பகிர்மானம் 2026-27</div>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 8px; font-size: 13px;">
            👤 {} ({})
        </span>
    </div>
</div>
""".format(st.session_state["user_name"], st.session_state["user_role"]), unsafe_allow_html=True)

col_logout = st.columns([11, 1])
with col_logout[1]:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["current_menu"] = None
        st.rerun()

ALL_MENU_OPTIONS = [
    ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
    ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி")
]

# ---------------------------------------------------------------------------
# பயனர் பங்கிற்கு ஏற்ப மெனு வடிகட்டுதல் (role-based menu filtering)
# ---------------------------------------------------------------------------
allowed_labels = ROLE_MENU_ACCESS.get(st.session_state["user_role"])
if allowed_labels is None:
    menu_options = ALL_MENU_OPTIONS
else:
    menu_options = [item for item in ALL_MENU_OPTIONS if item[1] in allowed_labels]

# கிடைக்கும் மெனு பட்டன்களை 6-வீதம் வரிசைகளாக அமைத்தல்
menu_rows = [menu_options[i:i + 6] for i in range(0, len(menu_options), 6)]
btn_counter = 0
for row in menu_rows:
    cols = st.columns(len(row))
    for col, (icon, label) in zip(cols, row):
        with col:
            btn_type = "primary" if st.session_state["current_menu"] == label else "secondary"
            if st.button(f"{icon}\n{label}", key=f"menu_btn_{btn_counter}", use_container_width=True, type=btn_type):
                st.session_state["current_menu"] = label
                st.rerun()
        btn_counter += 1

# பாதுகாப்பு சரிபார்ப்பு: பங்கு மாறினாலோ / session state பழையதாக இருந்தாலோ,
# அனுமதிக்கப்படாத மெனுவில் தங்கிவிடாமல் தடுக்கும் (defence-in-depth)
if allowed_labels is not None and st.session_state["current_menu"] not in allowed_labels:
    st.session_state["current_menu"] = None

st.markdown("---")

total_submitted_count = sum([int(item.get("Received Qty", 0)) for item in st.session_state['submitted_reports']])
today_str = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="ticker-container">
    <div class="ticker-badge">🔴 Live News</div>
    <div style="overflow: hidden; width: 100%;">
        <div class="marquee-text">
            📚 பெறப்பட்ட நூல்கள் : <b>45,305</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ✅ பிரிக்கப்பட்டது : <b>{total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ⏳ மீதம் பிரிக்க வேண்டியது : <b>{45305 - total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            📤 அனுப்பப்பட்டது : <b>0</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            🗓️ இன்று ({today_str}) பிரிக்கப்பட்டது : <b>{total_submitted_count}</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

current = st.session_state["current_menu"]

@st.cache_data
def load_neon_database():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT * FROM books;", con=conn)
        conn.close()
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"❌ டேட்டாபேஸ் இணைப்பில் பிழை: {e}")
    return pd.DataFrame()

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றைத் தேர்வு செய்யவும்.")

elif current == "பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    
    neon_df = load_neon_database()

    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
        author_col = next((c for c in neon_df.columns if 'author' in c), None)
        price_col = next((c for c in neon_df.columns if c == 'price'), None)
        accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'accepted' in c or 'rate' in c or 'offer' in c), None)
        isbn_col = next((c for c in neon_df.columns if 'isbn' in c), None)

        all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []

        selected_publisher = st.selectbox(
            "🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers,
            key="publisher_dropdown"
        )

        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            pub_filtered_df = neon_df[neon_df[pub_col] == selected_publisher].copy()
            
            total_pub_titles_count = len(pub_filtered_df[title_col].dropna().unique())
            total_pub_books_count = len(pub_filtered_df)
            
            submitted_titles = [item["Title"] for item in st.session_state["submitted_reports"] if item["Publisher"] == selected_publisher]
            temp_added_titles = [item["Title"] for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher]
            
            excluded_titles = set(submitted_titles + temp_added_titles)
            available_filtered_df = pub_filtered_df[~pub_filtered_df[title_col].isin(excluded_titles)]
            all_titles = sorted(available_filtered_df[title_col].dropna().unique().tolist())

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #34d399; padding: 14px 18px; border-radius: 10px; margin: 10px 0 15px 0;">
                <div style="font-size: 15px; font-weight: 800; color: #064e3b; margin-bottom: 8px;">
                    🏢 பதிப்பகம்: {selected_publisher} — சுருக்க விவரம்
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 20px; font-size: 14px; color: #065f46; font-weight: 600;">
                    <div>📚 மொத்த தலைப்புகள்: <b>{total_pub_titles_count}</b></div>
                    <div>📦 மொத்த நூல்கள்: <b>{total_pub_books_count}</b></div>
                    <div>✅ சமர்ப்பிக்கப்பட்டது: <b>{len(submitted_titles)}</b></div>
                    <div>⏳ மீதம் உள்ளவை: <b>{len(all_titles)}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if all_titles:
                selected_title = st.selectbox(
                    "📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும் (Select Book Title):",
                    ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles,
                    key="title_dropdown"
                )

                if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_row_df = pub_filtered_df[pub_filtered_df[title_col] == selected_title]
                    if not title_row_df.empty:
                        title_row = title_row_df.iloc[0]
                        author_name = str(title_row[author_col]) if author_col and author_col in title_row and pd.notna(title_row[author_col]) else "-"
                        book_price = str(title_row[price_col]) if price_col and price_col in title_row and pd.notna(title_row[price_col]) else "0"
                        
                        accepted_price = "0"
                        if accepted_price_col and accepted_price_col in title_row and pd.notna(title_row[accepted_price_col]):
                            accepted_price = str(title_row[accepted_price_col])

                        isbn_val = str(title_row[isbn_col]) if isbn_col and isbn_col in title_row and pd.notna(title_row[isbn_col]) else "-"
                        required_qty = len(title_row_df)

                        with st.form(f"distribution_entry_form_{selected_publisher}_{selected_title}"):
                            entered_qty = st.number_input(
                                "📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும்:", 
                                min_value=0, max_value=500, value=int(required_qty), step=1
                            )
                            submitted_temp = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
                            
                            if submitted_temp:
                                entry_data = {
                                    "Publisher": selected_publisher,
                                    "Title": selected_title,
                                    "Author": author_name,
                                    "Price": book_price,
                                    "Accepted Price": accepted_price,
                                    "ISBN": isbn_val,
                                    "Required Qty": required_qty,
                                    "Received Qty": entered_qty,
                                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                if not any(item["Title"] == selected_title for item in st.session_state["temp_distributed_list"]):
                                    st.session_state["temp_distributed_list"].append(entry_data)
                                st.success(f"✅ '{selected_title}' தற்காலிக பட்டியலில் சேர்க்கப்பட்டது!")
                                st.rerun()
            else:
                st.success(f"🎉 '{selected_publisher}' பதிப்பகத்தில் உள்ள அனைத்து நூல்களும் வெற்றிகரமாகச் சரிபார்க்கப்பட்டுவிட்டன!")

            if st.session_state["temp_distributed_list"]:
                st.markdown("---")
                st.markdown("#### 📋 தற்காலிகமாகச் சேமிக்கப்பட்ட தலைப்புகளின் பட்டியல்")
                temp_df = pd.DataFrame(st.session_state["temp_distributed_list"])
                st.dataframe(temp_df, use_container_width=True)
                
                current_pub_temp_count = len([item for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher])
                remaining_to_add = total_pub_titles_count - (len(submitted_titles) + current_pub_temp_count)
                
                if remaining_to_add > 0:
                    st.warning(f"⚠️ எச்சரிக்கை: இந்தப் பதிப்பகத்தில் இன்னும் **{remaining_to_add}** தலைப்புகள் சரிபார்க்கப்படாமல் உள்ளன. அனைத்து தலைப்புகளையும் சேர்த்த பிறகுதான் இறுதியாகச் சமர்ப்பிக்க முடியும்!")
                else:
                    if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பிக்க", type="primary", key="final_submit_btn"):
                        try:
                            conn = psycopg2.connect(DB_URL)
                            cur = conn.cursor()
                            for item in st.session_state["temp_distributed_list"]:
                                cur.execute("""
                                    INSERT INTO submitted_reports (publisher, title, author, price, accepted_price, isbn, required_qty, received_qty, date)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    item["Publisher"], item["Title"], item["Author"], item["Price"], 
                                    item["Accepted Price"], item["ISBN"], item["Required Qty"], 
                                    item["Received Qty"], item["Date"]
                                ))
                            conn.commit()
                            cur.close()
                            conn.close()
                            
                            st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                            st.session_state["temp_distributed_list"] = []
                            st.session_state["current_menu"] = "அறிக்கைகள்"
                            st.success("🎉 தரவுகள் Neon Database-ல் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Database save error: {e}")

elif current == "அனுப்ப":
    st.subheader("📤 நூல்கள் அனுப்பும் பகுதி (Dispatch to Libraries)")

    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ முதலில் '🔀 பிரிக்க' பகுதியில் நூல்களைப் பிரித்துச் சமர்ப்பிக்கவும். அதன் பிறகே அனுப்பும் பதிவு செய்ய முடியும்.")
    else:
        rep_df = pd.DataFrame(st.session_state["submitted_reports"])
        pub_list = sorted(rep_df["Publisher"].dropna().unique().tolist())
        sel_pub = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + pub_list, key="dispatch_pub_sel")

        if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            title_list = sorted(rep_df[rep_df["Publisher"] == sel_pub]["Title"].dropna().unique().tolist())
            sel_title = st.selectbox("📖 தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="dispatch_title_sel")

            if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                row = rep_df[(rep_df["Publisher"] == sel_pub) & (rep_df["Title"] == sel_title)].iloc[0]
                st.markdown(f"""
                <div style="background:#f8fafc; border:1.5px solid #cbd5e1; padding:12px; border-radius:8px; margin-bottom:15px;">
                    <b>📖 நூல் தலைப்பு:</b> {sel_title}<br>
                    <b>📥 பெறப்பட்ட எண்ணிக்கை:</b> {int(row.get('Received Qty', 0))}
                </div>
                """, unsafe_allow_html=True)

                with st.form("dispatch_form"):
                    library_name = st.text_input("🏛️ நூலகத்தின் பெயர்")
                    dispatch_qty = st.number_input("📦 அனுப்பப்படும் எண்ணிக்கை", min_value=0, max_value=int(row.get("Received Qty", 0)), value=0, step=1)
                    submitted_dispatch = st.form_submit_button("📤 அனுப்புதலைப் பதிவு செய்", type="primary")

                    if submitted_dispatch:
                        if not library_name.strip():
                            st.error("❌ நூலகத்தின் பெயரை உள்ளிடவும்!")
                        else:
                            st.session_state["dispatch_records"].append({
                                "Publisher": sel_pub, "Title": sel_title, "Library": library_name.strip(),
                                "Dispatched Qty": dispatch_qty, "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                            })
                            st.success(f"✅ '{sel_title}' — {dispatch_qty} பிரதிகள் '{library_name}' நூலகத்திற்கு அனுப்பியதாகப் பதிவு செய்யப்பட்டது!")
                            st.rerun()

    if st.session_state["dispatch_records"]:
        st.markdown("---")
        st.markdown("#### 📋 இதுவரை அனுப்பப்பட்ட பதிவுகள்")
        st.dataframe(pd.DataFrame(st.session_state["dispatch_records"]), use_container_width=True)

elif current == "கவனிக்க":
    st.subheader("⚠️ கவனிக்க வேண்டிய பதிவுகள் (Price Conflicts & Review)")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        price_col = next((c for c in neon_df.columns if c == 'price'), None)
        accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'rate' in c or 'offer' in c), None)
        pub_col = next((c for c in neon_df.columns if 'publication' in c or c == 'publisher_name'), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not price_col or not accepted_price_col:
            st.info("ℹ️ விலை (Price) மற்றும் ஏற்றுக்கொள்ளப்பட்ட விலை (Accepted Price) நெடுவரிசைகள் தரவுத்தளத்தில் கிடைக்கவில்லை.")
        else:
            temp_df = neon_df.copy()
            temp_df["_price_num"] = pd.to_numeric(temp_df[price_col], errors="coerce")
            temp_df["_accepted_num"] = pd.to_numeric(temp_df[accepted_price_col], errors="coerce")
            conflict_df = temp_df[temp_df["_price_num"] != temp_df["_accepted_num"]].copy()

            if conflict_df.empty:
                st.success("🎉 விலை முரண்பாடு உள்ள பதிவுகள் எதுவும் இல்லை!")
            else:
                st.warning(f"⚠️ மொத்தம் **{len(conflict_df)}** பதிவுகளில் விலை முரண்பாடு (Price Conflict) உள்ளது.")
                cols_to_show = [c for c in [pub_col, title_col, price_col, accepted_price_col] if c]
                st.dataframe(conflict_df[cols_to_show], use_container_width=True)

                csv_conflict = conflict_df[cols_to_show].to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 முரண்பாடு பட்டியலைப் பதிவிறக்குக (CSV)",
                    data=csv_conflict,
                    file_name=f"Price_Conflicts_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )

elif current == "பதிவெண் மாற்ற":
    st.subheader("🔢 பதிவெண் மாற்றும் பகுதி (Accession Number Updates)")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        acc_col = next((c for c in neon_df.columns if 'accession' in c or c == 'acc_no' or 'reg_no' in c), None)
        pub_col = next((c for c in neon_df.columns if 'publication' in c or c == 'publisher_name'), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not acc_col:
            st.info("ℹ️ 'Accession Number' நெடுவரிசை தரவுத்தளத்தில் கண்டறியப்படவில்லை. நெடுவரிசைப் பெயரைச் சரிபார்க்கவும்.")
        else:
            all_pubs = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
            sel_pub = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_pubs, key="acc_pub_sel")

            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                pub_df = neon_df[neon_df[pub_col] == sel_pub] if pub_col else neon_df
                title_list = sorted(pub_df[title_col].dropna().unique().tolist())
                sel_title = st.selectbox("📖 தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="acc_title_sel")

                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_df = pub_df[pub_df[title_col] == sel_title].reset_index(drop=True)
                    st.dataframe(title_df[[c for c in [acc_col, title_col] if c]], use_container_width=True)

                    if not title_df.empty:
                        row_num = st.number_input("✏️ மாற்ற வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(title_df) - 1, value=0, step=1, key="acc_row_num")
                        new_acc_no = st.text_input("🔢 புதிய பதிவெண்", value=str(title_df.iloc[int(row_num)][acc_col]), key="acc_new_val")

                        if st.button("💾 பதிவெண்ணைப் புதுப்பி", type="primary", key="acc_update_btn"):
                            try:
                                conn = psycopg2.connect(DB_URL)
                                cur = conn.cursor()
                                old_acc_no = title_df.iloc[int(row_num)][acc_col]
                                cur.execute(
                                    f"UPDATE books SET {acc_col} = %s WHERE {acc_col} = %s AND {title_col} = %s;",
                                    (new_acc_no, old_acc_no, sel_title)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ பதிவெண் '{old_acc_no}' இலிருந்து '{new_acc_no}' ஆக மாற்றப்பட்டது!")
                                load_neon_database.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Update error: {e}")

elif current == "அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு (Publishers & Title & Books Verification Report)")
    
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
    else:
        full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
        unique_report_publishers = ["-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --"] + sorted(full_report_df["Publisher"].dropna().unique().tolist())
        selected_report_pub = st.selectbox("🔍 பதிப்பகம் வாரியாக வடிகட்டுக (Filter by Publisher):", unique_report_publishers)
        
        if selected_report_pub != "-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --":
            display_df = full_report_df[full_report_df["Publisher"] == selected_report_pub].reset_index(drop=True)
            st.markdown(f"### 🏢 பதிப்பகம்: {selected_report_pub} (பதிவு செய்யப்பட்ட தலைப்புகள்: {len(display_df)})")
        else:
            display_df = full_report_df
            st.markdown(f"**மொத்தப் பதிவு செய்யப்பட்ட தலைப்புகள்:** {len(display_df)}")
            
        st.dataframe(display_df, use_container_width=True)
        
        csv_all = full_report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 அறிக்கையைப் பதிவிறக்குக (Download CSV)",
            data=csv_all,
            file_name=f"Verification_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

elif current == "தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல் / திருத்துதல் (Delete / Edit Verified Records)")
    
    edit_action_option = st.selectbox(
        "📌 எந்தப் பகுதியில் உள்ள தரவுகளை மாற்ற / நீக்க வேண்டும் என்பதைத் தேர்ந்தெடுக்கவும்:",
        [
            "-- பகுதியைத் தேர்ந்தெடுக்கவும் --",
            "1. பதிப்பாளர் தேர்வு (Publisher Records)",
            "2. அனுப்பிய விவரங்கள் (Dispatch Records)",
            "3. அறிக்கை தரவுகள் (Submitted Reports)",
            "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)",
            "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)",
            "6. Master Data தரவுகள்",
            "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)"
        ],
        key="main_error_correction_sub_menu"
    )
    
    st.markdown("---")
    
    if edit_action_option == "1. பதிப்பாளர் தேர்வு (Publisher Records)":
        st.markdown("### 🏢 1. பதிப்பாளர் தேர்வு & திருத்துதல் / நீக்குதல்")
        
        completed_publishers = set()
        for item in st.session_state.get("submitted_reports", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
        for item in st.session_state.get("temp_distributed_list", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
                
        pub_list = sorted(list(completed_publishers))
        
        if not pub_list:
            st.info("ℹ️ இதுவரை எந்தப் பதிப்பகப் பணியும் முடிக்கப்படவில்லை.")
        else:
            sel_pub = st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + pub_list, key="err_pub_sel")
            
            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                completed_titles = set()
                for item in st.session_state.get("submitted_reports", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                for item in st.session_state.get("temp_distributed_list", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                        
                title_list = sorted(list(completed_titles))
                
                sel_title = st.selectbox("தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="err_title_sel")
                
                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    req_qty = 90
                    rec_qty = 75
                    target_index = None
                    target_id = None
                    
                    for idx, item in enumerate(st.session_state.get("submitted_reports", [])):
                        if item.get("Publisher") == sel_pub and item.get("Title") == sel_title:
                            req_qty = int(item.get("Required Qty", 90))
                            rec_qty = int(item.get("Received Qty", 75))
                            target_index = idx
                            target_id = item.get("Id")
                            break

                    st.markdown(f"""
                    <div style="background: #f8fafc; border: 1.5px solid #cbd5e1; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                        <b>📖 நூல் தலைப்பு:</b> {sel_title}<br>
                        <b>📌 பெறப்பட வேண்டிய மொத்த எண்ணிக்கை (Required):</b> <span style="color: #2563eb; font-weight: bold;">{req_qty}</span><br>
                        <b>📥 ஏற்கனவே பெறப்பட்ட எண்ணிக்கை (Received):</b> <span style="color: #16a34a; font-weight: bold;">{rec_qty}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        new_val = st.number_input("📥 பெறப்பட்ட எண்ணிக்கையைத் திருத்துக (Update Received Qty):", min_value=0, max_value=req_qty*2, value=rec_qty, key="err_pub_qty")
                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_d, col_u = st.columns(2)
                        with col_d:
                            if st.button("🗑️ நீக்கு", key="err_pub_del_btn", use_container_width=True):
                                if target_id is not None:
                                    try:
                                        conn = psycopg2.connect(DB_URL)
                                        cur = conn.cursor()
                                        cur.execute("DELETE FROM submitted_reports WHERE id = %s;", (target_id,))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                        st.success("✅ பதிவு வெற்றிகரமாக நீக்கப்பட்டது!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Delete error: {e}")
                                else:
                                    st.warning("⚠️ இந்தப் பதிவு database-ல் கிடைக்கவில்லை (Id காணப்படவில்லை).")
                        with col_u:
                            if st.button("💾 மாற்று/புதுப்பி", key="err_pub_upd_btn", type="primary", use_container_width=True):
                                try:
                                    conn = psycopg2.connect(DB_URL)
                                    cur = conn.cursor()
                                    if target_id is not None:
                                        cur.execute("UPDATE submitted_reports SET received_qty = %s WHERE id = %s;", (new_val, target_id))
                                    else:
                                        cur.execute("""
                                            INSERT INTO submitted_reports (publisher, title, required_qty, received_qty, date)
                                            VALUES (%s, %s, %s, %s, %s)
                                        """, (sel_pub, sel_title, req_qty, new_val, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                except Exception as e:
                                    st.error(f"❌ Update error: {e}")
                                st.success(f"✅ எண்ணிக்கை வெற்றிகரமாக {new_val} என மாற்றப்பட்டது!")
                                st.rerun()

    elif edit_action_option == "2. அனுப்பிய விவரங்கள் (Dispatch Records)":
        st.markdown("### 📤 2. அனுப்பிய விவரங்கள் — திருத்துதல் / நீக்குதல்")
        if not st.session_state.get("dispatch_records"):
            st.info("ℹ️ இதுவரை எந்த நூல்களும் அனுப்பப்படவில்லை.")
        else:
            disp_df = pd.DataFrame(st.session_state["dispatch_records"])
            st.dataframe(disp_df, use_container_width=True)
            row_idx = st.number_input("🗑️ நீக்க வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(disp_df) - 1, value=0, step=1, key="disp_del_idx")
            if st.button("🗑️ தேர்ந்தெடுத்த பதிவை நீக்கு", key="disp_del_btn", type="primary"):
                st.session_state["dispatch_records"].pop(int(row_idx))
                st.success("✅ அனுப்பிய பதிவு நீக்கப்பட்டது!")
                st.rerun()

    elif edit_action_option == "3. அறிக்கை தரவுகள் (Submitted Reports)":
        st.markdown("### 📊 3. அறிக்கை தரவுகள் — முழுப் பட்டியல் (திருத்த/நீக்க பதிப்பகம் வாரியாகச் செல்லவும்)")
        if not st.session_state.get("submitted_reports"):
            st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
        else:
            all_rep_df = pd.DataFrame(st.session_state["submitted_reports"])
            st.dataframe(all_rep_df, use_container_width=True)
            st.caption("💡 குறிப்பிட்ட ஒரு பதிவைத் திருத்த அல்லது நீக்க '1. பதிப்பாளர் தேர்வு' பகுதியைப் பயன்படுத்தவும்.")

    elif edit_action_option == "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)":
        st.markdown("### ⚠️ 4. விலை முரண்பாடு உள்ள பதிவுகள்")
        neon_df = load_neon_database()
        if neon_df.empty:
            st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
        else:
            price_col = next((c for c in neon_df.columns if c == 'price'), None)
            accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'rate' in c or 'offer' in c), None)
            if not price_col or not accepted_price_col:
                st.info("ℹ️ விலை நெடுவரிசைகள் கண்டறியப்படவில்லை.")
            else:
                cmp_df = neon_df.copy()
                cmp_df["_p"] = pd.to_numeric(cmp_df[price_col], errors="coerce")
                cmp_df["_a"] = pd.to_numeric(cmp_df[accepted_price_col], errors="coerce")
                conflicts = cmp_df[cmp_df["_p"] != cmp_df["_a"]]
                if conflicts.empty:
                    st.success("🎉 முரண்பாடுகள் எதுவும் இல்லை!")
                else:
                    st.dataframe(conflicts.drop(columns=["_p", "_a"]), use_container_width=True)

    elif edit_action_option == "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)":
        st.markdown("### 🔢 5. பதிவெண் மாற்றத் தேவைப்படும் இடத்திற்குச் செல்ல மேல் மெனுவில் '🔢 பதிவெண் மாற்ற' பட்டனை அழுத்தவும்.")
        st.info("ℹ️ பதிவெண் புதுப்பிப்பதற்கான முழு வசதி '🔢 பதிவெண் மாற்ற' மெனுவில் உள்ளது.")

    elif edit_action_option == "6. Master Data தரவுகள்":
        st.markdown("### 🗂️ 6. Master Data — முழு பட்டியலைப் பார்வையிட '🗂️ Master Data' மெனுவைப் பயன்படுத்தவும்.")
        st.info("ℹ️ Master Data-வைத் திருத்த நேரடியாக Neon Database-ல் மாற்றங்களைச் செய்ய வேண்டும்; இங்கிருந்து நேரடி நீக்கம் ஆதரிக்கப்படவில்லை.")

    elif edit_action_option == "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)":
        st.markdown("### 🏷️ 7. பகுப்பு எண் புதுப்பிப்பதற்கு மேல் மெனுவில் '🏷️ பகுப்பு எண் புதுப்பி' பட்டனை அழுத்தவும்.")
        st.info("ℹ️ பகுப்பு எண் புதுப்பிப்பதற்கான முழு வசதி '🏷️ பகுப்பு எண் புதுப்பி' மெனுவில் உள்ளது.")

    else:
        st.info("👆 மேல் உள்ள தேர்வில் ஏதேனும் ஒரு பிரிவைத் தேர்வு செய்தால், அதற்கான திருத்தும் மற்றும் நீக்கும் வசதிகள் உடனே தோன்றும்.")

elif current == "கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Change Password)")
    with st.form("pwd_form"):
        old_p = st.text_input("பழைய கடவுச்சொல்", type="password")
        new_p = st.text_input("புதிய கடவுச்சொல்", type="password")
        conf_p = st.text_input("உங்களை உறுதிப்படுத்த புதிய கடவுச்சொல்", type="password")
        if st.form_submit_button("கடவுச்சொல்லை மாற்றுக", type="primary"):
            if new_p == conf_p and len(new_p) > 0:
                st.success("✅ கடவுச்சொல் வெற்றிகரமாக மாற்றப்பட்டது!")
            else:
                st.error("❌ கடவுச்சொற்கள் பொருந்தவில்லை!")

elif current == "Excel பதிவிறக்கம்":
    st.subheader("📥 Excel அறிக்கை பதிவிறக்கம்")
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ பதிவிறக்கம் செய்யத் தரவுகள் எதுவும் இல்லை.")
    else:
        report_df = pd.DataFrame(st.session_state["submitted_reports"])
        csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 முழுமையான தரவுகளை Excel கோப்பாகப் பதிவிறக்குக",
            data=csv_data,
            file_name=f"Master_Verification_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )

elif current == "Master Data":
    st.subheader("🗂️ Master Data சேமிப்பு & மேலாண்மை பகுதி (Neon Table Data with Received Stats)")
    
    neon_df = load_neon_database()
    if neon_df.empty or not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை எந்தப் பதிப்புகளும் பிரிக்கப்பட்டுச் சமர்ப்பிக்கப்படவில்லை அல்லது Neon தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
        submitted_pubs = list(set([item["Publisher"] for item in st.session_state["submitted_reports"]]))
        submitted_pubs = sorted([p for p in submitted_pubs if p in neon_df[pub_col].values]) if pub_col else []
        
        view_mode = st.radio(
            "📂 பார்வைக் முறையைத் தேர்ந்தெடுக்கவும்:",
            ["🏢 பதிப்பகம் வாரியாக (Publisher-wise)", "🏛️ நூலகம் வாரியாக (Library-wise)"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if "Publisher-wise" in view_mode:
            st.markdown("### 🏢 பணி முடிக்கப்பட்ட பதிப்பகங்கள் வாரியான முழு விவரங்கள் (Received Stats உடன்)")
            
            if not submitted_pubs:
                st.info("ℹ️ பணி முடிக்கப்பட்ட பதிப்பகங்கள் எதுவும் இல்லை.")
            else:
                sel_master_pub = st.selectbox("🔍 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + submitted_pubs)
                
                if sel_master_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    pub_neon_df = neon_df[neon_df[pub_col] == sel_master_pub].copy()
                    
                    rep_df = pd.DataFrame(st.session_state["submitted_reports"])
                    pub_rep = rep_df[rep_df["Publisher"] == sel_master_pub]
                    title_received_map = dict(zip(pub_rep["Title"], pub_rep["Received Qty"])) if not pub_rep.empty else {}
                    
                    rows_list = []
                    for title_val, group_df in pub_neon_df.groupby(title_col):
                        req_qty = len(group_df)
                        rec_qty = int(title_received_map.get(title_val, 0))
                        
                        group_df = group_df.copy()
                        received_status = [1 if i < rec_qty else 0 for i in range(req_qty)]
                        group_df["received_stats"] = received_status
                        rows_list.append(group_df)
                    
                    if rows_list:
                        final_pub_df = pd.concat(rows_list, ignore_index=True)
                    else:
                        final_pub_df = pub_neon_df
                        
                    total_titles = final_pub_df[title_col].nunique()
                    total_books = len(final_pub_df)
                    total_rec_books = final_pub_df["received_stats"].sum() if "received_stats" in final_pub_df.columns else 0
                    total_not_rec_books = total_books - total_rec_books
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏢 பதிப்பகம்", sel_master_pub)
                    with col2:
                        st.metric("📚 தலைப்புகள்", total_titles)
                    with col3:
                        st.metric("✅ பெறப்பட்ட நூல்கள்", int(total_rec_books))
                    with col4:
                        st.metric("⏳ பெறப்படாத நூல்கள்", int(total_not_rec_books))
                        
                    st.markdown(f"### 📍 பதிப்பகம்: {sel_master_pub} — முழு அட்டவணை விவரங்கள்")
                    st.dataframe(final_pub_df, use_container_width=True)
                    
                    csv_master = final_pub_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 பதிப்பக Master Data பதிவிறக்கம் (CSV)",
                        data=csv_master,
                        file_name=f"Master_Data_ReceivedStats_{sel_master_pub}.csv",
                        mime="text/csv",
                        type="primary"
                    )
        else:
            st.markdown("### 🏛️ பணி முடிக்கப்பட்ட நூலகம் வாரியான முழு விவரங்கள்")
            lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
            if lib_col_name:
                submitted_neon_df = neon_df[neon_df[pub_col].isin(submitted_pubs)].copy() if pub_col else neon_df
                all_libs = sorted(submitted_neon_df[lib_col_name].dropna().unique().tolist())
                
                sel_lib = st.selectbox("🔍 நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_libs)
                if sel_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                    lib_df = submitted_neon_df[submitted_neon_df[lib_col_name] == sel_lib].copy()
                    st.markdown(f"### 🏛️ நூலகம்: {sel_lib} (மொத்த நூல்கள்: {len(lib_df)})")
                    st.dataframe(lib_df, use_container_width=True)
                    
                    csv_lib = lib_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 நூலக Master Data பதிவிறக்கம் (CSV)",
                        data=csv_lib,
                        file_name=f"Master_Data_Library_{sel_lib}.csv",
                        mime="text/csv",
                        type="primary"
                    )
            else:
                st.warning("⚠️ நூலகப் பெயர் காலம் (Library Name Column) டேட்டாபேஸில் கிடைக்கவில்லை.")

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள் மேலாண்மை")
    st.info("ℹ️ ஒவ்வொரு நூலகருக்கும் பார்வைக் காலத்தைப் (ஆண்டு) பதிவு செய்யவும், தேவைப்படின் திருத்தவும்.")

    with st.form("librarian_year_form"):
        lc1, lc2 = st.columns(2)
        with lc1:
            librarian_name = st.text_input("👤 நூலகர் பெயர்")
            library_name = st.text_input("🏛️ நூலகத்தின் பெயர்")
        with lc2:
            view_year = st.text_input("📅 பார்வை ஆண்டு (உ.ம். 2026-27)", value="2026-27")
        add_lib_record = st.form_submit_button("➕ பதிவு சேர்", type="primary")

        if add_lib_record:
            if not librarian_name.strip() or not library_name.strip():
                st.error("❌ நூலகர் பெயர் மற்றும் நூலகத்தின் பெயரை உள்ளிடவும்!")
            else:
                st.session_state["librarian_records"].append({
                    "Librarian": librarian_name.strip(), "Library": library_name.strip(),
                    "View Year": view_year.strip(), "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"✅ '{librarian_name}' — {view_year} பதிவு சேர்க்கப்பட்டது!")
                st.rerun()

    if st.session_state["librarian_records"]:
        st.markdown("---")
        lib_rec_df = pd.DataFrame(st.session_state["librarian_records"])
        st.dataframe(lib_rec_df, use_container_width=True)
        del_idx = st.number_input("🗑️ நீக்க வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(lib_rec_df) - 1, value=0, step=1, key="lib_rec_del_idx")
        if st.button("🗑️ தேர்ந்தெடுத்த பதிவை நீக்கு", key="lib_rec_del_btn"):
            st.session_state["librarian_records"].pop(int(del_idx))
            st.success("✅ பதிவு நீக்கப்பட்டது!")
            st.rerun()
    else:
        st.info("ℹ️ இதுவரை நூலகர் பார்வை ஆண்டு பதிவுகள் எதுவும் சேர்க்கப்படவில்லை.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் & மேலாண்மை")
    uploaded_file = st.file_uploader("Excel அல்லது CSV கோப்பினைத் தேர்ந்தெடுக்கவும்", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                up_df = pd.read_csv(uploaded_file)
            else:
                up_df = pd.read_excel(uploaded_file)
            st.success(f"✅ கோப்பு வெற்றிகரமாகப் பெறப்பட்டது! ({len(up_df)} வரிசைகள் கண்டறியப்பட்டன)")
            st.dataframe(up_df.head(50), use_container_width=True)

            up_df.columns = [str(c).strip().lower() for c in up_df.columns]
            books_columns = set(load_neon_database().columns) if not load_neon_database().empty else set()

            if books_columns and not books_columns.issuperset(up_df.columns):
                missing = set(up_df.columns) - books_columns
                st.warning(f"⚠️ கோப்பில் உள்ள சில நெடுவரிசைகள் 'books' அட்டவணையில் இல்லை: {', '.join(missing)}. அப்லோடு செய்யும் முன் நெடுவரிசைப் பெயர்களை உறுதி செய்யவும்.")
            else:
                if st.button("💾 இந்தத் தரவை Neon Database-ல் சேமி", type="primary", key="excel_upload_save_btn"):
                    try:
                        conn = psycopg2.connect(DB_URL)
                        cur = conn.cursor()
                        cols = list(up_df.columns)
                        placeholders = ", ".join(["%s"] * len(cols))
                        col_names = ", ".join(cols)
                        for _, r in up_df.iterrows():
                            cur.execute(f"INSERT INTO books ({col_names}) VALUES ({placeholders});", tuple(r[c] for c in cols))
                        conn.commit()
                        cur.close()
                        conn.close()
                        load_neon_database.clear()
                        st.success(f"✅ {len(up_df)} வரிசைகள் Neon Database-ல் சேமிக்கப்பட்டன!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Upload save error: {e}")
        except Exception as e:
            st.error(f"❌ கோப்பைப் படிக்க முடியவில்லை: {e}")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல் மற்றும் திருத்துதல்")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        class_col = next((c for c in neon_df.columns if 'classification' in c or c == 'class_no' or 'call_no' in c or 'call number' in c), None)
        pub_col = next((c for c in neon_df.columns if 'publication' in c or c == 'publisher_name'), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not class_col:
            st.info("ℹ️ 'Classification Number' நெடுவரிசை தரவுத்தளத்தில் கண்டறியப்படவில்லை. நெடுவரிசைப் பெயரைச் சரிபார்க்கவும்.")
        else:
            all_pubs = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
            sel_pub = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_pubs, key="class_pub_sel")

            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                pub_df = neon_df[neon_df[pub_col] == sel_pub] if pub_col else neon_df
                title_list = sorted(pub_df[title_col].dropna().unique().tolist())
                sel_title = st.selectbox("📖 தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="class_title_sel")

                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_df = pub_df[pub_df[title_col] == sel_title].reset_index(drop=True)
                    st.dataframe(title_df[[c for c in [class_col, title_col] if c]], use_container_width=True)

                    if not title_df.empty:
                        row_num = st.number_input("✏️ மாற்ற வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(title_df) - 1, value=0, step=1, key="class_row_num")
                        new_class_no = st.text_input("🏷️ புதிய பகுப்பு எண்", value=str(title_df.iloc[int(row_num)][class_col]), key="class_new_val")

                        if st.button("💾 பகுப்பு எண்ணைப் புதுப்பி", type="primary", key="class_update_btn"):
                            try:
                                conn = psycopg2.connect(DB_URL)
                                cur = conn.cursor()
                                old_class_no = title_df.iloc[int(row_num)][class_col]
                                cur.execute(
                                    f"UPDATE books SET {class_col} = %s WHERE {class_col} = %s AND {title_col} = %s;",
                                    (new_class_no, old_class_no, sel_title)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ பகுப்பு எண் '{old_class_no}' இலிருந்து '{new_class_no}' ஆக மாற்றப்பட்டது!")
                                load_neon_database.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Update error: {e}")
