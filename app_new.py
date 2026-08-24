import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import pandas as pd
import streamlit as st

# Optional packages are imported safely so the app opens even before
# every optional PDF/Drive package is installed.
try:
    import gspread
    from gspread.cell import Cell
    from oauth2client.service_account import ServiceAccountCredentials
except Exception:
    gspread = None
    Cell = None
    ServiceAccountCredentials = None

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_READY = True
except Exception:
    REPORTLAB_READY = False

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload
    from google.oauth2.service_account import Credentials
    DRIVE_READY = True
except Exception:
    DRIVE_READY = False

st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
:root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--gold:#f59e0b}
.stApp{background:radial-gradient(circle at 8% 8%,rgba(0,188,212,.12),transparent 28%),linear-gradient(135deg,#eef5ff,#fbfdff 50%,#eaf2ff)}
[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{visibility:hidden}
h1{font-size:24px!important;padding:16px 20px!important;border-radius:16px;color:#fff!important;background:linear-gradient(135deg,#071a38,#1565c0 58%,#00acc1);box-shadow:0 6px 0 #041126,0 14px 24px #071a3833;text-shadow:2px 3px 3px #0006;text-align:center}
h2,h3{color:#092653!important}.profile-card{background:#fff;padding:12px 18px;border-radius:14px;border:1px solid #cfe0f5;box-shadow:5px 5px 0 #c8d8ed}.book-info{background:#fff;border-left:7px solid #1565c0;border-radius:14px;padding:14px 18px;line-height:1.9;box-shadow:5px 5px 0 #c8d8ed;margin:10px 0 16px}.total{color:#0b3d91;font-size:18px;font-weight:900}.notreceived{background:#fff8e1;border-left:7px solid #f59e0b;border-radius:12px;padding:12px 18px;color:#8a4b00;font-weight:800;box-shadow:4px 4px 0 #ead69b;margin:10px 0}.stButton>button,.stDownloadButton>button{min-height:45px!important;border-radius:13px!important;font-weight:800!important;color:#fff!important;background:linear-gradient(145deg,#1976d2,#082b68)!important;box-shadow:0 4px 0 #041b42,0 8px 15px #082b6830!important;border:0!important}.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);filter:brightness(1.1)}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# CONFIGURATION
# -----------------------------
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
DRIVE_FOLDER_ID = "1XOTSn8f6ntfrG8rI0iSk0QVwDujGqs1f"

# -----------------------------
# BASIC HELPERS
# -----------------------------
def clean_text(value):
    if pd.isna(value) or value is None:
        return ""
    value = re.sub(r"^\d+[\.\s\-]*", "", str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF]", "", value).lower()

def safe_name(value):
    return re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()[:80] or "Report"

def vendor_number(vendor_id_name, vendor_name):
    match = re.search(r"\d+", str(vendor_id_name or vendor_name))
    return match.group(0) if match else "000"

# -----------------------------
# SAFE FONT / PDF
# -----------------------------
PDF_REGULAR = "Helvetica"
PDF_BOLD = "Helvetica-Bold"
TAMIL_FONT_AVAILABLE = False

if REPORTLAB_READY:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    regular_path = os.path.join(base_dir, "NotoSansTamil-Regular.ttf")
    bold_path = os.path.join(base_dir, "NotoSansTamil-Bold.ttf")
    try:
        if os.path.exists(regular_path):
            pdfmetrics.registerFont(TTFont("TamilRegular", regular_path))
            pdfmetrics.registerFont(TTFont("TamilBold", bold_path if os.path.exists(bold_path) else regular_path))
            PDF_REGULAR = "TamilRegular"
            PDF_BOLD = "TamilBold"
            TAMIL_FONT_AVAILABLE = True
    except Exception:
        pass

def pdf_bytes(df, title):
    if not REPORTLAB_READY:
        return None
    output = io.BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=7*mm, leftMargin=7*mm, topMargin=7*mm, bottomMargin=7*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TamilTitle", parent=styles["Title"], fontName=PDF_BOLD, fontSize=14, leading=18, alignment=TA_CENTER, textColor=colors.HexColor("#071a38"))
    body_style = ParagraphStyle("TamilBody", parent=styles["BodyText"], fontName=PDF_REGULAR, fontSize=7, leading=9)
    header_style = ParagraphStyle("TamilHeader", parent=styles["BodyText"], fontName=PDF_BOLD, fontSize=7, leading=9, textColor=colors.white)
    columns = list(df.columns)
    table_data = [[Paragraph(str(c), header_style) for c in columns]]
    for row in df.fillna("").astype(str).values.tolist():
        table_data.append([Paragraph(str(v)[:120], body_style) for v in row])
    widths = [max(20*mm, min(58*mm, 1.1*(max([len(str(c))]+[len(str(v)) for v in df[c].head(25)])+2)*mm)) for c in columns]
    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0b3d91")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#9db6d5")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eef5ff")]),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    document.build([Paragraph(str(title), title_style), Spacer(1,4*mm), table])
    return output.getvalue()

# -----------------------------
# SAFE EXCEL / CSV
# -----------------------------
def excel_bytes(df, sheet_name):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name[:31])
    return output.getvalue()

def csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")

def download_panel(df, prefix, sheet_name):
    c1,c2,c3=st.columns(3)
    with c1: st.download_button("📊 Excel பதிவிறக்கம்", excel_bytes(df,sheet_name), f"{prefix}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with c2: st.download_button("📄 CSV பதிவிறக்கம்", csv_bytes(df), f"{prefix}.csv", "text/csv", use_container_width=True)
    with c3:
        if REPORTLAB_READY:
            st.download_button("🧾 PDF பதிவிறக்கம்", pdf_bytes(df,sheet_name), f"{prefix}.pdf", "application/pdf", use_container_width=True)
        else:
            st.button("🧾 PDF (Package இல்லை)", disabled=True, use_container_width=True)

# -----------------------------
# SAFE GOOGLE SERVICES
# -----------------------------
@st.cache_resource
def init_gspread():
    if gspread is None or ServiceAccountCredentials is None:
        return None
    if "gcp_service_account" not in st.secrets:
        return None
    scope=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    credentials=ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]),scope)
    return gspread.authorize(credentials)

@st.cache_resource
def get_drive_service():
    if not DRIVE_READY or "gcp_service_account" not in st.secrets:
        return None
    credentials=Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]),scopes=["https://www.googleapis.com/auth/drive"])
    return build("drive","v3",credentials=credentials,cache_discovery=False)

