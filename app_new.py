import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 1. Streamlit பக்க அமைப்பு
st.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide")

# தலைப்பு மாற்றம்
st.title("📚 2026 புதிய நூல்கள் விநியோகம்")

# 2. கூகுள் ஷீட் இணைப்பு
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

# கேட்கப்பட்ட 20 புலன்களின் பட்டியல்
ALL_COLUMNS = [
    "Book Id", "Title", "Language", "Author Name", "Isbn", "Year", 
    "Publication Name", "Vendor Name", "Original Price", "Acccepted Price", 
    "library Type", "librarianId", "Library Name", "State Accession Number", 
    "Quantity", "Received", "Not Received"
]

# 3. இடதுபுற மெனு (Sidebar Menu)
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
    st.info("இங்கே பதிப்பகம் மற்றும் புத்தக தலைப்புகளை தேர்வு செய்து சரிபார்க்கலாம்.")

# ---------------------------------------------------------
# பணி 2: மொத்த பதிப்பாளர் விவரங்கள் (480)
# ---------------------------------------------------------
elif menu_choice == "2. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("📚 480 பதிப்பாளர் வாரியான நூல் விவரங்கள்")
    
    pub_search = st.text_input("🔎 பதிப்பாளர் பெயர் அல்லது குறியீடு கொண்டு தேடுக:")
    
    st.markdown("---")
    st.write("### 📄 பதிப்பாளர் அறிக்கை (Report)")
    
    empty_df = pd.DataFrame(columns=ALL_COLUMNS)
    st.dataframe(empty_df, use_container_width=True)

# ---------------------------------------------------------
# பணி 3: நூலகத்திற்கு விநியோகம் (104)
# ---------------------------------------------------------
elif menu_choice == "3. நூலகத்திற்கு விநியோகம் (104)":
    st.subheader("🏛️ 104 நூலகங்கள் வாரியான விநியோக அறிக்கை")
    
    selected_lib = st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும் (Library Name):", [f"நூலகம் {i}" for i in range(1, 105)])
    
    st.markdown("---")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.write(f"### 📋 {selected_lib} - ஒதுக்கீடு செய்யப்பட்ட நூல்கள் பட்டியல்")
    with col2:
        st.button("🖨️ Print / Save PDF")
        
    empty_df = pd.DataFrame(columns=ALL_COLUMNS)
    st.dataframe(empty_df, use_container_width=True)
