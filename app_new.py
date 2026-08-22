import hashlib
import hmac
import streamlit as st


# ============================================================
# 1. 3D CUSTOM CSS & THEME
# ============================================================
def get_custom_css():
    return """
    <style>
    /* ---------- Global theme ---------- */
    :root {
        --navy: #071a38;
        --blue: #1565c0;
        --cyan: #00bcd4;
        --purple: #7b1fa2;
        --orange: #ef6c00;
        --green: #2e7d32;
        --slate: #263238;
        --glass: rgba(255,255,255,.82);
    }
    .stApp {
        background:
          radial-gradient(circle at 10% 10%, rgba(0,188,212,.15), transparent 28%),
          radial-gradient(circle at 90% 15%, rgba(123,31,162,.14), transparent 30%),
          linear-gradient(135deg, #eef5ff 0%, #f8fbff 48%, #edf3ff 100%);
    }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { visibility: hidden; }
    /* ---------- Main title ---------- */
    h1 {
        padding: 22px 28px !important;
        border-radius: 22px;
        color: white !important;
        background: linear-gradient(135deg, #071a38, #1565c0 58%, #00acc1);
        box-shadow: 0 12px 0 #041127, 0 20px 32px rgba(7,26,56,.25);
        letter-spacing: .3px;
        text-shadow: 2px 3px 3px rgba(0,0,0,.35);
    }
    h2, h3 {
        color: #092653 !important;
        letter-spacing: .2px;
    }
    /* ---------- Sidebar glass panel ---------- */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #071a38 0%, #0b2e63 55%, #082044 100%);
        border-right: 1px solid rgba(255,255,255,.15);
    }
    section[data-testid="stSidebar"] > div:first-child {
        padding: 1.2rem .85rem;
    }
    section[data-testid="stSidebar"] h3,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] label {
        color: white !important;
    }
    /* ---------- Sidebar 3D buttons ---------- */
    section[data-testid="stSidebar"] button {
        width: 100% !important;
        min-height: 58px !important;
        margin: 9px 0 !important;
        padding: 12px 15px !important;
        border: 1px solid rgba(255,255,255,.28) !important;
        border-radius: 16px !important;
        color: white !important;
        font-size: 14px !important;
        font-weight: 800 !important;
        text-align: left !important;
        letter-spacing: .15px;
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease !important;
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.38),
          0 6px 0 rgba(0,0,0,.32),
          0 12px 18px rgba(0,0,0,.25) !important;
    }
    section[data-testid="stSidebar"] button p {
        color: white !important;
        font-weight: 800 !important;
    }
    /* Logout */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(1) button {
        background: linear-gradient(145deg, #ef5350, #b71c1c) !important;
    }
    /* Menu colours */
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
        box-shadow:
          inset 0 1px 0 rgba(255,255,255,.48),
          0 9px 0 rgba(0,0,0,.30),
          0 18px 25px rgba(0,0,0,.32) !important;
    }
    section[data-testid="stSidebar"] button:active {
        transform: translateY(4px) !important;
        box-shadow: inset 0 2px 4px rgba(0,0,0,.35), 0 2px 0 rgba(0,0,0,.3) !important;
    }
    /* ---------- Inputs ---------- */
    div[data-baseweb="select"] > div,
    input, textarea {
        border-radius: 13px !important;
        border: 1px solid #b7c9e5 !important;
        background: rgba(255,255,255,.9) !important;
    }
    /* ---------- Main buttons ---------- */
    .stButton > button, .stDownloadButton > button,
    button[kind="primary"] {
        min-height: 46px;
        border: none !important;
        border-radius: 13px !important;
        color: white !important;
        font-weight: 800 !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 5px 0 #061b42, 0 9px 15px rgba(8,43,104,.25) !important;
        transition: all .18s ease !important;
    }
    .stButton > button:hover, .stDownloadButton > button:hover {
        transform: translateY(-3px);
        filter: brightness(1.12);
        box-shadow: 0 8px 0 #061b42, 0 14px 22px rgba(8,43,104,.32) !important;
    }
    .stButton > button:active, .stDownloadButton > button:active {
        transform: translateY(3px);
        box-shadow: 0 2px 0 #061b42 !important;
    }
    /* ---------- Cards and metrics ---------- */
    div[data-testid="stMetric"] {
        padding: 18px !important;
        border-radius: 18px;
        background: var(--glass);
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
    /* ---------- Alerts ---------- */
    div[data-testid="stAlert"] {
        border-radius: 15px !important;
        box-shadow: 0 5px 14px rgba(30,70,120,.10);
    }
    /* ---------- Mobile responsive ---------- */
    @media (max-width: 768px) {
        h1 { font-size: 1.35rem !important; padding: 17px !important; }
        section[data-testid="stSidebar"] button { min-height: 52px !important; font-size: 13px !important; }
    }
    
    /* ---------- Portal Badge ---------- */
    .portal-badge {
        display: inline-block;
        margin-bottom: 12px;
        padding: 9px 18px;
        border-radius: 999px;
        color: white;
        font-size: 12px;
        font-weight: 900;
        letter-spacing: 1px;
        background: linear-gradient(135deg, #00acc1, #1565c0);
        box-shadow: 0 5px 0 #064276, 0 10px 18px rgba(0,80,150,.25);
    }
    .portal-badge span { margin-right: 7px; font-size: 16px; }
    </style>
    """