def upload_pdf(pdf_data, vendor_id, vendor_name):
    service=get_drive_service()
    if service is None:
        raise RuntimeError("Google Drive package அல்லது secrets.toml இணைப்பு கிடைக்கவில்லை.")
    filename=f"{vendor_number(vendor_id,vendor_name)}_{safe_name(vendor_name).replace(' ','_')}_Physical_Verification.pdf"
    metadata={"name":filename,"parents":[DRIVE_FOLDER_ID],"mimeType":"application/pdf"}
    media=MediaIoBaseUpload(io.BytesIO(pdf_data),mimetype="application/pdf",resumable=True)
    return service.files().create(body=metadata,media_body=media,fields="id,name,webViewLink",supportsAllDrives=True).execute()

# -----------------------------
# DATA LOAD
# -----------------------------
@st.cache_data
def load_data(path):
    if not os.path.exists(path):
        return pd.DataFrame(),pd.DataFrame()
    xls=pd.ExcelFile(path)
    vendors=pd.read_excel(path,sheet_name="Vendor Name") if "Vendor Name" in xls.sheet_names else pd.DataFrame()
    sheets=[s for s in xls.sheet_names if "Vendor Wise Book Data" in s]
    books=pd.read_excel(path,sheet_name=sheets[0]) if sheets else pd.DataFrame()
    return vendors,books

vendor_df,book_df=load_data(EXCEL_FILE)
client=init_gspread()
sheet_physically=sheet_vendor_wise=sheet_lib_detail=None
if client:
    try:
        worksheets={w.title.strip().lower():w for w in client.open_by_key(SPREADSHEET_ID).worksheets()}
        for title,ws in worksheets.items():
            if "physically verified" in title: sheet_physically=ws
            elif "vendor wise book data" in title: sheet_vendor_wise=ws
            elif "lib_detail" in title or "library" in title: sheet_lib_detail=ws
    except Exception as error:
        st.warning(f"Google Sheet இணைப்பு: {error}")

# -----------------------------
# LOGIN
# -----------------------------
def hash_password(value): return hashlib.sha256(value.encode("utf-8")).hexdigest()
USERS_DATABASE={"9842759306":{"password_hash":hash_password("123456"),"role":"Admin","name":"முதன்மை நிர்வாகி (Admin)"},"9787555290":{"password_hash":hash_password("123456"),"role":"User","name":"சரிபார்ப்பு பயனர் 1 (User)"},"9751687939":{"password_hash":hash_password("123456"),"role":"User","name":"சரிபார்ப்பு பயனர் 2 (User)"}}

