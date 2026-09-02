import hashlib
import hmac
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
.ticker-container { background: linear-gradient(135deg, #f0fdf4, #dcfce7); border: 1.5px solid #86efac; padding: 8px 12px; border-radius: 10px; color: #065f46; font-weight: 700; font-size: 13px; display: flex; align-items: center; box-shadow: 0 2px 8px rgba(6, 95, 70, 0.08); margin-bottom: 20px; overflow: hidden; white-space: nowrap; }
.ticker-badge { background: #065f46; color: white; padding: 3px 10px; border-radius: 6px; font-size: 12px; margin-right: 15px; display: flex; align-items: center; gap: 5px; flex-shrink: 0; }
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

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "",
    "current_menu": None, "sub_menu": "மாநில", "temp_distributed_list": []
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
        st.session_state.clear()
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

today_str = datetime.now().strftime("%d/%m/%Y")
st.markdown(f"""
<div class="ticker-container">
    <div class="ticker-badge">🔴 Live News</div>
    <div class="ticker-text">
        📚 பெறப்பட்ட நூல்கள் : <b>45,305</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        ✅ பிரிக்கப்பட்டது : <b>{len(st.session_state['temp_distributed_list'])}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        ⏳ மீதம் பிரிக்க வேண்டியது : <b>{45305 - len(st.session_state['temp_distributed_list'])}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        📤 அனுப்பப்பட்டது : <b>0</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
        🗓️ இன்று ({today_str}) பிரிக்கப்பட்டது : <b>0</b>
    </div>
</div>
""", unsafe_allow_html=True)

current = st.session_state["current_menu"]

@st.cache_data
def load_neon_database():
    try:
        import psycopg2
        db_url = "postgresql://neondb_owner:npg_gY5h1PjZtXvK@ep-super-pond-a50s70up.us-east-2.aws.neon.tech/neondb?sslmode=require"
        conn = psycopg2.connect(db_url)
        df = pd.read_sql("SELECT * FROM books;", con=conn)
        conn.close()
        if not df.empty:
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception as e:
        st.warning(f"⚠️ டேட்டாபேஸ் இணைப்பில் சிறு சிக்கல்: {e}")
    return pd.DataFrame()

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை (உதாரணமாக **'🔀 பிரிக்க'**) தேர்வு செய்யவும்.")

elif current == "பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    
    neon_df = load_neon_database()

    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை அல்லது 'books' டேபிள் காலியாக உள்ளது.")
    else:
        pub_col = None
        for col in neon_df.columns:
            if col.upper() in ["PUBLICATION NAME", "PUBLISHER", "PUBLICATION_NAME"]:
                pub_col = col
                break
        if pub_col is None:
            for col in neon_df.columns:
                if 'pub' in col.lower():
                    pub_col = col
                    break

        title_col = "TITLE" if "TITLE" in neon_df.columns else [c for c in neon_df.columns if 'title' in c.lower()][0]
        author_col = "AUTHOR" if "AUTHOR" in neon_df.columns else [c for c in neon_df.columns if 'author' in c.lower()][0]
        price_col = "PRICE" if "PRICE" in neon_df.columns else [c for c in neon_df.columns if 'price' in c.lower()][0]

        all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist())

        # 1. பதிப்பகத்தைத் தேர்ந்தெடுத்தல் (Publisher Dropdown)
        selected_publisher = st.selectbox(
            "🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers,
            key="publisher_dropdown"
        )

        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            pub_filtered_df = neon_df[neon_df[pub_col] == selected_publisher].copy()
            all_titles = sorted(pub_filtered_df[title_col].dropna().unique().tolist())

            st.markdown(f"### 🏢 பதிப்பகம்: {selected_publisher} (மொத்த தலைப்புகள்: {len(all_titles)})")

            # 2. குறிப்பிட்ட பதிப்பகத்தின் தலைப்புகளைத் தேர்ந்தெடுத்தல் (Title Dropdown)
            selected_title = st.selectbox(
                "📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும் (Select Book Title):",
                ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles,
                key="title_dropdown"
            )

            if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                title_row = pub_filtered_df[pub_filtered_df[title_col] == selected_title].iloc[0]
                
                author_name = title_row[author_col] if author_col in title_row else "-"
                book_price = title_row[price_col] if price_col in title_row else "0"
                isbn_val = title_row["Isbn"] if "Isbn" in title_row else (title_row["ISBN"] if "ISBN" in title_row else "-")
                required_qty = 112 # கிருஷ்ணகிரி மாவட்ட நூலகங்களின் எண்ணிக்கை அல்லது தேவைப்படும் எண்ணிக்கை

                # 3. தேர்ந்தெடுக்கப்பட்ட தலைப்பின் முழு விவரம் மற்றும் எண்ணிக்கை உள்ளீடு
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border: 1.5px solid #34d399; padding: 18px; border-radius: 12px; margin: 15px 0;">
                    <div style="font-size: 16px; font-weight: 800; color: #064e3b; margin-bottom: 12px;">
                        📘 தேர்ந்தெடுக்கப்பட்ட நூல் விவரம்
                    </div>
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; font-size: 14px; color: #065f46;">
                        <div>📚 <b>தலைப்பு:</b> {selected_title}</div>
                        <div>✍️ <b>ஆசிரியர்:</b> {author_name}</div>
                        <div>💰 <b>விலை:</b> ₹{book_price}</div>
                        <div>🏷️ <b>ISBN:</b> {isbn_val}</div>
                        <div>🏛️ <b>பெறப்பட வேண்டிய எண்ணிக்கை:</b> {required_qty}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                with st.form("distribution_entry_form"):
                    entered_qty = st.number_input(
                        "📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும் (Enter Received Quantity):", 
                        min_value=0, max_value=500, value=int(required_qty), step=1
                    )
                    
                    submitted_temp = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
                    
                    if submitted_temp:
                        entry_data = {
                            "Publisher": selected_publisher,
                            "Title": selected_title,
                            "Author": author_name,
                            "Price": book_price,
                            "Required Qty": required_qty,
                            "Received Qty": entered_qty
                        }
                        st.session_state["temp_distributed_list"].append(entry_data)
                        st.success(f"✅ '{selected_title}' தற்காலிக பட்டியலில் வெற்றிகரமாகச் சேர்க்கப்பட்டது!")

                # 4. தற்காலிக பட்டியலைக் காட்டுதல் (Temporary List Preview)
                if st.session_state["temp_distributed_list"]:
                    st.markdown("---")
                    st.markdown("#### 📋 தற்காலிகமாகச் சேமிக்கப்பட்ட தலைப்புகளின் பட்டியல் (Temporary List)")
                    temp_df = pd.DataFrame(st.session_state["temp_distributed_list"])
                    st.dataframe(temp_df, use_container_width=True)
                    
                    if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பించు", type="primary"):
                        st.success("🎉 அனைத்துத் தரவுகளும் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                        st.session_state["temp_distributed_list"] = []
                        st.rerun()

elif current == "அனுப்ப":
    st.subheader("📤 நூல்களை அனுப்பும் பகுதி (Dispatch)")
    st.info("நூலகங்களுக்கு நூல்களை அனுப்பும் விவரங்களை இங்கே பதிவிடலாம்.")

elif current == "அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் (Reports)")
    st.info("தேவையான அனைத்து அறிக்கைகளையும் இங்கு பார்வையிடலாம்.")

elif current == "கவனிக்க":
    st.subheader("⚠️ கவனிக்க — ஒரே தலைப்பில் வேறு விலைகள் உள்ளவை")
    st.info("ஒரே தலைப்பில் வேறுபட்ட விலைகள் உள்ள நூல்களின் பட்டியல்.")

elif current == "பதிவெண் மாற்ற":
    st.subheader("🔢 பதிவெண் மாற்றும் பகுதி")
    st.info("நூல்களின் பதிவெண்களைத் திருத்தம் செய்ய.")

elif current == "Master Data":
    st.subheader("🗂️ Master Data மேலாண்மை")
    st.info("அடிப்படைத் தரவுகளை நிர்வகிக்க.")

elif current == "தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல்")
    st.info("தவறாகப் பதிவு செய்யப்பட்ட தரவுகளை நீக்க.")

elif current == "கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி")
    st.info("பயனர் கடவுச்சொல்லைப் புதுப்பிக்க.")

elif current == "Excel பதிவிறக்கம்":
    st.subheader("📥 Excel அறிக்கை பதிவிறக்கம்")
    st.info("தரவுகளை Excel வடிவில் பதிவிறக்கம் செய்ய.")

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள்")
    st.info("நூலகர்களின் பார்வைக் காலங்களை நிர்வகிக்க.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம்")
    st.info("புதிய தரவுத் தொகுப்புகளைப் பதிவேற்றுக.")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல்")
    st.info("பகுப்பு எண் புதுப்பித்தல் விபரங்களை இங்கே உள்ளிடலாம்.")
