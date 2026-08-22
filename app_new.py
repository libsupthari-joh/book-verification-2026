import streamlit as st
import pandas as pd
import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# Page Config
st.set_page_config(page_title="2026 நூல்கள் சரிபார்ப்பு மையம்", page_icon="📚", layout="wide")

# Custom CSS for UI Matching Apps Script Design
st.markdown("""
    <style>
    .main-header { text-align: center; color: #1a73e8; font-family: 'Arial', sans-serif; margin-bottom: 20px; }
    .card-box { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; margin-bottom: 15px; }
    .stButton>button { background-color: #1a73e8; color: white; font-weight: bold; border-radius: 6px; border: none; }
    .metric-card { background-color: #eef5ff; border: 1px solid #c7dcff; padding: 15px; border-radius: 8px; text-align: center; }
    .metric-title { font-size: 14px; color: #1557b0; font-weight: bold; }
    .metric-value { font-size: 24px; color: #1a73e8; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# 1. Login Logic
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'verified_list' not in st.session_state:
    st.session_state['verified_list'] = []

if not st.session_state['logged_in']:
    st.markdown("<h2 class='main-header'>🔐 பணியாளர் உள்நுழைவு (Login)</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        phone = st.text_input("📱 உங்களது அழைப்பேசி எண் / PIN:", type="password")
        if st.button("🚀 உள்நுழை (Login)", use_container_width=True):
            if len(phone.strip()) >= 4:
                st.session_state['logged_in'] = True
                st.session_state['user_phone'] = phone.strip()
                st.rerun()
            else:
                st.error("சரியான எண்ணை உள்ளிடவும்!")
    st.stop()

st.markdown("<h1 class='main-header'>📚 2026 நூல்கள் தனித்தனி சரிபார்ப்பு போர்ட்டல்</h1>", unsafe_allow_html=True)

# 2. Fast Data Load using Pandas Caching
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

if vendor_df is None or book_df is None:
    st.error(f"❌ '{EXCEL_FILE}' கோப்பு காணப்படவில்லை!")
    st.stop()

# Vendor Options Setup
vendors = []
if not vendor_df.empty:
    for idx, row in vendor_df.iterrows():
        v_id = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ""
        v_name = str(row.iloc[2]).strip() if pd.notna(row.iloc[2]) else ""
        if v_name and v_name.lower() != "nan":
            full_name = f"{v_id} - {v_name}" if v_id and v_id.lower() != "nan" else v_name
            vendors.append((full_name, v_name))

# Step 1: Vendor Selection
st.subheader("1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:")
vendor_options = [v[0] for v in vendors]
selected_vendor_full = st.selectbox("🔍 பதிப்பகப் பெயரைத் தட்டச்சு செய்க...", [""] + vendor_options, label_visibility="collapsed")

if selected_vendor_full:
    actual_vendor = next((v[1] for v in vendors if v[0] == selected_vendor_full), selected_vendor_full)
    target = str(actual_vendor).strip().lower()

    colJ = book_df.iloc[:, 9].astype(str).str.strip().str.lower()
    colK = book_df.iloc[:, 10].astype(str).str.strip().str.lower()
    
    filtered_books = book_df[(colJ == target) | (colK == target)]

    if filtered_books.empty:
        st.warning("❌ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் எதுவும் இல்லை!")
    else:
        # Grouping and Summarizing Titles
        grouped = filtered_books.groupby([filtered_books.iloc[:, 4], filtered_books.iloc[:, 6], filtered_books.iloc[:, 5]]).size().reset_index(name='Quantity')
        grouped.columns = ['Title', 'Author', 'Language', 'TotalQty']

        total_titles = len(grouped)
        total_copies = grouped['TotalQty'].sum()

        # Summary Cards UI
        m_col1, m_col2 = st.columns(2)
        with m_col1:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>📖 மொத்த தலைப்புகள்</div><div class='metric-value'>{total_titles}</div></div>", unsafe_allow_html=True)
        with m_col2:
            st.markdown(f"<div class='metric-card'><div class='metric-title'>📦 மொத்த படிகள்</div><div class='metric-value'>{total_copies}</div></div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Step 2: Book Selection
        st.subheader("2. புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்:")
        
        # Filter already verified books
        verified_titles = [item['Title'] for item in st.session_state['verified_list']]
        available_grouped = grouped[~grouped['Title'].isin(verified_titles)]
        
        title_list = available_grouped['Title'].tolist()
        selected_title = st.selectbox("🔍 புத்தகத் தலைப்பைத் தேடுக...", [""] + title_list, label_visibility="collapsed")

        if selected_title:
            b_info = available_grouped[available_grouped['Title'] == selected_title].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                st.number_input("📦 மொத்த எண்ணிக்கை:", value=int(b_info['TotalQty']), disabled=True)
            with c2:
                rec_qty = st.number_input("✅ பெறப்பட்ட எண்ணிக்கை:", min_value=0, max_value=int(b_info['TotalQty'])*2, value=int(b_info['TotalQty']))

            if st.button("➕ சரிபார்ப்புப் பட்டியலில் சேர்", use_container_width=True):
                st.session_state['verified_list'].append({
                    'Title': selected_title,
                    'Author': b_info['Author'],
                    'Language': b_info['Language'],
                    'TotalQty': int(b_info['TotalQty']),
                    'ReceivedQty': int(rec_qty),
                    'NotReceivedQty': int(b_info['TotalQty']) - int(rec_qty)
                })
                st.rerun()

        # Step 3: Verified Draft Table UI
        if st.session_state['verified_list']:
            st.markdown("---")
            st.subheader(f"📋 சரிபார்க்கப்பட்ட புத்தகங்கள் பட்டியல் ({len(st.session_state['verified_list'])} / {total_titles})")

            v_df = pd.DataFrame(st.session_state['verified_list'])
            v_df.index = range(1, len(v_df) + 1)
            st.dataframe(v_df[['Title', 'Author', 'TotalQty', 'ReceivedQty']], use_container_width=True)

            col_sub, col_del = st.columns([3, 1])
            with col_del:
                if st.button("🔄 பட்டியலை அழி (Reset List)", use_container_width=True):
                    st.session_state['verified_list'] = []
                    st.rerun()

            with col_sub:
                if st.button("💾 Final Submit (Save to Google Sheet)", use_container_width=True):
                    if len(st.session_state['verified_list']) < total_titles:
                        st.error(f"⚠️ அனைத்துத் தலைப்புகளையும் சரிபார்க்க வேண்டும்! பாக்கி: {total_titles - len(st.session_state['verified_list'])}")
                    else:
                        try:
                            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
                            creds_dict = dict(st.secrets["gcp_service_account"])
                            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                            client = gspread.authorize(creds)
                            sheet = client.open_by_key("1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc").worksheet("Physically verified")

                            curr_date = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                            rows = []
                            for item in st.session_state['verified_list']:
                                rows.append([
                                    selected_vendor_full, item['Title'], item['Language'], item['Author'],
                                    actual_vendor, item['TotalQty'], item['ReceivedQty'], item['NotReceivedQty'],
                                    curr_date, st.session_state['user_phone']
                                ])

                            sheet.append_rows(rows)
                            st.balloons()
                            st.success("🎉 அனைத்து விவரங்களும் Google Sheet-இல் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                            st.session_state['verified_list'] = []
                        except Exception as e:
                            st.error(f"❌ பிழை: {e}")