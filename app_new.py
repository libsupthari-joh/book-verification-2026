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
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

USERS_DATABASE = {
    "Admin": {"password_hash": hash_password("Hari@@1979"), "name": "முதன்மை நிர்வாகி (Admin)"},
    "DCL Staff": {"password_hash": hash_password("123456"), "name": "DCL Staff"},
    "TNDPL01617": {"password_hash": hash_password("123456789"), "name": "சிந்தகம்பள்ளி நூலகர்", "lib_name": "CHINTHAKAMPALLI"},
    "TNDPL01586": {"password_hash": hash_password("123456789"), "name": "போச்சம்பள்ளி நூலகர்", "lib_name": "POCHAMPALLI"},
}

def authenticate_user(role_key, password, librarian_id=""):
    if role_key == "Librarian":
        user = USERS_DATABASE.get(librarian_id)
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
        pass

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
    "logged_in": False, "user_role": None, "user_name": "", "librarian_id": "", "librarian_location": "",
    "current_menu": None, "temp_distributed_list": [], 
    "submitted_reports": load_submitted_reports_from_db()
}.items():
    st.session_state.setdefault(key, default)

def show_login_page():
    st.markdown("""
    <div class="login-top-container">
        <div class="login-card-wrapper">
            <div class="login-header-box">
                <div style="font-size: 22px; margin-bottom: 2px;">📚</div>
                <div class="login-title">மாவட்ட மைய நூலகம்<br>கிருஷ்ணகிரி</div>
            </div>
    """, unsafe_allow_html=True)
    
    with st.form("secure_login_form"):
        selected_role = st.selectbox("பயனர் வகை (User)", ["-- தேர்ந்தெடுக்கவும் --", "Admin", "DCL Staff", "Librarian"])
        lib_id_input = st.text_input("🆔 நூலகர் ஐடி (Librarian ID)", placeholder="எ.கா: TNDPL01617") if selected_role == "Librarian" else ""
        password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
        submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        
    st.markdown("</div></div>", unsafe_allow_html=True)
    
    if submitted:
        if selected_role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
        elif selected_role == "Librarian" and not lib_id_input:
            st.warning("⚠️ தயவுசெய்து உங்களது Librarian ID-ஐ உள்ளிடவும்!")
        else:
            user = authenticate_user(selected_role, password, lib_id_input)
            if not user:
                st.error("❌ தவறான ஐடி அல்லது கடவுச்சொல்!")
            else:
                lib_loc = user.get("lib_name", "") if selected_role == "Librarian" else ""
                disp_name = f"{user['name']} ({lib_id_input})" if selected_role == "Librarian" else user["name"]
                st.session_state.update(
                    logged_in=True, 
                    user_role=selected_role, 
                    user_name=disp_name, 
                    librarian_id=lib_id_input,
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
        st.session_state["librarian_id"] = ""
        st.session_state["librarian_location"] = ""
        st.rerun()

if st.session_state["user_role"] == "Librarian":
    menu_options = [("📊", "நூலகத் தரவுகள்"), ("📥", "பதிவிறக்கம்")]
else:
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

elif st.session_state["user_role"] == "Librarian":
    neon_df = load_neon_database()
    id_col = next((c for c in neon_df.columns if 'librarian_id' in c or 'lib_id' in c), None)
    lib_filter_df = neon_df[neon_df[id_col].astype(str).str.strip().str.upper() == st.session_state["librarian_id"].strip().upper()] if not neon_df.empty and id_col else pd.DataFrame()

    if current == "நூலகத் தரவுகள்":
        st.subheader(f"📚 நூலகர் விவரங்கள்: {st.session_state['user_name']}")
        if not lib_filter_df.empty:
            st.dataframe(lib_filter_df, use_container_width=True)
        else:
            st.info("ℹ️ தரவுகள் எதுவும் காணப்படவில்லை.")
    elif current == "பதிவிறக்கம்":
        st.subheader("📥 நூலகத் தரவுகள் பதிவிறக்கம்")
        if not lib_filter_df.empty:
            st.dataframe(lib_filter_df, use_container_width=True)
            st.download_button("📥 பதிவிறக்குக (CSV)", data=lib_filter_df.to_csv(index=False).encode('utf-8-sig'), file_name=f"Library_Data.csv", mime="text/csv", type="primary")
        else:
            st.info("ℹ️ பதிவிறக்கம் செய்யத் தரவுகள் இல்லை.")

else:
    if current == "நூலகர் பார்வை ஆண்டு":
        st.subheader("👥 நூலகர் ஆண்டு பார்வை & ஐடி வாரியான விவரங்கள் (Librarian Annual View)")
        neon_df = load_neon_database()
        
        if neon_df.empty:
            st.warning("⚠️ டேட்டாபேஸ் தரவுகள் கிடைக்கவில்லை.")
        else:
            id_col = next((c for c in neon_df.columns if 'librarian_id' in c or 'lib_id' in c), None)
            lib_name_col = next((c for c in neon_df.columns if 'library_name' in c or 'library' in c), None)
            
            if id_col:
                unique_ids = sorted([str(x) for x in neon_df[id_col].dropna().unique() if str(x).strip() != ""])
                selected_lib_id = st.selectbox("🔍 நூலகர் ஐடியைத் தேர்ந்தெடுக்கவும் (Select Librarian ID):", ["-- ஐடியைத் தேர்ந்தெடுக்கவும் --"] + unique_ids)
                
                if selected_lib_id != "-- ஐடியைத் தேர்ந்தெடுக்கவும் --":
                    filtered_lib_df = neon_df[neon_df[id_col].astype(str).str.strip().str.upper() == selected_lib_id.strip().upper()]
                    
                    lib_name_val = filtered_lib_df[lib_name_col].iloc[0] if lib_name_col and not filtered_lib_df.empty else "தெரியவில்லை"
                    st.markdown(f"""
                    <div style="background: #ecfdf5; padding: 12px; border-radius: 8px; border: 1px solid #34d399; margin-bottom: 15px; color: #064e3b; font-weight: 700;">
                        🏛️ நூலக ஐடி: {selected_lib_id} &nbsp;&nbsp;|&nbsp;&nbsp; 📚 நூலகம்: {lib_name_val} &nbsp;&nbsp;|&nbsp;&nbsp; 📦 மொத்த புத்தகங்கள்: {len(filtered_lib_df)}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.dataframe(filtered_lib_df, use_container_width=True)
                    
                    csv_bytes = filtered_lib_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label=f"📥 {selected_lib_id} நூலகத் தரவுகளைப் பதிவிறக்குக (CSV)",
                        data=csv_bytes,
                        file_name=f"Librarian_Data_{selected_lib_id}.csv",
                        mime="text/csv",
                        type="primary"
                    )
            else:
                st.error("❌ டேட்டாபேஸில் 'librarian_id' அல்லது 'lib_id' என்ற العمود (Column) கண்டுபிடிக்கப்படவில்லை.")

    elif current == "பிரிக்க":
        st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி")
        st.info("பிரிக்கின்ற பணி மற்றும் பிற நிர்வாகப் பணிகள் வழக்கம்போல செயல்படுகின்றன.")
    else:
        st.subheader(f"⚙️ நிர்வாகி பகுதி: {current}")
        st.info(f"'{current}' பகுதிக்கான செயல்பாடுகள் فعالவாக உள்ளன.")
