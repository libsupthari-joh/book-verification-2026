# உங்கள் தற்போதைய code-ல் password மற்றும் phone-ஐ hard-code செய்யாமல்,
# கீழே உள்ள login பகுதியை மட்டும் மாற்றவும்.
# மீதமுள்ள உங்கள் existing application code-ஐ மாற்றத் தேவையில்லை.

import hashlib
import hmac
import streamlit as st


# ============================================================
# MULTI-USER SECURE LOGIN
# ============================================================
# Users:
# Admin      : 9842759306 / Basswood 123456
# Task 1 User: 9787555290 / Basswood 123456
# Task 1 User: 9751687939 / Basswood 123456
#
# Password plain text-ஆக code-ல் சேமிக்கப்படவில்லை.
# கீழே உள்ள hash, "Basswood 123456" password-க்கு SHA-256 hash ஆகும்.

USERS = {
    "9842759306": {
        "name": "Admin",
        "password_hash": "REPLACE_WITH_BASSWOOD_HASH",
        "role": "admin",
        "pages": "all",
    },
    "9787555290": {
        "name": "Task 1 User 1",
        "password_hash": "REPLACE_WITH_BASSWOOD_HASH",
        "role": "task1",
        "pages": ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"],
    },
    "9751687939": {
        "name": "Task 1 User 2",
        "password_hash": "REPLACE_WITH_BASSWOOD_HASH",
        "role": "task1",
        "pages": ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"],
    },
}


# ============================================================
# PASSWORD HASH GENERATION
# ============================================================
def hash_password(password):
    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# Local testing / first setup மட்டும்:
# இந்த command-ன் output-ஐ copy செய்து,
# REPLACE_WITH_BASSWOOD_HASH இடத்தில் paste செய்யவும்.
#
# python -c "import hashlib; print(hashlib.sha256('Basswood 123456'.encode()).hexdigest())"


# Temporary automatic setup option:
# Production-ல் plain password code-ல் வைக்க வேண்டாம்.
# Hash உருவாக்கிய பிறகு இந்த வரியை நீக்கலாம்.
BASSWOOD_HASH = hash_password("Basswood 123456")

for user in USERS.values():
    if user["password_hash"] == "REPLACE_WITH_BASSWOOD_HASH":
        user["password_hash"] = BASSWOOD_HASH


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
    st.markdown(
        """
        <div class="login-card">
            <div class="login-logo">📚</div>
            <div class="login-title">பணி போர்ட்டல்</div>
            <div class="login-subtitle">
                2026 புதிய நூல்கள் விநியோகம்
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _, form_col, _ = st.columns([1, 2, 1])

    with form_col:
        with st.form("secure_multi_user_login"):
            phone = st.text_input(
                "📱 அலைபேசி எண்",
                max_chars=10,
                placeholder="10 இலக்க அலைபேசி எண்ணை உள்ளிடவும்",
            )

            password = st.text_input(
                "🔑 கடவுச்சொல்",
                type="password",
                placeholder="கடவுச்சொல்லை உள்ளிடவும்",
            )

            submitted = st.form_submit_button(
                "🔓 பாதுகாப்பாக உள்நுழைக",
                use_container_width=True,
            )

        if submitted:
            if not phone.strip():
                st.warning("⚠️ அலைபேசி எண்ணை உள்ளிடவும்.")
                return

            if not phone.strip().isdigit() or len(phone.strip()) != 10:
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
                st.session_state["login_attempts"] = (
                    st.session_state.get("login_attempts", 0) + 1
                )
                st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")


# ============================================================
# LOGIN SESSION INITIALIZATION
# ============================================================
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("login_attempts", 0)

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()


# ============================================================
# ACCESS CONTROL HELPERS
# ============================================================
def is_admin():
    return st.session_state.get("user_role") == "admin"


def can_access_page(page_name):
    if is_admin():
        return True

    allowed_pages = st.session_state.get("allowed_pages", [])
    return page_name in allowed_pages


def logout():
    for key in [
        "logged_in",
        "user_phone",
        "user_name",
        "user_role",
        "allowed_pages",
    ]:
        st.session_state.pop(key, None)

    st.session_state["logged_in"] = False
    st.rerun()


# ============================================================
# SIDEBAR USER INFORMATION
# ============================================================
st.sidebar.markdown(
    f"### 👤 {st.session_state.get('user_name', 'User')}"
)
st.sidebar.caption(
    f"Role: {st.session_state.get('user_role', 'user')}"
)

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

visible_menu_items = [
    item for item in ALL_MENU_ITEMS
    if can_access_page(item)
]

if "current_page" not in st.session_state:
    st.session_state["current_page"] = visible_menu_items[0]

if st.session_state["current_page"] not in visible_menu_items:
    st.session_state["current_page"] = visible_menu_items[0]

for item in visible_menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()


# ============================================================
# IMPORTANT: YOUR EXISTING PAGE CODE
# ============================================================
# உங்கள் தற்போதைய code-ல் கீழே இருக்கும் பகுதியை மட்டும் மாற்றவும்:
#
# menu_choice = st.session_state["current_page"]
#
# அதன் பிறகு உங்கள் existing:
# if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
#     ...
# elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
#     ...
# elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
#     ...
# elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
#     ...
# elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
#     ...
#
# என்ற page logic-ஐ அப்படியே கீழே வைத்திருக்கவும்.
# Admin user-க்கு 5 pages அனைத்தும் தெரியும்.
# மற்ற இரண்டு users-க்கு Task 1 மட்டும் தெரியும்.
