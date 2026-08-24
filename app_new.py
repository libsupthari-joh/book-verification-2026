import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import gspread
from gspread.cell import Cell
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்", page_icon="📚", layout="wide", initial_sidebar_state="collapsed")

# ============================================================
# 1. 3D UI
# ============================================================
def get_custom_css():
    return """
    <style>
    :root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--green:#16803c;--red:#b42318}
    .stApp{background:radial-gradient(circle at 8% 8%,rgba(0,188,212,.12),transparent 28%),linear-gradient(135deg,#eef5ff,#fbfdff 50%,#eaf2ff)}
    [data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{visibility:hidden}
    h1{font-size:24px!important;padding:16px 20px!important;border-radius:16px;color:#fff!important;background:linear-gradient(135deg,#071a38,#1565c0 58%,#00acc1);box-shadow:0 6px 0 #041126,0 14px 24px #071a3833;text-shadow:2px 3px 3px #0006;text-align:center;margin-bottom:20px!important}
    h2,h3{color:#092653!important}
    .profile-card{background:linear-gradient(145deg,#fff,#eef5ff);padding:12px 18px;border-radius:14px;border:1px solid #cfe0f5;box-shadow:5px 5px 0 #c8d8ed,0 8px 18px #08265318}
    .stButton>button,.stDownloadButton>button{min-height:45px!important;border-radius:13px!important;font-size:14px!important;font-weight:800!important;color:#fff!important;background:linear-gradient(145deg,#1976d2,#082b68)!important;box-shadow:0 4px 0 #041b42,0 8px 15px #082b6830!important;border:0!important;transition:.2s!important}
    .stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);filter:brightness(1.1)}
    [data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;border-radius:14px;box-shadow:4px 4px 0 #c8d8ed;padding:10px}
    div[data-testid="stSelectbox"] label,div[data-testid="stNumberInput"] label,div[data-testid="stTextInput"] label{font-size:14px!important;font-weight:700!important;color:#092653!important}
    .book-info{background:#fff;border-left:6px solid #1565c0;border-radius:12px;padding:12px 16px;box-shadow:4px 4px 0 #d3e0f0;margin:8px 0}
    </style>
    """
st.markdown(get_custom_css(), unsafe_allow_html=True)

# ============================================================
# 2. LOGIN
# ============================================================
def hash_password(password): return hashlib.sha256(password.encode("utf-8")).hexdigest()
USERS_DATABASE={
    "9842759306":{"password_hash":hash_password("123456"),"role":"Admin","name":"முதன்மை நிர்வாகி (Admin)"},
    "9787555290":{"password_hash":hash_password("123456"),"role":"User","name":"சரிபார்ப்பு பயனர் 1 (User)"},
    "9751687939":{"password_hash":hash_password("123456"),"role":"User","name":"சரிபார்ப்பு பயனர் 2 (User)"},
}
def authenticate_user(phone,password):
    user=USERS_DATABASE.get(phone.strip())
    return user if user and hmac.compare_digest(hash_password(password),user["password_hash"]) else None

if "logged_in" not in st.session_state:
    st.session_state["logged_in"]=st.query_params.get("logged_in") == "true"
    st.session_state["user_role"]=st.query_params.get("role") if st.session_state["logged_in"] else None
    st.session_state["user_name"]=st.query_params.get("name") if st.session_state["logged_in"] else ""
st.session_state.setdefault("logged_in",False); st.session_state.setdefault("user_role",None); st.session_state.setdefault("user_name","")

def show_login_page():
    _,form_col,_=st.columns([1,1.2,1])
    with form_col:
        st.markdown('<div style="text-align:center;background:#fff;border-radius:20px;padding:20px;box-shadow:8px 8px 0 #c8d8ed"><div style="font-size:45px">📚</div><h2>பணி போர்ட்டல்</h2><small>2026 புதிய நூல்கள் விநியோகம்</small></div>',unsafe_allow_html=True)
        with st.form("secure_login_form"):
            phone=st.text_input("📱 அலைபேசி எண்",max_chars=10,placeholder="10 இலக்க எண்")
            password=st.text_input("🔑 கடவுச்சொல்",type="password")
            submitted=st.form_submit_button("🔓 உள்நுழைக",use_container_width=True)
        if submitted:
            user=authenticate_user(phone,password)
            if user:
                st.session_state.update(logged_in=True,user_role=user["role"],user_name=user["name"])
                st.query_params["logged_in"]="true"; st.query_params["role"]=user["role"]; st.query_params["name"]=user["name"]
                st.rerun()
            else: st.error("❌ தவறான அலைபேசி எண் அல்லது கடவுச்சொல்!")
