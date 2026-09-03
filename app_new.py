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
    "TNDPL01617": {"password_hash": hash_password("123456789"), "name": "சிந்தகம்பள்ளி நூலகர்", "lib_name": "Chinthakampalli"},
    "TNDPL01586": {"password_hash": hash_password("123456789"), "name": "போச்சம்பள்ளி நூலகர்", "lib_name": "Pochampalli"},
}

def authenticate_user(role_key, password, librarian_id=""):
    user = USERS_DATABASE.get(librarian_id) if role_key == "Librarian" else USERS_DATABASE.get(role_key)
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
        lib_id_input = st.text_input("🆔 நூலகர் ஐடி (Librarian ID)", placeholder="எ.கா: TNDPL01617") if selected_role == "Librarian" else ""
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
                st.error("❌ தவறான ID அல்லது கடவுச்சொல்!")
            else:
                display_name = f"{user['name']} ({lib_id_input})" if selected_role == "Librarian" else user["name"]
                lib_loc = user.get("lib_name", "") if selected_role == "Librarian" else ""
                st.session_state.update(logged_in=True, user_role=selected_role, user_name=display_name, librarian_location=lib_loc)
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

if st.session_state["user_role"] == "Admin":
    menu_options = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
        ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
        ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
        ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி")
    ]
elif st.session_state["user_role"] == "DCL Staff":
    menu_options = [
        ("🔀", "பிரிக்க"), ("📤", "அனுப்ப"), ("📊", "அறிக்கைகள்")
    ]
else:
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
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை தேர்வு செய்யவும்.")

elif st.session_state["user_role"] == "Librarian":
    if current == "நூலகத் தரவுகள்":
        st.subheader(f"📚 {st.session_state['librarian_location']} நூலகத்திற்கான ஒதுக்கீடு மற்றும் நூல்கள் விவரங்கள்")
        neon_df = load_neon_database()
        if not neon_df.empty:
            lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
            if lib_col_name:
                lib_specific_df = neon_df[neon_df[lib_col_name].astype(str).str.contains(st.session_state["librarian_location"], case=False, na=False)]
                st.dataframe(lib_specific_df, use_container_width=True)
                csv_data = lib_specific_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 நூலகத் தரவுகளைப் பதிவிறக்குக (CSV)", data=csv_data, file_name=f"Library_Data_{st.session_state['librarian_location']}.csv", mime="text/csv", type="primary")

