import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
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
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5">
<style>
:root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--gold:#f59e0b}
html,body,[class*="css"]{-webkit-tap-highlight-color:transparent}
.stApp{background:radial-gradient(circle at 8% 8%,rgba(0,188,212,.12),transparent 28%),linear-gradient(135deg,#eef5ff,#fbfdff 50%,#eaf2ff)}
[data-testid="stHeader"]{background:transparent}[data-testid="stToolbar"]{visibility:hidden}
h1{font-size:20px!important;padding:14px 16px!important;border-radius:16px;color:#fff!important;background:linear-gradient(135deg,#071a38,#1565c0 58%,#00acc1);box-shadow:0 6px 0 #041126,0 14px 24px #071a3833;text-shadow:2px 3px 3px #0006;text-align:center;margin-bottom:16px!important;line-height:1.4}
h2,h3{color:#092653!important}
.profile-card,.book-info-card,.login-card{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;box-shadow:5px 5px 0 #c8d8ed,0 8px 18px #08265318}
.profile-card{padding:12px 16px;border-radius:14px;font-size:14px;line-height:1.7}
.book-info-card{border-left:7px solid #1565c0;border-radius:14px;padding:14px 16px;line-height:1.9;margin:10px 0 16px;font-size:15px;word-break:break-word}
.total-qty{color:#0b3d91;font-size:18px;font-weight:900}
.not-received-card{background:linear-gradient(145deg,#fff8e1,#fff3c4);border-left:7px solid #f59e0b;border-radius:12px;padding:12px 16px;color:#8a4b00;font-size:16px;font-weight:800;box-shadow:4px 4px 0 #ead6б9b;margin:10px 0}
.stButton>button,.stDownloadButton>button{min-height:50px!important;border-radius:13px!important;font-size:15px!important;font-weight:800!important;color:#fff!important;background:linear-gradient(145deg,#1976d2,#082b68)!important;box-shadow:0 4px 0 #041b42,0 8px 15px #082b6830!important;border:0!important;transition:.2s!important;width:100%!important;white-space:normal!important}
.stButton>button:hover,.stDownloadButton>button:hover{transform:translateY(-2px);filter:brightness(1.1)}
[data-testid="stMetric"]{background:linear-gradient(145deg,#fff,#eef5ff);border:1px solid #cfe0f5;border-radius:14px;box-shadow:4px 4px 0 #c8d8ed;padding:10px}
div[data-testid="stTextInput"] label,div[data-testid="stSelectbox"] label,div[data-testid="stNumberInput"] label{font-weight:700!important;color:#092653!important}
div[data-baseweb="select"]>div{min-height:48px!important;font-size:15px!important}
input[type="number"],input[type="text"],input[type="password"]{min-height:44px!important;font-size:15px!important}
.login-card{text-align:center;border-radius:26px;padding:34px 26px 30px;position:relative;overflow:hidden}
.login-card .login-icon{font-size:52px}.login-card .login-badge{display:inline-block;margin-top:10px;padding:5px 16px;border-radius:999px;background:linear-gradient(135deg,#071a38,#1565c0 60%,#00acc1);color:#fff;font-weight:800}.login-card h2{margin:16px 0 6px;font-size:22px}.login-card p{margin:0;color:#5b7aa3;font-size:13.5px;font-weight:600}

/* ---------- மேம்படுத்தப்பட்ட Icon/Emoji காட்சி ---------- */
html,body,.stApp,button,input,textarea,select,label,td,th,
div[data-baseweb="select"]>div,[data-testid="stMetric"]{
  font-family:"Segoe UI","Noto Sans","Noto Sans Tamil","Noto Color Emoji","Segoe UI Emoji","Apple Color Emoji","Twemoj Mozilla",sans-serif;
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibizability}
.stButton>button,.stDownloadButton>button{font-family:"Segoe UI","Noto Color Emoji","Segoe UI Emoji","Apple Color Emoji",sans-serif;letter-spacing:.2px}
button,label,td,th{font-variant-emoji:emoji;font-kerning:normal}
.bi{display:inline-block;font-size:1.5em;line-height:1;vertal-align:-4px;margin-right:8px;filter:drop-shadow(0 1px 1px rgba(0,0,0,.18)}
.sec{color:#092653!important;font-size:1.14rem!important;font-weight:800!important;margin:1em 0 .55em!important;display:flex!important;align-itemas:center!important}
.dl-title{font-weight:800;color:#092653;margin:.9em 0 .4em;font-size:1.05rem}
@media(max-width:640px){h1{font-size:17px!important}.block-container{padding:12px 10px!important}[data-testid="column"]{width:100%!important;flex:1 1 100%!important;min-width:100%!important;margin-bottom:8px!important}.bi{font-size:1.3em}.sec{font-size:1.02rem!important}}
</style>
""",
    unsafe_allow_html=True,
)
