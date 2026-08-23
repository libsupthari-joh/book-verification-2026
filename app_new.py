import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from gspread.cell import Cell
import io
import re
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="நூல்கள் சரிபார்ப்புப் போர்ட்பால்",
    page_icon="📚",
    layout="wide"
)

# --- HELPER FUNCTIONS ---
def clean_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()

@st.cache_resource
def init_google_sheets():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        spreadsheet_title = st.secrets.get("SPREADSHEET_NAME", "Book Supply 2026")
        sh = client.open(spreadsheet_title)
        
        sheet_lib_detail = sh.worksheet("Lib_Detail")
        sheet_vendor_wise = sh.worksheet("Vendor Wise Book Data")
        
        data = sheet_vendor_wise.get_all_records()
        book_df = pd.DataFrame(data)
        
        return sh, sheet_lib_detail, sheet_vendor_wise, book_df
    except Exception as e:
        st.error(f"❌ Google Sheets இணைப்புப் பிழை: {e}")
        return None, None, None, None

# --- INITIALIZE SESSION STATE ---
if "library_key_t4" not in st.session_state:
    st.session_state["library_key_t4"] = 0
if "selected_library_t4" not in st.session_state:
    st.session_state["selected_library_t4"] = None

# --- SIDEBAR NAVIGATION ---
st.sidebar.title("📚 நூல்கள் சரிபார்ப்புப் போர்ட்பால்")
st.sidebar.markdown("---")
st.sidebar.subheader("அதிகார நிலை: **Admin (முதன்மைகள் நிர்வாகி)**")

menu_choice = st.sidebar.radio(
    "பணிகள் (Navigation)",
    [
        "1. பெறப்பட்ட நூல்களா சரிபார்ப்பு",
        "2. Vendor Wise Book Data சீட்டிற்கு எண்ணிக்கை மாற்றம் மற்றும் செய்தல்",
        "3. மொத்த பதிப்பாளர் விவரங்கள் (400)",
        "4. நூலக வாரியான Accession எண்கள் மேலாண்மை"
    ]
)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 வெளியேறு (Logout)", use_container_width=True):
    st.success("வெளியேற்றம் வெற்றிகரமாகச் செய்யப்பட்டது.")
    st.stop()

# Initialize Google Sheets connections
sh, sheet_lib_detail, sheet_vendor_wise, book_df = init_google_sheets()

# ==========================================
# TASK 1: பெறப்பட்ட நூல்களா சரிபார்ப்பு
# ==========================================
if menu_choice == "1. பெறப்பட்ட நூல்களா சரிபார்ப்பு":
    st.subheader("📋 1. பெறப்பட்ட நூல்களுக்கான சரிபார்ப்புப் பக்கம்")
    st.info("நூலகவாரியாகப் பெறப்பட்ட நூல்களின் விவரங்களைச் சரிபார்க்கவும்.")
    
    if book_df is not None and not book_df.empty:
        st.dataframe(book_df, use_container_width=True)
    else:
        st.warning("தரவுகள் கிடைக்கவில்லை.")

# ==========================================
# TASK 2: Vendor Wise Book Data சீட்டிற்கு எண்ணிக்கை மாற்றம்
# ==========================================
elif menu_choice == "2. Vendor Wise Book Data சீட்டிற்கு எண்ணிக்கை மாற்றம் மற்றும் செய்தல்":
    st.subheader("📊 2. Vendor Wise Book Data எண்ணிக்கை மாற்றம் மற்றும் மேலாண்மை")
    st.info("விற்பனையாளர் வாரியான புத்தக எண்ணிக்கையைச் சரிசெய்து பதிவு செய்தல்.")
    
    if book_df is not None and not book_df.empty:
        st.dataframe(book_df.head(50), use_container_width=True)
    else:
        st.warning("தரவுகள் கிடைக்கவில்லை.")

# ==========================================
# TASK 3: மொத்த பதிப்பாளர் விவரங்கள் (400)
# ==========================================
elif menu_choice == "3. மொத்த பதிப்பாளர் விவரங்கள் (400)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள்")
    st.info("பதிப்பாளர்கள் மற்றும் நிறுவனங்களின் பட்டியல் விவரங்கள்.")
    
    if book_df is not None and not book_df.empty and "Publication Name" in book_df.columns:
        pub_counts = book_df["Publication Name"].value_counts().reset_index()
        pub_counts.columns = ["Publication Name", "Total Books"]
        st.dataframe(pub_counts, use_container_width=True)
    else:
        st.warning("பதிப்பாளர் விவரங்கள் கிடைக்கவில்லை.")

