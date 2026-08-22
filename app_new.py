import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import re

# 1. Streamlit பக்க அமைப்பு
st.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide")

st.title("📚 2026 புதிய நூல்கள் விநியோகம் - பணி போர்ட்டல்")

# 2. எக்செல் கோப்பை ஏற்றுதல்
EXCEL_FILE = "Book Supply-2026.xlsx"

@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path):
        return None, None
    
    excel_data = pd.ExcelFile(file_path)
    vendor_df = pd.read_excel(file_path, sheet_name="Vendor Name") if "Vendor Name" in excel_data.sheet_names else pd.DataFrame()
    
    book_sheet_name = [s for s in excel_data.sheet_names if "Vendor Wise Book Data" in s]
    book_df = pd.read_excel(file_path, sheet_name=book_sheet_name[0]) if book_sheet_name else pd.DataFrame()
    
    return vendor_df, book_df

vendor_df, book_df = load_data(EXCEL_FILE)

# உரை சுத்தப்படுத்தும் சார்பு
def clean_text(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    s = re.sub(r'^\d+[\.\s\-]*', '', s)
    return re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', '', s).lower()

# 3. கூகுள் ஷீட் இணைப்பு
@st.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

sheet_physically = None
sheet_vendor_wise = None

try:
    client = init_gspread()
    spreadsheet = client.open_by_key("1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc")
    
    all_worksheets = {ws.title.strip().lower(): ws for ws in spreadsheet.worksheets()}
    
    for title, ws in all_worksheets.items():
        if "physically verified" in title:
            sheet_physically = ws
        elif "vendor wise book data" in title:
            sheet_vendor_wise = ws

except Exception as e:
    st.error(f"❌ Google Sheet இணைப்புப் பிழை: {e}")

# Session State அமைப்புகள்
if 'verified_list' not in st.session_state:
    st.session_state['verified_list'] = []

if 'vendor_key' not in st.session_state:
    st.session_state['vendor_key'] = 0

if 'book_key' not in st.session_state:
    st.session_state['book_key'] = 0

if 'show_vendor_select' not in st.session_state:
    st.session_state['show_vendor_select'] = True

if 'show_book_select' not in st.session_state:
    st.session_state['show_book_select'] = False

# 4. இடதுபுற மெனு
st.sidebar.header("📌 முதன்மைப் பணிகள்")
menu_choice = st.sidebar.radio(
    "பணியைத் தேர்ந்தெடுக்கவும்:",
    [
        "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)",
        "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "🏛️ 4. நூலகத்திற்கு விநியோகம் (104)"
    ]
)

# ---------------------------------------------------------
# பணி 1: பெறப்பட்ட நூல்கள் சரிபார்ப்பு
# ---------------------------------------------------------
if menu_choice == "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல்")
    
    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    # ஏற்கனவே சேமிக்கப்பட்ட தரவுகளை மீட்டெடுத்தல்
    saved_entries = set()
    if sheet_physically:
        try:
            records = sheet_physically.get_all_values()
            for r in records[1:]:
                if len(r) >= 2:
                    v_c = clean_text(r[0])
                    t_c = clean_text(r[1])
                    saved_entries.add((v_c, t_c))
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

    # வலது பக்க பொத்தான்களுக்கான லேஅவுட் (Layout with Right Side Buttons)
    col_left, col_right = st.columns([3, 1])

    with col_right:
        st.markdown("### 🔘 விரைவுப் பொத்தான்கள்")
        btn_select_vendor = st.button("🏢 1. பதிப்பகத்தைத் தேர்வு செய்க", use_container_width=True, type="primary")
        btn_change_title = st.button("📖 2. தலைப்பினைத் தேர்வு செய்க / மாற்றுக", use_container_width=True)

        if btn_select_vendor:
            st.session_state['show_vendor_select'] = True
            st.session_state['show_book_select'] = False
            st.rerun()

        if btn_change_title:
            st.session_state['show_vendor_select'] = False
            st.session_state['show_book_select'] = True
            st.rerun()

    with col_left:
        # பதிப்பகம் தேர்ந்தெடுக்கும் பகுதி
        selected_vendor_raw = None
        if st.session_state['show_vendor_select']:
            st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
            selected_vendor_raw = st.selectbox(
                "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
                ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list, 
                key=f"vendor_select_{st.session_state['vendor_key']}",
                label_visibility="collapsed"
            )
            if selected_vendor_raw and selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                st.session_state['selected_vendor_store'] = selected_vendor_raw
                st.session_state['show_vendor_select'] = False
                st.session_state['show_book_select'] = True
                st.rerun()
        else:
            selected_vendor_raw = st.session_state.get('selected_vendor_store', None)
            if selected_vendor_raw:
                st.success(f"🏢 **தேர்ந்தெடுக்கப்பட்ட பதிப்பகம்:** {selected_vendor_raw}")

        # புத்தகம் தேர்ந்தெடுக்கும் மற்றும் சரிபார்க்கும் பகுதி
        if selected_vendor_raw and selected_vendor_raw != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            target_vendor_clean = clean_text(selected_vendor_raw)
            
            def is_vendor_match(row_val):
                return clean_text(row_val) == target_vendor_clean

            mask = book_df.iloc[:, 9].apply(is_vendor_match) | book_df.iloc[:, 10].apply(is_vendor_match)
            filtered_books = book_df[mask]

            if filtered_books.empty:
                st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் எதுவும் இல்லை!")
            else:
                grouped = filtered_books.groupby(['Title', 'Author Name', 'Language'], as_index=False).agg({
                    'Quantity': 'sum',
                    'Original Price': 'first',
                    'Acccepted Price': 'first',
                    'Isbn': 'first',
                    'Book Id': 'first'
                })
                
                c1, c2 = st.columns(2)
                c1.metric("📚 மொத்தத் தலைப்புகள்", len(grouped))
                c2.metric("📦 மொத்தப் படிகள்", int(grouped['Quantity'].sum()))

                added_titles_clean = [clean_text(x['Title']) for x in st.session_state['verified_list']]
                title_options = ["-- 📖 புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
                
                for idx, row in grouped.iterrows():
                    t_str = str(row['Title']).strip()
                    t_clean = clean_text(t_str)
                    
                    if t_clean not in added_titles_clean and (target_vendor_clean, t_clean) not in saved_entries:
                        a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                        disp = f"{t_str} - {a_str}" if a_str else t_str
                        title_options.append(disp)
                
                if len(title_options) == 1:
                    st.success("🎉 இந்த பதிப்பகத்தின் அனைத்துப் புத்தகங்களும் ஏற்கனவே சரிபார்க்கப்பட்டுவிட்டன!")
                else:
                    st.markdown("### 📖 2. புத்தகத் தலைப்பதைத் தேர்ந்தெடுக்கவும்:")
                    selected_title_disp = st.selectbox(
                        "புத்தகத்தைத் தேர்ந்தெடுக்கவும்...", 
                        title_options, 
                        key=f"book_select_{st.session_state['book_key']}",
                        label_visibility="collapsed"
                    )
                    
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
                            with st.form("verify_form"):
                                st.write(f"📖 **புத்தகத் தலைப்பு:** {matched_row['Title']}")
                                st.write(f"✍️ **ஆசிரியர் பெயர்:** {matched_row['Author Name']}")
                                rec_qty = st.number_input("📦 பெறப்பட்ட படிகள் (எண்ணிக்கை):", min_value=0, max_value=1000, value=tot_qty)
                                submitted = st.form_submit_button("➕ பட்டியலில் சேர் (Add to List)")
                                
                                if submitted:
                                    not_rec_qty = max(0, tot_qty - rec_qty)
                                    item = {
                                        "Vendor": selected_vendor_raw,
                                        "Title": matched_row['Title'],
                                        "Language": matched_row['Language'],
                                        "Author": matched_row['Author Name'],
                                        "TotalQty": tot_qty,
                                        "ReceivedQty": rec_qty,
                                        "NotReceivedQty": not_rec_qty
                                    }
                                    st.session_state['verified_list'].append(item)
                                    st.session_state['book_key'] += 1
                                    st.rerun()

    if st.session_state['verified_list']:
        st.markdown("---")
        st.subheader("📋 சரிபார்க்கப்பட்ட தற்காலிகப் பட்டியல்")
        
        v_df = pd.DataFrame(st.session_state['verified_list'])
        v_df.index = range(1, len(v_df) + 1)
        st.dataframe(v_df[['Vendor', 'Title', 'Language', 'Author', 'TotalQty', 'ReceivedQty']], use_container_width=True)
        
        col_sub, col_del = st.columns([3, 1])
        with col_del:
            if st.button("🗑️ பட்டியலை அழி (Clear)", use_container_width=True):
                st.session_state['verified_list'] = []
                st.rerun()
                
        with col_sub:
            if st.button("💾 🟢 கூகுள் ஷீட்டில் சேமி (Save All to Sheet)", use_container_width=True):
                try:
                    curr_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    if sheet_physically:
                        rows_to_add = []
                        for item in st.session_state['verified_list']:
                            rows_to_add.append([
                                item['Vendor'], item['Title'], item['Language'], item['Author'],
                                item['Vendor'], item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'],
                                curr_date
                            ])
                        sheet_physically.append_rows(rows_to_add)

                    st.balloons()
                    st.success("🎉 வெற்றி! தரவுகள் கூகுள் ஷீட்டில் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    st.session_state['verified_list'] = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ பிழை: {e}")

# ---------------------------------------------------------
# பணி 2: Google Sheet தரவு ஒத்திசைவு (Sync)
# ---------------------------------------------------------
elif menu_choice == "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 2. பதிப்பகம் வாரியாக தரவு ஒத்திசைவு (Vendor Wise Sync)")
    st.info("💡 'Physically Verified' தாளில் சேமிக்கப்பட்டு, இன்னும் ஒத்திசைக்கப்படாத பதிப்பகங்கள் மட்டும் தோன்றும்.")

    if not sheet_physically or not sheet_vendor_wise:
        st.error("❌ கூகுள் ஷீட் இணைப்புகள் சரியாக இல்லை!")
    else:
        try:
            p_records = sheet_physically.get_all_values()
            vwbd_data = sheet_vendor_wise.get_all_values()

            synced_pairs = set()
            for r_data in vwbd_data[1:]:
                if len(r_data) >= 19 and str(r_data[18]).strip() == "1":
                    v_c = clean_text(r_data[10]) if len(r_data) > 10 else ""
                    t_c = clean_text(r_data[4]) if len(r_data) > 4 else ""
                    synced_pairs.add((v_c, t_c))

            p_vendors = []
            if len(p_records) > 1:
                for row in p_records[1:]:
                    if len(row) >= 2:
                        v_raw = row[0]
                        v_c = clean_text(v_raw)
                        t_c = clean_text(row[1])
                        if (v_c, t_c) not in synced_pairs and v_raw and v_raw not in p_vendors:
                            p_vendors.append(v_raw)

            if not p_vendors:
                st.success("🟢 அனைத்துப் பதிப்பகங்களின் தரவுகளும் ஏற்கனவே ஒத்திசைக்கப்பட்டுவிட்டன!")
            else:
                st.markdown("### 🏢 புதுப்பிக்க வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
                selected_sync_vendor = st.selectbox(
                    "பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்...", 
                    ["-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + p_vendors,
                    label_visibility="collapsed"
                )

                if selected_sync_vendor and selected_sync_vendor != "-- 🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    sync_vendor_clean = clean_text(selected_sync_vendor)
                    
                    filtered_records = []
                    for row in p_records[1:]:
                        if len(row) >= 7 and (clean_text(row[0]) == sync_vendor_clean or clean_text(row[4]) == sync_vendor_clean):
                            filtered_records.append({
                                "🏢 பதிப்பகம்": row[0],
                                "📖 புத்தகத் தலைப்பு": row[1],
                                "🗣️ மொழி": row[2],
                                "📦 மொத்த படிகள்": row[5],
                                "✅ பெறப்பட்ட படிகள்": row[6]
                            })

                    if filtered_records:
                        st.write(f"### 📋 {selected_sync_vendor} - ஒத்திசைக்கப்பட வேண்டிய புத்தகங்கள்:")
                        st.dataframe(pd.DataFrame(filtered_records), use_container_width=True)

                        if st.button(f"🚀 🔴 {selected_sync_vendor} - தரவை கூகுள் ஷீட்டில் புதுப்பி (Sync Now)", use_container_width=True):
                            with st.spinner("⏳ சரியான பதிப்பகத்தை சரிபார்த்து புதுப்பிக்கிறது..."):
                                updated_count = 0

                                for rec in filtered_records:
                                    target_title_clean = clean_text(rec["📖 புத்தகத் தலைப்பு"])
                                    target_vendor_clean = clean_text(rec["🏢 பதிப்பகம்"])
                                    
                                    try:
                                        needed_qty = int(rec["✅ பெறப்பட்ட படிகள்"])
                                    except ValueError:
                                        needed_qty = 0

                                    matched_count = 0
                                    
                                    for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                                        if len(r_data) > 10:
                                            sheet_title_clean = clean_text(r_data[4])   # Col E
                                            sheet_pub_clean = clean_text(r_data[9])     # Col J
                                            sheet_vendor_clean = clean_text(r_data[10]) # Col K
                                            
                                            is_vendor_matched = (target_vendor_clean == sheet_pub_clean or target_vendor_clean == sheet_vendor_clean)
                                            is_title_matched = (target_title_clean in sheet_title_clean or sheet_title_clean in target_title_clean or target_title_clean[:8] == sheet_title_clean[:8])
                                            
                                            if is_vendor_matched and is_title_matched:
                                                if matched_count < needed_qty:
                                                    sheet_vendor_wise.update_cell(r_idx, 19, 1)
                                                    sheet_vendor_wise.update_cell(r_idx, 20, 0)
                                                    matched_count += 1
                                                    updated_count += 1

                                if updated_count > 0:
                                    st.balloons()
                                    st.success(f"🎉 🟢 வெற்றி! '{selected_sync_vendor}' பதிப்பகத்திற்குச் சரியாக {updated_count} வரிகளுக்கு Received = 1 எனக் கூகுள் ஷீட்டில் எழுதப்பட்டது!")
                                    st.rerun()
                                else:
                                    st.error("❌ தேர்ந்தெடுத்த பதிப்பகம் மற்றும் புத்தக தலைப்புகள் கூகுள் ஷீட்டில் சரியாகப் பொருந்தவில்லை!")

        except Exception as e:
            st.error(f"❌ பிழை ஏற்பட்டது: {e}")

# ---------------------------------------------------------
# பணி 3 & 4
# ---------------------------------------------------------
elif menu_choice == "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    if vendor_df is not None and not vendor_df.empty:
        vendors_list = vendor_df.iloc[:, 2].dropna().unique().tolist()
        selected_vendor = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors_list)
        if selected_vendor and selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and book_df is not None:
            filtered_books = book_df[book_df.iloc[:, 9].astype(str).str.strip() == str(selected_vendor).strip()]
            st.dataframe(filtered_books, use_container_width=True)

elif menu_choice == "🏛️ 4. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 4. 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    if book_df is not None and not book_df.empty:
        lib_col_idx = 12 if book_df.shape[1] > 12 else 0
        libraries = book_df.iloc[:, lib_col_idx].dropna().unique().tolist()
        selected_lib = st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + libraries)
        if selected_lib and selected_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            filtered_lib_books = book_df[book_df.iloc[:, lib_col_idx].astype(str).str.strip() == str(selected_lib).strip()]
            st.dataframe(filtered_lib_books, use_container_width=True)