if not st.session_state["logged_in"]: show_login_page(); st.stop()

# ============================================================
# 3. DATA AND GOOGLE SHEETS
# ============================================================
EXCEL_FILE="Book Supply-2026.xlsx"
SPREADSHEET_ID="1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
@st.cache_data
def load_data(file_path):
    if not os.path.exists(file_path): return None,None
    xls=pd.ExcelFile(file_path)
    vendor=pd.read_excel(file_path,sheet_name="Vendor Name") if "Vendor Name" in xls.sheet_names else pd.DataFrame()
    sheets=[s for s in xls.sheet_names if "Vendor Wise Book Data" in s]
    books=pd.read_excel(file_path,sheet_name=sheets[0]) if sheets else pd.DataFrame()
    return vendor,books
@st.cache_resource
def init_gspread():
    scope=["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
    credentials=ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]),scope)
    return gspread.authorize(credentials)
def clean_text(value):
    if pd.isna(value) or value is None:return ""
    value=re.sub(r"^\d+[\.\s\-]*","",str(value).strip())
    return re.sub(r"[^a-zA-Z0-9\u0B80-\u0BFF]","",value).lower()
vendor_df,book_df=load_data(EXCEL_FILE)
sheet_physically=sheet_vendor_wise=sheet_lib_detail=None
try:
    worksheets={w.title.strip().lower():w for w in init_gspread().open_by_key(SPREADSHEET_ID).worksheets()}
    for title,worksheet in worksheets.items():
        if "physically verified" in title:sheet_physically=worksheet
        elif "vendor wise book data" in title:sheet_vendor_wise=worksheet
        elif "lib_detail" in title or "library" in title:sheet_lib_detail=worksheet
except Exception as error: st.error(f"❌ Google Sheet இணைப்புப் பிழை: {error}")

# ============================================================
# 4. DOWNLOAD HELPERS
# ============================================================
def safe_name(value): return re.sub(r"[^\w\u0B80-\u0BFF -]","",str(value)).strip()[:80] or "Report"
def make_excel(df,sheet_name):
    out=io.BytesIO()
    with pd.ExcelWriter(out,engine="openpyxl") as writer: df.to_excel(writer,index=False,sheet_name=sheet_name[:31])
    return out.getvalue()
def make_csv(df): return df.to_csv(index=False).encode("utf-8-sig")
def make_pdf(df,title):
    out=io.BytesIO(); doc=SimpleDocTemplate(out,pagesize=landscape(A4),rightMargin=7*mm,leftMargin=7*mm,topMargin=7*mm,bottomMargin=7*mm)
    styles=getSampleStyleSheet(); title_style=ParagraphStyle("title",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=14,alignment=TA_CENTER,textColor=colors.HexColor("#071a38")); body=ParagraphStyle("body",parent=styles["BodyText"],fontName="Helvetica",fontSize=7,leading=8)
    data=[[Paragraph(str(c),body) for c in df.columns]]+[[Paragraph(str(x)[:100],body) for x in row] for row in df.fillna("").astype(str).values.tolist()]
    widths=[max(20*mm,min(58*mm,(max([len(str(c))]+[len(str(x)) for x in df[c].head(25)])+2)*1.15*mm)) for c in df.columns]
    table=Table(data,colWidths=widths,repeatRows=1); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0b3d91")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.25,colors.HexColor("#9db6d5")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#eef5ff")]),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    doc.build([Paragraph(title,title_style),Spacer(1,4*mm),table]); return out.getvalue()