# ==========================================
# TASK 4: நூலக வாரியான Accession எண்கள் மேலாண்மை
# ==========================================
elif menu_choice == "4. நூலக வாரியான Accession எண்கள் மேலாண்மை":
    st.subheader("🏛️ 4. நூலக வாரியான Accession எண்கள் வழங்கி Google Sheet-ல் பதிவு செய்தல்")
    st.info("💡 மாவட்ட மைய நூலகத்திற்கு Column F (Central Accession) எண்ணும், மற்ற நூலகங்களுக்கு Column G எண்ணும் பயன்படுத்தப்படும். **பெறப்பட்ட நூல்களுக்கு மட்டுமே** தொடர் எண்கள் வழங்கப்படும்.")

    if book_df is None or book_df.empty or sheet_lib_detail is None or sheet_vendor_wise is None:
        st.error("❌ தேவையான Google Sheet இணைப்புகள் அல்லது தரவுகள் கிடைக்கவில்லை!")
    else:
        try:
            lib_detail_rows = sheet_lib_detail.get_all_values()
            
            # Column B = 1 (Lib Code), Column F = 5 (Central Accession), Column G = 6 (DCL/FTB/BL/VL Last Accession)
            lib_code_idx = 1
            central_acc_idx = 5
            lib_last_acc_idx = 6

            central_start_acc = 0
            lib_last_acc_map = {}

            for r in lib_detail_rows[1:]:
                if len(r) > max(lib_code_idx, central_acc_idx, lib_last_acc_idx):
                    l_code = str(r[lib_code_idx]).strip()
                    c_acc_str = str(r[central_acc_idx]).strip()
                    l_acc_str = str(r[lib_last_acc_idx]).strip()

                    if l_code == "TNDPL01584" and c_acc_str and c_acc_str.lower() != "nan":
                        try:
                            central_start_acc = int(c_acc_str)
                        except ValueError:
                            pass

                    if l_code:
                        try:
                            l_acc = int(l_acc_str) if l_acc_str and l_acc_str.lower() != "nan" else 0
                        except ValueError:
                            l_acc = 0
                        lib_last_acc_map[l_code] = l_acc

            base_df = book_df.copy()
            col_map_lower = {str(c).lower().strip(): c for c in base_df.columns}
            lib_id_col = next((col_map_lower[c] for c in col_map_lower if "librarianid" in c or "lib id" in c or "librarian" in c), base_df.columns[11] if len(base_df.columns) > 11 else None)
            lib_name_col = next((col_map_lower[c] for c in col_map_lower if "library name" in c), base_df.columns[12] if len(base_df.columns) > 12 else None)

            lib_dict = {}
            lib_name_list = []
            if lib_name_col and lib_id_col:
                for _, r in base_df.dropna(subset=[lib_name_col, lib_id_col]).iterrows():
                    l_name = str(r[lib_name_col]).strip()
                    l_id = str(r[lib_id_col]).strip()
                    if l_name and l_name.lower() != "nan":
                        lib_dict[l_name] = l_id
                        if l_name not in lib_name_list:
                            lib_name_list.append(l_name)

            lib_name_list = sorted(lib_name_list)

            st.markdown("---")
            st.markdown("### 🏢 நூலகத்தைத் தேர்ந்தெடுக்கவும் (Select Library)")

            selected_library_t4 = st.selectbox(
                "நூலகத்தின் பெயரினை உள்ளீடு செய்யவும் அல்லது தேர்ந்தெடுக்கவும்",
                ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + lib_name_list,
                key=f"library_select_t4_{st.session_state['library_key_t4']}",
            )

            if selected_library_t4 != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                if st.session_state["selected_library_t4"] != selected_library_t4:
                    st.session_state["selected_library_t4"] = selected_library_t4

            if st.session_state["selected_library_t4"]:
                selected_library = st.session_state["selected_library_t4"]

                if st.button("🔄 மற்றொரு நூலகத்தைத் தேர்ந்தெடுக்க", use_container_width=True, key="reset_lib_t4"):
                    st.session_state["selected_library_t4"] = None
                    st.session_state["library_key_t4"] += 1
                    st.rerun()

                target_lib_id = lib_dict.get(selected_library)
                if target_lib_id and lib_id_col:
                    filtered_lib_df = base_df[base_df[lib_id_col].astype(str).str.strip() == target_lib_id].copy()
                else:
                    filtered_lib_df = pd.DataFrame()

                if not filtered_lib_df.empty:
                    # Determine starting accession based on library type
                    if target_lib_id == "TNDPL01584":
                        starting_acc = central_start_acc
                        acc_type_label = "District Central Library (Column F)"
                    else:
                        starting_acc = lib_last_acc_map.get(target_lib_id, 0)
                        acc_type_label = "Branch / Village Library (Column G)"

                    st.success(f"📌 நூலக குறியீடு (Lib Code): **{target_lib_id}** | முறை: **{acc_type_label}** | தொடக்க எண்: **{starting_acc}**")

                    # Fetch 'Received' column values from Vendor Wise Book Data sheet
                    ws_data = sheet_vendor_wise.get_all_values()
                    ws_headers = [str(h).strip().lower() for h in ws_data[0]]
                    ws_lib_id_idx = next((i for i, h in enumerate(ws_headers) if "librarianid" in h or "lib id" in h), 11)
                    title_idx = next((i for i, h in enumerate(ws_headers) if "title" in h), 4)
                    received_idx = next((i for i, h in enumerate(ws_headers) if "received" in h and "not" not in h), 17)

                    # Map received quantities from Google Sheet for this library
                    received_map = {}
                    for w_row in ws_data[1:]:
                        w_lib = str(w_row[ws_lib_id_idx]).strip() if len(w_row) > ws_lib_id_idx else ""
                        w_title = clean_text(w_row[title_idx] if len(w_row) > title_idx else "")
                        w_rec_str = str(w_row[received_idx]).strip() if len(w_row) > received_idx else "0"
                        try:
                            w_rec = int(w_rec_str) if w_rec_str and w_rec_str.lower() != "nan" else 0
                        except ValueError:
                            w_rec = 0
                        if w_lib == target_lib_id:
                            received_map[w_title] = w_rec

                    acc_from_list = []
                    acc_to_list = []
                    current_acc = starting_acc

                    for _, row in filtered_lib_df.iterrows():
                        t_name = clean_text(row.get("Title", ""))
                        rec_qty = received_map.get(t_name, 0)  # Only received books get accession numbers

                        if rec_qty > 0:
                            f_val = current_acc + 1
                            t_val = current_acc + rec_qty
                            acc_from_list.append(f_val)
                            acc_to_list.append(t_val)
                            current_acc = t_val
                        else:
                            acc_from_list.append("")
                            acc_to_list.append("")

                    filtered_lib_df["Accession From"] = acc_from_list
                    filtered_lib_df["Accession To"] = acc_to_list

                    st.markdown("---")
                    st.markdown(f"### 📋 {selected_library} - பெறப்பட்ட நூல்களுக்கான Accession எண்கள் பட்டியல்")
                    st.dataframe(filtered_lib_df, use_container_width=True, hide_index=True)

                    st.markdown("---")
                    col_btn1, col_btn2 = st.columns(2)

                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        filtered_lib_df.to_excel(writer, index=False, sheet_name="Accession Register")
                    excel_data = output.getvalue()
                    file_prefix = re.sub(r"[^\w\s]", "", selected_library).strip()

                    with col_btn1:
                        st.download_button(
                            label="📊 Excel கோப்பாக பதிவிறக்குக",
                            data=excel_excel := excel_data,
                            file_name=f"{file_prefix}_Accession_Register.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )

                    with col_btn2:
                        if st.button("🚀 Vendor Wise Book Data சீட்டின் U & V கலங்களில் பதிவு செய்", use_container_width=True):
                            with st.spinner("Google Sheet-ல் பதிவு செய்யப்படுகிறது..."):
                                cell_list = []
                                current_acc_save = starting_acc

                                for _, row in filtered_lib_df.iterrows():
                                    t_name = clean_text(row.get("Title", ""))
                                    rec_qty = received_map.get(t_name, 0)

                                    if rec_qty > 0:
                                        f_val = current_acc_save + 1
                                        t_val = current_acc_save + rec_qty
                                        current_acc_save = t_val

                                        for r_idx, w_row in enumerate(ws_data[1:], start=2):
                                            w_lib = str(w_row[ws_lib_id_idx]).strip() if len(w_row) > ws_lib_id_idx else ""
                                            w_title = clean_text(w_row[title_idx] if len(w_row) > title_idx else "")
                                            if w_lib == target_lib_id and w_title == t_name:
                                                cell_list.append(Cell(row=r_idx, col=21, value=str(f_val))) # Column U
                                                cell_list.append(Cell(row=r_idx, col=22, value=str(t_val))) # Column V
                                                break

                                if cell_list:
                                    sheet_vendor_wise.update_cells(cell_list)
                                    st.success(f"✅ **{selected_library}** நூலகத்திற்கான Accession எண்கள் `Vendor Wise Book Data` சீட்டின் **U & V** கலங்களில் வெற்றிகரமாகப் பதிவு செய்யப்பட்டன!")
                                    time.sleep(1.5)
                                    st.rerun()
                                else:
                                    st.warning("⚠️ Google Sheet-ல் ஒத்த வரிசைகள் (Matching rows) எதுவும் காணப்படவில்லை.")
                else:
                    st.warning("⚠️ இந்த நூலகத்திற்கான தரவுகள் எதுவும் இல்லை.")
        except Exception as e:
            st.error(f"❌ பிழை ஏற்பட்டது: {e}")
