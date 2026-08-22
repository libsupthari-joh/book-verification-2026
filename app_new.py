import hashlib
import hmac
import streamlit as st


# ============================================================
# MULTI-USER SECURE LOGIN
# ============================================================
# இங்கு கடவுச்சொல் ஸ்பேஸ் இல்லாமல் "Basswood123456" என அமைக்கப்பட்டுள்ளது.
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


# ============================================================
# PASSWORD HASH GENERATION & AUTHENTICATION
# ============================================================
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
        "current_page",
    ]:
        st.session_state.pop(key, None)

    st.session_state["logged_in"] = False
    st.rerun()


# ============================================================
# SIDEBAR USER INFORMATION & NAVIGATION
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

if "current_page" not in st.session_state or st.session_state["current_page"] not in visible_menu_items:
    st.session_state["current_page"] = visible_menu_items[0]

for item in visible_menu_items:
    if st.sidebar.button(item, use_container_width=True):
        st.session_state["current_page"] = item
        st.rerun()


# ============================================================
# MAIN APPLICATION PAGE ROUTER (YOUR EXISTING CODE)
# ============================================================
menu_choice = st.session_state["current_page"]

if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    # உங்கள் தற்போதைய Task 1 கோடை இங்கு வைக்கவும்
    st.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")

elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    # உங்கள் தற்போதைய Sync கோடை இங்கு வைக்கவும்
    st.subheader("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)")

elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    # உங்கள் தற்போதைய பதிப்பாளர் கோடை இங்கு வைக்கவும்
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")

elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    # உங்கள் தற்போதைய விநியோக கோடை இங்கு வைக்கவும்
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")

elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை":
    # உங்கள் தற்போதைய Accession கோடை இங்கு வைக்கவும்
    st.subheader("⚙️ 5. Accession எண்கள் மேலாண்மை")
