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

# எண்களையும் தேவையில்லாத குறியீடுகளையும் நீக்கி சுத்தமான பெயராக மாற்றும் சார்பு
def get_clean_name(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    # முன்னால் உள்ள எண்கள் மற்றும் புள்ளிகளை நீக்குதல் (எ.கா: '340.Graphic Network' -> 'Graphic Network')
    s = re.sub(r'^\d+[\.\s\-]*', '', s)
    return s.strip()

def normalize_text(val):
    if pd.isna(val) or val is None:
        return ""
    # ஒப்பீட்டிற்காக அனைத்து எழுத்துக்களையும் lowercase செய்து குறியீடுகளை நீக்குதல்
    return re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', '', str(val)).lower()

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
                verified_vendors = set(normalize_text(row[0]) for row in existing_records[1:] if row and row[0])
        except Exception:
            pass

    # எண்களை நீக்கி சுத்தமான பெயர்களை மட்டும் Dropdown பட்டியலுக்குத் தயார் செய்தல்
    vendor_clean_list = []
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]) if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]) if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            
            clean_b = get_clean_name(col_b)
            clean_c = get_clean_name(col_c)
            
            chosen_name = clean_c if clean_c else clean_b
            if chosen_name and chosen_name.lower() != "nan" and chosen_name not in vendor_clean_list:
                vendor_clean_list.append(chosen_name)
                
    st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    
    selected_vendor = st.selectbox(
        "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + sorted(vendor_clean_list), 
        key=f"vendor_select_{st.session_state['vendor_key']}",
        label_visibility="collapsed"
    )
    
    if selected_vendor and selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        
        target_vendor_norm = normalize_text(selected_vendor)
        
        if target_vendor_norm in verified_vendors:
            st.warning("⚠️ இந்த பதிப்பகத்தின் விவரங்கள் ஏற்கனவே கூகுள் ஷீட்டில் சேமிக்கப்பட்டுவிட்டது!")
        else:
            # எக்செல் தரவில் இருந்து எண்களைத் தவிர்த்துப் பெயர்களைப் பொருத்துதல்
            def is_vendor_match(row_val):
                return normalize_text(get_clean_name(row_val)) == target_vendor_norm

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
                
                total_titles = len(grouped)
                total_copies = grouped['Quantity'].sum()
                
                c1, c2 = st.columns(2)
                c1.metric("📋 மொத்த தலைப்புகள்", total_titles)
                c2.metric("📦 மொத்த படிகள்", int(total_copies))
                
                st.subheader("2. புத்தகத் தலைப்பதைத் தேர்ந்தெடுக்கவும்:")
                
                added_titles_clean = [normalize_text(x['Title']) for x in st.session_state['verified_list']]
                
                title_options = ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
                remaining_books_count = 0
                
                for idx, row in grouped.iterrows():
                    t_str = str(row['Title']).strip()
                    if normalize_text(t_str) not in added_titles_clean:
                        a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                        disp = f"{t_str} - {a_str}" if a_str else t_str
                        title_options.append(disp)
                        remaining_books_count += 1
                
                if remaining_books_count == 0 and len(st.session_state['verified_list']) > 0:
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
                                submitted = st.form_submit_button("➕ பட்டியலில் சேர் & ஷீட்டைப் புதுப்பி")
                                
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
                                    
                                    # கூகுள் ஷீட்டை உடனுக்குடன் புதுப்பித்தல்
                                    if sheet_vendor_wise:
                                        try:
                                            vwbd_data = sheet_vendor_wise.get_all_values()
                                            if len(vwbd_data) > 1:
                                                cell_updates = []
                                                target_t_norm = normalize_text(matched_row['Title'])
                                                
                                                matching_row_indices = []
                                                for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                                                    if len(r_data) > 10:
                                                        row_title = normalize_text(r_data[1])  # Col B: Title
                                                        row_colJ = normalize_text(get_clean_name(r_data[9]))   # Col J
                                                        row_colK = normalize_text(get_clean_name(r_data[10]))  # Col K
                                                        
                                                        v_matched = (row_colJ == target_vendor_norm or row_colK == target_vendor_norm)
                                                        
                                                        if row_title == target_t_norm and v_matched:
                                                            matching_row_indices.append(r_idx)
                                                
                                                current_rec = 0
                                                for row_num in matching_row_indices:
                                                    if current_rec < rec_qty:
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
                                                st.toast(f"⚡ '{matched_row['Title']}' - Google Sheet-ல் Received = 1 என வெற்றிபெற்றது!", icon="✅")
                                        except Exception as sec_e:
                                            st.warning(f"⚠️ புதுப்பிப்பு எச்சரிக்கை: {sec_e}")

                                    st.session_state['book_key'] += 1
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
                    
                    if sheet_physically:
                        physically_rows = []
                        for item in st.session_state['verified_list']:
                            physically_rows.append([
                                selected_vendor,
                                item['Title'], item['language'], item['Author'],
                                selected_vendor,
                                item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'],
                                curr_date, st.session_state.get('user_phone', '')
                            ])
                        sheet_physically.append_rows(physically_rows)

                    st.balloons()
                    st.success("🎉 இந்த பதிப்பகத்தின் சரிபார்ப்பு பணி கூகுள் ஷீட்டில் சேமிக்கப்பட்டது!")
                    
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
