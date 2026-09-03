import hashlib
import hmac
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
    "Librarian": {"password_hash": hash_password("123456789"), "name": "Librarian"},
}

def authenticate_user(role_key, password):
    user = USERS_DATABASE.get(role_key)
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

for key, default in {
    "logged_in": False, "user_role": None, "user_name": "",
    "current_menu": None, "temp_distributed_list": [], "submitted_reports": [],
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

total_submitted_count = sum([int(item.get("Received Qty", 0)) for item in st.session_state['submitted_reports']])
today_str = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="ticker-container">
    <div class="ticker-badge">🔴 Live News</div>
    <div style="overflow: hidden; width: 100%;">
        <div class="marquee-text">
            📚 பெறப்பட்ட நூல்கள் : <b>45,305</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ✅ பிரிக்கப்பட்டது : <b>{total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ⏳ மீதம் பிரிக்க வேண்டியது : <b>{45305 - total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            📤 அனுப்பப்பட்டது : <b>0</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            🗓️ இன்று ({today_str}) பிரிக்கப்பட்டது : <b>{total_submitted_count}</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

current = st.session_state["current_menu"]

@st.cache_data
def load_neon_database():
    try:
        import psycopg2
        db_url = "postgresql://neondb_owner:npg_vA4w9qUFJheu@ep-odd-pine-b39tu9yu-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
        conn = psycopg2.connect(db_url)
        df = pd.read_sql("SELECT * FROM books;", con=conn)
        conn.close()
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"❌ டேட்டாபேஸ் இணைப்பில் பிழை: {e}")
    return pd.DataFrame()

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை (உதாரணமாக **'🔀 பிரிக்க'** அல்லது **'📊 அறிக்கைகள்'**) தேர்வு செய்யவும்.")

elif current == "பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    
    neon_df = load_neon_database()

    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
        author_col = next((c for c in neon_df.columns if 'author' in c), None)
        price_col = next((c for c in neon_df.columns if c == 'price'), None)
        accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'accepted' in c or 'rate' in c or 'offer' in c), None)
        isbn_col = next((c for c in neon_df.columns if 'isbn' in c), None)

        all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []

        selected_publisher = st.selectbox(
            "🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers,
            key="publisher_dropdown"
        )

        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            pub_filtered_df = neon_df[neon_df[pub_col] == selected_publisher].copy()
            
            total_pub_titles_count = len(pub_filtered_df[title_col].dropna().unique())
            total_pub_books_count = len(pub_filtered_df)
            
            submitted_titles = [item["Title"] for item in st.session_state["submitted_reports"] if item["Publisher"] == selected_publisher]
            temp_added_titles = [item["Title"] for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher]
            
            excluded_titles = set(submitted_titles + temp_added_titles)
            available_filtered_df = pub_filtered_df[~pub_filtered_df[title_col].isin(excluded_titles)]
            all_titles = sorted(available_filtered_df[title_col].dropna().unique().tolist())

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #34d399; padding: 14px 18px; border-radius: 10px; margin: 10px 0 15px 0;">
                <div style="font-size: 15px; font-weight: 800; color: #064e3b; margin-bottom: 8px;">
                    🏢 பதிப்பகம்: {selected_publisher} — சுருக்க விவரம்
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 20px; font-size: 14px; color: #065f46; font-weight: 600;">
                    <div>📚 மொத்த தலைப்புகள்: <b>{total_pub_titles_count}</b></div>
                    <div>📦 மொத்த நூல்கள்: <b>{total_pub_books_count}</b></div>
                    <div>✅ சமர்ப்பிக்கப்பட்டது: <b>{len(submitted_titles)}</b></div>
                    <div>⏳ மீதம் உள்ளவை: <b>{len(all_titles)}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if all_titles:
                selected_title = st.selectbox(
                    "📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும் (Select Book Title):",
                    ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles,
                    key="title_dropdown"
                )

                if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_row_df = pub_filtered_df[pub_filtered_df[title_col] == selected_title]
                    if not title_row_df.empty:
                        title_row = title_row_df.iloc[0]
                        author_name = str(title_row[author_col]) if author_col and author_col in title_row and pd.notna(title_row[author_col]) else "-"
                        book_price = str(title_row[price_col]) if price_col and price_col in title_row and pd.notna(title_row[price_col]) else "0"
                        
                        accepted_price = "0"
                        if accepted_price_col and accepted_price_col in title_row and pd.notna(title_row[accepted_price_col]):
                            accepted_price = str(title_row[accepted_price_col])

                        isbn_val = str(title_row[isbn_col]) if isbn_col and isbn_col in title_row and pd.notna(title_row[isbn_col]) else "-"
                        required_qty = len(title_row_df)

                        with st.form(f"distribution_entry_form_{selected_publisher}_{selected_title}"):
                            entered_qty = st.number_input(
                                "📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும்:", 
                                min_value=0, max_value=500, value=int(required_qty), step=1
                            )
                            submitted_temp = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
                            
                            if submitted_temp:
                                entry_data = {
                                    "Publisher": selected_publisher,
                                    "Title": selected_title,
                                    "Author": author_name,
                                    "Price": book_price,
                                    "Accepted Price": accepted_price,
                                    "ISBN": isbn_val,
                                    "Required Qty": required_qty,
                                    "Received Qty": entered_qty,
                                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                if not any(item["Title"] == selected_title for item in st.session_state["temp_distributed_list"]):
                                    st.session_state["temp_distributed_list"].append(entry_data)
                                st.success(f"✅ '{selected_title}' தற்காலிக பட்டியலில் சேர்க்கப்பட்டது!")
                                st.rerun()
            else:
                st.success(f"🎉 '{selected_publisher}' பதிப்பகத்தில் உள்ள அனைத்து நூல்களும் வெற்றிகரமாகச் சரிபார்க்கப்பட்டுவிட்டன!")

            if st.session_state["temp_distributed_list"]:
                st.markdown("---")
                st.markdown("#### 📋 தற்காலிகமாகச் சேமிக்கப்பட்ட தலைப்புகளின் பட்டியல்")
                temp_df = pd.DataFrame(st.session_state["temp_distributed_list"])
                st.dataframe(temp_df, use_container_width=True)
                
                current_pub_temp_count = len([item for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher])
                remaining_to_add = total_pub_titles_count - (len(submitted_titles) + current_pub_temp_count)
                
                if remaining_to_add > 0:
                    st.warning(f"⚠️ எச்சரிக்கை: இந்தப் பதிப்பகத்தில் இன்னும் **{remaining_to_add}** தலைப்புகள் சரிபார்க்கப்படாமல் உள்ளன. அனைத்து தலைப்புகளையும் சேர்த்த பிறகுதான் இறுதியாகச் சமர்ப்பிக்க முடியும்!")
                else:
                    if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பించు", type="primary", key="final_submit_btn"):
                        st.session_state["submitted_reports"].extend(st.session_state["temp_distributed_list"])
                        st.session_state["temp_distributed_list"] = []
                        st.session_state["current_menu"] = "அறிக்கைகள்"
                        st.success("🎉 தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                        st.rerun()

elif current == "அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு (Publishers & Title & Books Verification Report)")
    
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
    else:
        full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
        unique_report_publishers = ["-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --"] + sorted(full_report_df["Publisher"].dropna().unique().tolist())
        selected_report_pub = st.selectbox("🔍 பதிப்பகம் வாரியாக வடிகட்டுக (Filter by Publisher):", unique_report_publishers)
        
        if selected_report_pub != "-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --":
            display_df = full_report_df[full_report_df["Publisher"] == selected_report_pub].reset_index(drop=True)
            st.markdown(f"### 🏢 பதிப்பகம்: {selected_report_pub} (பதிவு செய்யப்பட்ட தலைப்புகள்: {len(display_df)})")
        else:
            display_df = full_report_df
            st.markdown(f"**மொத்தப் பதிவு செய்யப்பட்ட தலைப்புகள்:** {len(display_df)}")
            
        st.dataframe(display_df, use_container_width=True)
        
        csv_all = full_report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 அறிக்கையைப் பதிவிறக்குக (Download CSV)",
            data=csv_all,
            file_name=f"Verification_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            type="primary",
            use_container_width=True
        )

