import streamlit as str_lit
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from datetime import datetime
import re
import time

# 1. Streamlit பக்க அமைப்பு
str_lit.set_page_config(page_title="2026 புதிய நூல்கள் விநியோகம்", layout="wide", initial_sidebar_state="expanded")

# 🎨 பக்கவாட்டு மெனு பட்டன்களுக்கு தனித்துவமான வண்ணங்களுடன் கூடிய 3D CSS மற்றும் JS குறியீடு
def get_custom_css():
    return """
    <style>
    /* பக்கவாட்டு மெனு பட்டன்களின் பொதுவான 3D வடிவமைப்பு */
    div[data-testid="stSidebar"] button {
        width: 100% !important;
        text-align: left !important;
        padding: 14px 18px !important;
        margin-bottom: 12px !important;
        border-radius: 12px !important;
        font-weight: 800 !important;
        font-size: 15px !important;
        border: none !important;
        transition: all 0.25s ease-in-out !important;
        box-shadow: 0 5px 0 rgba(0,0,0,0.2), 0 7px 10px rgba(0,0,0,0.15) !important;
    }
    div[data-testid="stSidebar"] button p { color: white !important; }
    
    /* ஒவ்வொரு பட்டனுக்கும் தனித்தனி வண்ணங்கள் */
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(1) button { background: linear-gradient(135deg, #2e7d32, #1b5e20) !important; }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(2) button { background: linear-gradient(135deg, #7b1fa2, #4a148c) !important; }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(3) button { background: linear-gradient(135deg, #e65100, #bf360c) !important; }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(4) button { background: linear-gradient(135deg, #01579b, #002f6c) !important; }
    div[data-testid="stSidebar"] div[data-testid="stVerticalBlock"] > div:nth-of-type(5) button { background: linear-gradient(135deg, #37474f, #212121) !important; }
    
    /* மவுஸ் வைக்கும்போது (Hover) மற்றும் கிளிக் செய்யும்போது */
    div[data-testid="stSidebar"] button:hover {
        transform: translateY(-2px);
        box-shadow: 0 7px 0 rgba(0,0,0,0.25), 0 10px 15px rgba(0,0,0,0.2) !important;
        filter: brightness(1.1);
    }
    div[data-testid="stSidebar"] button:active {
        transform: translateY(3px);
        box-shadow: 0 2px 0 rgba(0,0,0,0.3) !important;
    }
    </style>
    """

str_lit.markdown(get_custom_css(), unsafe_allow_html=True)

# Session State
if 'current_page' not in str_lit.session_state:
    str_lit.session_state['current_page'] = "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"

# 📌 Sidebar Navigation (பட்டன்கள்)
str_lit.sidebar.markdown("### 👤 **பயனர் கணக்கு**")
if str_lit.sidebar.button("🚪 வெளியேறு (Logout)"):
    str_lit.session_state['logged_in'] = False
    str_lit.rerun()

str_lit.sidebar.markdown("---")
str_lit.sidebar.markdown("### 📌 **முதன்மைப் பணிகள்**")

if str_lit.sidebar.button("📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"):
    str_lit.session_state['current_page'] = "📥 1. பெறப்பட்ட நூல்கள் சரிபார்ப்பு"
if str_lit.sidebar.button("🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)"):
    str_lit.session_state['current_page'] = "🔄 2. Google Sheet தரவு ஒத்திசைவு (Sync)"
if str_lit.sidebar.button("🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)"):
    str_lit.session_state['current_page'] = "🏢 3. மொத்த பதிப்பாளர் விவரங்கள் (480)"
if str_lit.sidebar.button("🏛️ 4. நூலகத்திற்கு விநியோகம் (103)"):
    str_lit.session_state['current_page'] = "🏛️ 4. நூலகத்திற்கு விநியோகம் (103)"
if str_lit.sidebar.button("⚙️ 5. Accession எண்கள் மேலாண்மை"):
    str_lit.session_state['current_page'] = "⚙️ 5. Accession எண்கள் மேலாண்மை"

# பிரதான பக்கம்
str_lit.title(f"பணி: {str_lit.session_state['current_page']}")
str_lit.write("தற்போதைய பக்கத்திற்கான பணிகள் இங்கே செயல்படும்.")
