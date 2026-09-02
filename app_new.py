import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="மாவட்ட மைய நூலகம், கிருஷ்ணகிரி",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Sans Tamil', sans-serif !important;
}

.stApp {
    background: #f8fafc;
}

[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

/* Top Header Bar */
.top-header-container {
    background: linear-gradient(135deg, #064e3b, #022c22);
    padding: 18px 24px;
    border-radius: 14px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 15px rgba(6,78,59,0.2);
    margin-bottom: 20px;
}

.header-title {
    font-size: 22px;
    font-weight: 800;
    line-height: 1.4;
    color: #ffffff;
}

.header-subtitle {
    font-size: 13px;
    color: #a7f3d0;
    font-weight: 600;
}

/* Compact Login Card Styling */
.login-card-wrapper {
    background: #ffffff;
    border-radius: 16px;
    padding: 25px 20px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
    border: 1.5px solid #a7f3d0;
    max-width: 380px;
    margin: 30px auto;
}

.login-header-box {
    text-align: center;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    border: 1.5px solid #a7f3d0;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 15px;
}

.login-title {
    color: #064e3b;
    font-size: 16px;
    font-weight: 800;
}

/* 3D Colorful Menu Buttons with Clear Text Styling */
div.stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    min-height: 52px !important;
    color: #ffffff !important;
    border: none !important;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.12), inset 0 2px 4px rgba(255, 255, 255, 0.3) !important;
    transition: all 0.2s ease-in-out;
}

div.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(0, 0, 0, 0.2), inset 0 2px 4px rgba(255, 255, 255, 0.4) !important;
    color: #ffffff !important;
}