def download_panel(df,prefix,sheet_name):
    st.markdown("### 📥 பதிவிறக்க வசதிகள்"); c1,c2,c3=st.columns(3)
    with c1: st.download_button("📊 Excel பதிவிறக்கம்",make_excel(df,sheet_name),f"{prefix}.xlsx","application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",use_container_width=True)
    with c2: st.download_button("📄 CSV பதிவிறக்கம்",make_csv(df),f"{prefix}.csv","text/csv",use_container_width=True)
    with c3: st.download_button("🧾 PDF பதிவிறக்கம்",make_pdf(df,sheet_name),f"{prefix}.pdf","application/pdf",use_container_width=True)

# ============================================================
# 5. NAVIGATION
# ============================================================
st.session_state.setdefault("current_page","📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"); st.session_state.setdefault("vendor_key",0); st.session_state.setdefault("selected_vendor",None); st.session_state.setdefault("temp_verified_records",[]); st.session_state.setdefault("library_key",0); st.session_state.setdefault("selected_library",None); st.session_state.setdefault("acc_library_key",0); st.session_state.setdefault("selected_acc_library",None)
if st.session_state["user_role"]=="Admin":
    menu_items=["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு","🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்","🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)","🏛️ 4. நூலகத்திற்கு விநியோகம் (103)","⚙️ 5. Accession எண்கள் மேலாண்மை"]
