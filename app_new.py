import hashlib
import hmac
import io
import os
import secrets as py_secrets
from datetime import datetime
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
    padding: 16px 22px;
    border-radius: 12px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 15px rgba(6,78,59,0.2);
    margin-bottom: 20px;
}

.header-title {
    font-size: 20px;
    font-weight: 800;
    line-height: 1.3;
    color: #ffffff;
}

.header-subtitle {
    font-size: 13px;
    color: #a7f3d0;
    font-weight: 600;
}

/* Compact Top-Aligned Login Card */
.login-top-container {
    display: flex;
    justify-content: center;
    align-items: flex-start;
    padding-top: 30px;
}

.login-card-wrapper {
    background: #ffffff;
    border-radius: 16px;
    padding: 22px 25px;
    box-shadow: 0 10px 25px rgba(0, 0, 0, 0.25);
    border: 1.5px solid #a7f3d0;
    width: 100%;
    max-width: 380px;
}

.login-header-box {
    text-align: center;
    background: linear-gradient(135deg, #ecfdf5, #d1fae5);
    border: 1.5px solid #a7f3d0;
    border-radius: 10px;
    padding: 10px;
    margin-bottom: 12px;
}

.login-title {
    color: #064e3b;
    font-size: 15px;
    font-weight: 800;
}

/* Custom HTML Menu Buttons Styling */
.custom-menu-btn {
    display: block;
    width: 100%;
    background: linear-gradient(135deg, #065f46, #047857);
    color: white !important;
    padding: 10px 4px;
    border-radius: 10px;
    text-align: center;
    font-weight: 700;
    font-size: 11px;
    text-decoration: none;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    transition: all 0.2s ease-in-out;
    min-height: 52px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    line-height: 1.3;
    border: 1px solid #047857;
}

.custom-menu-btn:hover {
    background: linear-gradient(135deg, #047857, #065f46);
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(4, 120, 87, 0.3);
    color: white !important;
}

.custom-menu-btn.active {
    background: linear-gradient(135deg, #1e3a8a, #1e40af) !important;
    border: 2px solid #93c5fd !important;
    box-shadow: 0 0 12px rgba(30, 64, 175, 0.5);
}

/* Logout Button Special Unique Color */
.logout-custom-btn {
    display: block;
    width: 100%;
    background: linear-gradient(135deg, #991b1b, #7f1d1d);
    color: white !important;
    padding: 8px 14px;
    border-radius: 10px;
    text-align: center;
    font-weight: 700;
    font-size: 12px;
    text-decoration: none;
    box-shadow: 0 4px 6px rgba(153, 27, 27, 0.2);
    transition: all 0.2s ease-in-out;
    border: 1px solid #7f1d1d;
}

.logout-custom-btn:hover {
    background: linear-gradient(135deg, #b91c1c, #991b1b);
    transform: translateY(-2px);
    box-shadow: 0 6px 12px rgba(185, 28, 28, 0.4);
    color: white !important;
}

/* Running Live News Ticker Bar Styling */
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
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.ticker-text {
    display: inline-block;
    animation: marquee 25s linear infinite;
}

.ticker-text:hover {
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
    "current_menu": None, "sub_menu": "மாநில", "verified_records": [],
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

# Handle Query Param Menu Navigation safely
query_menu = st.query_params.get("menu")
if query_menu and not st.session_state.get("menu_initialized"):
    st.session_state["current_menu"] = query_menu
    st.session_state["menu_initialized"] = True

query_logout = st.query_params.get("logout")
if query_logout == "true":
    st.query_params.clear()
    st.session_state.clear()
    st.rerun()

def show_login_page():
    st.markdown("""
    <style>
    .stApp { background: linear-gradient(135deg, #064e3b, #022c22) !important; }
    </style>
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
        <span style="background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 8px; font-size: 13px;">
            👤 {} ({})
        </span>
    </div>
</div>
""".format(st.session_state["user_name"], st.session_state["user_role"]), unsafe_allow_html=True)

# Logout Button Column
col_logout = st.columns([11, 1])
with col_logout[1]:
    current_role = st.session_state.get("user_role", "Admin")
    current_token = make_session_token(current_role)
    st.markdown(f'<a href="?role={current_role}&token={current_token}&logout=true" target="_self" class="logout-custom-btn">🚪 வெளியேறு</a>', unsafe_allow_html=True)

# --- Menu Items List in Single Straight Line ---
menu_options = [
    ("🔀", "பிரிக்க"),
    ("📤", "அனுப்ப"),
    ("📊", "அறிக்கைகள்"),
    ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண்<br>மாற்ற"),
    ("🗂️", "Master<br>Data"),
    ("❌", "தவறான<br>பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல்<br>மாற்ற"),
    ("📥", "Excel<br>பதிவிறக்கம்"),
    ("👥", "நூலகர்<br>பார்வை ஆண்டு"),
    ("📂", "Excel<br>அப்லோடு"),
    ("🏷️", "பகுப்பு எண்<br>புதுப்பி")
]

cols = st.columns(len(menu_options))
for i, (icon, label_html) in enumerate(menu_options):
    raw_label = label_html.replace("<br>", " ")
    is_active = st.session_state["current_menu"] == raw_label
    active_class = " active" if is_active else ""
    
    current_role = st.session_state.get("user_role", "Admin")
    current_token = make_session_token(current_role)
    
    with cols[i]:
        st.markdown(
            f'<a href="?role={current_role}&token={current_token}&menu={raw_label}" target="_self" class="custom-menu-btn{active_class}">'
            f'<span style="font-size: 14px; margin-bottom: 2px;">{icon}</span>'
            f'<span>{label_html}</span>'
            f'</a>',
            unsafe_allow_html=True
        )

# --- Horizontal Divider Line ---
st.markdown("---")

# --- Running Live News Ticker Bar ---
today_str = datetime.now().strftime("%d/%m/%Y")
st.markdown(f"""
<div class="ticker-container">
    <div class="ticker-badge">🔴 Live News</div>
    <div class="ticker-text">
        📚 பெறப்பட்ட நூல்கள் : <b>45,305</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        ✅ பிரிக்கப்பட்டது : <b>2</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        ⏳ மீதம் பிரிக்க வேண்டியது : <b>45,303</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        📤 அனுப்பப்பட்டது : <b>0</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        🗓️ இன்று ({today_str}) பிரிக்கப்பட்டது : <b>0</b>
    </div>
</div>
""", unsafe_allow_html=True)

# Content Display
current = st.session_state["current_menu"]

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை (உதாரணமாக **'🔀 பிரிக்க'**) தேர்வு செய்யவும்.")

elif current == "பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    
    # --- Neno டேபிளிலிருந்து உண்மையான தரவுகளைப் படித்தல் ---
    @st.cache_data
    def load_neno_database():
        # உங்கள் Neno டேபிள் ஃபைலின் உண்மையான பெயருக்கு ஏற்ப மாற்றிக் கொள்ளவும் (எ.கா: "neno_data.xlsx" அல்லது உங்கள் DataFrame variable)
        # தற்போது உங்களுடைய Neno டேபிள் ஃபைல் இணைக்கப்படவில்லை எனில் பிழை வராமல் இருக்க செக் செய்யப்பட்டுள்ளது:
        try:
            return pd.read_excel("neno_database.xlsx")
        except Exception:
            # உங்களுடைய சொந்த Neno டேபிள் ஃபைல் கோப்புப் பெயர் இங்கே கொடுக்கப்பட வேண்டும்
            # உதாரணத்திற்கு உங்களுடைய உண்மையான டேபிள் பெயர் neno_df எனில் அதை இங்கே பயன்படுத்தலாம்
            return pd.DataFrame(columns=["பதிப்பாளர் பெயர்", "நூல் தலைப்பு", "ஆசிரியர்", "விலை", "நூலகத்தின் எண்ணிக்கை", "பகுப்பு"])

    neno_df = load_neno_database()

    if neno_df.empty or "பதிப்பாளர் பெயர்" not in neno_df.columns:
        st.warning("⚠️ Neno டேபிளில் இருந்து தரவுகள் கிடைக்கவில்லை. தயவுசெய்து உங்களது Neno டேபிள் ஃபைல் பாதையை (File Path) சரியாக இணைக்கவும்.")
    else:
        all_publishers = sorted(neno_df["பதிப்பாளர் பெயர்"].dropna().unique().tolist())

        # Live Search / Dropdown (Type first 2-3 letters to filter publishers)
        selected_publisher = st.selectbox(
            "🔍 பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும் (பதிப்பகத்தின் முதல் எழுத்துக்களை உள்ளிடவும் / தேடவும்):",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers,
            key="publisher_dropdown"
        )

        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            pub_filtered_df = neno_df[neno_df["பதிப்பாளர் பெயர்"] == selected_publisher]
            
            total_books = len(pub_filtered_df)
            total_titles = pub_filtered_df["நூல் தலைப்பு"].nunique() if "நூல் தலைப்பு" in pub_filtered_df.columns else 0
            authors_list = ", ".join(pub_filtered_df["ஆசிரியர்"].unique().tolist()) if "ஆசிரியர்" in pub_filtered_df.columns else "-"
            
            if "விலை" in pub_filtered_df.columns:
                min_price = pub_filtered_df["விலை"].min()
                max_price = pub_filtered_df["விலை"].max()
                price_range = f"₹{min_price} - ₹{max_price}" if min_price != max_price else f"₹{min_price}"
            else:
                price_range = "₹0"
                
            lib_count = pub_filtered_df["நூலகத்தின் எண்ணிக்கை"].iloc[0] if "நூலகத்தின் எண்ணிக்கை" in pub_filtered_df.columns else 112

            # --- Publisher Details Summary Box with Icons ---
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border: 1.5px solid #34d399; padding: 16px; border-radius: 12px; margin: 15px 0; box-shadow: 0 4px 10px rgba(5,150,105,0.1);">
                <div style="font-size: 15px; font-weight: 800; color: #064e3b; margin-bottom: 10px; border-bottom: 1px solid #6ee7b7; padding-bottom: 6px;">
                    🏢 தேர்ந்தெடுக்கப்பட்ட பதிப்பகம்: <span style="color: #047857;">{selected_publisher}</span>
                </div>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; font-size: 13px; color: #065f46;">
                    <div>📚 <b>மொத்த நூல்கள்:</b> {total_books}</div>
                    <div>📑 <b>தலைப்புகள்:</b> {total_titles}</div>
                    <div>✍️ <b>ஆசிரியர்(கள்):</b> {authors_list}</div>
                    <div>💰 <b>விலை:</b> {price_range}</div>
                    <div>🏛️ <b>நூலகத்தின் எண்ணிக்கை:</b> {lib_count}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### 📋 அனுமதிக்கப்பட்டுள்ள தலைப்புகள் தேர்வு விவரம் (Allowed Titles Selection)")
            
            # Interactive Data Editor for selecting allowed titles
            if "தேர்வு" not in pub_filtered_df.columns:
                pub_filtered_df.insert(0, "தேர்வு", True)
                
            edited_titles = st.data_editor(pub_filtered_df, hide_index=True, use_container_width=True)
            
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("💾 சேமி & பிரிக்க", type="primary", use_container_width=True):
                    st.success("✅ தேர்ந்தெடுக்கப்பட்ட நூல்கள் வெற்றிகரமாகப் பிரிக்கப்பட்டு சேமிக்கப்பட்டன!")

elif current == "அனுப்ப":
    st.subheader("📤 நூல்களை அனுப்பும் பகுதி (Dispatch)")
    st.info("நூலகங்களுக்கு நூல்களை அனுப்பும் விவரங்களை இங்கே பதிவிடலாம்.")

elif current == "அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் (Reports)")
    st.info("தேவையான அனைத்து அறிக்கைகளையும் இங்கு பார்வையிடலாம் மற்றும் பதிவிறக்கலாம்.")

elif current == "கவனிக்க":
    st.subheader("⚠️ கவனிக்க — ஒரே தலைப்பில் வேறு விலைகள் உள்ளவை (Dashboard)")
    st.markdown("""
    * **1001 அரேபிய இரவுகள் - தொகுதி 1** (₹380 | ₹510 | ₹530)
    * **21-ம் நூற்றாண்டின் அறிவியல் அதிசயங்கள்** (₹100 | ₹280)
    * **A JOURNEY TO THE CENTRE OF THE EARTH** (₹109 | ₹99)
    * **A Modern Approach To Verbal & Non-Verbal Reasoning: Tamil Edition** (₹725 | ₹899)
    """)

elif current == "பதிவெண் மாற்ற":
    st.subheader("🔢 பதிவெண் மாற்றும் பகுதி (Change Registration No)")
    st.info("நூல்களின் பதிவெண்களைத் திருத்தம் செய்ய அல்லது மாற்ற.")

elif current == "Master Data":
    st.subheader("🗂️ Master Data மேலாண்மை")
    st.info("அடிப்படைத் தரவுகளைச் சேமிக்கவும் நிர்வகிக்கவும்.")

elif current == "தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல் (Delete Invalid Records)")
    st.info("தவறாகப் பதிவு செய்யப்பட்ட தரவுகளை நீக்க.")

elif current == "கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Change Password)")
    st.info("பயனர் கடவுச்சொல்லைப் புதுப்பிக்க.")

elif current == "Excel பதிவிறக்கம்":
    st.subheader("📥 Excel அறிக்கை பதிவிறக்கம்")
    st.info("தேவையான தரவுகளை Excel வடிவில் பதிவிறக்கம் செய்ய.")

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள்")
    st.info("நூலகர்களின் பார்வைக் காலங்களை நிர்வகிக்க.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் (Excel Upload)")
    st.info("புதிய தரவுத் தொகுப்புகளை Excel மூலம் பதிவேற்றுக.")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல்")
    st.success("பகுப்பு எண் புதுப்பித்தல் விபரங்களை இங்கே உள்ளிடலாம்.")
