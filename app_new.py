import streamlit as str_lit
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import re
import time

# 1. Streamlit பக்க அமைப்பு
str_lit.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide", initial_sidebar_state="expanded")

# 🎨 பக்கவாட்டு மெனுவிற்கான நவீன 3D ஸ்டைலிங் (CSS)
def get_custom_css():
    return """
    <style>
    /* பக்கவாட்டு மெனுவின் பட்டன்களுக்கு 3D லுக் */
    div[data-testid="stSidebar"] button {
        width: 100% !important;
        text-align: left !important;
        padding: 15px 20px !important;
        margin-bottom: 12px !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        border: none !important;
        transition: all 0.3s ease !important;
        /* பட்டனுக்கு 3D நிழல் */
        box-shadow: 0 6px 0 #999, 0 8px 10px rgba(0,0,0,0.3) !important;
    }

    /* சாதாரண நிலை பட்டன் - சாம்பல் நிறம் */
    div[data-testid="stSidebar"] button:not([kind="primary"]) {
        background: linear-gradient(145deg, #f0f0f0, #d1d1d1) !important;
        color: #333 !important;
    }

    /* ஆக்டிவ் / கிளிக் செய்த நிலை (3D ப்ளூ) */
    div[data-testid="stSidebar"] button[kind="primary"] {
        background: linear-gradient(145deg, #007bff, #0056b3) !important;
        color: white !important;
        /* அழுத்தப்பட்ட 3D உணர்வு */
        transform: translateY(4px) !important;
        box-shadow: 0 2px 0 #003d80 !important;
    }

    /* மவுஸ் வைக்கும் போது சிறிய மாற்றம் */
    div[data-testid="stSidebar"] button:hover {
        filter: brightness(1.1) !important;
    }
    </style>
    """

# 🔒 Login Page
if not str_lit.session_state['logged_in']:
    str_lit.markdown("<h2 style='text-align: center;'>🔐 பணி போர்ட்டல் - உள்நுழைவு (Login)</h2>", unsafe_allow_html=True)
    col1, col2, col3 = str_lit.columns([1, 2, 1])
    with col2:
        with str_lit.form("login_form"):
            phone = str_lit.text_input("📱 அலைபேசி எண்:")
            password = str_lit.text_input("🔑 கடவுச்சொல்:", type="password")
            submit = str_lit.form_submit_button("🔓 உள்நுழை (Login)", use_container_width=True)
            if submit:
                if phone == "9876543210" and password == "123456":
                    str_lit.session_state['logged_in'] = True
                    str_lit.success("✅ உள்நுழைவு வெற்றிகரமானது!")
                    str_lit.rerun()
                else:
                    str_lit.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")
    str_lit.stop()

# 📌 Sidebar Navigation (பக்கவாட்டு மெனு)
str_lit.sidebar.markdown("### 👤 **பயனர் கணக்கு**")
if str_lit.sidebar.button("🚪 வெளியேறு (Logout)", key="logout_btn", use_container_width=True):
    str_lit.session_state['logged_in'] = False
    str_lit.rerun()

str_lit.sidebar.markdown("---")
str_lit.sidebar.markdown("### 📌 **முதன்மைப் பணிகள்**")

active_page = str_lit.session_state['current_page']

def style_button_active(page_num_str):
    return active_page.startswith(page_num_str)

if str_lit.sidebar.button("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு", key="nav_1", use_container_width=True, type="primary" if style_button_active("📥 1.") else "secondary"):
    str_lit.session_state['current_page'] = "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"
    str_lit.rerun()

if str_lit.sidebar.button("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)", key="nav_2", use_container_width=True, type="primary" if style_button_active("🔄 2.") else "secondary"):
    str_lit.session_state['current_page'] = "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)"
    str_lit.rerun()

if str_lit.sidebar.button("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)", key="nav_3", use_container_width=True, type="primary" if style_button_active("🏢 3.") else "secondary"):
    str_lit.session_state['current_page'] = "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)"
    str_lit.rerun()