# CSS-ஐ அப்ளிகேஷனில் இணைக்கிறோம்
st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================
# 2. MULTI-USER SECURE LOGIN (HASHED)
# ============================================================
# கடவுச்சொல் ஸ்பேஸ் இல்லாமல் "Basswood123456" என அமைக்கப்பட்டுள்ளது.
BASSWOOD_HASH = hashlib.sha256("Basswood123456".encode("utf-8")).hexdigest()

USERS = {
    "9842759306": {
        "name": "Admin",
        "password_hash": BASSWOOD_HASH,
        "role": "admin",
        "pages": "all",
    },
    "9787555290": {
        "name": "Task 1 User 1",
        "password_hash": BASSWOOD_HASH,
        "role": "task1",
        "pages": ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"],
    },
    "9751687939": {
        "name": "Task 1 User 2",
        "password_hash": BASSWOOD_HASH,
        "role": "task1",
        "pages": ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"],
    },
}

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def authenticate_user(phone, password):
    phone = str(phone).strip()
    password = str(password)

    user = USERS.get(phone)
    if not user:
        return None

    entered_hash = hash_password(password)
    if hmac.compare_digest(entered_hash, user["password_hash"]):
        return user

    return None

def show_login_page():
    # 3D Portal Badge
    st.markdown(
        """
        <div class="portal-badge" style="display:flex; justify-content:center; max-width: max-content; margin: 0 auto 20px auto;">
            <span>📚</span> DISTRICT LIBRARY ADMINISTRATION PORTAL
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #0b2e63 !important; font-weight: 900;">பணி போர்ட்டல்</h2>
            <p style="color: #546e7a;">2026 புதிய நூல்கள் விநியோகம்</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        with st.form("secure_multi_user_login"):
            phone = st.text_input("📱 அலைபேசி எண்", max_chars=10, placeholder="10 இலக்க எண்ணை உள்ளிடவும்")
            password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
            submitted = st.form_submit_button("🔓 பாதுகாப்பாக உள்நுழைக", use_container_width=True)

        if submitted:
            if not phone.strip() or not phone.strip().isdigit() or len(phone.strip()) != 10:
                st.warning("⚠️ சரியான 10 இலக்க அலைபேசி எண்ணை உள்ளிடவும்.")
                return
            if not password:
                st.warning("⚠️ கடவுச்சொல்லை உள்ளிடவும்.")
                return

            authenticated_user = authenticate_user(phone, password)

            if authenticated_user:
                st.session_state["logged_in"] = True
                st.session_state["user_phone"] = phone.strip()
                st.session_state["user_name"] = authenticated_user["name"]
                st.session_state["user_role"] = authenticated_user["role"]
                st.session_state["allowed_pages"] = authenticated_user["pages"]
                st.session_state["login_attempts"] = 0
                st.rerun()
            else:
                st.session_state["login_attempts"] = st.session_state.get("login_attempts", 0) + 1
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


# ============================================================
# 3. LOGIN SESSION INITIALIZATION
# ============================================================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("login_attempts", 0)

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# 4. ACCESS CONTROL HELPERS
# ============================================================
def is_admin():
    return st.session_state.get("user_role") == "admin"

def can_access_page(page_name):
    if is_admin():
        return True
    return page_name in st.session_state.get("allowed_pages", [])

def logout():
    for key in ["logged_in", "user_phone", "user_name", "user_role", "allowed_pages", "current_page"]:
        st.session_state.pop(key, None)
    st.session_state["logged_in"] = False
    st.rerun()


# ============================================================
# 5. SIDEBAR NAVIGATION & 3D MENU
# ============================================================
st.sidebar.markdown(f"### 👤 {st.session_state.get('user_name', 'User')}")
st.sidebar.caption(f"Role: {st.session_state.get('user_role', 'user').upper()}")

if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    logout()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📌 முதன்மைப் பணிகள்")

ALL_MENU_ITEMS = [
    "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
    "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
    "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
    "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)",
    "⚙️ 5. Accession எண்கள் மேலாண்மை",
]

visible_menu_items = [item for item in ALL_MENU_ITEMS if can_access_page(item)]

if "current_page" not in st.session_state or st.session_state["current_page"] not in visible_menu_items:
    st.session_state["current_page"] = visible_menu_items[0]

for item in visible_menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()


# ============================================================
# 6. MAIN APPLICATION PAGE ROUTER
# ============================================================
# தலைப்பில் 3D Portal Badge-ஐ காட்டுகிறோம்
st.markdown(
    """
    <div class="portal-badge">
        <span>📚</span> DISTRICT LIBRARY ADMINISTRATION PORTAL
    </div>
    """,
    unsafe_allow_html=True
)

menu_choice = st.session_state["current_page"]

if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.title("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    # உங்கள் பழைய Task 1 கோடை (Code) இங்கே முழுமையாக ஒட்டவும்
    
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.title("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)")
    # உங்கள் பழைய Sync கோடை இங்கே முழுமையாக ஒட்டவும்

elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.title("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")
    # உங்கள் பழைய பதிப்பாளர் கோடை இங்கே முழுமையாக ஒட்டவும்

elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.title("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")
    # உங்கள் பழைய விநியோக கோடை இங்கே முழுமையாக ஒட்டவும்

elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.title("⚙️ 5. Accession எண்கள் மேலாண்மை")
    # உங்கள் பழைய Accession கோடை இங்கே முழுமையாக ஒட்டவும்