else: menu_items=["📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"]
if st.session_state["current_page"] not in menu_items: st.session_state["current_page"]=menu_items[0]
st.title("📚 2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
col_info,col_logout=st.columns([3.2,.8])
with col_info: st.markdown(f'<div class="profile-card">👤 <b>பயனர்:</b> {st.session_state["user_name"]} &nbsp;|&nbsp; <b>அதிகாரம்:</b> {"👑 Admin" if st.session_state["user_role"]=="Admin" else "👤 User"}</div>',unsafe_allow_html=True)
with col_logout:
    if st.button("🚪 வெளியேறு",use_container_width=True): st.query_params.clear(); st.session_state.clear(); st.rerun()
selected_main_menu=st.selectbox("🧭 செய்ய வேண்டிய பணியைத் தேர்ந்தெடுக்கவும்",menu_items,index=menu_items.index(st.session_state["current_page"]),key="main_screen_menu_selectbox")
if selected_main_menu!=st.session_state["current_page"]: st.session_state["current_page"]=selected_main_menu; st.rerun()
menu_choice=st.session_state["current_page"]; st.markdown("---")

# ============================================================
# 6. TASK 1 - EXACT ORIGINAL WORKFLOW
# ============================================================
if menu_choice=="📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு":
    st.subheader("📥 பெறப்பட்ட நூல்கள் சரிபார்ப்பு")
    if vendor_df is None or book_df is None: st.error("❌ 'Book Supply-2026.xlsx' கோப்பு காணப்படவில்லை!"); st.stop()
    already_verified_clean=set()
    if sheet_physically:
        try:
            p_rows=sheet_physically.get_all_values()
            for row in p_rows[1:]:
                if len(row)>4 and row[4]: already_verified_clean.add(clean_text(row[4]))
                elif row and row[0]: already_verified_clean.add(clean_text(row[0]))
        except Exception: pass
    vendor_list=[]; vendor_id_map={}
    for _,row in vendor_df.iterrows():
        col_b=str(row.iloc[1]).strip() if len(row)>1 and pd.notna(row.iloc[1]) else ""; col_c=str(row.iloc[2]).strip() if len(row)>2 and pd.notna(row.iloc[2]) else ""
        vendor_name=col_c if col_c and col_c.lower()!="nan" else col_b; full_id_name=col_b if col_b and col_b.lower()!="nan" else col_c
        if vendor_name and vendor_name.lower()!="nan" and vendor_name not in vendor_list: vendor_list.append(vendor_name); vendor_id_map[vendor_name]=full_id_name
    st.markdown("### 🏢 1. பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்")
    selected_vendor_raw=st.selectbox("பதிப்பகத்தின் பெயரைத் தேர்ந்தெடுக்கவும்",["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"]+vendor_list,key=f"vendor_select_{st.session_state['vendor_key']}")
    if selected_vendor_raw!="-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --" and st.session_state["selected_vendor"]!=selected_vendor_raw:
        st.session_state["selected_vendor"]=selected_vendor_raw; st.session_state["temp_verified_records"]=[]
    if st.session_state["selected_vendor"]:
        completed_vendor_name=st.session_state["selected_vendor"]; target_vendor_clean=clean_text(completed_vendor_name)
        if target_vendor_clean in already_verified_clean:
            st.error(f"⚠️ **{completed_vendor_name}** பதிப்பகத்தின் சரிபார்ப்பு பணி ஏற்கனவே முடிவுற்றது!")
            if st.button("🔄 மற்றொரு பதிப்பகத்தைத் தேர்ந்தெடுக்க",use_container_width=True): st.session_state["selected_vendor"]=None; st.session_state["temp_verified_records"]=[]; st.session_state["vendor_key"]+=1; st.rerun()
        else:
            vendor_mask=(book_df.iloc[:,9].apply(clean_text)==target_vendor_clean)|(book_df.iloc[:,10].apply(clean_text)==target_vendor_clean); filtered_books=book_df[vendor_mask]
            if filtered_books.empty: st.warning("⚠️ இந்த பதிப்பகத்திற்குப் புத்தகத் தரவுகள் இல்லை!")
            else:
                grouped=filtered_books.groupby(["Title","Author Name","Language"],as_index=False).agg({"Quantity":"sum","Original Price":"first","Acccepted Price":"first","Isbn":"first","Book Id":"first"})
                c1,c2=st.columns(2); c1.metric("📚 மொத்தத் தலைப்புகள்",len(grouped)); c2.metric("📦 மொத்தப் படிகள்",int(grouped["Quantity"].sum()))
                st.markdown("### 🔍 2. ஒவ்வொரு தலைப்பாகத் தேர்வு செய்து சரிபார்க்கவும்")
                verified_titles={item["Title"] for item in st.session_state["temp_verified_records"]}; remaining=[t for t in grouped["Title"].tolist() if t not in verified_titles]
                if not remaining: st.success("🎉 இந்த பதிப்பகத்தில் உள்ள அனைத்துத் தலைப்புகளும் சேர்க்கப்பட்டுவிட்டன!")
                else:
                    selected_title=st.selectbox("புத்தகத் தலைப்பைத் தேர்ந்தெடுக்கவும்",["-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --"]+remaining,key=f"title_select_{len(st.session_state['temp_verified_records'])}")
                    if selected_title!="-- புத்தகத்தைத் தேர்ந்தெடுக்கவும் --":
                        book_row=grouped[grouped["Title"]==selected_title].iloc[0]; t_author=book_row["Author Name"] if pd.notna(book_row["Author Name"]) else ""; t_lang=book_row["Language"]; t_total_qty=int(book_row["Quantity"])
                        st.markdown(f'<div class="book-info">📖 <b>தலைப்பு:</b> {selected_title}<br>✍️ <b>ஆசிரியர்:</b> {t_author}<br>🌐 <b>மொழி:</b> {t_lang}<br>📦 <b>மொத்த எண்ணிக்கை:</b> {t_total_qty}</div>',unsafe_allow_html=True)
                        rec_qty=st.number_input("பெறப்பட்ட எண்ணிக்கை (Received Qty)",min_value=0,max_value=t_total_qty,value=t_total_qty,step=1,key=f"rec_inp_{selected_title}")
                        not_rec_qty=t_total_qty-rec_qty
                        st.number_input("பெறப்படாத எண்ணிக்கை (Not Received Qty)",min_value=0,value=not_rec_qty,step=1,disabled=True,key=f"not_rec_view_{selected_title}")
                        st.caption("பெறப்பட்ட எண்ணிக்கை மாற்றினால், பெறப்படாத எண்ணிக்கை தானாகக் கணக்கிடப்படும்.")
                        if st.button("➕ தற்காலிகப் பட்டியலில் சேர்",use_container_width=True):
                            st.session_state["temp_verified_records"].append({"Title":selected_title,"Author Name":t_author,"Language":t_lang,"Total Qty":t_total_qty,"Received":rec_qty,"Not Received":not_rec_qty,"Short / Extra":str(rec_qty-t_total_qty) if rec_qty!=t_total_qty else "0","ID with Vendor Name":vendor_id_map.get(completed_vendor_name,completed_vendor_name),"Vendor Name":completed_vendor_name,"Date":datetime.now().strftime("%d-%m-%y %H:%M:%S")}); st.success(f"✅ '{selected_title}' சேர்க்கப்பட்டது!"); time.sleep(.3); st.rerun()
                if st.session_state["temp_verified_records"]:
                    temp_df=pd.DataFrame(st.session_state["temp_verified_records"]); display_cols=["Title","Author Name","Language","Total Qty","Received","Not Received","Short / Extra","Date"]; st.dataframe(temp_df[display_cols],use_container_width=True,hide_index=True)
                    c_clear,c_save=st.columns(2)
                    with c_clear:
                        if st.button("🗑️ அனைத்தையும் அழி",use_container_width=True): st.session_state["temp_verified_records"]=[]; st.rerun()
                    with c_save:
                        if st.button("💾 சீட்டில் சேமி",use_container_width=True):
                            if len(st.session_state["temp_verified_records"])<len(grouped): st.error(f"⚠️ மொத்தம் {len(grouped)} தலைப்புகள் உள்ளன. அனைத்தையும் சேர்த்த பின்னரே சேமிக்க முடியும்!")
                            elif sheet_physically:
                                try:
                                    with st.spinner("சீட்டில் சேமிக்கப்படுகிறது..."):
                                        for item in st.session_state["temp_verified_records"]: sheet_physically.append_row([item["ID with Vendor Name"],item["Title"],item["Language"],item["Author Name"],item["Vendor Name"],item["Total Qty"],item["Received"],item["Not Received"],item["Short / Extra"],item["Date"]])
                                    st.success("✅ Google Sheet-ல் தரவுகள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!"); time.sleep(1); st.session_state["selected_vendor"]=None; st.session_state["temp_verified_records"]=[]; st.session_state["vendor_key"]+=1; st.rerun()
                                except Exception as e: st.error(f"❌ பிழை: {e}")
                            else: st.error("❌ Google Sheet இணைப்பு கிடைக்கவில்லை!")

# ============================================================
# 7. TASK 2 - ORIGINAL SYNC
# ============================================================
elif menu_choice=="🔄 2. Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை மாற்றம் செய்தல்":
    st.subheader("🔄 Vendor Wise Book Data சீட்டிற்கு பெறப்பட்ட எண்ணிக்கை ஒத்திசைவு (Sync)")
    st.info("💡 Physically verified சீட்டில் உள்ள பதிப்பகங்களில், இன்னும் ஒத்திசைவு செய்யப்படாதவை மட்டுமே தோன்றும்.")
    if sheet_physically is None or sheet_vendor_wise is None: st.error("❌ Google Sheet இணைப்புகள் கிடைக்கவில்லை!"); st.stop()
    try:
        phys_rows=sheet_physically.get_all_values(); phys_headers=[str(h).strip().lower() for h in phys_rows[0]] if phys_rows else []; v_name_idx=next((i for i,h in enumerate(phys_headers) if "vendor" in h),4); title_idx=next((i for i,h in enumerate(phys_headers) if "title" in h),1); rec_idx=next((i for i,h in enumerate(phys_headers) if "received" in h and "not" not in h),6)
        ws_data=sheet_vendor_wise.get_all_values(); ws_headers=[str(h).strip().lower() for h in ws_data[0]]; s_col=next((i for i,h in enumerate(ws_headers) if "received" in h and "not" not in h),18)
        vendor_records_map={}
        for row in phys_rows[1:]:
            if len(row)>v_name_idx and row[v_name_idx].strip(): vendor_records_map.setdefault(row[v_name_idx].strip(),[]).append(row)
        unsynced=[]
        for v_name,records in vendor_records_map.items():
            synced=True
            for p_row in records:
                p_title=clean_text(p_row[title_idx] if len(p_row)>title_idx else ""); found=False
                for w_row in ws_data[1:]:
                    w_vendor=clean_text(w_row[10] if len(w_row)>10 else (w_row[9] if len(w_row)>9 else "")); w_title=clean_text(w_row[4] if len(w_row)>4 else "")
                    if clean_text(v_name) in w_vendor and p_title==w_title and len(w_row)>s_col and str(w_row[s_col]).strip(): found=True; break
                if not found: synced=False; break
            if not synced: unsynced.append(v_name)
        if not unsynced: st.warning("⚠️ ஒத்திசைவு செய்ய வேண்டிய புதிய பதிப்பகங்கள் எதுவும் இல்லை.")
        else:
            selected_vendor_t2=st.selectbox("ஒத்திசைவு செய்ய வேண்டிய பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"]+unsynced,key="vendor_select_t2")
            if selected_vendor_t2!="-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                target=clean_text(selected_vendor_t2); lang_idx=next((i for i,h in enumerate(phys_headers) if "language" in h),2); author_idx=next((i for i,h in enumerate(phys_headers) if "author" in h),3); total_idx=next((i for i,h in enumerate(phys_headers) if "total" in h or h=="quantity"),5); not_idx=next((i for i,h in enumerate(phys_headers) if "not received" in h),7); short_idx=next((i for i,h in enumerate(phys_headers) if "short" in h),8); date_idx=next((i for i,h in enumerate(phys_headers) if "date" in h),9)
                records=[r for r in phys_rows[1:] if len(r)>max(v_name_idx,title_idx,rec_idx) and target in clean_text(r[v_name_idx])]
                view=pd.DataFrame([{ "Title":r[title_idx],"Author Name":r[author_idx],"Language":r[lang_idx],"Total Qty":r[total_idx],"Received":r[rec_idx],"Not Received":r[not_idx],"Short / Extra":r[short_idx],"Date":r[date_idx]} for r in records]); st.dataframe(view,use_container_width=True,hide_index=True)
                if st.button("🚀 இந்த பதிப்பகத்திற்கு மட்டும் ஒத்திசைவு செய்க",use_container_width=True):
                    ws_data=sheet_vendor_wise.get_all_values(); ws_headers=[str(h).strip().lower() for h in ws_data[0]]; s_col=next((i+1 for i,h in enumerate(ws_headers) if "received" in h and "not" not in h),19); t_col=next((i+1 for i,h in enumerate(ws_headers) if "not received" in h or ("not" in h and "received" in h)),20); qty_col=next((i+1 for i,h in enumerate(ws_headers) if h=="quantity"),18); cells=[]
                    for p_row in records:
                        try: remaining=int(p_row[rec_idx])
                        except: remaining=0
                        matches=[]
                        for row_num,row in enumerate(ws_data[1:],start=2):
                            if target in clean_text(row[10] if len(row)>10 else (row[9] if len(row)>9 else "")) and clean_text(p_row[title_idx])==clean_text(row[4] if len(row)>4 else ""): matches.append((row_num,row))
                        for row_num,row in matches:
                            try: qty=int(row[qty_col-1]) if len(row)>=qty_col and row[qty_col-1] else 1
                            except: qty=1
                            got=min(remaining,qty); cells.extend([Cell(row=row_num,col=s_col,value=str(got)),Cell(row=row_num,col=t_col,value=str(qty-got))]); remaining-=got
                    if cells: sheet_vendor_wise.update_cells(cells)
                    st.success(f"✅ {selected_vendor_t2} ஒத்திசைக்கப்பட்டது!"); time.sleep(1); st.rerun()
    except Exception as e: st.error(f"❌ பிழை: {e}")

