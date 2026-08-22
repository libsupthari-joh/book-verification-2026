import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

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
    st.info("இங்கே பதிப்பகம் மற்றும் புத்தக தலைப்புகளைத் தேர்வு செய்து சரிபார்க்கலாம்.")

# ---------------------------------------------------------
# பணி 2: மொத்த பதிப்பாளர் விவரங்கள் (480)
# ---------------------------------------------------------
elif menu_choice == "2. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("📚 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    
    if vendor_df is not None and not vendor_df.empty:
        # Registred Vendors / Publishers Dropdown
        vendors_list = vendor_df.iloc[:, 2].dropna().unique().tolist()
        selected_vendor = st.selectbox("பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்:", vendors_list)
        
        st.markdown("---")
        if selected_vendor and book_df is not None and not book_df.empty:
            filtered_books = book_df[book_df.iloc[:, 9].astype(str).str.strip() == str(selected_vendor).strip()]
            
            st.write(f"### 📄 {selected_vendor} - நூல் விவரங்கள் (மொத்தம்: {len(filtered_books)})")
            st.dataframe(filtered_books, use_container_width=True)
            
            # Save / Export CSV Button
            csv = filtered_books.to_csv(index=False).encode('utf-8')
            st.download_button("📥 அறிக்கை பதிவிறக்கம் (Save CSV)", csv, f"{selected_vendor}_Report.csv", "text/csv")
    else:
        st.warning("எக்செல் கோப்பில் பதிப்பாளர் விவரங்கள் காணப்படவில்லை.")

# ---------------------------------------------------------
# பணி 3: நூலகத்திற்கு விநியோகம் (104)
# ---------------------------------------------------------
elif menu_choice == "3. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    
    if book_df is not None and not book_df.empty:
        # Library Column Check (Assumed Column for Library Name)
        lib_col_idx = 12 if book_df.shape[1] > 12 else 0
        libraries = book_df.iloc[:, lib_col_idx].dropna().unique().tolist()
        
        selected_lib = st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும் (Library Name):", libraries)
        
        st.markdown("---")
        
        filtered_lib_books = book_df[book_df.iloc[:, lib_col_idx].astype(str).str.strip() == str(selected_lib).strip()]
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.write(f"### 📋 {selected_lib} - ஒதுக்கீடு செய்யப்பட்ட நூல்கள் பட்டியல்")
        with col2:
            csv_lib = filtered_lib_books.to_csv(index=False).encode('utf-8')
            st.download_button("🖨️ அறிக்கை பதிவிறக்கம் (Save CSV)", csv_lib, f"{selected_lib}_Distribution.csv", "text/csv")
            
        st.dataframe(filtered_lib_books, use_container_width=True)
    else:
        st.warning("எக்செல் கோப்பில் நூலக விவரங்கள் காணப்படவில்லை.")
