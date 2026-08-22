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

# பதிப்பகப் பெயரில் உள்ள எண்களை நீக்கி சுத்தப்படுத்தும் சார்பு (340.Graphic Network -> Graphic Network)
def clean_vendor_name(val):
    if pd.isna(val) or val is None:
        return ""
    s = str(val).strip()
    # பெயருக்கு முன் வரும் எண்கள் மற்றும் புள்ளிகளை நீக்குதல்
    cleaned = re.sub(r'^\d+[\.\s\-]*', '', s)
    return cleaned.strip()

# ஒப்பீட்டிற்கு மட்டும் பயன்படுத்தும் சார்பு
def clean_for_match(val):
    cleaned = clean_vendor_name(val)
    return re.sub(r'[^a-zA-Z0-9\u0B80-\u0BFF]', '', cleaned).lower()

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

    verified_vendors = set()
    if sheet_physically:
        try:
            existing_records = sheet_physically.get_all_values()
            if len(existing_records) > 1:
                verified_vendors = set(clean_for_match(row[0]) for row in existing_records[1:] if row and row[0])
        except Exception:
            pass

    # எண்களற்ற சுத்தமான பதிப்பாளர் பட்டியல் தயாரித்தல்
    vendor_list = []
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            col_b = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            col_c = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""
            
            raw_label = col_b if col_b else col_c
            clean_label = clean_vendor_name(raw_label) # எண்கள் நீக்கப்பட்ட பெயர்
            
            if clean_label and clean_label.lower() != "nan" and clean_label not in vendor_list:
                vendor_list.append(clean_label)
                
    st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    
    selected_vendor_clean = st.selectbox(
        "பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", 
        ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_list, 
        key=f"vendor_select_{st.session_state['vendor_key']}",
        label_visibility="collapsed"
    )
    
    if selected_vendor_clean and selected_vendor_clean != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        
        target_vendor_clean = clean_for_match(selected_vendor_clean)
        
        if target_vendor_clean in verified_vendors:
            st.warning("⚠️ இந்த பதிப்பகத்தின் விவரங்கள் ஏற்கனவே கூகுள் ஷீட்டில் சேமிக்கப்பட்டுவிட்டது!")
        else:
            def is_vendor_match(row_val):
                return clean_for_match(row_val) == target_vendor_clean

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
                
                added_titles_clean = [clean_for_match(x['Title']) for x in st.session_state['verified_list']]
                
                title_options = ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
                remaining_books_count = 0
                
                for idx, row in grouped.iterrows():
                    t_str = str(row['Title']).strip()
                    if clean_for_match(t_str) not in added_titles_clean:
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
                                submitted = st.form_submit_button("➕ பட்டியலில் சேர்")
                                
                                if submitted:
                                    not_rec_qty = max(0, tot_qty - rec_qty)
                                    item = {
                                        "Vendor": selected_vendor_clean, # எண்களற்ற சுத்தமான பெயர்
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

    # சரிபார்க்கப்பட்ட அறிக்கை (Report) மற்றும் கூகுள் ஷீட்டிற்கு அனுப்பும் பகுதி
    if st.session_state['verified_list']:
        st.markdown("---")
        st.subheader(f"📊 சரிபார்க்கப்பட்ட அறிக்கை (Draft Report) - {st.session_state['verified_list'][0]['Vendor']}")
        
        v_df = pd.DataFrame(st.session_state['verified_list'])
        v_df.index = range(1, len(v_df) + 1)
        
        # எண்கள் இல்லாத சுத்தமான அறிக்கை அட்டவணை
        report_df = v_df[['Vendor', 'Title', 'Language', 'Author', 'TotalQty', 'ReceivedQty', 'NotReceivedQty']].rename(columns={
            'Vendor': 'பதிப்பகப் பெயர்',
            'Title': 'புத்தகத் தலைப்பு',
            'Language': 'மொழி',
            'Author': 'ஆசிரியர் பெயர்',
            'TotalQty': 'மொத்தப் படிகள்',
            'ReceivedQty': 'பெறப்பட்டவை',
            'NotReceivedQty': 'வராதவை'
        })
        st.dataframe(report_df, use_container_width=True)
        
        col_sub, col_del = st.columns([3, 1])
        with col_del:
            if st.button("🗑️ பட்டியலை அழி", use_container_width=True):
                st.session_state['verified_list'] = []
                st.session_state['book_key'] += 1
                st.rerun()
                
        with col_sub:
            if st.button("💾 கூகுள் ஷீட்டில் சேமி (Save to Sheet)", use_container_width=True):
                try:
                    curr_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    
                    if sheet_physically:
                        physically_rows = []
                        for item in st.session_state['verified_list']:
                            # எண்கள் இல்லாத பெயராகவே கூகுள் ஷீட்டில் பதிவு செய்யப்படும்
                            physically_rows.append([
                                item['Vendor'],
                                item['Title'], 
                                item['Language'], 
                                item['Author'],
                                item['Vendor'],
                                item['TotalQty'], 
                                item['ReceivedQty'], 
                                item['NotReceivedQty'],
                                curr_date
                            ])
                        sheet_physically.append_rows(physically_rows)

                    st.balloons()
                    st.success("🎉 எண்களற்ற சுத்தமான பெயருடன் கூகுள் ஷீட்டில் வெற்றிகரமாகச் சேமிக்கப்பட்டது!")
                    
                    st.session_state['verified_list'] = []
                    st.session_state['vendor_key'] += 1
                    st.session_state['book_key'] += 1
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ பிழை: {e}")

# ---------------------------------------------------------
# பணி 2: Google Sheet தரவு ஒத்திசைவு (Sync)
# ---------------------------------------------------------
elif menu_choice == "2. 🔄 Google Sheet தரவு ஒத்திசைவு (Sync)":
    st.subheader("🔄 Vendor Wise Sheet-ஐப் புதுப்பித்தல் (Sync Data)")
    st.info("💡 'Physically Verified' தாளில் சேமிக்கப்பட்ட விவரங்களை அடிப்படையாகக் கொண்டு 'Vendor Wise Book Data' தாளில் Received = 1 என ஒரே நேரத்தில் புதுப்பிக்கும் பகுதி.")

    if st.button("🚀 Sync செயலாக்கத்தைத் தொடங்கு (Sync Now)", use_container_width=True):
        if not sheet_physically or not sheet_vendor_wise:
            st.error("❌ கூகுள் ஷீட் இணைப்புகள் சரியாக இல்லை!")
        else:
            try:
                with st.spinner("⏳ கூகுள் ஷீட் தரவுகள் ஒத்திசைக்கப்படுகின்றன... தயவுசெய்து காத்திருக்கவும்..."):
                    p_records = sheet_physically.get_all_values()
                    
                    if len(p_records) <= 1:
                        st.warning("⚠️ 'Physically Verified' தாளில் தரவுகள் எதுவும் இல்லை!")
                    else:
                        title_received_map = {}
                        for row in p_records[1:]:
                            if len(row) >= 7:
                                t_clean = clean_for_match(row[1]) # Col B (Title)
                                try:
                                    rec_qty = int(row[6]) # Col G (Received Qty)
                                except ValueError:
                                    rec_qty = 0
                                
                                if t_clean:
                                    title_received_map[t_clean] = title_received_map.get(t_clean, 0) + rec_qty

                        vwbd_data = sheet_vendor_wise.get_all_values()
                        cell_updates = []
                        title_counter = {}

                        for r_idx, r_data in enumerate(vwbd_data[1:], start=2):
                            if len(r_data) > 1:
                                row_title = clean_for_match(r_data[1]) # Col B (Title)

                                if row_title in title_received_map:
                                    allowed_qty = title_received_map[row_title]
                                    current_count = title_counter.get(row_title, 0)

                                    if current_count < allowed_qty:
                                        s_val = 1
                                        t_val = 0
                                        title_counter[row_title] = current_count + 1
                                    else:
                                        s_val = 0
                                        t_val = 1

                                    # Column S (19) & Column T (20)
                                    cell_updates.append(gspread.Cell(r_idx, 19, s_val))
                                    cell_updates.append(gspread.Cell(r_idx, 20, t_val))

                        if cell_updates:
                            sheet_vendor_wise.update_cells(cell_updates)
                            st.balloons()
                            st.success(f"✅ வெற்றி! மொத்தம் {len(cell_updates)//2} வரிகள் 'Vendor Wise Book Data' தாளில் Received = 1 எனப் புதுப்பிக்கப்பட்டன!")
                        else:
                            st.warning("⚠️ புதுப்பிப்பதற்குப் புதிய தரவுகள் எதுவும் இல்லை!")

            except Exception as e:
                st.error(f"❌ ஒத்திசைவில் பிழை ஏற்பட்டது: {e}")

# ---------------------------------------------------------
# பணி 3: மொத்த பதிப்பாளர் விவரங்கள் (480)
# ---------------------------------------------------------
elif menu_choice == "3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("📚 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    
    if vendor_df is not None and not vendor_df.empty:
        vendors_list = vendor_df.iloc[:, 2].dropna().unique().tolist()
        selected_vendor = st.selectbox("பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendors_list)
        
        st.markdown("---")
        if selected_vendor and selected_vendor != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and book_df is not None and not book_df.empty:
            filtered_books = book_df[book_df.iloc[:, 9].astype(str).str.strip() == str(selected_vendor).strip()]
            
            st.write(f"### 📄 {selected_vendor} - நூல் விவரங்கள் (மொத்தம்: {len(filtered_books)})")
            st.dataframe(filtered_books, use_container_width=True)

# ---------------------------------------------------------
# பணி 4: நூலகத்திற்கு விநியோகம் (104)
# ---------------------------------------------------------
elif menu_choice == "4. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    
    if book_df is not None and not book_df.empty:
        lib_col_idx = 12 if book_df.shape[1] > 12 else 0
        libraries = book_df.iloc[:, lib_col_idx].dropna().unique().tolist()
        
        selected_lib = st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + libraries)
        
        st.markdown("---")
        if selected_lib and selected_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
            filtered_lib_books = book_df[book_df.iloc[:, lib_col_idx].astype(str).str.strip() == str(selected_lib).strip()]
            st.dataframe(filtered_lib_books, use_container_width=True)