if str_lit.sidebar.button("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)", key="nav_4", use_container_width=True, type="primary" if style_button_active("🏛️ 4.") else "secondary"):
    str_lit.session_state['current_page'] = "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)"
    str_lit.rerun()

if str_lit.sidebar.button("⚙️ 5. Accession எண்கள் மேலாண்மை (இறுதிக்கட்டப் பணி)", key="nav_5", use_container_width=True, type="primary" if style_button_active("⚙️ 5.") else "secondary"):
    str_lit.session_state['current_page'] = "⚙️ 5. Accession எண்கள் மேலாண்மை (இறுதிக்கட்டப் பணி)"
    str_lit.rerun()

str_lit.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")

EXCEL_FILE = "Book Supply-2026.xlsx"

@str_lit.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    excel_data = pd.ExcelFile(file_path)
    vendor_df = pd.read_excel(file_path, sheet_name="Vendor Name") if "Vendor Name" in excel_data.sheet_names else pd.DataFrame()
    book_sheet_name = [s for s in excel_data.sheet_names if "Vendor Wise Book Data" in s]
    book_df = pd.read_excel(file_path, sheet_name=book_sheet_name[0]) if book_sheet_name else pd.DataFrame()
    return vendor_df, book_df

vendor_df, book_df = load_data(EXCEL_FILE)