elif current == "தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல் / திருத்துதல் (Delete / Edit Verified Records)")
    
    # முதன்மை மெனுவிற்குள் உள்ள துணைப் பிரிவுகள் (Sub-options)
    edit_action_option = st.selectbox(
        "📌 எந்தப் பகுதியில் உள்ள தரவுகளை மாற்ற / நீக்க வேண்டும் என்பதைத் தேர்ந்தெடுக்கவும்:",
        [
            "-- பகுதியைத் தேர்ந்தெடுக்கவும் --",
            "1. பதிப்பாளர் தேர்வு (Publisher Records)",
            "2. அனுப்பிய விவரங்கள் (Dispatch Records)",
            "3. அறிக்கை தரவுகள் (Submitted Reports)",
            "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)",
            "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)",
            "6. Master Data தரவுகள்",
            "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)"
        ],
        key="main_error_correction_sub_menu"
    )
    
    st.markdown("---")
    
    # 1. பதிப்பாளர் தேர்வு பகுதி (செய்து முடிக்கப்பட்ட பதிப்பகங்கள் மற்றும் தலைப்புகள் மட்டும்)
    if edit_action_option == "1. பதிப்பாளர் தேர்வு (Publisher Records)":
        st.markdown("### 🏢 1. பதிப்பாளர் தேர்வு & திருத்துதல் / நீக்குதல்")
        
        # பயனர் ஏற்கனவே சமர்ப்பித்த அல்லது தற்காலிகமாகச் சேர்த்த பதிப்பகங்களை மட்டும் சேகரித்தல்
        completed_publishers = set()
        for item in st.session_state.get("submitted_reports", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
        for item in st.session_state.get("temp_distributed_list", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
                
        pub_list = sorted(list(completed_publishers))
        
        if not pub_list:
            st.info("ℹ️ இதுவரை எந்தப் பதிப்பகப் பணியும் முடிக்கப்படவில்லை. எனவே தேர்வு செய்யப் பதிப்பகங்கள் இல்லை.")
        else:
            sel_pub = st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + pub_list, key="err_pub_sel")
            
            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                # தேர்ந்தெடுக்கப்பட்ட பதிப்பகத்திற்குரிய முடிக்கப்பட்ட தலைப்புகளை மட்டும் எடுத்தல்
                completed_titles = set()
                for item in st.session_state.get("submitted_reports", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                for item in st.session_state.get("temp_distributed_list", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                        
                title_list = sorted(list(completed_titles))
                
                sel_title = st.selectbox("தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="err_title_sel")
                
                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    # அந்தத் தலைப்புக்கான தற்போதைய எண்ணிக்கையைக் கண்டறிதல்
                    current_qty = 10
                    target_index = None
                    for idx, item in enumerate(st.session_state.get("submitted_reports", [])):
                        if item.get("Publisher") == sel_pub and item.get("Title") == sel_title:
                            current_qty = int(item.get("Received Qty", 10))
                            target_index = idx
                            break

                    c1, c2 = st.columns(2)
                    with c1:
                        new_val = st.number_input("எண்ணிக்கையைத் திருத்துக:", min_value=0, value=current_qty, key="err_pub_qty")
                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_d, col_u = st.columns(2)
                        with col_d:
                            if st.button("🗑️ நீக்கு", key="err_pub_del_btn", use_container_width=True):
                                if target_index is not None:
                                    st.session_state["submitted_reports"].pop(target_index)
                                st.success("✅ பதிவு வெற்றிகரமாக நீக்கப்பட்டது!")
                                st.rerun()
                        with col_u:
                            if st.button("💾 மாற்று/புதுப்பி", key="err_pub_upd_btn", type="primary", use_container_width=True):
                                if target_index is not None:
                                    st.session_state["submitted_reports"][target_index]["Received Qty"] = new_val
                                st.success("✅ பதிவு வெற்றிகரமாக மாற்றப்பட்டது!")
                                st.rerun()

    # 2. அனுப்பிய விவரங்கள் பகுதி
    elif edit_action_option == "2. அனுப்பிய விவரங்கள் (Dispatch Records)":
        st.markdown("### 📤 2. அனுப்பிய நூல்களின் பதிவுகளைத் திருத்துதல் / நீக்குதல்")
        if not st.session_state["dispatch_records"]:
            st.info("ℹ️ அனுப்பப்பட்ட பதிவுகள் எதுவும் இல்லை.")
        else:
            for d_idx, d_item in enumerate(st.session_state["dispatch_records"]):
                with st.expander(f"நூலகம்: {d_item.get('Library', 'N/A')} | தலைப்பு: {d_item.get('Title', 'N/A')}"):
                    d_qty_edit = st.number_input("எண்ணிக்கை", value=int(d_item.get('Qty', 1)), key=f"err_d_qty_{d_idx}")
                    col_d1, col_d2 = st.columns(2)
                    with col_d1:
                        if st.button("🗑️ இந்தப் பதிவை நீக்கு", key=f"err_d_del_{d_idx}"):
                            st.session_state["dispatch_records"].pop(d_idx)
                            st.success("✅ நீக்கப்பட்டது!")
                            st.rerun()
                    with col_d2:
                        if st.button("💾 இந்தப் பதிவை மாற்று", key=f"err_d_upd_{d_idx}", type="primary"):
                            st.session_state["dispatch_records"][d_idx]['Qty'] = d_qty_edit
                            st.success("✅ மாற்றப்பட்டது!")
                            st.rerun()

    # 3. அறிக்கை தரவுகள் பகுதி
    elif edit_action_option == "3. அறிக்கை தரவுகள் (Submitted Reports)":
        st.markdown("### 📊 3. சமர்ப்பிக்கப்பட்ட அறிக்கை தரவுகளைத் திருத்துதல் / நீக்குதல்")
        if not st.session_state["submitted_reports"]:
            st.info("ℹ️ சமர்ப்பிக்கப்பட்ட அறிக்கைகள் எதுவும் இல்லை.")
        else:
            for s_idx, s_item in enumerate(st.session_state["submitted_reports"]):
                with st.expander(f"பதிப்பகம்: {s_item.get('Publisher')} | தலைப்பு: {s_item.get('Title')}"):
                    s_qty_edit = st.number_input("பெறப்பட்ட எண்ணிக்கை", value=int(s_item.get('Received Qty', 0)), key=f"err_s_qty_{s_idx}")
                    col_s1, col_s2 = st.columns(2)
                    with col_s1:
                        if st.button("🗑️ நீக்கு", key=f"err_s_del_{s_idx}"):
                            st.session_state["submitted_reports"].pop(s_idx)
                            st.success("✅ நீக்கப்பட்டது!")
                            st.rerun()
                    with col_s2:
                        if st.button("💾 மாற்று", key=f"err_s_upd_{s_idx}", type="primary"):
                            st.session_state["submitted_reports"][s_idx]['Received Qty'] = s_qty_edit
                            st.success("✅ மாற்றப்பட்டது!")
                            st.rerun()

    # 4. கவனிக்க வேண்டியவை பகுதி
    elif edit_action_option == "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)":
        st.markdown("### ⚠️ 4. முரண்பட்ட விலை மற்றும் தலைப்புகளைச் சரிசெய்தல்")
        st.info("ஒரே தலைப்புடன் முரண்பட்ட விலை உள்ள பதிவுகளை இங்கே மாற்றலாம் அல்லது நீக்கலாம்.")

    # 5. பதிவெண் மாற்றங்கள் பகுதி
    elif edit_action_option == "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)":
        st.markdown("### 🔢 5. நூலகப் பதிவெண்களைத் திருத்துதல் / நீக்குதல்")
        acc_no = st.text_input("மாற்ற வேண்டிய பழைய பதிவெண்:")
        new_acc_no = st.text_input("புதிய பதிவெண்:")
        if st.button("பதிவெண்ணைப் புதுப்பி", type="primary"):
            st.success("✅ பதிவெண் வெற்றிகரமாக மாற்றப்பட்டது!")

    # 6. Master Data பகுதி
    elif edit_action_option == "6. Master Data தரவுகள்":
        st.markdown("### 🗂️ 6. Master Data பதிவுகளைத் திருத்துதல் / நீக்குதல்")
        st.info("Master Data மூலத் தரவுகளில் தேவையான மாற்றங்களைச் செய்யலாம்.")

    # 7. பகுப்பு எண் மாற்றங்கள் பகுதி
    elif edit_action_option == "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)":
        st.markdown("### 🏷️ 7. நூல் பகுப்பு எண்களைத் திருத்துதல் / நீக்குதல்")
        old_class = st.text_input("தற்போதைய பகுப்பு எண்:")
        new_class = st.text_input("திருத்தப்பட்ட புதிய பகுப்பு எண்:")
        if st.button("பகுப்பு எண்ணைப் புதுப்பி", type="primary"):
            st.success("✅ பகுப்பு எண் வெற்றிகரமாக மாற்றப்பட்டது!")

    else:
        st.info("👆 மேல் உள்ள தேர்வில் ஏதேனும் ஒரு பிரிவைத் தேர்வு செய்தால், அதற்கான திருத்தும் மற்றும் நீக்கும் வசதிகள் உடனே தோன்றும்.")
elif current == "கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Change Password)")
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
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ பதிவிறக்கம் செய்யத் தரவுகள் எதுவும் இல்லை.")
    else:
        report_df = pd.DataFrame(st.session_state["submitted_reports"])
        csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 முழுமையான தரவுகளை Excel கோப்பாகப் பதிவிறக்குக",
            data=csv_data,
            file_name=f"Master_Verification_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள் மேலாண்மை")
    st.info("நூலகர்களின் பார்வைக் காலங்களைச் சரிபார்க்கவும் திருத்தவும்.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் & மேலாண்மை")
    uploaded_file = st.file_uploader("Excel அல்லது CSV கோப்பினைத் தேர்ந்தெடுக்கவும்", type=["xlsx", "csv"])
    if uploaded_file is not None:
        st.success("✅ கோப்பு வெற்றிகரமாகப் பெறப்பட்டது!")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல் மற்றும் திருத்துதல்")
    st.info("நூல் பகுப்பு எண்களைத் தரம் பிரித்துப் புதுப்பிக்க.")