/* Vibrant 3D Button Colors */
.btn-0 > button { background: linear-gradient(135deg, #2563eb, #1d4ed8) !important; }
.btn-1 > button { background: linear-gradient(135deg, #059669, #047857) !important; }
.btn-2 > button { background: linear-gradient(135deg, #7c3aed, #6d28d9) !important; }
.btn-3 > button { background: linear-gradient(135deg, #d97706, #b45309) !important; }
.btn-4 > button { background: linear-gradient(135deg, #0891b2, #0e7490) !important; }
.btn-5 > button { background: linear-gradient(135deg, #db2777, #be185d) !important; }
.btn-6 > button { background: linear-gradient(135deg, #dc2626, #b91c1c) !important; }
.btn-7 > button { background: linear-gradient(135deg, #0d9488, #0f766e) !important; }
.btn-8 > button { background: linear-gradient(135deg, #4f46e5, #4338ca) !important; }
.btn-9 > button { background: linear-gradient(135deg, #65a30d, #4d7c0f) !important; }
.btn-10 > button { background: linear-gradient(135deg, #ea580c, #c2410c) !important; }
.btn-11 > button { background: linear-gradient(135deg, #ca8a04, #a16207) !important; }
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
    "current_menu": "பிரிக்க", "sub_menu": "மாநில", "verified_records": [],
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
    <style>
    .stApp { background: linear-gradient(135deg, #064e3b, #022c22) !important; }
    </style>
    <div class="login-card-wrapper">
        <div class="login-header-box">
            <div style="font-size: 26px; margin-bottom: 4px;">📚</div>
            <div class="login-title">மாவட்ட மைய நூலகம்<br>கிருஷ்ணகிரி</div>
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

# --- Main Dashboard Header ---
st.markdown("""
<div class="top-header-container">
    <div>
        <div class="header-title">📚 மாவட்ட மைய நூலகம்</div>
        <div class="header-subtitle">கிருஷ்ணகிரி — புதிய நூல்கள் பகிர்மானம் 2026-27</div>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 8px; font-size: 14px;">
            👤 {} ({})
        </span>
    </div>
</div>
""".format(st.session_state["user_name"], st.session_state["user_role"]), unsafe_allow_html=True)

col_logout = st.columns([11, 1])
with col_logout[1]:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.query_params.clear()
        st.session_state.clear()
        st.rerun()

# --- Menu Items List with 3D Colors ---
menu_options = [
    ("🔀", "பிரிக்க"),
    ("📤", "அனுப்ப"),
    ("📊", "அறிக்கைகள்"),
    ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண் மாற்ற"),
    ("🗂️", "Master Data"),
    ("❌", "தவறான பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல் மாற்ற"),
    ("📥", "Excel பதிவிறக்கம்"),
    ("👥", "நூலகர் பார்வை ஆண்டு"),
    ("📂", "Excel அப்லோடு"),
    ("🏷️", "பகுப்பு எண் புதுப்பி")
]

cols = st.columns(len(menu_options))
for i, (icon, label) in enumerate(menu_options):
    with cols[i]:
        st.markdown(f'<div class="btn-{i}">', unsafe_allow_html=True)
        if st.button(f"{icon}\n{label}", key=f"menu_item_{i}", use_container_width=True):
            st.session_state["current_menu"] = label
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# Sub-menu for 'பகுப்பு எண் புதுப்பி'
if st.session_state["current_menu"] == "🏷️ பகுப்பு எண் புதுப்பி":
    st.markdown("### 🏷️ பகுப்பு எண் புதுப்பித்தல் துணை மெனு")
    sub_cols = st.columns(3)
    sub_menus = ["மாநில", "மாவட்ட", "கிளை"]
    for idx, sm in enumerate(sub_menus):
        with sub_cols[idx]:
            is_sub_active = st.session_state["sub_menu"] == sm
            if st.button(f"📌 {sm} பகுப்பு", key=f"submenu_{idx}", use_container_width=True, type="primary" if is_sub_active else "secondary"):
                st.session_state["sub_menu"] = sm
                st.rerun()
    st.markdown(f"**தற்போது தேர்ந்தெடுக்கப்பட்டது:** {st.session_state['sub_menu']} பகுப்பு எண் புதுப்பித்தல் பிரிவு.")
    st.markdown("---")

# Content Display
current = st.session_state["current_menu"]

if current == "🔀 பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Distribution / Splitting)")
    st.info("இங்கு நூல்களை உரிய வழிமுறைகளின்படி பிரிக்கலாம்.")

elif current == "📤 அனுப்ப":
    st.subheader("📤 நூல்களை அனுப்பும் பகுதி (Dispatch)")
    st.info("நூலகங்களுக்கு நூல்களை அனுப்பும் விவரங்களை இங்கே பதிவிடலாம்.")

elif current == "📊 அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் (Reports)")
    st.info("தேவையான அனைத்து அறிக்கைகளையும் இங்கு பார்வையிடலாம் மற்றும் பதிவிறக்கலாம்.")

elif current == "⚠️ கவனிக்க":
    st.subheader("⚠️ கவனிக்க — ஒரே தலைப்பில் வேறு விலைகள் உள்ளவை (Dashboard)")
    st.markdown("""
    * **1001 அரேபிய இரவுகள் - தொகுதி 1** (₹380 | ₹510 | ₹530)
    * **21-ம் நூற்றாண்டின் அறிவியல் அதிசயங்கள்** (₹100 | ₹280)
    * **A JOURNEY TO THE CENTRE OF THE EARTH** (₹109 | ₹99)
    * **A Modern Approach To Verbal & Non-Verbal Reasoning: Tamil Edition** (₹725 | ₹899)
    """)

elif current == "🔢 பதிவெண் மாற்ற":
    st.subheader("🔢 பதிவெண் மாற்றும் பகுதி (Change Registration No)")
    st.info("நூல்களின் பதிவெண்களைத் திருத்தம் செய்ய அல்லது மாற்ற.")

elif current == "🗂️ Master Data":
    st.subheader("🗂️ Master Data மேலாண்மை")
    st.info("அடிப்படைத் தரவுகளைச் சேமிக்கவும் நிர்வகிக்கவும்.")

elif current == "❌ தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல் (Delete Invalid Records)")
    st.info("தவறாகப் பதிவு செய்யப்பட்ட தரவுகளை நீக்க.")

elif current == "🔑 கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Change Password)")
    st.info("பயனர் கடவுச்சொல்லைப் புதுப்பிக்க.")

elif current == "📥 Excel பதிவிறக்கம்":
    st.subheader("📥 Excel அறிக்கை பதிவிறக்கம்")
    st.info("தேவையான தரவுகளை Excel வடிவில் பதிவிறக்கம் செய்ய.")

elif current == "👥 நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள்")
    st.info("நூலகர்களின் பார்வைக் காலங்களை நிர்வகிக்க.")

elif current == "📂 Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் (Excel Upload)")
    st.info("புதிய தரவுத் தொகுப்புகளை Excel மூலம் பதிவேற்றுக.")

elif current == "🏷️ பகுப்பு எண் புதுப்பி":
    st.subheader(f"🏷️ பகுப்பு எண் புதுப்பித்தல் — {st.session_state['sub_menu']}")
    st.success(f"தங்கள் தேர்வு: {st.session_state['sub_menu']} பகுப்புக்கான விபரங்களை இங்கே உள்ளிடலாம்/புதுப்பிக்கலாம்.")
