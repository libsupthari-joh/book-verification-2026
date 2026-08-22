import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import re

# 1. Streamlit பக்க அமைப்பு
st.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide")

st.title("📚 2026 புதிய நூல்கள் விநியோகம்")

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
    st.error(f"Google Sheet இணைப்புப் பிழை: {e}")

# Session State
if 'verified_list' not in st.session_state:
    st.session_state['verified_list'] = []

if 'vendor_key' not in st.session_state:
    st.session_state['vendor_key'] = 0

if 'book_key' not in st.session_state:
    st.session_state['book_key'] = 0

# 4. இடதுபுற மெனு
st.sidebar.header("📋 முதன்மை பணிகள்")
menu_choice = st.sidebar.radio(
    "பணியைத் தேர்ந்தெடுக்கவும்:",
    [
        "1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "2. 🔄 Google Sheet தரவு ஒத்திசைவு (Sync)",
        "3. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "4. நூலகத்திற்கு விநியோகம் (104)"
    ]
)

# ---------------------------------------------------------
# பணி 1: பெறப்பட்ட நூல்கள் சரிபார்ப்பு
# ---------------------------------------------------------
if menu_choice == "1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("🔍 பெறப்பட்ட நூல்கள் சரிபார்ப்பு போர்ட்டல்")
    
    if vendor_df is None or book_df is None:
        st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!")
        st.stop()

    vendor_list = []
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            label = col_b if col_b else col_c
            if label and label.lower() != "nan" and label not in vendor_list:
                vendor_list.append(label)
                
    st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    
    selected_vendor_raw = st.selectbox(
        "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list, 
        key=f"vendor_select_{st.session_state['vendor_key']}",
        label_visibility="collapsed"
    )
    
    if selected_vendor_raw and selected_vendor_raw != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
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
            c1.metric("📋 மொத்த தலைப்புகள்", len(grouped))
            c2.metric("📦 மொத்த படிகள்", int(grouped['Quantity'].sum()))
            
            st.subheader("2. புத்தகத் தலைப்பதைத் தேர்ந்தெடுக்கவும்:")
            
            added_titles_clean = [clean_text(x['Title']) for x in st.session_state['verified_list']]
            title_options = ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
            
            for idx, row in grouped.iterrows():
                t_str = str(row['Title']).strip()
                if clean_text(t_str) not in added_titles_clean:
                    a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                    disp = f"{t_str} - {a_str}" if a_str else t_str
                    title_options.append(disp)
            
            selected_title_disp = st.selectbox(
                "புத்தகத்தைத் தேர்ந்தெடுக்கவும்...", 
                title_options, 
                key=f"book_select_{st.session_state['book_key']}",
                label_visibility="collapsed"
            )
            
            if selected_title_disp and selected_title_disp != "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
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
                        st.write(f"**புத்தகத் தலைப்பு:** {matched_row['Title']}")
                        st.write(f"**ஆசிரியர் பெயர்:** {matched_row['Author Name']}")
                        rec_qty = st.number_input("பெறப்பட்ட படிகள் (எண்ணிக்கை):", min_value=0, max_value=1000, value=tot_qty)
                        submitted = st.form_submit_button("➕ பட்டியலில் சேர்")
                        
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
        st.subheader("📋 சரிபார்க்கப்பட்ட அறிக்கை")
        
        v_df = pd.DataFrame(st.session_state['verified_list'])
        v_df.index = range(1, len(v_df) + 1)
        st.dataframe(v_df[['Vendor', 'Title', 'Language', 'Author', 'TotalQty', 'ReceivedQty']], use_container_width=True)
        
        col_sub, col_del = st.columns([3, 1])
        with col_del:
            if st.button("🗑️ பட்டியலை அழி", use_container_width=True):
                st.session_state['verified_list'] = []
                st.rerun()
                
        with col_sub:
            if st.button("💾 கூகுள் ஷீட்டில் சேமி (Physically Verified)", use_container_width=True):
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
                    st.success("🎉 கூகுள் ஷீட்டில் சேமிக்கப்பட்டது!")
                    st.session_state['verified_list'] = []
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ பிழை: {e}")

