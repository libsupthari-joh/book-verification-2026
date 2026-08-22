import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime

# 1. Streamlit பக்க அமைப்பு
st.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide")

# தலைப்பு
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

# 3. கூகுள் ஷீட் இணைப்பு
@st.cache_resource
def init_gspread():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

try:
    client = init_gspread()
    sheet = client.open_by_key("1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc").worksheet("Physically verified")
except Exception as e:
    st.error(f"Google Sheet இணைப்புப் பிழை: {e}")

# Session State Setup
if 'verified_list' not in st.session_state:
    st.session_state['verified_list'] = []

if 'selected_title_idx' not in st.session_state:
    st.session_state['selected_title_idx'] = "-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"

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
        
    vendors = []
    if not vendor_df.empty:
        for idx, row in vendor_df.iterrows():
            v_id = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
            v_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
            if v_name and v_name.lower() != "nan":
                full_name = f"{v_id}.{v_name}" if v_id and v_id.lower() != "nan" else v_name
                vendors.append((full_name, v_name))
                
    st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
    vendor_options = [v[0] for v in vendors]
    selected_vendor_full = st.selectbox("பதிப்பகப் பெயரைத் தேர்ந்தெடுக்கவும்...", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + vendor_options, label_visibility="collapsed")
    
    if selected_vendor_full and selected_vendor_full != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
        actual_vendor = next((v[1] for v in vendors if v[0] == selected_vendor_full), selected_vendor_full)
        target = str(actual_vendor).strip().lower()
        
        colJ = book_df.iloc[:, 9].astype(str).str.strip().str.lower()
        colK = book_df.iloc[:, 10].astype(str).str.strip().str.lower()
        
        filtered_books = book_df[(colJ == target) | (colK == target)]
        
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
            
            title_options = ["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]
            for idx, row in grouped.iterrows():
                t_str = str(row['Title']).strip()
                a_str = str(row['Author Name']).strip() if pd.notna(row['Author Name']) else ""
                disp = f"{t_str} - {a_str}" if a_str else t_str
                title_options.append(disp)
                
            selected_title_disp = st.selectbox(
                "புத்தகத்தைத் தேர்ந்தெடுக்கவும்...", 
                title_options, 
                key="book_dropdown",
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
                    
                    already = any(x['Title'] == matched_row['Title'] for x in st.session_state['verified_list'])
                    if already:
                        st.info("ℹ️ இந்தப் புத்தகம் ஏற்கனவே பட்டியலில் சேர்க்கப்பட்டுவிட்டது.")
                    else:
                        with st.form("verify_form"):
                            st.write(f"**புத்தகத் தலைப்பு:** {matched_row['Title']}")
                            st.write(f"**ஆசிரியர் பெயர்:** {matched_row['Author Name']}")
                            rec_qty = st.number_input("பெறப்பட்ட படிகள் (எண்ணிக்கை):", min_value=0, max_value=tot_qty, value=tot_qty)
                            submitted = st.form_submit_button("➕ பட்டியலில் சேர்")
                            
                            if submitted:
                                not_rec_qty = tot_qty - rec_qty
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
                st.rerun()
                
        with col_sub:
            if st.button("💾 கூகுள் ஷீட்டில் சேமி (Final Submit)", use_container_width=True):
                try:
                    curr_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    rows = []
                    for item in st.session_state['verified_list']:
                        rows.append([
                            selected_vendor_full if 'selected_vendor_full' in locals() else '',
                            item['Title'], item['language'], item['Author'],
                            actual_vendor if 'actual_vendor' in locals() else '',
                            item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'],
                            curr_date, st.session_state.get('user_phone', '')
                        ])
                    sheet.append_rows(rows)
                    st.balloons()
                    st.success("🎉 அனைத்து விவரங்களும் கூகுள் ஷீட்டில் சேமிக்கப்பட்டன!")
                    st.session_state['verified_list'] = []
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