# ============================================================
# 8. TASK 3 - ORIGINAL VENDOR DETAILS + DOWNLOADS
# ============================================================
elif menu_choice=="🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)":
    st.subheader("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)")
    if vendor_df is None or book_df is None: st.error("❌ தரவு கிடைக்கவில்லை!"); st.stop()
    vendors=[]
    for _,row in vendor_df.iterrows():
        b=str(row.iloc[1]).strip() if len(row)>1 and pd.notna(row.iloc[1]) else ""; c=str(row.iloc[2]).strip() if len(row)>2 and pd.notna(row.iloc[2]) else ""; name=c if c and c.lower()!="nan" else b
        if name and name not in vendors: vendors.append(name)
    selected=st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்",["-- அனைத்து பதிப்பாளர்களும் (All Publishers) --"]+vendors,key="vendor_select_t3")
    if selected=="-- அனைத்து பதிப்பாளர்களும் (All Publishers) --": result=vendor_df; st.dataframe(result,use_container_width=True,hide_index=True); download_panel(result,"All_Vendors_Summary","Vendor Summary")
    else:
        mask=(book_df.iloc[:,9].apply(clean_text)==clean_text(selected))|(book_df.iloc[:,10].apply(clean_text)==clean_text(selected)); result=book_df[mask]
        if result.empty: st.warning("⚠️ இந்த பதிப்பகத்திற்குத் தரவு இல்லை!")
        else: st.dataframe(result,use_container_width=True,hide_index=True); download_panel(result,safe_name(selected)+"_Vendor_Details","Vendor Details")

