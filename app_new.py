import hashlib
import hmac
import time
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="மாவட்ட நூலக ஆணைக்குழு - பணி போர்ட்டல்",
    page_icon="📚",
    layout="wide",
)


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

    /* Logout button style */
    section[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(1) button {
        background: linear-gradient(145deg, #ef5350, #b71c1c) !important;
    }

    /* Menu colors */
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

    /* ---------- Inputs & Cards ---------- */
    div[data-baseweb="select"] > div, input, textarea {
        border-radius: 13px !important;
        border: 1px solid #b7c9e5 !important;
        background: rgba(255,255,255,.9) !important;
    }
    .stButton > button, .stDownloadButton > button, button[kind="primary"] {
        min-height: 46px;
        border: none !important;
        border-radius: 13px !important;
        color: white !important;
        font-weight: 800 !important;
        background: linear-gradient(145deg, #1565c0, #082b68) !important;
        box-shadow: 0 5px 0 #061b42, 0 9px 15px rgba(8,43,104,.25) !important;
        transition: all .18s ease !important;
    }
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


st.markdown(get_custom_css(), unsafe_allow_html=True)


# ============================================================
# 2. MULTI-USER AUTHENTICATION
# ============================================================
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
    user = USERS.get(phone)
    if not user:
        return None
    entered_hash = hash_password(str(password))
    if hmac.compare_digest(entered_hash, user["password_hash"]):
        return user
    return None


def show_login_page():
    st.markdown(
        """
        <div class="portal-badge" style="display:flex; justify-content:center; max-width: max-content; margin: 20px auto;">
            <span>📚</span> DISTRICT LIBRARY ADMINISTRATION PORTAL
        </div>
        <div style="text-align: center; margin-bottom: 25px;">
            <h2 style="color: #0b2e63 !important; font-weight: 900;">பணி போர்ட்டல்</h2>
            <p style="color: #546e7a;">2026 புதிய நூல்கள் விநியோகம்</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, form_col, _ = st.columns([1, 2, 1])
    with form_col:
        with st.form("secure_login_form"):
            phone = st.text_input(
                "📱 அலைபேசி எண்",
                max_chars=10,
                placeholder="10 இலக்க எண்ணை உள்ளிடவும்",
            )
            password = st.text_input(
                "🔑 கடவுச்சொல்",
                type="password",
                placeholder="கடவுச்சொல்லை உள்ளிடவும்",
            )
            submitted = st.form_submit_button(
                "🔓 பாதுகாப்பாக உள்நுழைக", use_container_width=True
            )

        if submitted:
            if (
                not phone.strip()
                or not phone.strip().isdigit()
                or len(phone.strip()) != 10
            ):
                st.warning("⚠️ சரியான 10 இலக்க அலைபேசி எண்ணை உள்ளிடவும்.")
                return
            if not password:
                st.warning("⚠️ கடவுச்சொல்லை உள்ளிடவும்.")
                return

            user = authenticate_user(phone, password)
            if user:
                st.session_state["logged_in"] = True
                st.session_state["user_phone"] = phone.strip()
                st.session_state["user_name"] = user["name"]
                st.session_state["user_role"] = user["role"]
                st.session_state["allowed_pages"] = user["pages"]
                st.rerun()
            else:
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


# Login Enforcement
st.session_state.setdefault("logged_in", False)
if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# 3. ACCESS CONTROL & NAVIGATION
# ============================================================
def is_admin():
    return st.session_state.get("user_role") == "admin"


def can_access_page(page_name):
    if is_admin():
        return True
    return page_name in st.session_state.get("allowed_pages", [])


def logout():
    for key in [
        "logged_in",
        "user_phone",
        "user_name",
        "user_role",
        "allowed_pages",
        "current_page",
    ]:
        st.session_state.pop(key, None)
    st.session_state["logged_in"] = False
    st.rerun()


# Sidebar setup
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

if (
    "current_page" not in st.session_state
    or st.session_state["current_page"] not in visible_menu_items
):
    st.session_state["current_page"] = visible_menu_items[0]

for item in visible_menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()


# ============================================================
# 4. MAIN PAGES LOGIC
# ============================================================
st.markdown(
    """
    <div class="portal-badge">
        <span>📚</span> DISTRICT LIBRARY ADMINISTRATION PORTAL
    </div>
    """,
    unsafe_allow_html=True,
)

menu_choice = st.session_state["current_page"]

# ------------------------------------------------------------
# PAGE 1: பெறப்பட்ட நூல்கள் சரிபார்ப்பு
# ------------------------------------------------------------
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.title("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")

    col1, col2, col3 = st.columns(3)
    col1.metric("மொத்த நூல்கள்", "12,450", "2026 Procurement")
    col2.metric("சரிபார்க்கப்பட்டவை", "8,320", "66.8%")
    col3.metric("நிலுவையில் உள்ளவை", "4,130", "33.2%")

    st.markdown("---")
    st.subheader("📋 புதிய நூல் சரிபார்ப்பு படிவம்")

    with st.form("book_verify_form"):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            book_id = st.text_input(
                "நூல் ஐடி / ISBN", placeholder="எ.கா: BK-2026-0891"
            )
            title = st.text_input("நூலின் பெயர்", placeholder="புத்தகத்தின் தலைப்பு")
        with f_col2:
            publisher = st.text_input(
                "பதிப்பாளர் பெயர்", placeholder="பதிப்பகத்தின் பெயர்"
            )
            copies = st.number_input("பிரதிகளின் எண்ணிக்கை", min_value=1, value=5)

        status = st.selectbox(
            "சரிபார்ப்பு நிலை", ["சரிபார்க்கப்பட்டது (Verified)", "சேதம் / குறைபாடு (Damaged)", "நிலுவை (Pending)"]
        )
        submit_btn = st.form_submit_button("💾 சரிபார்ப்பை சேமிக்குக")

        if submit_btn:
            if book_id and title:
                st.success(
                    f"✅ நூல் '{title}' ({book_id}) வெற்றிகரமாக பதிவேற்றப்பட்டது!"
                )
            else:
                st.warning("⚠️ தயவுசெய்து நூல் ஐடி மற்றும் தலைப்பை உள்ளிடவும்.")

    st.subheader("📊 சமீபத்திய சரிபார்ப்பு தரவுகள்")
    sample_data = pd.DataFrame(
        {
            "நூல் ஐடி": [
                "BK-2026-001",
                "BK-2026-002",
                "BK-2026-003",
                "BK-2026-004",
            ],
            "நூலின் பெயர்": [
                "பொன்னியின் செல்வன்",
                "திருக்குறள் தெளிவுரை",
                "கணினி அறிவியல் தொடக்கம்",
                "தமிழ் இலக்கிய வரலாறு",
            ],
            "பதிப்பகம்": [
                "விகடன் பிரசுரம்",
                "பூம்புகார் பதிப்பகம்",
                "நியூ செஞ்சுரி புக் ஹவுஸ்",
                "சாகித்திய அகாதெமி",
            ],
            "பிரதிகள்": [10, 5, 8, 12],
            "நிலை": [
                "Verified",
                "Verified",
                "Pending",
                "Verified",
            ],
        }
    )
    st.dataframe(sample_data, use_container_width=True)

# ------------------------------------------------------------
# PAGE 2: Google Sheet தரவு ஒத்திசைவு
# ------------------------------------------------------------
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.title("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)")

    st.info(
        "💡 Google Sheet மற்றும் உள்ளூர் தரவுத்தளத்தை ஒத்திசைக்க கீழே உள்ள பொத்தானைக் கிளிக் செய்யவும்."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.metric("கடைசியாக ஒத்திசைக்கப்பட்ட நேரம்", "22-08-2026 08:30 PM")
    with c2:
        st.metric("ஒத்திசைவு நிலை", "இணைக்கப்பட்டுள்ளது", "Live Cloud Sync")

    if st.button("🚀 Google Sheet தரவை ஒத்திசை (Sync Now)", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i in range(1, 101):
            time.sleep(0.02)
            progress_bar.progress(i)
            status_text.text(f"Google Sheet உடன் இணைக்கப்படுகிறது... {i}%")

        status_text.text("✅ தரவுகள் வெற்றிகரமாக ஒத்திசைக்கப்பட்டன!")
        st.success("🎉 12,450 பதிவுகள் Google Sheet உடன் வெற்றிகரமாக புதுப்பிக்கப்பட்டன.")

# ------------------------------------------------------------
# PAGE 3: மொத்த பதிப்பாளர் விவரங்கள் (480)
# ------------------------------------------------------------
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.title("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")

    st.metric("மொத்த பதிப்பாளர்கள்", "480", "பதிவு செய்யப்பட்டவை")

    search = st.text_input("🔍 பதிப்பாளர் பெயரைத் தேடுக...", "")

    publishers_list = [
        {"ஐடி": "PUB-001", "பதிப்பகம்": "விகடன் பிரசுரம்", "மாவட்டம்": "சென்னை", "வழங்கிய நூல்கள்": 145},
        {"ஐடி": "PUB-002", "பதிப்பகம்": "கிழக்கு பதிப்பகம்", "மாவட்டம்": "சென்னை", "வழங்கிய நூல்கள்": 210},
        {"ஐடி": "PUB-003", "பதிப்பகம்": "நியூ செஞ்சுரி புக் ஹவுஸ்", "மாவட்டம்": "மதுரை", "வழங்கிய நூல்கள்": 320},
        {"ஐடி": "PUB-004", "பதிப்பகம்": "பாரதி புத்தகாலயம்", "மாவட்டம்": "கோவை", "வழங்கிய நூல்கள்": 180},
        {"ஐடி": "PUB-005", "பதிப்பகம்": "பூம்புகார் பதிப்பகம்", "மாவட்டம்": "திருச்சி", "வழங்கிய நூல்கள்": 95},
    ]

    df_pub = pd.DataFrame(publishers_list)

    if search:
        df_pub = df_pub[df_pub["பதிப்பகம்"].str.contains(search, case=False)]

    st.dataframe(df_pub, use_container_width=True)

# ------------------------------------------------------------
# PAGE 4: நூலகத்திற்கு விநியோகம் (103)
# ------------------------------------------------------------
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.title("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")

    m1, m2, m3 = st.columns(3)
    m1.metric("மொத்த நூலகங்கள்", "103")
    m2.metric("விநியோகிக்கப்பட்டவை", "82", "80%")
    m3.metric("நிலுவை நூலகங்கள்", "21", "20%")

    st.subheader("📍 மாவட்ட வாரியாக விநியோக நிலை")

    dist_data = pd.DataFrame(
        {
            "நூலக மையம்": ["மைய நூலகம் 1", "கிளை நூலகம் 12", "ஊர்ப்புற நூலகம் 45", "பகுதி நேர நூலகம் 8"],
            "மாவட்டம்": ["மதுரை", "திண்டுக்கல்", "தேனி", "விருதுநகர்"],
            "ஒதுக்கப்பட்ட நூல்கள்": [500, 250, 150, 100],
            "விநியோக நிலை": ["முடிக்கப்பட்டது", "முடிக்கப்பட்டது", "செயல்பாட்டில்", "நிலுவை"],
        }
    )
    st.dataframe(dist_data, use_container_width=True)

# ------------------------------------------------------------
# PAGE 5: Accession எண்கள் மேலாண்மை
# ------------------------------------------------------------
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.title("⚙️ 5. Accession எண்கள் மேலாண்மை")

    st.subheader("🔢 Accession எண் தொடர் உருவாக்குதல்")

    with st.form("accession_form"):
        col_a, col_b = st.columns(2)
        with col_a:
            start_num = st.number_input("ஆரம்ப Accession எண்", value=10001)
        with col_b:
            end_num = st.number_input("முடிவு Accession எண்", value=10500)

        prefix = st.text_input("Prefix Code", value="LIB-2026-")
        gen_btn = st.form_submit_button("⚙️ Accession தொடரை உருவாக்கு")

        if gen_btn:
            count = end_num - start_num + 1
            st.success(
                f"✅ {prefix}{start_num} முதல் {prefix}{end_num} வரை மொத்தம் {count} Accession எண்கள் வெற்றிகரமாக ஒதுக்கப்பட்டன!"
            )
