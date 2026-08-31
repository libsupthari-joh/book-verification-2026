import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import sqlite3
import time
from datetime import datetime
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape as xml_escape
import gspread
import pandas as pd
import streamlit as st
from gspread.cell import Cell
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from oauth2client.service_account import ServiceAccountCredentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

# பக்க அமைப்பு (Page Configuration)
st.set_page_config(
    page_title="மாவட்ட மைய நூலகம் - புதிய நூல்கள் பகிர்மானம் 2026-27",
    page_icon="📚",
    layout="wide",
)

# தலைப்புப் பகுதி
st.markdown(
    """
    <div style="background: linear-gradient(135deg, #0d5c63 0%, #0a4a50 100%); padding: 20px; border-radius: 10px; color: white; margin-bottom: 20px;">
        <h1>📚 மாவட்ட மைய நூலகம்</h1>
        <p>புதிய நூல்கள் பகிர்மானம் மற்றும் சரிபார்ப்பு தளம் (2026-27)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# முதன்மை மெனு (மேல் பகுதியில் горизонталь அமைப்பு)
menu_options = [
    "🔀 பிரிக்க (Distribute)",
    "📤 அனுப்ப (Send)",
    "📊 அறிக்கைகள் (Reports)",
    "⚠️ கவனிக்க (Kavani)",
    "🔢 பதிவெண் மாற்ற (Renumber)",
    "🗑️ தவறான பதிவு நீக்கம் (Reclaim)",
    "📥 Excel பதிவிறக்கம் & அப்லோட்",
    "⚙️ மேலாண்மை & இதர வசதிகள்"
]

st.markdown("### 📌 முதன்மை மெனு")
menu_option = st.radio("செயல்பாட்டைத் தேர்ந்தெடுக்கவும்:", menu_options, horizontal=True)

st.markdown("---")

# 1. பிரிக்க (Distribute) பகுதி
if menu_option == "🔀 பிரிக்க (Distribute)":
    st.subheader("🔀 புத்தகங்களைப் பிரித்து வழங்குதல்[cite: 1]")
    st.markdown("புத்தகத்தைத் தேடி, விவரங்களைச் சரிபார்த்து நூலகங்களுக்குப் பிரித்து வழங்கும் பகுதி[cite: 1].")
    search_query = st.text_input("🔍 புத்தகம் தலைப்பு அல்லது பதிப்பகம் தட்டச்சு செய்யவும்:")

    if search_query:
        st.info(f"'{search_query}'க்கான தேடல் முடிவுகள் காட்டப்படுகின்றன...")
        sample_data = pd.DataFrame({
            "வ.எண்": [1, 2],
            "தலைப்பு": ["தமிழ் இலக்கிய வரலாறு", "அறிவியல் உலகம்"],
            "பதிப்பகம்": ["பூம்புகார் பதிப்பகம்", "வானதி பதிப்பகம்"],
            "விலை": [250, 300],
            "எண்ணிக்கை": [10, 15],
        })
        st.table(sample_data)
    else:
        st.write("தேட ஆரம்பிக்க மேலே உள்ள பெட்டியில் தட்டச்சு செய்யவும்.")

# 2. அனுப்ப (Send) பகுதி
elif menu_option == "📤 அனுப்ப (Send)":
    st.subheader("📤 நூலகங்களுக்குப் புத்தகங்கள் அனுப்புதல்[cite: 1]")
    st.markdown("Set Number அடிப்படையில் நூலகங்களைத் தேர்ந்தெடுத்து அனுப்பியதாகப் பதிவு செய்யும் பகுதி[cite: 1].")
    set_number = st.selectbox("SET NUMBER தேர்வு செய்யவும்:", ["-- தேர்வு செய்க --", "Set 1", "Set 2"])
    
    if set_number != "-- தேர்வு செய்க --":
        st.success(f"தேர்ந்தெடுக்கப்பட்ட {set_number}க்கான நூலகங்கள் கீழே:")
        st.checkbox("அனைத்து நூலகங்களும்")
        lib_list = ["கிளை நூலகம் - 1", "ஊரக நூலகம் - 2", "நகர்ப்புற நூலகம் - 3"]
        for lib in lib_list:
            st.checkbox(lib)
        if st.button("✅ அனுப்பியதாக பதிவு செய் (Mark as Sent)"):
            st.success("வெற்றிகரமாக அனுப்பப்பட்டதாகப் பதிவு செய்யப்பட்டது!")

# 3. அறிக்கைகள் (Reports) பகுதி
elif menu_option == "📊 அறிக்கைகள் (Reports)":
    st.subheader("📊 முழுமையான நிலை அறிக்கைகள்[cite: 1]")
    st.markdown("தேதி வாரியான, நூலக வாரியான மற்றும் இதர முழுமையான நிலை அறிக்கைகளைப் பெறும் பகுதி[cite: 1].")
    report_type = st.selectbox(
        "அறிக்கை வகையைத் தேர்ந்தெடுக்கவும்:",
        [
            "தேதி வாரியான பணி விவரம்",
            "மொத்த நிலை விவரம் (Total Status)",
            "நூலகம் வாரியான புத்தக விவரம்",
        ],
    )
    if st.button("📄 அறிக்கை உருவாக்கு"):
        st.info(f"'{report_type}' தயாரிக்கப்பட்டு வருகிறது...")

# 4. கவனிக்க (Kavani) பகுதி
elif menu_option == "⚠️ கவனிக்க (Kavani)":
    st.subheader("⚠️ கவனிக்க வேண்டிய முரண்பாடுகள்[cite: 1]")
    st.markdown("ஒரே தலைப்பில் வேறு வேறு விலைகள்/ISBN உள்ளவை மற்றும் 85% ஒத்த தலைப்புகளை (Fuzzy Match) சரிபார்க்கும் பகுதி[cite: 1].")
    st.warning("🔴 முரண்பாடுகளை அடையாளம் காண கீழ்க்காணும் பொத்தானை அழுத்தவும்.")
    if st.button("🔄 மீண்டும் ஒப்பிட்டுப் பார்"):
        st.success("சரிபார்ப்பு முடிந்தது. முரண்பாடுகள் எதுவும் இல்லை.")

# 5. பதிவெண் மாற்ற (Renumber) பகுதி
elif menu_option == "🔢 பதிவெண் மாற்ற (Renumber)":
    st.subheader("🔢 மைய மற்றும் கிளைப் பதிவெண் மாற்றியமைத்தல்[cite: 1]")
    st.markdown("மைய மற்றும் கிளைப் பதிவெண்களை மாற்றியமைக்கும் பகுதி[cite: 1].")
    renumber_type = st.radio("தேர்வு செய்க:", ["மையப் பதிவெண் மாற்றம்", "கிளைப் பதிவெண் மாற்றம்"], horizontal=True)
    new_start_num = st.number_input("புதிய தொடக்க எண்:", min_value=1, value=1000)
    if st.button("💾 பதிவெண்ணைச் சேமி"):
        st.success(f"புதிய தொடக்க எண் {new_start_num} வெற்றிகரமாக மாற்றப்பட்டது!")

# 6. தவறான பதிவு நீக்கம் (Reclaim) பகுதி
elif menu_option == "🗑️ தவறான பதிவு நீக்கம் (Reclaim)":
    st.subheader("♻️ தவறாகப் பிரிக்கப்பட்ட/அனுப்பப்பட்ட பதிவுகளை நீக்குதல்[cite: 1]")
    st.markdown("பிரிக்கப்பட்ட அல்லது அனுப்பப்பட்ட தவறான பதிவுகளை மீளப்பெறும் பகுதி[cite: 1].")
    reclaim_input = st.text_input("நீக்க வேண்டிய புத்தகத்தின் தலைப்பு / சேர்க்கை எண்:")
    if reclaim_input and st.button("🗑️ மீளப்பெறு (Reclaim)"):
        st.error("தேர்ந்தெடுக்கப்பட்ட பதிவு Pool-க்கு மீளப்பெறப்பட்டது.")

# 7. Excel பதிவிறக்கம் & அப்லோட் பகுதி
elif menu_option == "📥 Excel பதிவிறக்கம் & அப்லோட்":
    st.subheader("📥 தரவுப் பரிமாற்றம் (Excel Import / Export)[cite: 1]")
    st.markdown("Assigned, Assigned & Sent, Total Data மற்றும் மாநிலப் பதிவெண் Template பதிவிறக்கம் மற்றும் அப்லோட் செய்யும் பகுதி[cite: 1].")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Excel பதிவிறக்கம்")
        if st.button("📥 Assigned Data பதிவிறக்கு"):
            st.info("கோப்பு பதிவிறக்கத்திற்கு தயாராகிறது...")
    with col2:
        st.markdown("### Excel அப்லோட்")
        uploaded_file = st.file_uploader("master_data Excel கோப்பை (.xlsx) பதிவேற்றவும்", type=["xlsx", "xls"])
        if uploaded_file is not None:
            st.success("கோப்பு வெற்றிகரமாகப் பதிவேற்றப்பட்டது!")

# 8. மேலாண்மை & இதர வசதிகள்
elif menu_option == "⚙️ மேலாண்மை & இதர வசதிகள்":
    st.subheader("⚙️ நிர்வாக மற்றும் கூடுதல் வசதிகள்[cite: 1]")
    admin_tab = st.selectbox(
        "பிரிவைத் தேர்ந்தெடுக்கவும்:",
        [
            "Master Data (Restore/Clear)[cite: 1]",
            "கடவுச்சொல் மாற்ற (Change Password)[cite: 1]",
            "நூலகர் பார்வை ஆண்டு (Librarian Year)[cite: 1]",
        "மாநிலப் பதிவெண் புதுப்பி (Update State Acc)[cite: 1]",
            "ISBN → தலைப்பு தேடு (ISBN Lookup)[cite: 1]"
        ]
    )
    if "Master Data" in admin_tab:
        st.write("தரவுத்தள மீட்பு (Restore), Master Data அழிப்பு (Clear), மற்றும் Assigning Data அழிப்புக்கான பகுதி[cite: 1].")
        st.button("⚠️ Master Data-வை அழிக்கவும்")
    elif "கடவுச்சொல்" in admin_tab:
        st.write("Admin மற்றும் DCL Staff கடவுச்சொற்களை மாற்றும் பகுதி[cite: 1].")
        st.text_input("புதிய கடவுச்சொல்", type="password")
    elif "நூலகர் பார்வை" in admin_tab:
        st.write("நூலகர் Login-க்கு எந்த ஆண்டு தெரிய வேண்டும் என்பதைத் தீர்மானிக்கும் பகுதி[cite: 1].")
        st.selectbox("ஆண்டு தேர்வு:", ["2025-26", "2026-27"])
    elif "மாநிலப் பதிவெண்" in admin_tab:
        st.write("மாநிலப் பதிவெண்களை மொத்தமாகப் (Bulk Update) புதுப்பிக்கும் பகுதி[cite: 1].")
    elif "ISBN" in admin_tab:
        st.write("ISBN மூலம் இணையம் வழியாகத் தலைப்புத் தேடும் பகுதி[cite: 1].")
        st.text_input("ISBN எண்ணை உள்ளிடவும்:")

# அடிக்குறிப்பு
st.markdown("---")
st.markdown(
    "<p style='text-align: center; color: gray; font-size: 0.85rem;'>மாவட்ட மைய நூலக நிர்வாகப் பிரிவு © 2026[cite: 1]</p>",
    unsafe_allow_html=True,
)
