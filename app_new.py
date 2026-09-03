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
.login-card-wrapper { background: #ffffff; border-radius: 16px; padding: 22px 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); border: 1.5px solid #a7f3d0; width: 100%; max-width: 420px; }
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
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

if "users_db" not in st.session_state:
    st.session_state["users_db"] = {
        "Admin": {"password_hash": hash_password("Hari@@1979"), "name": "முதன்மை நிர்வாகி (Admin)"},
        "DCL Staff": {"password_hash": hash_password("123456"), "name": "DCL Staff"},
    }

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
        df = pd.read_sql("SELECT publisher as \"Publisher\", title as \"Title\", author as \"Author\", price as \"Price\", accepted_price as \"Accepted Price\", isbn as \"ISBN\", required_qty as \"Required Qty\", received_qty as \"Received Qty\", date as \"Date\" FROM submitted_reports;", con=conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        return []

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "", "assigned_library": None,
    "current_menu": "பிரிக்க", "temp_distributed_list": [], 
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
    
    neon_df = load_neon_database()
    lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None) if not neon_df.empty else None
    id_col_name = next((c for c in neon_df.columns if 'id' in c or 'code' in c or 'no' in c), None) if not neon_df.empty else None
    
    all_libraries = sorted(neon_df[lib_col_name].dropna().unique().tolist()) if lib_col_name else []

    with st.form("secure_login_form"):
        selected_role = st.selectbox("பயனர் வகை (User)", ["-- தேர்ந்தெடுக்கவும் --", "Admin", "DCL Staff", "Librarian"])
        
        selected_lib = None
        lib_id_input = ""
        password = ""
        
        if selected_role == "Librarian":
            selected_lib = st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_libraries)
            lib_id_input = st.text_input("🆔 Library ID / குறியீடு உள்ளிடவும்:", placeholder="உதாரணமாக: LIB001 அல்லது நூலக குறியீடு")
        else:
            password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
            
        submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if submitted:
        if selected_role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
        elif selected_role == "Librarian":
            if selected_lib == "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --" or not selected_lib:
                st.warning("⚠️ தயவுசெய்து உங்களது நூலகத்தைத் தேர்ந்தெடுக்கவும்!")
            elif not lib_id_input.strip():
                st.warning("⚠️ தயவுசெய்து Library ID-ஐ உள்ளிடவும்!")
            else:
                st.session_state.update(
                    logged_in=True, 
                    user_role="Librarian", 
                    user_name=f"நூலகர் ({selected_lib})",
                    assigned_library=selected_lib,
                    current_menu="நூலகர் பார்வை ஆண்டு"
                )
                st.rerun()
        else:
            user = st.session_state["users_db"].get(selected_role)
            if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
                st.session_state.update(
                    logged_in=True, 
                    user_role=selected_role, 
                    user_name=user["name"], 
                    assigned_library=None,
                    current_menu="பிரிக்க"
                )
                st.rerun()
            else:
                st.error("❌ தவறான கடவுச்சொல்!")

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
            👤 {}
        </span>
    </div>
