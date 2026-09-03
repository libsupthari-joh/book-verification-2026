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
    "TNDPL01617": {"password_hash": hash_password("123456789"), "name": "Chinthakampalli Librarian", "lib_name": "Chinthakampalli"},
    "TNDPL01586": {"password_hash": hash_password("123456789"), "name": "Pochampalli Librarian", "lib_name": "Pochampalli"},
}

def authenticate_user(role_key, password, librarian_id=""):
    if role_key == "Librarian":
        user = USERS_DATABASE.get(librarian_id)
        if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
            return user
        return None
    else:
        user = USERS_DATABASE.get(role_key)
        if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
            return user
        return None

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
    "logged_in": False, "user_role": None, "user_name": "", "librarian_location": "",
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
        
        lib_id_input = ""
        if selected_role == "Librarian":
            lib_id_input = st.text_input("🆔 நூலகர் ஐடி (Librarian ID)", placeholder="எ.கா: TNDPL01617")
            
        password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
        submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if submitted:
        if selected_role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
        elif selected_role == "Librarian" and not lib_id_input:
            st.warning("⚠️ தயவுசெய்து உங்கள் Librarian ID-ஐ உள்ளிடவும்!")
        else:
            user = authenticate_user(selected_role, password, lib_id_input)
            if not user:
                st.error("❌ தவறான Librarian ID அல்லது கடவுச்சொல்!")
            else:
                display_name = f"{user['name']} ({lib_id_input})" if selected_role == "Librarian" else user["name"]
                lib_loc = user.get("lib_name", "") if selected_role == "Librarian" else ""
                st.session_state.update(
                    logged_in=True, 
                    user_role=selected_role, 
                    user_name=display_name,
                    librarian_location=lib_loc
                )
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

# பங்கை (Role) பொறுத்து மெனு பட்டியலை நிர்ணயித்தல்
if st.session_state["user_role"] == "Admin":
    menu_options = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
        ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
        ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
        ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி")
    ]
elif st.session_state["user_role"] == "DCL Staff":
    # DCL Staff-க்கு குறிப்பிட்ட 3 பணிகள் மட்டும்
    menu_options = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்")
    ]
else:
    # Librarian-க்கு சம்பந்தப்பட்ட நூலகத் தரவுகளை மட்டும் பார்க்கும் பகுதி
    menu_options = [
        ("📊", "நூலகத் தரவுகள்"), ("📥", "பதிவிறக்கம்")
    ]

cols = st.columns(len(menu_options))
for i, (icon, label) in enumerate(menu_options):
    with cols[i]:
        btn_type = "primary" if st.session_state["current_menu"] == label else "secondary"
        if st.button(f"{icon}\n{label}", key=f"menu_btn_{i}", use_container_width=True, type=btn_type):
            st.session_state["current_menu"] = label
            st.rerun()

st.markdown("---")

today_str = datetime.now().strftime("%d/%m/%Y")

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
        pass
    return pd.DataFrame()

current = st.session_state["current_menu"]

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை தேர்வு செய்யவும்.")

elif current == "பிரிக்க" and st.session_state["user_role"] in ["Admin", "DCL Staff"]:
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or 'title' in c), neon_df.columns[2])
        all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
        selected_publisher = st.selectbox("🔍 பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers)
        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            st.success(f"தேர்ந்தெடுக்கப்பட்ட பதிப்பகம்: {selected_publisher}")

elif current == "அனுப்ப" and st.session_state["user_role"] in ["Admin", "DCL Staff"]:
    st.subheader("📤 அனுப்பும் பகுதி (Dispatch Section)")
    st.info("நூல்களை நூலகங்களுக்கு அனுப்பும் விவரங்கள்.")

elif current == "அறிக்கைகள்" and st.session_state["user_role"] in ["Admin", "DCL Staff"]:
    st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு")
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
    else:
        full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
        st.dataframe(full_report_df, use_container_width=True)

elif current == "நூலகத் தரவுகள்" and st.session_state["user_role"] == "Librarian":
    st.subheader(f"📚 {st.session_state['librarian_location']} நூலகத்திற்கான ஒதுக்கீடு மற்றும் நூல்கள் விவரங்கள்")
    neon_df = load_neon_database()
    if neon_df.empty:
        st.info("ℹ️ நூலகத் தரவுகள் தற்பொழுது கிடைக்கவில்லை.")
    else:
        lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
        if lib_col_name:
            lib_specific_df = neon_df[neon_df[lib_col_name].astype(str).str.contains(st.session_state["librarian_location"], case=False, na=False)]
            if not lib_specific_df.empty:
                st.dataframe(lib_specific_df, use_container_width=True)
                csv_data = lib_specific_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 நூலகத் தரவுகளைப் பதிவிறக்குக (CSV)",
                    data=csv_data,
                    file_name=f"Library_Data_{st.session_state['librarian_location']}.csv",
                    mime="text/csv",
                    type="primary"
                )
            else:
                st.info(f"ℹ️ {st.session_state['librarian_location']} நூலகத்திற்குரிய தனிப்பட்ட நூல்கள் எதுவும் டேட்டாபேஸில் காணப்படவில்லை.")
        else:
            st.warning("⚠️ நூலகப் பெயர் அடையாளம் காணப்படவில்லை.")

elif current == "பதிவிறக்கம்" and st.session_state["user_role"] == "Librarian":
    st.subheader("📥 உங்கள் நூலக அறிக்கைப் பதிவிறக்கம்")
    st.info(f"{st.session_state['librarian_location']} நூலக அறிக்கைகளைப் பதிவிறக்கலாம்.")

elif st.session_state["user_role"] == "Admin":
    st.subheader(f"⚙️ நிர்வாகி பகுதி: {current}")
    st.info("Admin கணக்கின் கீழ் இப்பகுதியை நீங்கள் முழுமையாக நிர்வகிக்கலாம்.")

else:
    st.warning("⚠️ இந்தப் பகுதிக்குச் செல்ல உங்களுக்கு அனுமதி இல்லை.")