def clean_text(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    s = re.sub(r'^\d+[\.\s\-]*', '', s)
    return re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', '', s).lower()

@str_lit.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(str_lit.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

sheet_physically = None
sheet_vendor_wise = None
sheet_library_details = None

try:
    client = init_gspread()
    spreadsheet = client.open_by_key("1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc")
    all_worksheets = {ws.title.strip().lower(): ws for ws in spreadsheet.worksheets()}
    
    for title, ws in all_worksheets.items():
        if "physically verified" in title:
            sheet_physically = ws
        elif "vendor wise book data" in title:
            sheet_vendor_wise = ws
        elif "lib_detail" in title or "library detail" in title or "library details" in title:
            sheet_library_details = ws
except Exception as e:
    str_lit.error(f"❌ Google Sheet இணைப்புப் பிழை: {e}")

if 'verified_list' not in str_lit.session_state:
    str_lit.session_state['verified_list'] = []
if 'vendor_key' not in str_lit.session_state:
    str_lit.session_state['vendor_key'] = 0
if 'book_key' not in str_lit.session_state:
    str_lit.session_state['book_key'] = 0
if 'selected_vendor' not in str_lit.session_state:
    str_lit.session_state['selected_vendor'] = None

menu_choice = str_lit.session_state['current_page']

# ---------------------------------------------------------
# பணி 1: பெறப்பட்ட நூல்கள் சரிபார்ப்பு
# ---------------------------------------------------------
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    str_lit.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல்")
    if vendor_df is None or book_df is None:
        str_lit.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        str_lit.stop()

    saved_entries = set()
    if sheet_physically:
        try:
            records = sheet_physically.get_all_values()
            for r in records[1:]:
                if len(r) >= 2:
                    saved_entries.add((clean_text(r[0]), clean_text(r[1])))
        except Exception:
            pass

    vendor_list = []
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            label = col_b if col_b else col_c
            if label and label.lower() != "nan" and label not in vendor_list:
                vendor_list.append(label)

    str_lit.markdown("---")
    str_lit.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    col_v_select, col_v_btn = str_lit.columns([5, 1])

    with col_v_select:
        selected_vendor_raw = str_lit.selectbox(
            "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
            ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list, 
            key=f"vendor_select_{str_lit.session_state['vendor_key']}",
            label_visibility="collapsed"
        )

    with col_v_btn:
        if str_lit.button("🔄 பதிப்பகத்தை மாற்றுக", key="btn_v_change", use_container_width=True):
            str_lit.session_state['selected_vendor'] = None
            str_lit.session_state['vendor_key'] += 1
            str_lit.rerun()

    if selected_vendor_raw and selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        str_lit.session_state['selected_vendor'] = selected_vendor_raw

    if str_lit.session_state['selected_vendor']:
        target_vendor_clean = clean_text(str_lit.session_state['selected_vendor'])
        mask = book_df.iloc[:, 9].apply(lambda x: clean_text(x) == target_vendor_clean) | book_df.iloc[:, 10].apply(lambda x: clean_text(x) == target_vendor_clean)
        filtered_books = book_df[mask]

        if filtered_books.empty:
            str_lit.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் எதுவும் இல்லை!")
        else:
            grouped = filtered_books.groupby(['Title', 'Author Name', 'Language'], as_index=False).agg({
                'Quantity': 'sum', 'Original Price': 'first', 'Acccepted Price': 'first', 'Isbn': 'first', 'Book Id': 'first'
            })
            
            c1, c2 = str_lit.columns(2)
            c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
            c2.metric("📦 மொத்தப் படிகள்", int(grouped['Quantity'].sum()))

            added_titles_clean = [clean_text(x['Title']) for x in str_lit.session_state['verified_list']]
            title_options = ["-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
            
            for idx, row in grouped.iterrows():
                t_str = str(row['Title']).strip()
                t_clean = clean_text(t_str)
                if t_clean not in added_titles_clean and (target_vendor_clean, t_clean) not in saved_entries:
                    a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                    disp = f"{t_str} - {a_str}" if a_str else t_str
                    title_options.append(disp)
            
            if len(title_options) == 1:
                str_lit.success("🎉 இந்த பதிப்பகத்தின் அனைத்துப் புத்தகங்களும் ஏற்கனவே சரிபார்க்கப்பட்டுவிட்டன!")
            else:
                str_lit.markdown("### 📖 2. புத்தகத் தலைப்பதைத் தேர்ந்தெடுக்கவும்:")
                col_b_select, col_b_btn = str_lit.columns([5, 1])

                with col_b_select:
                    selected_title_disp = str_lit.selectbox(
                        "புத்தகத்தைத் தேர்ந்தெடுக்கவும்...", 
                        title_options, 
                        key=f"book_select_{str_lit.session_state['book_key']}",
                        label_visibility="collapsed"
                    )

                with col_b_btn:
                    if str_lit.button("🔄 தலைப்பை மாற்றுக", key="btn_b_change", use_container_width=True):
                        str_lit.session_state['book_key'] += 1
                        str_lit.rerun()

                if selected_title_disp and selected_title_disp != "-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                    matched_row = None
                    for idx, row in grouped.iterrows():
                        t_str = str(row['Title']).strip()
                        a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                        disp = f"{t_str} - {a_str}" if a_str else t_str
                        if disp == selected_title_disp:
                            matched_row = row
                            break
                            
                    if matched_row is not None:
                        tot_qty = int(matched_row['Quantity'])
                        with str_lit.form("verify_form"):
                            str_lit.write(f"📖 **புத்தகத் தலைப்பு:** {matched_row['Title']}")
                            str_lit.write(f"✍️ **ஆசிரியர் பெயர்:** {matched_row['Author Name']}")
                            rec_qty = str_lit.number_input("📦 பெறப்பட்ட படிகள் (எண்ணிக்கை):", min_value=0, max_value=1000, value=tot_qty)
                            submitted = str_lit.form_submit_button("➕ பட்டியலில் சேர் (Add to List)")
                            
                            if submitted:
                                not_rec_qty = max(0, tot_qty - rec_qty)
                                item = {
                                    "Vendor": str_lit.session_state['selected_vendor'],
                                    "Title": matched_row['Title'],
                                    "Language": matched_row['Language'],
                                    "Author": matched_row['Author Name'],
                                    "TotalQty": tot_qty,
                                    "ReceivedQty": rec_qty,
                                    "NotReceivedQty": not_rec_qty
                                }
                                str_lit.session_state['verified_list'].append(item)
                                str_lit.session_state['book_key'] += 1
                                str_lit.rerun()

    if str_lit.session_state['verified_list']:
        str_lit.markdown("---")
        str_lit.markdown("### 📋 சரிபார்க்கப்பட்ட தற்காலிகப் பட்டியல்:")
        v_df = pd.DataFrame(str_lit.session_state['verified_list'])
        v_df.index = range(1, len(v_df) + 1)
        str_lit.dataframe(v_df[['Vendor', 'Title', 'Language', 'Author', 'TotalQty', 'ReceivedQty', 'NotReceivedQty']], use_container_width=True)
        
        col_sub, col_del = str_lit.columns([3, 1])
        with col_sub:
            if str_lit.button("💾 கூகுள் ஷீட்டில் சேமி (Save All to Sheet)", key="btn_save", use_container_width=True):
                try:
                    curr_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    if sheet_physically:
                        rows_to_add = []
                        for item in str_lit.session_state['verified_list']:
                            rows_to_add.append([
                                item['Vendor'], item['Title'], item['Language'], item['Author'],
                                item['Vendor'], item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'], curr_date
                            ])
                        sheet_physically.append_rows(rows_to_add)
                    str_lit.balloons()
                    str_lit.success("🎉 வெற்றி! தரவுகள் கூகுள் ஷீட்டில் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    str_lit.session_state['verified_list'] = []
                    str_lit.rerun()
                except Exception as e:
                    str_lit.error(f"❌ பிழை: {e}")

        with col_del:
            if str_lit.button("🗑️ பட்டியலை அழி (Clear)", key="btn_clear", use_container_width=True):
                str_lit.session_state['verified_list'] = []
                str_lit.rerun()

# ---------------------------------------------------------
# பணி 2: Google Sheet தரவு ஒத்திசைவு (Sync)
# ---------------------------------------------------------
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    str_lit.subheader("🔄 2. பதிப்பகம் வாரியாக பெறப்பட்ட நூல்களின் பட்டியல் & ஒத்திசைவு")

    if not sheet_physically or not sheet_vendor_wise:
        str_lit.error("❌ கூகுள் ஷீட் இணைப்புகள் சரியாக இல்லை!")
    else:
        try:
            p_records = sheet_physically.get_all_values()
            vwbd_all_data = sheet_vendor_wise.get_all_values()
            
            synced_vendors = set()
            if len(vwbd_all_data) > 1:
                for r in vwbd_all_data[1:]:
                    if len(r) > 18 and str(r[18]).strip() == "1":
                        synced_vendors.add(clean_text(r[10]))

            p_vendors = []
            if len(p_records) > 1:
                for row in p_records[1:]:
                    if len(row) >= 1:
                        v_raw = row[0]
                        if v_raw and clean_text(v_raw) not in synced_vendors and v_raw not in p_vendors:
                            p_vendors.append(v_raw)

            if not p_vendors:
                str_lit.success("🟢 அனைத்துப் பதிப்பகங்களின் தரவுகளும் ஏற்கனவே ஒத்திசைவு செய்யப்பட்டுவிட்டன!")
            else:
                selected_sync_vendor = str_lit.selectbox("ஒத்திசைவு செய்ய வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + p_vendors)

                if selected_sync_vendor and selected_sync_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    sync_vendor_clean = clean_text(selected_sync_vendor)
                    str_lit.markdown(f"### 📋 {selected_sync_vendor} - விவரங்கள்:")
                    
                    vendor_books = [r for r in p_records[1:] if clean_text(r[0]) == sync_vendor_clean]
                    df_v = pd.DataFrame(vendor_books, columns=["Vendor", "Title", "Lang", "Auth", "V2", "Total", "Rec", "NotRec", "Date"])
                    str_lit.dataframe(df_v[['Title', 'Total', 'Rec']], use_container_width=True)

                    if str_lit.button(f"🚀 {selected_sync_vendor} தரவை மட்டும் ஒத்திசைவு செய்", key="btn_sync_single"):
                        with str_lit.spinner("⏳ தேர்ந்தெடுக்கப்பட்ட பதிப்பகத்தின் தரவுகள் மட்டும் துல்லியமாக ஒத்திசைவு செய்யப்படுகின்றன..."):
                            batch_updates = []
                            
                            for rec in vendor_books:
                                target_title = clean_text(rec[1])
                                r_qty = int(rec[6]) if str(rec[6]).isdigit() else 0
                                
                                matched_count = 0
                                for r_idx, r_data in enumerate(vwbd_all_data[1:], start=2):
                                    if len(r_data) > 10:
                                        s_title = clean_text(r_data[4])
                                        s_pub = clean_text(r_data[9])
                                        s_vendor = clean_text(r_data[10])

                                        if (sync_vendor_clean == s_pub or sync_vendor_clean == s_vendor) and (target_title == s_title):
                                            if matched_count < r_qty:
                                                batch_updates.append({'range': f'S{r_idx}:T{r_idx}', 'values': [[1, 0]]})
                                                matched_count += 1
                                            else:
                                                break
                            
                            if batch_updates:
                                sheet_vendor_wise.batch_update(batch_updates)
                                str_lit.success(f"✅ {selected_sync_vendor} தரவுகள் வெற்றிகரமாக ஒத்திசைக்கப்பட்டன!")
                                time.sleep(1)
                                str_lit.rerun()
                            else:
                                str_lit.warning("⚠️ தரவுகள் ஷீட்டுடன் பொருந்தவில்லை, சரிபார்க்கவும்.")

        except Exception as e:
            str_lit.error(f"❌ பிழை: {e}")

# ---------------------------------------------------------
# பணி 3: 480 பதிப்பாளர் விவரங்கள்
# ---------------------------------------------------------
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    str_lit.subheader("🏢 3. 480 பதிப்பாளர் வாரியான நூல் விவரங்கள் (Live Google Sheet)")
    if not sheet_vendor_wise:
        str_lit.error("❌ கூகுள் ஷீட் 'Vendor Wise Book Data' கிடைக்கவில்லை!")
    else:
        with str_lit.spinner("⏳ Google Sheet-ல் இருந்து நேரலைத் தரவை ஏற்றி வருகிறது..."):
            vwbd_all_data = sheet_vendor_wise.get_all_values()
            if len(vwbd_all_data) > 1:
                live_df = pd.DataFrame(vwbd_all_data[1:], columns=vwbd_all_data[0])
                vendor_col = live_df.columns[10] if len(live_df.columns) > 10 else live_df.columns[9]
                live_vendors = sorted(list(set(live_df[vendor_col].dropna().astype(str).str.strip())))
                
                selected_v = str_lit.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + live_vendors)
                if selected_v and selected_v != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    filtered_live_df = live_df[live_df[vendor_col].astype(str).str.strip() == selected_v]
                    str_lit.markdown(f"### 📋 {selected_v} - மொத்தப் புத்தகங்கள் ({len(filtered_live_df)})")
                    str_lit.dataframe(filtered_live_df, use_container_width=True)

# ---------------------------------------------------------
# பணி 4: நூலகத்திற்கு விநியோகம் (103)
# ---------------------------------------------------------
elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    str_lit.subheader("🏛️ 4. 103 நூலகங்கள் வாரியான விநியோக அறிக்கை (Report Generator)")
    if not sheet_vendor_wise or not sheet_library_details:
        str_lit.error("❌ கூகுள் ஷீட் தரவுகள் கிடைக்கவில்லை!")
    else:
        with str_lit.spinner("⏳ கூகுள் ஷீட்டில் உள்ள நேரலைத் தரவுகள் மற்றும் Accession எண்களை ஏற்றி வருகிறது..."):
            vwbd_all_data = sheet_vendor_wise.get_all_values()
            live_df = pd.DataFrame(vwbd_all_data[1:], columns=vwbd_all_data[0])
            
            lib_records = sheet_library_details.get_all_values()
            lib_map = {}
            lib_name_list = []

            for r in lib_records[1:]:
                if len(r) >= 3:
                    code = str(r[1]).strip()
                    name = str(r[2]).strip()
                    if name and name.lower() != "nan":
                        lib_map[code] = name
                        if name not in lib_name_list:
                            lib_name_list.append(name)

            lib_name_list = sorted(lib_name_list)
            
            str_lit.markdown("### 🏛️ நூலகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்:")
            selected_lib_name = str_lit.selectbox(
                "நூலகத்தைத் தேர்ந்தெடுக்கவும்...", 
                ["-- 🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + lib_name_list,
                label_visibility="collapsed"
            )

            if selected_lib_name and selected_lib_name != "-- 🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                col_o = live_df.columns[14] if len(live_df.columns) > 14 else None
                col_p = live_df.columns[15] if len(live_df.columns) > 15 else None
                
                selected_code = ""
                for c_code, c_name in lib_map.items():
                    if c_name == selected_lib_name:
                        selected_code = c_code
                        break

                clean_selected_name = clean_text(selected_lib_name)
                clean_selected_code = clean_text(selected_code)

                def is_match(row):
                    p_val = clean_text(row[col_p]) if col_p and col_p in row else ""
                    o_val = clean_text(row[col_o]) if col_o and col_o in row else ""
                    if clean_selected_name in p_val or p_val in clean_selected_name:
                        return True
                    if clean_selected_code and (clean_selected_code in o_val or o_val in clean_selected_code):
                        return True
                    return False

                filtered_lib_df = live_df[live_df.apply(is_match, axis=1)]

                if filtered_lib_df.empty:
                    str_lit.warning(f"⚠️ **{selected_lib_name}** நூலகத்திற்கு ஒதுக்கீடு செய்யப்பட்ட விவரங்கள் எதுவும் இல்லை!")
                else:
                    rec_col = live_df.columns[18] if len(live_df.columns) > 18 else None
                    if rec_col:
                        rec_df = filtered_lib_df[filtered_lib_df[rec_col].astype(str).str.strip() == "1"]
                    else:
                        rec_df = filtered_lib_df

                    c1, c2, c3 = str_lit.columns(3)
                    c1.metric("📖 மொத்த ஒதுக்கீடு", len(filtered_lib_df))
                    c2.metric("✅ பெறப்பட்ட புத்தகங்கள்", len(rec_df))
                    c3.metric("🏛️ நூலகக் குறியீடு (Code)", selected_code if selected_code else "N/A")

                    str_lit.markdown(f"### 📋 {selected_lib_name} - விநியோக அறிக்கை (Delivery Report)")
                    str_lit.dataframe(filtered_lib_df, use_container_width=True)

                    str_lit.markdown("---")
                    str_lit.markdown("### 📥 அறிக்கை பதிவிறக்கம் (Download Report):")
                    
                    csv_data = filtered_lib_df.to_csv(index=False).encode('utf-8-sig')
                    str_lit.download_button(
                        label=f"📄 {selected_lib_name} - CSV அறிக்கையைப் பதிவிறக்கு",
                        data=csv_data,
                        file_name=f"{selected_lib_name}_Book_Delivery_Report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )

# ---------------------------------------------------------
# பணி 5: Accession எண்கள் மேலாண்மை (இறுதிக்கட்டப் பணி)
# ---------------------------------------------------------
elif menu_choice == "⚙️ 5. Accession எண்கள் மேலாண்மை (இறுதிக்கட்டப் பணி)":
    str_lit.subheader("⚙️ 5. இறுதிக்கட்டப் பணி: Accession எண்கள் மற்றும் Batch ஒதுக்கீடு மேலாண்மை")
    str_lit.info("💡 **குறிப்பு:** அனைத்துப் பதிப்பகங்களின் நூலகங்களும் முழுமையாகச் சரிபார்க்கப்பட்டு, Vendor Wise Book Data ஷீட்டிற்கு ஒத்திசைவு செய்யப்பட்ட பிறகே இந்தப் பணியைச் செய்ய வேண்டும்.")

    if not sheet_library_details or not sheet_vendor_wise or not sheet_physically:
        str_lit.error("❌ கூகுள் ஷீட் தரவுகள் முழுமையாகக் கிடைக்கவில்லை!")
    else:
        with str_lit.spinner("⏳ Lib_Detail மற்றும் Vendor தரவுகள் பெறப்படுகின்றன..."):
            lib_records = sheet_library_details.get_all_values()
            vwbd_data = sheet_vendor_wise.get_all_values()
            p_records = sheet_physically.get_all_values()
            
            if len(lib_records) > 1:
                central_val = lib_records[1][5] if len(lib_records[1]) > 5 and str(lib_records[1][5]).strip() != "" else "1001"

                str_lit.markdown("---")
                str_lit.markdown("### 🏷️ 1. Last Central Accession Number")
                c1, c2 = str_lit.columns([2, 3])
                with c1:
                    str_lit.metric("தற்போதைய எண்கள் (F2)", central_val)
                with c2:
                    new_central = str_lit.number_input("புதிய Central Accession Number அமைக்கவும்:", min_value=1, value=int(central_val) if str(central_val).isdigit() else 1001)
                    if str_lit.button("💾 Central Accession எண்ணைப் புதுப்பி", key="btn_update_central"):
                        sheet_library_details.update_cell(2, 6, new_central)
                        str_lit.success(f"✅ Last Central Accession Number {new_central} எனப் புதுப்பிக்கப்பட்டது!")
                        str_lit.rerun()

                str_lit.markdown("---")
                str_lit.markdown("### 🚀 2. அனைத்துப் பதிப்பகங்களுக்கும் இறுதி Accession எண்களை ஒட்டுமொத்தமாக வழங்குதல் (Batch Sync)")
                str_lit.warning("⚠️ இந்த பொத்தானை அழுத்தினால், இதுவரை சரிபார்க்கப்பட்ட அனைத்துப் புத்தகங்களுக்கும் Central மற்றும் நூலக Accession எண்கள் கணக்கிட்டு Google Sheet-ல் பதியப்படும்.")
                
                if str_lit.button("⚡ அனைத்துப் பதிப்பகங்களுக்கும் Accession எண்களை ஒதுக்கு (Final Allocation)", key="btn_final_sync", use_container_width=True):
                    with str_lit.spinner("⏳ இறுதி Accession எண்கள் ஒதுக்கீடு செய்யப்படுகின்றன..."):
                        last_central_acc = int(central_val) if str(central_val).isdigit() else 1001
                        
                        lib_acc_map = {}
                        for idx, r in enumerate(lib_records[1:], start=2):
                            if len(r) >= 7:
                                code = str(r[1]).strip()
                                g_val = str(r[6]).strip()
                                last_lib_acc = int(g_val) if g_val.isdigit() else 1000
                                if code:
                                    lib_acc_map[code] = {'last_acc': last_lib_acc, 'row_idx': idx}

                        curr_central_acc = last_central_acc
                        updated_count = 0
                        batch_updates_vendor = []

                        for rec in p_records[1:]:
                            if len(rec) >= 8:
                                sync_vendor_clean = clean_text(rec[0])
                                target_title_clean = clean_text(rec[1])
                                needed_qty = int(rec[6]) if str(rec[6]).isdigit() else 0
                                matched_count = 0

                                for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                                    if len(r_data) > 14:
                                        sheet_title_clean = clean_text(r_data[4])
                                        sheet_pub_clean = clean_text(r_data[9])
                                        sheet_vendor_clean = clean_text(r_data[10])
                                        lib_code = str(r_data[14]).strip()

                                        is_vendor_matched = (sync_vendor_clean == sheet_pub_clean or sync_vendor_clean == sheet_vendor_clean)
                                        is_title_matched = (target_title_clean in sheet_title_clean or sheet_title_clean in target_title_clean)

                                        if is_vendor_matched and is_title_matched:
                                            if matched_count < needed_qty:
                                                curr_central_acc += 1
                                                if lib_code in lib_acc_map:
                                                    lib_acc_map[lib_code]['last_acc'] += 1
                                                    next_lib_acc = lib_acc_map[lib_code]['last_acc']
                                                else:
                                                    next_lib_acc = 1001

                                                batch_updates_vendor.append({
                                                    'range': f'S{r_idx}:V{r_idx}',
                                                    'values': [[1, 0, curr_central_acc, next_lib_acc]]
                                                })
                                                matched_count += 1
                                                updated_count += 1
                                            else:
                                                batch_updates_vendor.append({
                                                    'range': f'S{r_idx}:V{r_idx}',
                                                    'values': [[0, 1, "", ""]]
                                                })

                        if batch_updates_vendor:
                            sheet_vendor_wise.batch_update(batch_updates_vendor)

                        batch_updates_lib = [{'range': 'F2', 'values': [[curr_central_acc]]}]
                        for code, data in lib_acc_map.items():
                            batch_updates_lib.append({
                                'range': f'G{data["row_idx"]}',
                                'values': [[data['last_acc']]]
                            })
                        sheet_library_details.batch_update(batch_updates_lib)

                        str_lit.balloons()
                        str_lit.success(f"🎉 வெற்றி! அனைத்துப் புத்தகங்களுக்கும் {updated_count} Accession எண்கள் வெற்றிகரமாக ஒதுக்கப்பட்டுவிட்டன!")
                        time.sleep(1.5)
                        str_lit.rerun()

                str_lit.markdown("---")
                str_lit.markdown("### 🏛️ 3. நூலகங்கள் வாரியான Last Accession Number மேலாண்மை (DCL / FTB / BL / VL)")
                
                extracted_data = []
                for idx, r in enumerate(lib_records[1:], start=2):
                    if len(r) >= 3:
                        l_code = str(r[1]).strip()
                        l_name = str(r[2]).strip()
                        l_acc = str(r[6]).strip() if len(r) > 6 else ""
                        if l_code and l_code.lower() != "nan":
                            extracted_data.append({
                                'row_idx': idx,
                                'Lib Code': l_code,
                                'Library Name': l_name,
                                'DCL /FTB /BL / VL LAST ACCESION NUMBER': l_acc
                            })
                
                df_lib_extracted = pd.DataFrame(extracted_data)
                type_filter = str_lit.radio("நூலக வகையைத் தேர்ந்தெடுக்கவும் (Category Filter):", ["அனைத்தும் (All 103)", "DCL", "FTB", "BL", "VL"], horizontal=True)
                
                filtered_df = df_lib_extracted.copy()
                if type_filter != "அனைத்தும் (All 103)":
                    filtered_df = filtered_df[filtered_df['Lib Code'].astype(str).str.upper().str.contains(type_filter.upper(), na=False)]
                
                str_lit.dataframe(filtered_df[['Lib Code', 'Library Name', 'DCL /FTB /BL / VL LAST ACCESION NUMBER']], use_container_width=True)

                str_lit.markdown("---")
                str_lit.markdown("### ✏️ குறிப்பிட்ட நூலகத்தின் எண்களை நேரடியாக மாற்ற:")
                
                lib_options = []
                for idx, row in filtered_df.iterrows():
                    lib_options.append(f"{row['Lib Code']} - {row['Library Name']}")
                
                if not lib_options:
                    str_lit.warning("⚠️ தேர்ந்தெடுக்கப்பட்ட பிரிவில் நூலகங்கள் எதுவும் கிடைக்கவில்லை!")
                else:
                    col_sel, col_val = str_lit.columns([3, 2])
                    with col_sel:
                        selected_lib_opt = str_lit.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- தேர்ந்தெடுக்கவும் --"] + lib_options)
                    
                    if selected_lib_opt and selected_lib_opt != "-- தேர்ந்தெடுக்கவும் --":
                        sel_code = selected_lib_opt.split(" - ")[0].strip()
                        target_row_info = filtered_df[filtered_df['Lib Code'] == sel_code].iloc[0]
                        target_row_idx = target_row_info['row_idx']
                        curr_acc_str = str(target_row_info['DCL /FTB /BL / VL LAST ACCESION NUMBER']).strip()
                        curr_acc = int(curr_acc_str) if curr_acc_str.isdigit() else 1000
                        
                        with col_val:
                            new_lib_acc = str_lit.number_input(f"{sel_code} - புதிய Acc No:", min_value=1, value=curr_acc)
                        
                        if str_lit.button("💾 நூலக Accession எண்ணைப் புதுப்பி", key="btn_update_lib", use_container_width=True):
                            sheet_library_details.update_cell(target_row_idx, 7, new_lib_acc)
                            str_lit.success(f"✅ {sel_code} நூலகத்தின் Last Accession Number {new_lib_acc} என வெற்றிகரமாக மாற்றப்பட்டது!")
                            str_lit.rerun()