</div>
""".format(st.session_state["user_name"]), unsafe_allow_html=True)

col_logout = st.columns([11, 1])
with col_logout[1]:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["assigned_library"] = None
        st.rerun()

role = st.session_state["user_role"]
if role == "Admin":
    allowed_menus = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
        ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
        ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
        ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி")
    ]
elif role == "DCL Staff":
    allowed_menus = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), 
        ("👥", "நூலகர் பார்வை ஆண்டு")
    ]
elif role == "Librarian":
    allowed_menus = [
        ("👥", "நூலகர் பார்வை ஆண்டு")
    ]
else:
    allowed_menus = []

cols = st.columns(len(allowed_menus)) if allowed_menus else [st.container()]
for i, (icon, label) in enumerate(allowed_menus):
    with cols[i]:
        btn_type = "primary" if st.session_state["current_menu"] == label else "secondary"
        if st.button(f"{icon}\n{label}", key=f"menu_btn_{i}", use_container_width=True, type=btn_type):
            st.session_state["current_menu"] = label
            st.rerun()

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

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை தேர்வு செய்யவும்.")

elif current == "பிரிக்க" and role in ["Admin", "DCL Staff"]:
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
        selected_publisher = st.selectbox("🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers, key="publisher_dropdown")

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
                selected_title = st.selectbox("📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும் (Select Book Title):", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles, key="title_dropdown")
                if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_row_df = pub_filtered_df[pub_filtered_df[title_col] == selected_title]
                    if not title_row_df.empty:
                        title_row = title_row_df.iloc[0]
                        author_name = str(title_row[author_col]) if author_col and author_col in title_row and pd.notna(title_row[author_col]) else "-"
                        book_price = str(title_row[price_col]) if price_col and price_col in title_row and pd.notna(title_row[price_col]) else "0"
                        accepted_price = str(title_row[accepted_price_col]) if accepted_price_col and accepted_price_col in title_row and pd.notna(title_row[accepted_price_col]) else "0"
                        isbn_val = str(title_row[isbn_col]) if isbn_col and isbn_col in title_row and pd.notna(title_row[isbn_col]) else "-"
                        required_qty = len(title_row_df)

                        with st.form(f"distribution_entry_form_{selected_publisher}_{selected_title}"):
                            entered_qty = st.number_input("📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும்:", min_value=0, max_value=500, value=int(required_qty), step=1)
                            submitted_temp = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
                            
                            if submitted_temp:
                                entry_data = {
                                    "Publisher": selected_publisher, "Title": selected_title, "Author": author_name,
                                    "Price": book_price, "Accepted Price": accepted_price, "ISBN": isbn_val,
                                    "Required Qty": required_qty, "Received Qty": entered_qty,
                                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                if not any(item["Title"] == selected_title for item in st.session_state["temp_distributed_list"]):
                                    st.session_state["temp_distributed_list"].append(entry_data)
                                st.success(f"✅ '{selected_title}' தற்காலிக பட்டியலில் சேர்க்கப்பட்டது!")
                                st.rerun()

            if st.session_state["temp_distributed_list"]:
                st.markdown("---")
                st.markdown("#### 📋 தற்காலிகமாகச் சேமிக்கப்பட்ட தலைப்புகளின் பட்டியல்")
                temp_df = pd.DataFrame(st.session_state["temp_distributed_list"])
                st.dataframe(temp_df, use_container_width=True)
                
                current_pub_temp_count = len([item for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher])
                remaining_to_add = total_pub_titles_count - (len(submitted_titles) + current_pub_temp_count)
                
                if remaining_to_add > 0:
                    st.warning(f"⚠️ எச்சரிக்கை: இந்தப் பதிப்பகத்தில் இன்னும் **{remaining_to_add}** தலைப்புகள் சரிபார்க்கப்படாமல் உள்ளன.")
                else:
                    if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பించు", type="primary", key="final_submit_btn"):
                        try:
                            conn = psycopg2.connect(DB_URL)
                            cur = conn.cursor()
                            for item in st.session_state["temp_distributed_list"]:
                                cur.execute("""
                                    INSERT INTO submitted_reports (publisher, title, author, price, accepted_price, isbn, required_qty, received_qty, date)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (item["Publisher"], item["Title"], item["Author"], item["Price"], item["Accepted Price"], item["ISBN"], item["Required Qty"], item["Received Qty"], item["Date"]))
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

