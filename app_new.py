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

# பதிப்பகர் பெயரைச் சுத்தப்படுத்தும் முக்கியச் சார்பு (Cleaning Function)
def extract_clean_vendor(raw_str):
    if pd.isna(raw_str) or not raw_str:
        return ""
    text = str(raw_str).strip()
    
    # "340.Graphic Network. GRAPHIC NETWORK" போன்ற தொடர்களில் இருந்து சுத்தமான பெயரைப் பிரித்தல்
    parts = [p.strip() for p in text.split('.') if p.strip()]
    
    # எண்கள் இல்லாத வார்த்தைகளை மட்டும் எடுத்தல்
    cleaned_parts = []
    for p in parts:
        if not p.isdigit():
            cleaned_parts.append(p)
            
    if cleaned_parts:
        # கடைசி அல்லது முதல் சுத்தமான பெயரைப் பயன்படுத்துதல்
        return cleaned_parts[-1]
    return text

def clean_for_match(val):
    if pd.isna(val) or val is None:
        return ""
    # சிறப்பு எழுத்துக்கள் மற்றும் இடைவெளிகளை நீக்கி ஒப்பிடுதல்
    return re.sub(r'[^a-zA-Z0-9]', '', str(val)).lower()

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

# Session State Setup
if 'verified_list' not in st.session_state:
    st.session_state['verified_list'] = []

if 'vendor_key' not in st.session_state:
    st.session_state['vendor_key'] = 0

if 'book_key' not in st.session_state:
    st.session_state['book_key'] = 0

