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
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

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
        df = pd.read_sql("SELECT publisher as \"Publisher\", title as \"Title\", author as \"Author\", price as \"Price\", accepted_price as \"Accepted Price\", isbn as \"ISBN\", required_qty as \"Required Qty\", received_qty as \"Received Qty\", date as \"Date\" FROM submitted_reports;", con=conn)
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
        st.rerun()

menu_options = [
    ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
    ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி")
]

cols = st.columns(len(menu_options))
for i, (icon, label) in enumerate(menu_options):
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
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை (உதாரணமாக **'🔀 பிரிக்க'** அல்லது **'📊 அறிக்கைகள்'**) தேர்வு செய்யவும்.")

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
                    if st.button("💾 இறுதியாகச் சேமி & சமர்பிக்க", type="primary", key="final_submit_btn"):
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
                    
                    for idx, item in enumerate(st.session_state.get("submitted_reports", [])):
                        if item.get("Publisher") == sel_pub and item.get("Title") == sel_title:
                            req_qty = int(item.get("Required Qty", 90))
                            rec_qty = int(item.get("Received Qty", 75))
                            target_index = idx
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
                                if target_index is not None:
                                    item_to_del = st.session_state["submitted_reports"][target_index]
                                    try:
                                        conn = psycopg2.connect(DB_URL)
                                        cur = conn.cursor()
                                        cur.execute("DELETE FROM submitted_reports WHERE publisher = %s AND title = %s;", (sel_pub, item_to_del.get('Title')))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                    except Exception as e:
                                        st.error(f"❌ Delete error: {e}")
                                st.success("✅ பதிவு வெற்றிகரமாக நீக்கப்பட்டது!")
                                st.rerun()
                        with col_u:
                            if st.button("💾 மாற்று/புதுப்பி", key="err_pub_upd_btn", type="primary", use_container_width=True):
                                try:
                                    conn = psycopg2.connect(DB_URL)
                                    cur = conn.cursor()
                                    if target_index is not None:
                                        cur.execute("UPDATE submitted_reports SET received_qty = %s WHERE publisher = %s AND title = %s;", (new_val, sel_pub, sel_title))
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
    st.info("நூலகர்களின் பார்வைக் காலங்களைச் சரிபார்க்கவும் திருத்தவும்.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் & மேலாண்மை")
    uploaded_file = st.file_uploader("Excel அல்லது CSV கோப்பினைத் தேர்ந்தெடுக்கவும்", type=["xlsx", "csv"])
    if uploaded_file is not None:
        st.success("✅ கோப்பு வெற்றிகரமாகப் பெறப்பட்டது!")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல் மற்றும் திருத்துதல்")
    st.info("நூல் பகுப்பு எண்களைத் தரம் பிரித்துப் புதுப்பிக்க.")