def authenticate(phone,password):
    item=USERS_DATABASE.get(phone.strip())
    return item if item and hmac.compare_digest(hash_password(password),item["password_hash"]) else None

st.session_state.setdefault("logged_in",False);st.session_state.setdefault("user_role",None);st.session_state.setdefault("user_name","")
if not st.session_state["logged_in"]:
    _,col,_=st.columns([1,1.2,1])
    with col:
        st.markdown('<div class="profile-card" style="text-align:center"><div style="font-size:45px">📚</div><h2>பணி போர்ட்டல்</h2></div>',unsafe_allow_html=True)
        with st.form("login"):
            phone=st.text_input("📱 அலைபேசி எண்",max_chars=10);password=st.text_input("🔑 கடவுச்சொல்",type="password");submit=st.form_submit_button("🔓 உள்நுழைக",use_container_width=True)
        if submit:
            user=authenticate(phone,password)
            if user: st.session_state.update(logged_in=True,user_role=user["role"],user_name=user["name"]);st.rerun()
            else: st.error("தவறான அலைபேசி எண் அல்லது கடவுச்சொல்")
    st.stop()

# -----------------------------
# NAVIGATION
# -----------------------------
st.session_state.setdefault("vendor_key",0);st.session_state.setdefault("selected_vendor",None);st.session_state.setdefault("temp_verified_records",[]);st.session_state.setdefault("current_page","📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
menu=["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"] if st.session_state["user_role"]!="Admin" else ["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு","🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்","🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)","🏛️ 4. நூலகத்திற்கு விநியோகம் (103)","⚙️ 5. Accession எண்கள் மேலாண்மை"]
st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
st.markdown(f'<div class="profile-card">👤 <b>பயனர்:</b> {st.session_state["user_name"]} | <b>அதிகாரம்:</b> {st.session_state["user_role"]}</div>',unsafe_allow_html=True)
choice=st.selectbox("🧭 செய்ய வேண்டிய பணியைத் தேர்ந்தெடுக்கவும்",menu,index=menu.index(st.session_state["current_page"]))
st.session_state["current_page"]=choice

# -----------------------------
# TASK 1 - CORE FUNCTIONALITY
# -----------------------------
if choice==menu[0]:
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if vendor_df.empty or book_df.empty: st.error("Book Supply-2026.xlsx கோப்பு கிடைக்கவில்லை.");st.stop()
    vendors=[];vendor_map={}
    for _,row in vendor_df.iterrows():
        b=str(row.iloc[1]).strip() if len(row)>1 and pd.notna(row.iloc[1]) else "";c=str(row.iloc[2]).strip() if len(row)>2 and pd.notna(row.iloc[2]) else "";name=c if c and c.lower()!="nan" else b
        if name and name not in vendors: vendors.append(name);vendor_map[name]=b or c
    vendor=st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",["-- தேர்ந்தெடுக்கவும் --"]+vendors,key=f"vendor_{st.session_state['vendor_key']}")
    if vendor!="-- தேர்ந்தெடுக்கவும் --":
        if st.session_state["selected_vendor"]!=vendor: st.session_state["selected_vendor"]=vendor;st.session_state["temp_verified_records"]=[]
    if st.session_state["selected_vendor"]:
        vendor=st.session_state["selected_vendor"];target=clean_text(vendor)
        mask=(book_df.iloc[:,9].apply(clean_text)==target)|(book_df.iloc[:,10].apply(clean_text)==target);filtered=book_df[mask]
        if filtered.empty: st.warning("இந்த பதிப்பகத்திற்குத் தரவு இல்லை.")
        else:
            grouped=filtered.groupby(["Title","Author Name","Language"],as_index=False).agg({"Quantity":"sum","Original Price":"first","Acccepted Price":"first","Isbn":"first","Book Id":"first"})
            st.metric("📚 மொத்தத் தலைப்புகள்",len(grouped))
            done={x["Title"] for x in st.session_state["temp_verified_records"]};remaining=[x for x in grouped["Title"].tolist() if x not in done]
            if remaining:
                title=st.selectbox("📖 புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்",["-- தேர்ந்தெடுக்கவும் --"]+remaining,key=f"title_{len(done)}")
                if title!="-- தேர்ந்தெடுக்கவும் --":
                    row=grouped[grouped["Title"]==title].iloc[0];total=int(row["Quantity"]);author=row["Author Name"];language=row["Language"]
                    st.markdown(f'<div class="book-info">📖 <b>தலைப்பு:</b> {title}<br>✍️ <b>ஆசிரியர்:</b> {author}<br>🌐 <b>மொழி:</b> {language}<br><span class="total">📦 பெற வேண்டிய எண்ணிக்கை: {total}</span></div>',unsafe_allow_html=True)
                    received=st.number_input("✍️ பெறப்பட்ட எண்ணிக்கையை மட்டும் உள்ளிடவும்",min_value=0,max_value=total,value=0,step=1,key=f"received_{title}")
                    not_received=total-received
                    st.markdown(f'<div class="notreceived">❌ பெறப்படாத எண்ணிக்கை: {not_received}</div>',unsafe_allow_html=True)
                    if st.button("➕ தற்காலிகப் பட்டியலில் சேர்",use_container_width=True):
                        st.session_state["temp_verified_records"].append({"Title":title,"Author Name":author,"Language":language,"Total Qty":total,"Received":received,"Not Received":not_received,"Short / Extra":str(received-total) if received!=total else "0","ID with Vendor Name":vendor_map.get(vendor,vendor),"Vendor Name":vendor,"Date":datetime.now().strftime("%d-%m-%y %H:%M:%S")});st.rerun()
            else: st.success("அனைத்து தலைப்புகளும் சேர்க்கப்பட்டன.")
            if st.session_state["temp_verified_records"]:
                temp=pd.DataFrame(st.session_state["temp_verified_records"]);display=temp[["Title","Author Name","Language","Total Qty","Received","Not Received","Short / Extra","Date"]];st.dataframe(display,use_container_width=True,hide_index=True)
                if REPORTLAB_READY:
                    data=pdf_bytes(display,f"{vendor} - Physical Verification");prefix=f"{vendor_number(vendor_map.get(vendor),vendor)}_{safe_name(vendor).replace(' ','_')}_Physical_Verification";st.download_button("🧾 PDF பதிவிறக்கம்",data,f"{prefix}.pdf","application/pdf",use_container_width=True)
                    if st.button("☁️ Google Drive-ல் PDF சேமிக்கவும்",use_container_width=True):
                        try: uploaded=upload_pdf(data,vendor_map.get(vendor),vendor);st.success(f"Drive-ல் சேமிக்கப்பட்டது: {uploaded['name']}")
                        except Exception as error: st.error(f"Drive சேமிப்பு தோல்வி: {error}")
                c1,c2=st.columns(2)
                with c1:
                    if st.button("🗑️ அனைத்தையும் அழி",use_container_width=True): st.session_state["temp_verified_records"]=[];st.rerun()
                with c2:
                    if st.button("💾 சீட்டில் சேமி",use_container_width=True):
                        if len(st.session_state["temp_verified_records"])<len(grouped): st.error("அனைத்து தலைப்புகளையும் சேர்த்த பிறகே சேமிக்கவும்.")
                        elif sheet_physically:
                            for item in st.session_state["temp_verified_records"]: sheet_physically.append_row([item["ID with Vendor Name"],item["Title"],item["Language"],item["Author Name"],item["Vendor Name"],item["Total Qty"],item["Received"],item["Not Received"],item["Short / Extra"],item["Date"]])
                            st.success("Google Sheet-ல் சேமிக்கப்பட்டது!");st.session_state["temp_verified_records"]=[];st.session_state["selected_vendor"]=None;st.rerun()

# -----------------------------
# TASK 3/4 basic display and downloads
# -----------------------------
elif choice==menu[2]:
    st.subheader("🏢 மொத்த பதிப்பாளர் விவரங்கள்")
    st.dataframe(vendor_df,use_container_width=True,hide_index=True);download_panel(vendor_df,"All_Vendors","Vendor Summary")
elif choice==menu[3]:
    st.subheader("🏛️ நூலகத்திற்கு விநியோகம்")
    st.dataframe(book_df,use_container_width=True,hide_index=True);download_panel(book_df,"Library_Distribution","Library Distribution")
elif choice==menu[4]:
    st.subheader("⚙️ Accession எண்கள் மேலாண்மை")
    st.info("Vendor Wise Book Data-ல் உள்ள Received Qty அடிப்படையில் Accession எண்கள் உருவாக்கப்பட வேண்டும்.")
    st.dataframe(book_df.head(0),use_container_width=True,hide_index=True)
    download_panel(book_df.head(0),"Accession_Register","Accession Register")
elif choice==menu[1]:
    st.subheader("🔄 Vendor Wise Book Data ஒத்திசைவு")
    st.info("Google Sheet இணைப்பு இருந்தால் இந்தப் பகுதியில் உங்கள் Sync செயல்பாட்டைத் தொடரலாம்.")
    if sheet_vendor_wise: st.success("Vendor Wise Book Data இணைக்கப்பட்டுள்ளது.")