else: # Admin மற்றும் DCL Staff பகுதிகள்
    if current == "பிரிக்க":
        st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
        neon_df = load_neon_database()
        if not neon_df.empty:
            pub_col = next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
            title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
            if not title_col:
                title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
            all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
            selected_publisher = st.selectbox("🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers, key="pub_sel_main")

            if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                pub_filtered_df = neon_df[neon_df[pub_col] == selected_publisher].copy()
                all_titles = sorted(pub_filtered_df[title_col].dropna().unique().tolist())
                selected_title = st.selectbox("📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles, key="title_sel_main")

                if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_row_df = pub_filtered_df[pub_filtered_df[title_col] == selected_title]
                    if not title_row_df.empty:
                        required_qty = len(title_row_df)
                        with st.form("dist_form_main"):
                            entered_qty = st.number_input("📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும்:", min_value=0, max_value=500, value=int(required_qty), step=1)
                            if st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary"):
                                entry_data = {
                                    "Publisher": selected_publisher, "Title": selected_title,
                                    "Required Qty": required_qty, "Received Qty": entered_qty,
                                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                st.session_state["temp_distributed_list"].append(entry_data)
                                st.success("✅ தற்காலிக பட்டியலில் சேர்க்கப்பட்டது!")
                                st.rerun()

        if st.session_state["temp_distributed_list"]:
            st.markdown("---")
            st.markdown("#### 📋 தற்காலிக பட்டியல்")
            st.dataframe(pd.DataFrame(st.session_state["temp_distributed_list"]), use_container_width=True)
            if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பించు", type="primary"):
                try:
                    conn = psycopg2.connect(DB_URL)
                    cur = conn.cursor()
                    for item in st.session_state["temp_distributed_list"]:
                        cur.execute("""
                            INSERT INTO submitted_reports (publisher, title, required_qty, received_qty, date)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (item["Publisher"], item["Title"], item["Required Qty"], item["Received Qty"], item["Date"]))
                    conn.commit()
                    cur.close()
                    conn.close()
                    st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                    st.session_state["temp_distributed_list"] = []
                    st.success("🎉 தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ பிழை: {e}")

    elif current == "அறிக்கைகள்":
        st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு")
        if st.session_state["submitted_reports"]:
            st.dataframe(pd.DataFrame(st.session_state["submitted_reports"]), use_container_width=True)
        else:
            st.info("ℹ️ தரவுகள் எதுவும் இல்லை.")

    elif current == "தவறான பதிவு நீக்கம்":
        st.subheader("❌ தவறான பதிவினை நீக்குதல் / திருத்துதல் (Delete / Edit Verified Records)")
        completed_publishers = set(item["Publisher"] for item in st.session_state.get("submitted_reports", []))
        pub_list = sorted(list(completed_publishers))
        
        if not pub_list:
            st.info("ℹ️ இதுவரை எந்தப் பதிப்பகப் பணியும் முடிக்கப்படவில்லை.")
        else:
            sel_pub = st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + pub_list, key="err_pub")
            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                completed_titles = set(item["Title"] for item in st.session_state.get("submitted_reports", []) if item.get("Publisher") == sel_pub)
                sel_title = st.selectbox("தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + sorted(list(completed_titles)), key="err_title")
                
                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    target_item = None
                    target_idx = None
                    for idx, item in enumerate(st.session_state["submitted_reports"]):
                        if item.get("Publisher") == sel_pub and item.get("Title") == sel_title:
                            target_item = item
                            target_idx = idx
                            break
                    
                    if target_item:
                        req_q = int(target_item.get("Required Qty", 10))
                        rec_q = int(target_item.get("Received Qty", 5))
                        
                        st.markdown(f"""
                        <div style="background: #f0fdf4; border: 1.5px solid #86efac; padding: 12px; border-radius: 8px; margin-bottom: 15px; color: #065f46;">
                            <b>📖 தேர்ந்தெடுக்கப்பட்ட பதிப்பகம்:</b> {sel_pub}<br>
                            <b>📌 தலைப்பு:</b> {sel_title}<br>
                            <b>📦 தேவைப்படும் எண்ணிக்கை:</b> {req_q} | <b>📥 பெறப்பட்ட எண்ணிக்கை:</b> {rec_q}
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_upd, col_del = st.columns(2)
                        with col_upd:
                            new_received = st.number_input("புதிய பெறப்பட்ட எண்ணிக்கையை உள்ளிடவும்:", min_value=0, max_value=500, value=rec_q, key="edit_rec_qty")
                            if st.button("💾 எண்ணிக்கையைப் புதுப்பி (Update)", type="primary", use_container_width=True):
                                try:
                                    conn = psycopg2.connect(DB_URL)
                                    cur = conn.cursor()
                                    cur.execute("UPDATE submitted_reports SET received_qty = %s WHERE publisher = %s AND title = %s;", (new_received, sel_pub, sel_title))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                    st.success("✅ எண்ணிக்கை வெற்றிகரமாக மாற்றப்பட்டது!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ பிழை: {e}")
                        
                        with col_del:
                            st.markdown("<br>", unsafe_allow_html=True)
                            if st.button("🗑️ இந்தப் பதிவை முழுமையாக நீக்கு (Delete)", type="secondary", use_container_width=True):
                                try:
                                    conn = psycopg2.connect(DB_URL)
                                    cur = conn.cursor()
                                    cur.execute("DELETE FROM submitted_reports WHERE publisher = %s AND title = %s;", (sel_pub, sel_title))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                    st.success("✅ பதிவு வெற்றிகரமாக நீக்கப்பட்டது!")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ பிழை: {e}")

    elif current == "Master Data":
        st.subheader("🗂️ Master Data சேமிப்பு & மேலாண்மை பகுதி")
        neon_df = load_neon_database()
        if not neon_df.empty:
            st.dataframe(neon_df, use_container_width=True)
        else:
            st.info("ℹ️ தரவுகள் கிடைக்கவில்லை.")

    elif current == "கடவுச்சொல் மாற்ற":
        st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி")
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
        if st.session_state["submitted_reports"]:
            report_df = pd.DataFrame(st.session_state["submitted_reports"])
            csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 முழுமையான தரவுகளை Excel கோப்பாகப் பதிவிறக்குக", data=csv_data, file_name=f"Master_Verification_Data_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv", type="primary")
        else:
            st.info("ℹ️ பதிவிறக்கம் செய்யத் தரவுகள் எதுவும் இல்லை.")

    else:
        st.subheader(f"⚙️ நிர்வாகி பகுதி: {current}")
        st.info(f"இப்பகுதிக்கான ({current}) செயல்பாடுகள் فعالவாக உள்ளன.")