# ============================================================
# 9. TASK 4 - ORIGINAL LIBRARY DISTRIBUTION + DOWNLOADS
# ============================================================
elif menu_choice=="🏛️ 4. நூலகத்திற்கு விநியோகம் (103)":
    st.subheader("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)")
    if book_df is None or book_df.empty: st.error("❌ புத்தகத் தரவு கிடைக்கவில்லை!"); st.stop()
    base_df=book_df.copy(); drop_cols=[c for c in base_df.columns if any(k in str(c).lower() for k in ["v s.no","temp no","v.s.no","temp"] )]; base_df=base_df.drop(columns=drop_cols,errors="ignore"); cmap={str(c).lower().strip():c for c in base_df.columns}; lib_id_col=next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k or "librarian" in k),base_df.columns[11] if len(base_df.columns)>11 else None); lib_name_col=next((cmap[k] for k in cmap if "library name" in k),base_df.columns[12] if len(base_df.columns)>12 else None); lib_type_col=next((cmap[k] for k in cmap if "library type" in k),base_df.columns[10] if len(base_df.columns)>10 else None)
    lib_dict={}; names=[]
    if lib_name_col and lib_id_col:
        for _,r in base_df.dropna(subset=[lib_name_col,lib_id_col]).iterrows():
            name=str(r[lib_name_col]).strip(); lid=str(r[lib_id_col]).strip(); lib_dict[name]=lid
            if name and name not in names:names.append(name)
    selected=st.selectbox("நூலகத்தைத் தேர்ந்தெடுக்கவும்",["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --","-- அனைத்து நூலகங்களும் (All Libraries) --"]+sorted(names),key=f"library_select_{st.session_state['library_key']}")
    if selected!="-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
        st.session_state["selected_library"]=selected
    if st.session_state["selected_library"]:
        selected=st.session_state["selected_library"]
        if selected=="-- அனைத்து நூலகங்களும் (All Libraries) --": result=base_df.copy()
        elif lib_id_col and lib_dict.get(selected): result=base_df[base_df[lib_id_col].astype(str).str.strip()==lib_dict[selected]].copy()
        else: result=base_df[base_df[lib_name_col].astype(str).str.strip()==selected].copy()
        if not result.empty:
            result=result.drop(columns=["S.No"],errors="ignore"); result.insert(0,"S.No",range(1,len(result)+1)); st.dataframe(result,use_container_width=True,hide_index=True); download_panel(result,safe_name(selected)+"_Distribution","Library Distribution")
        else: st.warning("⚠️ தரவுகள் எதுவும் இல்லை.")