# ---------------------------------------------------------
# பணி 2: Google Sheet தரவு ஒத்திசைவு (Sync) - நேரடி செல் புதுப்பிப்பு
# ---------------------------------------------------------
elif menu_choice == "2. 🔄 Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 பதிப்பகம் வாரியாக தரவு ஒத்திசைவு (Vendor Wise Sync)")
    st.info("💡 'Physically Verified' தாளில் சேமிக்கப்பட்ட பதிப்பகத்தைத் தேர்ந்தெடுத்து புதுப்பிக்கலாம்.")

    if not sheet_physically or not sheet_vendor_wise:
        st.error("❌ கூகுள் ஷீட் இணைப்புகள் சரியாக இல்லை!")
    else:
        try:
            p_records = sheet_physically.get_all_values()
            
            p_vendors = []
            if len(p_records) > 1:
                p_df = pd.DataFrame(p_records[1:])
                raw_v_list = p_df.iloc[:, 0].unique().tolist()
                p_vendors = [v for v in raw_v_list if v and str(v).strip() != ""]

            if not p_vendors:
                st.warning("⚠️ 'Physically Verified' தாளில் தரவுகள் எதுவும் இல்லை!")
            else:
                st.subheader("1. புதுப்பிக்க வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
                selected_sync_vendor = st.selectbox(
                    "பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்...", 
                    ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + p_vendors,
                    label_visibility="collapsed"
                )

                if selected_sync_vendor and selected_sync_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    sync_vendor_clean = clean_text(selected_sync_vendor)
                    
                    filtered_records = []
                    for row in p_records[1:]:
                        if len(row) >= 7 and (clean_text(row[0]) == sync_vendor_clean or clean_text(row[4]) == sync_vendor_clean):
                            filtered_records.append({
                                "பதிப்பகம்": row[0],
                                "புத்தகத் தலைப்பு": row[1],
                                "மொழி": row[2],
                                "மொத்த படிகள்": row[5],
                                "பெறப்பட்ட படிகள்": row[6]
                            })

                    if filtered_records:
                        st.write(f"### 📋 {selected_sync_vendor} - பெறப்பட்ட புத்தகங்கள் விவரம்:")
                        st.dataframe(pd.DataFrame(filtered_records), use_container_width=True)

                        if st.button(f"🚀 {selected_sync_vendor} - தரவை Vendor Wise Sheet-ல் புதுப்பி (Sync Now)", use_container_width=True):
                            with st.spinner("⏳ கூகுள் ஷீட்டில் Received & Not Received காலம்களில் நேரடியாக எழுதப்படுகிறது..."):
                                
                                vwbd_data = sheet_vendor_wise.get_all_values()
                                updated_count = 0

                                for rec in filtered_records:
                                    target_title_clean = clean_text(rec["புத்தகத் தலைப்பு"])
                                    try:
                                        needed_qty = int(rec["பெறப்பட்ட படிகள்"])
                                    except ValueError:
                                        needed_qty = 0

                                    matched_count = 0
                                    
                                    for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                                        if len(r_data) > 1:
                                            sheet_title_clean = clean_text(r_data[1]) # Col B (Title)
                                            
                                            # தலைப்பு பொருத்தம்
                                            if (target_title_clean in sheet_title_clean or sheet_title_clean in target_title_clean or target_title_clean[:8] == sheet_title_clean[:8]):
                                                if matched_count < needed_qty:
                                                    # Col S (19th Column) -> Received = 1
                                                    # Col T (20th Column) -> Not Received = 0
                                                    sheet_vendor_wise.update_cell(r_idx, 19, 1)
                                                    sheet_vendor_wise.update_cell(r_idx, 20, 0)
                                                    matched_count += 1
                                                    updated_count += 1

                                if updated_count > 0:
                                    st.balloons()
                                    st.success(f"✅ வெற்றி! 'Vendor Wise Book Data' தாளில் {updated_count} வரிகளுக்கு Received = 1 மற்றும் Not Received = 0 என நேரடியாக கூகுள் ஷீட்டில் எழுதப்பட்டுவிட்டது!")
                                else:
                                    st.error("❌ புத்தகத் தலைப்புகள் கூகுள் ஷீட்டில் சரியாகப் பொருந்தவில்லை!")

        except Exception as e:
            st.error(f"❌ பிழை ஏற்பட்டது: {e}")

# ---------------------------------------------------------
# பணி 3 & 4
# ---------------------------------------------------------
elif menu_choice == "3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("📚 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    if vendor_df is not None and not vendor_df.empty:
        vendors_list = vendor_df.iloc[:, 2].dropna().unique().tolist()
        selected_vendor = st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors_list)
        if selected_vendor and selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and book_df is not None:
            filtered_books = book_df[book_df.iloc[:, 9].astype(str).str.strip() == str(selected_vendor).strip()]
            st.dataframe(filtered_books, use_container_width=True)

elif menu_choice == "4. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    if book_df is not None and not book_df.empty:
        lib_col_idx = 12 if book_df.shape[1] > 12 else 0
        libraries = book_df.iloc[:, lib_col_idx].dropna().unique().tolist()
        selected_lib = st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + libraries)
        if selected_lib and selected_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            filtered_lib_books = book_df[book_df.iloc[:, lib_col_idx].astype(str).str.strip() == str(selected_lib).strip()]
            st.dataframe(filtered_lib_books, use_container_width=True)