# 4. இடதுபுற மெனு (Sidebar Menu)
st.sidebar.header("📋 முதன்மை பணிகள்")
menu_choice = st.sidebar.radio(
    "பணியைத் தேர்ந்தெடுக்கவும்:",
    [
        "1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு",
        "2. மொத்த பதிப்பாளர் விவரங்கள் (480)",
        "3. நூலகத்திற்கு விநியோகம் (104)"
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

    # ஏற்கனவே கூகுள் ஷீட்டில் உள்ள பதிப்பகங்களைப் படித்தல்
    verified_vendors = set()
    if sheet_physically:
        try:
            existing_records = sheet_physically.get_all_values()
            if len(existing_records) > 1:
                verified_vendors = set(clean_for_match(row[0]) for row in existing_records[1:] if row and row[0])
        except Exception:
            pass

    # Dropdown-ற்கான பட்டியலைச் சரியாக உருவாக்குதல்
    vendor_options_map = {}
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            v_id = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) and str(row.iloc[1]).strip().lower() != "nan" else ""
            v_raw_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
            
            clean_name = extract_clean_vendor(v_raw_name)
            
            if clean_name and clean_name.lower() != "nan":
                display_label = f"{v_id}. {clean_name}" if v_id else clean_name
                vendor_options_map[display_label] = clean_name
                
    st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    vendor_disp_list = list(vendor_options_map.keys())
    
    selected_vendor_disp = st.selectbox(
        "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_disp_list, 
        key=f"vendor_select_{st.session_state['vendor_key']}",
        label_visibility="collapsed"
    )
    
    if selected_vendor_disp and selected_vendor_disp != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        
        # உண்மையான பதிப்பகத்தின் பெயர் (எ.கா: GRAPHIC NETWORK)
        actual_vendor = vendor_options_map[selected_vendor_disp]
        
        if clean_for_match(selected_vendor_disp) in verified_vendors or clean_for_match(actual_vendor) in verified_vendors:
            st.warning("⚠️ இந்த பதிப்பகத்தின் விவரங்கள் ஏற்கனவே கூகுள் ஷீட்டில் சேமிக்கப்பட்டுவிட்டது!")
        else:
            target_match = clean_for_match(actual_vendor)
            
            colJ = book_df.iloc[:, 9].apply(clean_for_match)
            colK = book_df.iloc[:, 10].apply(clean_for_match)
            
            filtered_books = book_df[(colJ == target_match) | (colK == target_match) | colJ.str.contains(target_match, regex=False) | colK.str.contains(target_match, regex=False)]

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
                
                total_titles = len(grouped)
                total_copies = grouped['Quantity'].sum()
                
                c1, c2 = st.columns(2)
                c1.metric("📋 மொத்த தலைப்புகள்", total_titles)
                c2.metric("📦 மொத்த படிகள்", int(total_copies))
                
                st.subheader("2. புத்தகத் தலைப்பதைத் தேர்ந்தெடுக்கவும்:")
                
                added_titles = [clean_for_match(x['Title']) for x in st.session_state['verified_list']]
                
                title_options = ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
                for idx, row in grouped.iterrows():
                    t_str = str(row['Title']).strip()
                    if clean_for_match(t_str) not in added_titles:
                        a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                        disp = f"{t_str} - {a_str}" if a_str else t_str
                        title_options.append(disp)
                
                if len(title_options) == 1 and len(added_titles) > 0:
                    st.success("🎉 இந்த பதிப்பகத்தின் அனைத்துப் புத்தகங்களும் பட்டியலில் சேர்க்கப்பட்டுவிட்டன!")
                else:
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
                                        "Book Id": matched_row.get('Book Id', ''),
                                        "Title": matched_row['Title'],
                                        "Author": matched_row['Author Name'],
                                        "language": matched_row['Language'],
                                        "TotalQty": tot_qty,
                                        "ReceivedQty": rec_qty,
                                        "NotReceivedQty": not_rec_qty,
                                        "OriginalPrice": matched_row.get('Original Price', ''),
                                        "AcceptedPrice": matched_row.get('Acccepted Price', ''),
                                        "Isbn": matched_row.get('Isbn', '')
                                    }
                                    st.session_state['verified_list'].append(item)
                                    st.session_state['book_key'] += 1
                                    st.success("✅ பட்டியல் சேர்க்கப்பட்டது!")
                                    st.rerun()

    # Step 3: Verified Draft Table & Save to Google Sheet
    if st.session_state['verified_list']:
        st.markdown("---")
        st.subheader(f"📋 சரிபார்க்கப்பட்ட புத்தகங்கள் பட்டியல் ({len(st.session_state['verified_list'])})")
        
        v_df = pd.DataFrame(st.session_state['verified_list'])
        v_df.index = range(1, len(v_df) + 1)
        v_df_tamil = v_df[['Title', 'Author', 'TotalQty', 'ReceivedQty']].rename(columns={
            'Title': 'புத்தகத் தலைப்பு',
            'Author': 'ஆசிரியர் பெயர்',
            'TotalQty': 'மொத்தப் படிகள்',
            'ReceivedQty': 'பெறப்பட்டவை'
        })
        st.dataframe(v_df_tamil, use_container_width=True)
        
        col_sub, col_del = st.columns([3, 1])
        with col_del:
            if st.button("🗑️ பட்டியலை அழி", use_container_width=True):
                st.session_state['verified_list'] = []
                st.session_state['book_key'] += 1
                st.rerun()
                
        with col_sub:
            if st.button("💾 கூகுள் ஷீட்டில் சேமி (Final Submit)", use_container_width=True):
                try:
                    curr_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    # 1. Physically verified பக்கத்தில் சேமிப்பு
                    if sheet_physically:
                        physically_rows = []
                        for item in st.session_state['verified_list']:
                            physically_rows.append([
                                selected_vendor_disp if 'selected_vendor_disp' in locals() else '',
                                item['Title'], item['language'], item['Author'],
                                actual_vendor if 'actual_vendor' in locals() else '',
                                item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'],
                                curr_date, st.session_state.get('user_phone', '')
                            ])
                        sheet_physically.append_rows(physically_rows)
                    
                    # 2. Vendor Wise Book Data பக்கத்தைப் புதுப்பித்தல் (S & T பத்திகள்)
                    if sheet_vendor_wise:
                        try:
                            vwbd_data = sheet_vendor_wise.get_all_values()
                            if len(vwbd_data) > 1:
                                cell_updates = []
                                target_v_match = clean_for_match(actual_vendor)
                                
                                for item in st.session_state['verified_list']:
                                    target_t_match = clean_for_match(item['Title'])
                                    rec_count = item['ReceivedQty']
                                    
                                    matching_row_indices = []
                                    for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                                        if len(r_data) > 10:
                                            row_title = clean_for_match(r_data[1])   # Col B: Title
                                            colJ_v = clean_for_match(r_data[9])      # Col J: Vendor/Publication
                                            colK_v = clean_for_match(r_data[10])     # Col K: Vendor Name
                                            
                                            if row_title == target_t_match and (target_v_match in colJ_v or target_v_match in colK_v or colJ_v in target_v_match or colK_v in target_v_match):
                                                matching_row_indices.append(r_idx)
                                    
                                    current_rec = 0
                                    for row_num in matching_row_indices:
                                        if current_rec < rec_count:
                                            s_val = 1
                                            t_val = 0
                                            current_rec += 1
                                        else:
                                            s_val = 0
                                            t_val = 1
                                        
                                        # Column S (19) மற்றும் Column T (20)
                                        cell_updates.append(gspread.Cell(row_num, 19, s_val))
                                        cell_updates.append(gspread.Cell(row_num, 20, t_val))
                                
                                if cell_updates:
                                    sheet_vendor_wise.update_cells(cell_updates)
                        except Exception as sec_e:
                            st.warning(f"⚠️ 'Vendor Wise Book Data' புதுப்பிப்பில் எச்சரிக்கை: {sec_e}")

                    st.balloons()
                    st.success("🎉 இரண்டு கூகுள் ஷீட்களிலும் விவரங்கள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                    
                    st.session_state['verified_list'] = []
                    st.session_state['vendor_key'] += 1
                    st.session_state['book_key'] += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ பிழை: {e}")

# ---------------------------------------------------------
# பணி 2: மொத்த பதிப்பாளர் விவரங்கள் (480)
# ---------------------------------------------------------
elif menu_choice == "2. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("📚 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    
    if vendor_df is not None and not vendor_df.empty:
        vendors_list = vendor_df.iloc[:, 2].dropna().unique().tolist()
        selected_vendor = st.selectbox("பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors_list)
        
        st.markdown("---")
        if selected_vendor and selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and book_df is not None and not book_df.empty:
            filtered_books = book_df[book_df.iloc[:, 9].astype(str).str.strip() == str(selected_vendor).strip()]
            
            st.write(f"### 📄 {selected_vendor} - நூல் விவரங்கள் (மொத்தம்: {len(filtered_books)})")
            st.dataframe(filtered_books, use_container_width=True)
            
            csv = filtered_books.to_csv(index=False).encode('utf-8')
            st.download_button("📥 அறிக்கை பதிவிறக்கம் (Save CSV)", csv, f"{selected_vendor}_Report.csv", "text/csv")

# ---------------------------------------------------------
# பணி 3: நூலகத்திற்கு விநியோகம் (104)
# ---------------------------------------------------------
elif menu_choice == "3. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    
    if book_df is not None and not book_df.empty:
        lib_col_idx = 12 if book_df.shape[1] > 12 else 0
        libraries = book_df.iloc[:, lib_col_idx].dropna().unique().tolist()
        
        selected_lib = st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + libraries)
        
        st.markdown("---")
        if selected_lib and selected_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            filtered_lib_books = book_df[book_df.iloc[:, lib_col_idx].astype(str).str.strip() == str(selected_lib).strip()]
            
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"### 📋 {selected_lib} - ஒதுக்கீடு செய்யப்பட்ட நூல்கள் பட்டியல்")
            with col2:
                csv_lib = filtered_lib_books.to_csv(index=False).encode('utf-8')
                st.download_button("📥 அறிக்கை பதிவிறக்கம் (Save CSV)", csv_lib, f"{selected_lib}_Distribution.csv", "text/csv")
                
            st.dataframe(filtered_lib_books, use_container_width=True)