elif current == "அறிக்கைகள்" and role in ["Admin", "DCL Staff"]:
    st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு (Publishers & Title & Books Verification Report)")
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
    else:
        full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
        unique_report_publishers = ["-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --"] + sorted(full_report_df["Publisher"].dropna().unique().tolist())
        selected_report_pub = st.selectbox("🔍 பதிப்பகம் வாரியாக வடிகட்டுக:", unique_report_publishers)
        
        display_df = full_report_df[full_report_df["Publisher"] == selected_report_pub].reset_index(drop=True) if selected_report_pub != "-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --" else full_report_df
        st.dataframe(display_df, use_container_width=True)
        
        csv_all = full_report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(label="📥 அறிக்கையைப் பதிவிறக்குக (Download CSV)", data=csv_all, file_name=f"Verification_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", type="primary", use_container_width=True)

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள்")
    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ டேட்டாபேஸ் தரவுகள் கிடைக்கவில்லை.")
    else:
        lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
        if lib_col_name:
            if role == "Librarian":
                sel_lib = st.session_state["assigned_library"]
                st.info(f"🏛️ உங்களது நூலகம்: **{sel_lib}**")
            else:
                all_libs = sorted(neon_df[lib_col_name].dropna().unique().tolist())
                sel_lib = st.selectbox("🔍 நூலகத்தைத் தேர்ந்தெடுக்கவும் (Select Library):", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_libs)
            
            if sel_lib and sel_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                lib_df = neon_df[neon_df[lib_col_name] == sel_lib].copy()
                st.markdown(f"### 🏛️ நூலகம்: {sel_lib} (மொத்த நூல்கள்: {len(lib_df)})")
                st.dataframe(lib_df, use_container_width=True)
                
                csv_lib = lib_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(label="📥 நூலக Master Data பதிவிறக்கம் (CSV)", data=csv_lib, file_name=f"Library_{sel_lib}.csv", mime="text/csv", type="primary")
        else:
            st.warning("⚠️ நூலகப் பெயர் காலம் (Library Name Column) டேட்டாபேஸில் கிடைக்கவில்லை.")

elif current == "கடவுச்சொல் மாற்ற" and role == "Admin":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Admin Only)")
    with st.form("pwd_form"):
        old_p = st.text_input("பழைய கடவுச்சொல்", type="password")
        new_p = st.text_input("புதிய கடவுச்சொல்", type="password")
        conf_p = st.text_input("புதிய கடவுச்சொல்லை உறுதிப்படுத்தவும்", type="password")
        submitted_pwd = st.form_submit_button("கடவுச்சொல்லை மாற்றுக", type="primary")
        
        if submitted_pwd:
            stored_hash = st.session_state["users_db"]["Admin"]["password_hash"]
            if hmac.compare_digest(hash_password(old_p), stored_hash):
                if new_p == conf_p and len(new_p) > 0:
                    st.session_state["users_db"]["Admin"]["password_hash"] = hash_password(new_p)
                    st.success("✅ கடவுச்சொல் வெற்றிகரமாக மாற்றப்பட்டது!")
                else:
                    st.error("❌ புதிய கடவுச்சொற்கள் பொருந்தவில்லை அல்லது காலியாக உள்ளது!")
            else:
                st.error("❌ பழைய கடவுச்சொல் தவறானது!")

elif role == "Admin":
    st.subheader(f"⚙️ {current} பகுதி (Admin Control Panel)")
    st.info(f"ℹ️ நீங்கள் '{current}' பகுதியை வெற்றிகரமாக அணுகியுள்ளீர்கள். Admin-ஆதலால் அனைத்து நிர்வாகப் பணிகளையும் இங்கு மேற்கொள்ளலாம்.")
    
    # Admin-க்கான பொதுவான மேலாண்மை டேட்டா அல்லது எடிட்டிங் பகுதி
    neon_df = load_neon_database()
    if not neon_df.empty:
        st.markdown("#### 📋 டேட்டாபேஸ் தரவு மேலாண்மை (Database Records)")
        st.dataframe(neon_df.head(50), use_container_width=True)
else:
    st.warning("⚠️ உங்களுக்கு இந்தப் பக்கத்தை அணுக அனுமதி இல்லை.")