# ============================================================
# 10. TASK 5 - ORIGINAL ACCESSION + DOWNLOADS
# ============================================================
elif menu_choice=="⚙️ 5. Accession எண்கள் மேலாண்மை":
    st.subheader("⚙️ 5. தானியங்கி மைய மற்றும் கிளை நூல் சேர்க்கை எண்கள் மேலாண்மை")
    st.error("🚨 பெறப்பட்ட நூல்களுக்கு (Received Qty) மட்டுமே சேர்க்கை எண்கள் உருவாக்கப்படும்.")
    if book_df is None or book_df.empty or sheet_vendor_wise is None: st.error("❌ புத்தகத் தரவு அல்லது Google Sheet இணைப்பு கிடைக்கவில்லை!"); st.stop()
    base_df=book_df.copy(); cmap={str(c).lower().strip():c for c in base_df.columns}; lib_name_col=next((cmap[k] for k in cmap if "library name" in k),base_df.columns[12] if len(base_df.columns)>12 else None); lib_id_col=next((cmap[k] for k in cmap if "librarianid" in k or "lib id" in k),base_df.columns[11] if len(base_df.columns)>11 else None); names=sorted(base_df[lib_name_col].dropna().astype(str).str.strip().unique().tolist()) if lib_name_col else []; lib_dict={str(r[lib_name_col]).strip():str(r[lib_id_col]).strip() for _,r in base_df.dropna(subset=[lib_name_col,lib_id_col]).iterrows()}
    selected=st.selectbox("சேர்க்கை எண்களைப் பதிவு செய்ய நூலகத்தைத் தேர்ந்தெடுக்கவும்",["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"]+names,key=f"acc_library_select_{st.session_state['acc_library_key']}")
    if selected!="-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":st.session_state["selected_acc_library"]=selected
    if st.session_state["selected_acc_library"]:
        selected=st.session_state["selected_acc_library"]; target_id=lib_dict.get(selected); central_start=branch_start=None
        if sheet_lib_detail:
            try:
                rows=sheet_lib_detail.get_all_values()
                for row in rows[1:]:
                    if len(row)>5 and str(row[5]).strip().isdigit():central_start=int(str(row[5]).strip());break
                for row in rows[1:]:
                    if len(row)>1 and str(row[1]).strip()==target_id and len(row)>6 and str(row[6]).strip().isdigit():branch_start=int(str(row[6]).strip());break
            except Exception as e:st.warning(f"⚠️ Lib_Detail பிழை: {e}")
        try:
            rows=sheet_vendor_wise.get_all_values(); headers=[str(h).strip().lower() for h in rows[0]]; lib_idx=next((i for i,h in enumerate(headers) if "librarianid" in h or "lib id" in h),11); title_idx=next((i for i,h in enumerate(headers) if "title" in h),4); qty_idx=next((i for i,h in enumerate(headers) if h=="quantity"),17); rec_idx=next((i for i,h in enumerate(headers) if "received" in h and "not" not in h),18); library_rows=[]
            for row_num,row in enumerate(rows[1:],start=2):
                if len(row)>lib_idx and str(row[lib_idx]).strip()==target_id:
                    try:q=int(row[qty_idx]) if str(row[qty_idx]).strip().isdigit() else 1
                    except:q=1
                    try:r=int(row[rec_idx]) if str(row[rec_idx]).strip().isdigit() else 0
                    except:r=0
                    library_rows.append({"Sheet Row":row_num,"Title":row[title_idx],"Quantity":q,"Received":r,"Author Name":row[3] if len(row)>3 else "","Language":row[2] if len(row)>2 else ""})
            if library_rows:
                curr_c=central_start or 0; curr_b=branch_start or 0; display=[]
                for item in library_rows:
                    c=[];b=[]
                    for _ in range(item["Received"]):curr_c+=1;c.append(str(curr_c));curr_b+=1;b.append(str(curr_b))
                    display.append({**item,"Central Accession No":", ".join(c),"Branch Accession No":", ".join(b)})
                preview=pd.DataFrame(display); st.dataframe(preview.drop(columns=["Sheet Row"]),use_container_width=True,hide_index=True)
                if st.button("💾 Google Sheet (U & V தூண்களில்) சேமி",use_container_width=True):
                    cells=[]
                    for item in display:cells.extend([Cell(row=item["Sheet Row"],col=21,value=item["Central Accession No"]),Cell(row=item["Sheet Row"],col=22,value=item["Branch Accession No"])])
                    if cells:sheet_vendor_wise.update_cells(cells)
                    st.success("✅ சேர்க்கை எண்கள் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                download_panel(preview.drop(columns=["Sheet Row"]),safe_name(selected)+"_Accession_Register","Accession Register")
            else:st.warning("⚠️ இந்த நூலகத்திற்குப் புத்தகங்கள் எதுவும் இல்லை.")
        except Exception as e:st.error(f"❌ பிழை ஏற்பட்டது: {e}")
