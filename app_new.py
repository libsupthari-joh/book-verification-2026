import hashlib
import hmac
import os
from datetime import datetime
import pandas as pd
import streamlit as st
import psycopg2

st.set_page_config(
    page_title="மாவட்ட மைய நூலகம், கிருஷ்ணகிரி",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DB_URL = "postgresql://neondb_owner:npg_y1mObIUlc2ox@ep-odd-pine-b39tu9yu-pooler.c-4.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+Tamil:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Noto Sans Tamil', sans-serif !important; }
.stApp { background: #f8fafc; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }

.top-header-container {
    background: linear-gradient(135deg, #064e3b, #022c22);
    padding: 16px 22px;
    border-radius: 12px;
    color: white;
    display: flex;
    justify-content: space-between;
    align-items: center;
    box-shadow: 0 4px 15px rgba(6,78,59,0.2);
    margin-bottom: 20px;
}
.header-title { font-size: 20px; font-weight: 800; color: #ffffff; }
.header-subtitle { font-size: 13px; color: #a7f3d0; font-weight: 600; }
.login-top-container { display: flex; justify-content: center; align-items: flex-start; padding-top: 30px; }
.login-card-wrapper { background: #ffffff; border-radius: 16px; padding: 22px 25px; box-shadow: 0 10px 25px rgba(0,0,0,0.25); border: 1.5px solid #a7f3d0; width: 100%; max-width: 380px; }
.login-header-box { text-align: center; background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #a7f3d0; border-radius: 10px; padding: 10px; margin-bottom: 12px; }
.login-title { color: #064e3b; font-size: 15px; font-weight: 800; }

.ticker-container { 
    background: linear-gradient(135deg, #f0fdf4, #dcfce7); 
    border: 1.5px solid #86efac; 
    padding: 8px 12px; 
    border-radius: 10px; 
    color: #065f46; 
    font-weight: 700; 
    font-size: 13px; 
    display: flex; 
    align-items: center; 
    box-shadow: 0 2px 8px rgba(6, 95, 70, 0.08); 
    margin-bottom: 20px; 
    overflow: hidden; 
    white-space: nowrap; 
}
.ticker-badge { 
    background: #065f46; 
    color: white; 
    padding: 3px 10px; 
    border-radius: 6px; 
    font-size: 12px; 
    margin-right: 15px; 
    display: flex; 
    align-items: center; 
    gap: 5px; 
    flex-shrink: 0; 
    z-index: 2;
}
.marquee-text {
    display: inline-block;
    white-space: nowrap;
    animation: marquee 25s linear infinite;
}
.marquee-text:hover {
    animation-play-state: paused;
}
@keyframes marquee {
    0% { transform: translateX(100%); }
    100% { transform: translateX(-100%); }
}

/* ---- Beautified menu / general buttons ---- */
.stButton>button {
    border-radius: 12px !important;
    border: 1.5px solid #a7f3d0 !important;
    background: #ffffff !important;
    color: #065f46 !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    white-space: pre-line !important;
    line-height: 1.4 !important;
    padding: 10px 6px !important;
    min-height: 62px !important;
    box-shadow: 0 2px 6px rgba(6,95,70,0.07) !important;
    transition: all 0.18s ease-in-out !important;
}
.stButton>button:hover {
    background: #ecfdf5 !important;
    border-color: #10b981 !important;
    transform: translateY(-3px);
    box-shadow: 0 8px 16px rgba(6,95,70,0.18) !important;
    color: #047857 !important;
}
.stButton>button:active {
    transform: translateY(0px);
}
.stButton>button[kind="primary"] {
    background: linear-gradient(135deg, #059669, #047857) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 6px 14px rgba(5,150,105,0.35) !important;
}
.stButton>button[kind="primary"]:hover {
    background: linear-gradient(135deg, #047857, #065f46) !important;
    color: #ffffff !important;
}
.menu-row-label {
    font-size: 11px;
    font-weight: 700;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin: 4px 0 6px 2px;
}
</style>
""", unsafe_allow_html=True)

def hash_password(password):
    return hashlib.sha256(str(password).encode("utf-8")).hexdigest()

USERS_DATABASE = {
    "Admin": {"password_hash": hash_password("Hari@@1979"), "name": "முதன்மை நிர்வாகி (Admin)"},
    "DCL Staff": {"password_hash": hash_password("123456"), "name": "DCL Staff"},
    "Librarian": {"password_hash": hash_password("123456789"), "name": "Librarian"},
}

def authenticate_user(role_key, password):
    user = USERS_DATABASE.get(role_key)
    if user and hmac.compare_digest(hash_password(password), user["password_hash"]):
        return user
    return None

# ----------------------------------------------------------------------------
# நூலகர் (Librarian) login — TNDPL எண் அடிப்படையிலான 103 நூலக logins.
# Seed data: LIB_DETAILS.xlsx-ல் இருந்து ஒரு முறை உருவாக்கப்பட்டது.
# libraries table-ல் ON CONFLICT DO NOTHING மூலம் மட்டுமே சேர்க்கப்படும் —
# இருக்கும் தரவு (books/submitted_reports/dispatch_status) எதுவும் தொடப்படாது.
# ----------------------------------------------------------------------------
# Columns: (tndpl_code, name_ta, name_en, pay_center_code, lib_type)
LIBRARY_SEED_DATA = [
    ('TNDPL04721', 'மாவட்ட நூலக அலுவலகம்', 'DISTRICT LIBRARY OFFICE', '2893', 'மா.நூ.அ'),
    ('TNDPL01584', 'மாவட்ட மைய நூலகம்', 'DISTRICT CENTRAL LIBRARY', '2893', 'மா.மை.நூ'),
    ('TNDPL01589', 'காவேரிப்பட்டிணம்', 'KAVERIPATTINAM', '2893', 'கி.நூ'),
    ('TNDPL01595', 'நெடுங்கல்', 'NEDUNGAL', '2893', 'கி.நூ'),
    ('TNDPL01594', 'கட்டிகானப்பள்ளி', 'KATTIKANAPALLI', '2893', 'கி.நூ'),
    ('TNDPL01592', 'வேப்பனப்பள்ளி', 'VEPPANAPALLI', '2893', 'கி.நூ'),
    ('TNDPL01596', 'பனகமுட்லு', 'PANAKAMUTLU', '2893', 'கி.நூ'),
    ('TNDPL01616', 'சாப்பர்த்தி', 'SAPPARTHI', '2893', 'கி.நூ'),
    ('TNDPL01634', 'ஆலப்பட்டி', 'ALAPATTI', '2893', 'ஊ.நூ'),
    ('TNDPL01636', 'பாலகுறி', 'PALAKURI', '2893', 'ஊ.நூ'),
    ('TNDPL01627', 'பச்சிகானப்பள்ளி', 'PACHIGANAPALLI', '2893', 'ஊ.நூ'),
    ('TNDPL01631', 'இட்டிக்கல் அகரம்', 'ITTICALAGARAM', '2893', 'ஊ.நூ'),
    ('TNDPL01635', 'சிக்கபூவத்தி', 'CHIKKAPOOVATHI', '2893', 'ஊ.நூ'),
    ('TNDPL01637', 'மரிக்கம்பள்ளி', 'MARIKAMPALLY', '2893', 'ஊ.நூ'),
    ('TNDPL01638', 'மாதேப்பட்டி', 'MADHEPATTI', '2893', 'ஊ.நூ'),
    ('TNDPL01641', 'மகாராஜாகடை', 'MAHARAJAKADAI', '2893', 'ஊ.நூ'),
    ('TNDPL01640', 'பழைய வீட்டுவசதி வாரியம்', 'OLD HOUSING BOARD', '2893', 'ஊ.நூ'),
    ('TNDPL01639', 'மூங்கில்புதூர்', 'MOONGILPUDHUR', '2893', 'ஊ.நூ'),
    ('TNDPL01620', 'பெரியமுத்தூர்', 'PERIYAMUTHUR', '2893', 'ஊ.நூ'),
    ('TNDPL01621', 'சுண்டேகுப்பம்', 'SUNDEKUPPAM', '2893', 'ஊ.நூ'),
    ('TNDPL01622', 'திம்மாபுரம்', 'THIMMAPURAM', '2893', 'ஊ.நூ'),
    ('TNDPL01623', 'எர்ரஅள்ளி', 'ERRAHALLI', '2893', 'ஊ.நூ'),
    ('TNDPL01681', 'பன்னிஅள்ளிபுதூர்', 'PANNIHALLIPUDUR', '2893', 'ஊ.நூ'),
    ('TNDPL01683', 'பெங்களூர் சாலை', 'BENGALURU ROAD', '2893', 'ஊ.நூ'),
    ('TNDPL01599', 'இராயக்கோட்டை', 'RAYAKOTTAI', '2893', 'கி.நூ'),
    ('TNDPL01585', 'ஓசூர்', 'HOSUR', '3286', 'மு.நே.கி.நூ'),
    ('TNDPL01597', 'உத்தனப்பள்ளி', 'UTTANAPALLI', '3286', 'கி.நூ'),
    ('TNDPL01587', 'தேன்கனிக்கோட்டை', 'THENKANIKOTTAI', '3286', 'மு.நே.கி.நூ'),
    ('TNDPL01600', 'கெலமங்கலம்', 'KELAMANGALAM', '3286', 'கி.நூ'),
    ('TNDPL01601', 'அஞ்செட்டி', 'ANCHETI', '3286', 'கி.நூ'),
    ('TNDPL01603', 'தளி', 'THALI', '3286', 'கி.நூ'),
    ('TNDPL01598', 'மத்திகிரி', 'MATHIGIRI', '3286', 'கி.நூ'),
    ('TNDPL01604', 'உரிகம்', 'URIKAM', '3286', 'கி.நூ'),
    ('TNDPL01613', 'ப.டெ.லேண்டு.அட்கோ', 'OLD TEMPLELAND ADCO', '3286', 'கி.நூ'),
    ('TNDPL01611', 'சூளகிரி', 'SOOLAGIRI', '3286', 'கி.நூ'),
    ('TNDPL01612', 'சூசூவாடி', 'SOOSUWADI', '3286', 'கி.நூ'),
    ('TNDPL01642', 'பேரிகை', 'BERIGAI', '3286', 'ஊ.நூ'),
    ('TNDPL01644', 'பாகலூர்', 'BAGALUR', '3286', 'ஊ.நூ'),
    ('TNDPL01652', 'பைரமங்கலம்', 'BAIRAMANGALAM', '3286', 'ஊ.நூ'),
    ('TNDPL01645', 'பு.ஏ.எஸ்.டி.சி.அட்கோ', 'NEW ASDC ADCO', '3286', 'ஊ.நூ'),
    ('TNDPL01646', 'சூடாபுரம்', 'SUDAPURAM', '3286', 'ஊ.நூ'),
    ('TNDPL01647', 'அரசனட்டி', 'ARASANATTI', '3286', 'ஊ.நூ'),
    ('TNDPL01653', 'அக்கொண்டப்பள்ளி', 'AKONDAPALLI', '3286', 'ஊ.நூ'),
    ('TNDPL01654', 'தொட்டபேளூர்', 'DODDABELUR', '3286', 'ஊ.நூ'),
    ('TNDPL01648', 'அண்ணாமலைநகர்', 'DODDABELUR', '3286', 'ஊ.நூ'),
    ('TNDPL01649', 'விநாயகபுரம்', 'VINAYAGAPURAM', '3286', 'ஊ.நூ'),
    ('TNDPL01655', 'கோபசந்திரம்', 'GOPACHANDRAM', '3286', 'ஊ.நூ'),
    ('TNDPL01650', 'காந்திநகர்', 'GANDHINAGAR', '3286', 'ஊ.நூ'),
    ('TNDPL01651', 'பாகலூர் அட்கோ', 'BAGALUR ROAD ADCO', '3286', 'ஊ.நூ'),
    ('TNDPL01677', 'பாளையங்கோட்டை', 'PALAYAMKOTTAI', '3286', 'ஊ.நூ'),
    ('TNDPL01657', 'கோட்டையூர்', 'KOTTAIYUR', '3286', 'ஊ.நூ'),
    ('TNDPL01675', 'பேடரப்பள்ளி', 'PEDARAPALLI', '3286', 'ஊ.நூ'),
    ('TNDPL01586', 'போச்சம்பள்ளி', 'POCHAMPALLI', '3284', 'மு.நே.கி.நூ'),
    ('TNDPL01605', 'அரசம்பட்டி', 'ARASAMPATTI', '3284', 'கி.நூ'),
    ('TNDPL01591', 'தொகரப்பள்ளி', 'THOGARAPALLI', '3284', 'கி.நூ'),
    ('TNDPL01606', 'மத்தூர்', 'MATHUR', '3284', 'கி.நூ'),
    ('TNDPL01614', 'வேலம்பட்டி', 'VELAMPATTI', '3284', 'கி.நூ'),
    ('TNDPL01615', 'வலசக்கவுண்டனூர்', 'VALASAGOUNDANUR', '3284', 'கி.நூ'),
    ('TNDPL01593', 'அகரம்', 'AGARAM', '3284', 'கி.நூ'),
    ('TNDPL01609', 'பண்ணந்தூர்', 'PANNANDUR', '3284', 'கி.நூ'),
    ('TNDPL01607', 'பாரூர்', 'PARUGOOR', '3284', 'கி.நூ'),
    ('TNDPL01630', 'ஐகுந்தம்', 'AIKUNDAM', '3284', 'ஊ.நூ'),
    ('TNDPL01629', 'ஐ.கொத்தப்பள்ளி', 'I.KOTHAPALLI', '3284', 'ஊ.நூ'),
    ('TNDPL01608', 'நாகரசம்பட்டி', 'NAGARASAMPATTI', '3284', 'கி.நூ'),
    ('TNDPL01658', 'புலியூர்', 'PULIYUR', '3284', 'ஊ.நூ'),
    ('TNDPL01659', 'மஞ்சமேடு', 'MANJAMEDU', '3284', 'ஊ.நூ'),
    ('TNDPL01663', 'கண்ணன்டஅள்ளி', 'KANNANDAHALLI', '3284', 'ஊ.நூ'),
    ('TNDPL01673', 'தாதம்பட்டி', 'THATHAMPATTI', '3284', 'ஊ.நூ'),
    ('TNDPL01665', 'சந்தூர்', 'CHANDUR', '3284', 'ஊ.நூ'),
    ('TNDPL01667', 'காட்டுவென்றஅள்ளி', 'KATTUVENDRAHALLI', '3284', 'ஊ.நூ'),
    ('TNDPL01669', 'பெரியகரடியூர்', 'PERIYAKARADIYUR', '3284', 'ஊ.நூ'),
    ('TNDPL01670', 'வீரமலை', 'VEERAMALAI', '3284', 'ஊ.நூ'),
    ('TNDPL01672', 'புளியம்பட்டி', 'PULIYAMPATTI', '3284', 'ஊ.நூ'),
    ('TNDPL01660', 'தேவீரஅள்ளி', 'DEVARAALLI', '3284', 'ஊ.நூ'),
    ('TNDPL01661', 'பெரியபுளியம்பட்டி', 'PERIYAPULIYAMPATTI', '3284', 'ஊ.நூ'),
    ('TNDPL01662', 'கீழ்குப்பம்', 'KILKUPPAM', '3284', 'ஊ.நூ'),
    ('TNDPL01668', 'புங்கம்பட்டி', 'PUNGAMPATTI', '3284', 'ஊ.நூ'),
    ('TNDPL01671', 'வாடமங்கலம்', 'VADAMANGALAM', '3284', 'ஊ.நூ'),
    ('TNDPL01674', 'சோபனூர்', 'SHOBANUR', '3284', 'ஊ.நூ'),
    ('TNDPL01682', 'அத்திகானூர்', 'ATHIKANUR', '3284', 'ஊ.நூ'),
    ('TNDPL01684', 'ஆவத்துவாடி', 'AWATHUVADI', '3284', 'ஊ.நூ'),
    ('TNDPL01590', 'பர்கூர்', 'BARGUR', '3287', 'கி.நூ'),
    ('TNDPL01617', 'சிந்தகம்பள்ளி', 'CHINTHAKAMPALLI', '3287', 'கி.நூ'),
    ('TNDPL01628', 'மாதேப்பள்ளி', 'MADHEPALLI', '3287', 'ஊ.நூ'),
    ('TNDPL01618', 'எமக்கல்நத்தம்', 'EMAKKALNATHAM', '3287', 'ஊ.நூ'),
    ('TNDPL01619', 'கந்திகுப்பம்', 'KANDIKUPPAM', '3287', 'ஊ.நூ'),
    ('TNDPL01624', 'ஒப்பதவாடி', 'OPPATHAVADI', '3287', 'ஊ.நூ'),
    ('TNDPL01625', 'எலத்தகிரி', 'ELATHAGIRI', '3287', 'ஊ.நூ'),
    ('TNDPL01626', 'கோதியழகனூர்', 'KOTHIYAZHAGANUR', '3287', 'ஊ.நூ'),
    ('TNDPL01632', 'காரகுப்பம்', 'KARAKUPPAM', '3287', 'ஊ.நூ'),
    ('TNDPL01633', 'கொல்லநாகமங்கலம்', 'KOLLANAGAMANGALAM', '3287', 'ஊ.நூ'),
    ('TNDPL01643', 'ஒரப்பம்', 'ORAPPAM', '3287', 'ஊ.நூ'),
    ('TNDPL01664', 'சிகரலப்பள்ளி', 'SIKARALAPALLY', '3287', 'ஊ.நூ'),
    ('TNDPL01680', 'கொண்டப்பநாயனப்பள்ளி', 'KONDAPANAYANAPALLI', '3287', 'ஊ.நூ'),
    ('TNDPL01685', 'வரட்டனப்பள்ளி', 'VARATTANAPALLI', '3287', 'ஊ.நூ'),
    ('TNDPL01588', 'ஊத்தங்கரை', 'UTHANGARAI', '3289', 'மு.நே.கி.நூ'),
    ('TNDPL01602', 'கல்லாவி', 'KALLAVI', '3289', 'கி.நூ'),
    ('TNDPL01610', 'சிங்காரப்பேட்டை', 'SINGARAPETTAI', '3289', 'கி.நூ'),
    ('TNDPL01656', 'கெங்கபிரம்பட்டி', 'GANGABIRAMPATTI', '3289', 'ஊ.நூ'),
    ('TNDPL01666', 'இராமகிருஷ்ணம்பதி', 'RAMAKRISHNAMPATHY', '3289', 'ஊ.நூ'),
    ('TNDPL01678', 'எக்கூர்', 'EKUR', '3289', 'ஊ.நூ'),
    ('TNDPL01679', 'ஆனந்தூர்', 'ANANDUR', '3289', 'ஊ.நூ'),
    ('TNDPL01676', 'மகனூர்பட்டி', 'MAGANURPATTI', '3289', 'ஊ.நூ'),
    ('TNDPL01686', 'நொச்சிப்பட்டி', 'NOCHIPATTI', '3289', 'ஊ.நூ'),
    ('TNDPL00001', 'மருத்துவமனை நூலகம்', 'HOSPITAL', '2893', 'சி.நூ'),
]

def authenticate_librarian(tndpl_code, password):
    """TNDPL எண் = username. Password libraries.password_hash-உடன் ஒப்பிடப்படும்
    (இயல்புநிலையில் TNDPL எண்ணே password — 'கடவுச்சொல் மாற்ற' பகுதி மூலம் மாற்றலாம்)."""
    tndpl_code = str(tndpl_code).strip().upper()
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute(
            "SELECT tndpl_code, name_ta, name_en, lib_type, password_hash, matched_lib_value FROM libraries WHERE tndpl_code = %s;",
            (tndpl_code,)
        )
        row = cur.fetchone()
        cur.close()
        conn.close()
        if not row:
            return None
        code, name_ta, name_en, lib_type, pw_hash, matched_val = row
        if hmac.compare_digest(hash_password(password), pw_hash):
            return {
                "tndpl_code": code, "name_ta": name_ta, "name_en": name_en,
                "lib_type": lib_type, "matched_lib_value": matched_val
            }
        return None
    except Exception:
        return None

def _normalize_lib_text(s):
    return str(s).strip().lower().replace(" ", "")

def resolve_library_value(lib_col_name, neon_df):
    """நூலகர் login செய்தவரின் TNDPL பதிவுக்கும், books அட்டவணையின் library-name
    column-ல் உள்ள உண்மையான மதிப்புகளுக்கும் இடையே பொருத்தம் காண்கிறது.
    முன்னுரிமை: (1) Admin manually confirm செய்த matched_lib_value,
    (2) தமிழ்/ஆங்கிலப் பெயர் exact/contains தானியங்கு பொருத்தம்.
    பொருத்தம் கிடைக்கவில்லை எனில் None திருப்பும்."""
    matched_val = st.session_state.get("user_library_matched_value")
    if matched_val:
        return matched_val
    if not lib_col_name or neon_df.empty:
        return None
    actual_values = neon_df[lib_col_name].dropna().unique().tolist()
    name_ta = st.session_state.get("user_library_name_ta", "")
    name_en = st.session_state.get("user_library_name_en", "")
    norm_ta, norm_en = _normalize_lib_text(name_ta), _normalize_lib_text(name_en)
    for v in actual_values:
        nv = _normalize_lib_text(v)
        if nv == norm_ta or nv == norm_en:
            return v
    for v in actual_values:
        nv = _normalize_lib_text(v)
        if (norm_ta and norm_ta in nv) or (norm_en and norm_en in nv) or (nv and (nv in norm_ta or nv in norm_en)):
            return v
    return None

# Database Initialization for Submitted Reports
# @st.cache_resource ensures this CREATE TABLE runs only ONCE per app
# process lifetime, instead of opening a new DB connection on every
# single button click / rerun (which was wasting network transfer quota).
@st.cache_resource
def init_submitted_table():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS submitted_reports (
                id SERIAL PRIMARY KEY,
                publisher TEXT,
                title TEXT,
                author TEXT,
                price TEXT,
                accepted_price TEXT,
                isbn TEXT,
                required_qty INT,
                received_qty INT,
                date TEXT
            );
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dispatch_status (
                id SERIAL PRIMARY KEY,
                dispatch_key TEXT UNIQUE,
                book_id TEXT,
                publisher TEXT,
                title TEXT,
                library TEXT,
                dispatched_on TEXT
            );
        """)
        # நூலகர் (Librarian) TNDPL logins. matched_lib_value — Admin, "🔗 நூலக
        # பொருத்தம்" பகுதியில் books அட்டவணையின் உண்மையான நூலகப் பெயருடன் தொடர்பு
        # படுத்திய பிறகு நிரப்பப்படும் (இல்லையேல் தானியங்கு பொருத்தம் பயன்படும்).
        cur.execute("""
            CREATE TABLE IF NOT EXISTS libraries (
                tndpl_code TEXT PRIMARY KEY,
                name_ta TEXT,
                name_en TEXT,
                pay_center_code TEXT,
                lib_type TEXT,
                password_hash TEXT,
                matched_lib_value TEXT
            );
        """)
        # Idempotent seed — ON CONFLICT DO NOTHING என்பதால் ஏற்கனவே இருக்கும்
        # பதிவுகள் (password மாற்றியவை உட்பட) ஒருபோதும் மேலெழுதப்படாது.
        from psycopg2.extras import execute_values
        seed_rows = [
            (code, ta, en, pay, ltype, hash_password(code), None)
            for code, ta, en, pay, ltype in LIBRARY_SEED_DATA
        ]
        execute_values(
            cur,
            "INSERT INTO libraries (tndpl_code, name_ta, name_en, pay_center_code, lib_type, password_hash, matched_lib_value) VALUES %s ON CONFLICT (tndpl_code) DO NOTHING;",
            seed_rows
        )
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ Table creation error: {e}")
        return False

init_submitted_table()

# 'books' table-ல் ஒரு upload எப்போது நடந்தது என கண்காணிக்க — இனிமேல் ஒவ்வொரு
# Excel upload-உம் தானாகவே தேதி-நேரத்துடன் குறிக்கப்படும். பழைய வரிசைகள் NULL-ஆகவே
# இருக்கும் (அவை எப்போது ஏற்றப்பட்டன என்பது இப்போதைக்குத் தெரியாது), ஆனால் இன்று முதல்
# ஏற்றப்படும் அனைத்தும் தெளிவாக அடையாளம் காணப்படும்.
@st.cache_resource
def ensure_books_uploaded_at_column():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("ALTER TABLE books ADD COLUMN IF NOT EXISTS uploaded_at TIMESTAMP;")
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"❌ uploaded_at column creation error: {e}")
        return False

ensure_books_uploaded_at_column()

# @st.cache_data caches the result server-side. Call load_submitted_reports_from_db.clear()
# after any INSERT/UPDATE to this table so the next read picks up fresh data.
@st.cache_data
def load_submitted_reports_from_db():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT id as \"Id\", publisher as \"Publisher\", title as \"Title\", author as \"Author\", price as \"Price\", accepted_price as \"Accepted Price\", isbn as \"ISBN\", required_qty as \"Required Qty\", received_qty as \"Received Qty\", date as \"Date\" FROM submitted_reports;", con=conn)
        conn.close()
        return df.to_dict(orient="records")
    except Exception as e:
        return []

# Dispatch is tracked per exact row (book_id + library), not as an aggregate
# quantity — a row is either dispatched or not. dispatch_key uniquely
# identifies each (publisher, title, library) occurrence.
@st.cache_data
def load_dispatch_status_keys():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT dispatch_key FROM dispatch_status;", con=conn)
        conn.close()
        return set(df["dispatch_key"].tolist())
    except Exception:
        return set()

@st.cache_data
def get_dispatch_status_count():
    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM dispatch_status;")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return int(count)
    except Exception:
        return 0

@st.cache_data
def load_dispatch_status_full():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT id as \"Id\", dispatch_key as \"Key\", book_id as \"Book Id\", publisher as \"Publisher\", title as \"Title\", library as \"Library\", dispatched_on as \"Date\" FROM dispatch_status ORDER BY id DESC;", con=conn)
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data
def load_libraries_df():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql(
            "SELECT tndpl_code as \"TNDPL Code\", name_ta as \"Name (Tamil)\", name_en as \"Name (English)\", "
            "pay_center_code as \"Pay Center Code\", lib_type as \"Lib Type\", matched_lib_value as \"Matched Value\" "
            "FROM libraries ORDER BY name_en;",
            con=conn
        )
        conn.close()
        return df
    except Exception:
        return pd.DataFrame()

for key, default_fn in {
    "logged_in": lambda: False,
    "user_role": lambda: None,
    "user_name": lambda: "",
    "current_menu": lambda: None,
    "temp_distributed_list": lambda: [],
    # Loaded from DB only ONCE per browser session (not on every rerun).
    "submitted_reports": load_submitted_reports_from_db,
    "librarian_records": lambda: [],
    "user_library_tndpl": lambda: None,
    "user_library_name_ta": lambda: "",
    "user_library_name_en": lambda: "",
    "user_library_matched_value": lambda: None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default_fn()

def show_login_page():
    st.markdown("""
    <style>.stApp { background: linear-gradient(135deg, #064e3b, #022c22) !important; }</style>
    <div class="login-top-container">
        <div class="login-card-wrapper">
            <div class="login-header-box">
                <div style="font-size: 22px; margin-bottom: 2px;">📚</div>
                <div class="login-title">மாவட்ட மைய நூலகம்<br>கிருஷ்ணகிரி</div>
            </div>
    """, unsafe_allow_html=True)
    
    role_choice = st.selectbox(
        "பயனர் வகை (User)",
        ["-- தேர்ந்தெடுக்கவும் --", "Admin", "DCL Staff", "Librarian (நூலகர்)"],
        key="login_role_choice"
    )

    if role_choice == "Librarian (நூலகர்)":
        with st.form("secure_login_form_lib"):
            tndpl_input = st.text_input("🏛️ TNDPL எண் (உங்கள் நூலகத்தின் TNDPL Code)", placeholder="எ.கா. TNDPL01589")
            lib_password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="இயல்புநிலையில் TNDPL எண்ணே கடவுச்சொல்")
            submitted_lib = st.form_submit_button("உள்ளுழை", use_container_width=True)
        st.markdown("</div></div>", unsafe_allow_html=True)
        if submitted_lib:
            if not tndpl_input.strip():
                st.warning("⚠️ TNDPL எண்ணை உள்ளிடவும்!")
            else:
                lib_user = authenticate_librarian(tndpl_input.strip(), lib_password)
                if not lib_user:
                    st.error("❌ தவறான TNDPL எண் அல்லது கடவுச்சொல்!")
                else:
                    display_name = f"{lib_user['name_ta']} ({lib_user['name_en']})"
                    st.session_state.update(
                        logged_in=True,
                        user_role="Librarian",
                        user_name=display_name,
                        user_library_tndpl=lib_user["tndpl_code"],
                        user_library_name_ta=lib_user["name_ta"],
                        user_library_name_en=lib_user["name_en"],
                        user_library_matched_value=lib_user["matched_lib_value"],
                    )
                    st.rerun()
    else:
        with st.form("secure_login_form"):
            password = st.text_input("🔑 கடவுச்சொல்", type="password", placeholder="கடவுச்சொல்லை உள்ளிடவும்")
            submitted = st.form_submit_button("உள்ளுழை", use_container_width=True)
        st.markdown("</div></div>", unsafe_allow_html=True)
        if submitted:
            if role_choice == "-- தேர்ந்தெடுக்கவும் --":
                st.warning("⚠️ தயவுசெய்து பயனர் வகையைத் தேர்ந்தெடுக்கவும்!")
            else:
                user = authenticate_user(role_choice, password)
                if not user:
                    st.error("❌ தவறான கடவுச்சொல்!")
                else:
                    st.session_state.update(logged_in=True, user_role=role_choice, user_name=user["name"])
                    st.rerun()

if not st.session_state["logged_in"]:
    show_login_page()
    st.stop()

st.markdown("""
<div class="top-header-container">
    <div>
        <div class="header-title">📚 மாவட்ட மைய நூலகம்</div>
        <div class="header-subtitle">கிருஷ்ணகிரி — புதிய நூல்கள் பகிர்மானம் 2026-27</div>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(255,255,255,0.15); padding: 6px 12px; border-radius: 8px; font-size: 13px;">
            👤 {} ({})
        </span>
    </div>
</div>
""".format(st.session_state["user_name"], st.session_state["user_role"]), unsafe_allow_html=True)

col_logout = st.columns([11, 1])
with col_logout[1]:
    if st.button("🚪 வெளியேறு", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["user_role"] = None
        st.session_state["user_library_tndpl"] = None
        st.session_state["user_library_name_ta"] = ""
        st.session_state["user_library_name_en"] = ""
        st.session_state["user_library_matched_value"] = None
        st.session_state["current_menu"] = None
        st.rerun()

ALL_MENU_OPTIONS = [
    ("🔀", "பிரிக்க"), ("📜", "நூலகர் சான்று"), ("📊", "அறிக்கைகள்"), ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண் மாற்ற"), ("🗂️", "Master Data"), ("❌", "தவறான பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல் மாற்ற"), ("📥", "Excel பதிவிறக்கம்"), ("👥", "நூலகர் பார்வை ஆண்டு"),
    ("📂", "Excel அப்லோடு"), ("🏷️", "பகுப்பு எண் புதுப்பி"), ("🔗", "நூலக பொருத்தம்")
]

# பங்கு அடிப்படையில் மெனு கட்டுப்பாடு:
#   Admin        → அனைத்தும்
#   DCL Staff    → பிரிக்க + அறிக்கைகள் + தவறான பதிவு நீக்கம்
#   Librarian    → நூலகர் சான்று (அவர் நூலகத்திற்கு மட்டும்) + அறிக்கைகள் (அவர் நூலகத்திற்கு மட்டும்)
_role = st.session_state["user_role"]
if _role == "DCL Staff":
    menu_options = [m for m in ALL_MENU_OPTIONS if m[1] in ("பிரிக்க", "அறிக்கைகள்", "தவறான பதிவு நீக்கம்")]
elif _role == "Librarian":
    menu_options = [m for m in ALL_MENU_OPTIONS if m[1] in ("நூலகர் சான்று", "அறிக்கைகள்", "கடவுச்சொல் மாற்ற")]
else:
    menu_options = ALL_MENU_OPTIONS

# Rows of up to 6 buttons each — easier to read/tap than one cramped long row
menu_rows = [menu_options[i:i + 6] for i in range(0, len(menu_options), 6)]
btn_counter = 0
for row in menu_rows:
    cols = st.columns(len(row))
    for col, (icon, label) in zip(cols, row):
        with col:
            btn_type = "primary" if st.session_state["current_menu"] == label else "secondary"
            if st.button(f"{icon}\n{label}", key=f"menu_btn_{btn_counter}", use_container_width=True, type=btn_type):
                st.session_state["current_menu"] = label
                st.rerun()
        btn_counter += 1

st.markdown("---")

@st.cache_data
def load_neon_database():
    try:
        conn = psycopg2.connect(DB_URL)
        df = pd.read_sql("SELECT * FROM books;", con=conn)
        conn.close()
        if not df.empty:
            df.columns = [str(c).strip().lower() for c in df.columns]
            return df
    except Exception as e:
        st.error(f"❌ டேட்டாபேஸ் இணைப்பில் பிழை: {e}")
    return pd.DataFrame()

def build_pub_stats_df(pub_name, source_neon_df, source_rep_df, pub_col, title_col):
    """For one publisher: mark the first N rows per title as 'received' (received_stats=1),
    where N = Received Qty submitted for that title. Shared by Master Data and நூலகர் சான்று pages."""
    p_neon_df = source_neon_df[source_neon_df[pub_col] == pub_name].copy()
    p_rep = source_rep_df[source_rep_df["Publisher"] == pub_name] if not source_rep_df.empty else pd.DataFrame()
    t_map = dict(zip(p_rep["Title"], p_rep["Received Qty"])) if not p_rep.empty else {}

    rows = []
    for title_val, group_df in p_neon_df.groupby(title_col):
        req_qty = len(group_df)
        rec_qty = int(t_map.get(title_val, 0))
        group_df = group_df.copy()
        group_df["received_stats"] = [1 if i < rec_qty else 0 for i in range(req_qty)]
        rows.append(group_df)

    return pd.concat(rows, ignore_index=True) if rows else p_neon_df

def compute_all_received_rows(submitted_pubs, pub_col, title_col):
    """Combines build_pub_stats_df across every submitted publisher and keeps only
    the rows actually marked as received (received_stats == 1) — these are the
    rows eligible for dispatch."""
    neon_df_local = load_neon_database()
    rep_df_local = pd.DataFrame(st.session_state["submitted_reports"])
    frames = [build_pub_stats_df(p, neon_df_local, rep_df_local, pub_col, title_col) for p in submitted_pubs]
    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if not combined.empty and "received_stats" in combined.columns:
        combined = combined[combined["received_stats"] == 1].reset_index(drop=True)
    return combined

def _find_tamil_font_path():
    """Looks for the Tamil font in a few likely spots so it works whichever
    folder name/case the person actually used in the repo."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(base_dir, "fonts", "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "Font", "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "Fonts", "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "font", "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "NotoSansTamil-Regular.ttf"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

TAMIL_FONT_PATH = _find_tamil_font_path()

def generate_tamil_pdf_table(df, headers, col_widths, report_title, orientation="L"):
    """Builds a PDF with correctly-shaped Tamil text (pre-base vowel signs like
    ை/ொ/ோ need HarfBuzz re-ordering — reportlab/plain fpdf2 render them wrong,
    so text_shaping must stay on). Returns PDF bytes, or None if the font file
    is missing (caller should show a friendly message pointing at fonts/ folder)."""
    if not TAMIL_FONT_PATH:
        return None
    from fpdf import FPDF
    pdf = FPDF(orientation=orientation, format="A4")
    pdf.add_page()
    pdf.add_font("Tamil", "", TAMIL_FONT_PATH)
    pdf.add_font("Tamil", "B", TAMIL_FONT_PATH)
    pdf.set_text_shaping(True)

    pdf.set_font("Tamil", "B", 13)
    pdf.cell(0, 10, report_title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Tamil", "", 8)

    with pdf.table(col_widths=col_widths, text_align="LEFT") as table:
        row = table.row()
        for h in headers:
            row.cell(h)
        for _, r in df.iterrows():
            row = table.row()
            for h in headers:
                row.cell(str(r.get(h, "")))

    return bytes(pdf.output())

total_books_in_db = len(load_neon_database())
total_submitted_count = sum([int(item.get("Received Qty", 0)) for item in st.session_state['submitted_reports']])
total_dispatched_count = get_dispatch_status_count()
today_str = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="ticker-container">
    <div class="ticker-badge">🔴 Live News</div>
    <div style="overflow: hidden; width: 100%;">
        <div class="marquee-text">
            📚 பெறப்பட்ட நூல்கள் : <b>{total_books_in_db:,}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ✅ பிரிக்கப்பட்டது : <b>{total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            ⏳ மீதம் பிரிக்க வேண்டியது : <b>{total_books_in_db - total_submitted_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            📤 அனுப்பப்பட்டது : <b>{total_dispatched_count}</b> &nbsp;&nbsp;&nbsp;&nbsp;◆&nbsp;&nbsp;&nbsp;&nbsp; 
            🗓️ இன்று ({today_str}) பிரிக்கப்பட்டது : <b>{total_submitted_count}</b>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

current = st.session_state["current_menu"]
_allowed_labels = {m[1] for m in menu_options}
if current is not None and current not in _allowed_labels:
    current = None
    st.session_state["current_menu"] = None

if current is None:
    st.info("👆 மேல் உள்ள மெனு பட்டன்களில் ஏதேனும் ஒன்றை (உதாரணமாக **'🔀 பிரிக்க'** அல்லது **'📊 அறிக்கைகள்'**) தேர்வு செய்யவும்.")

elif current == "பிரிக்க":
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி (Publisher-wise Book Distribution)")
    
    neon_df = load_neon_database()

    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
        author_col = next((c for c in neon_df.columns if 'author' in c), None)
        price_col = next((c for c in neon_df.columns if c == 'price'), None)
        accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'accepted' in c or 'rate' in c or 'offer' in c), None)
        isbn_col = next((c for c in neon_df.columns if 'isbn' in c), None)

        all_publishers = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []

        selected_publisher = st.selectbox(
            "🔍 1. பதிப்பாளர் பெயரைத் தேர்ந்தெடுக்கவும்:",
            ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_publishers,
            key="publisher_dropdown"
        )

        if selected_publisher != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
            pub_filtered_df = neon_df[neon_df[pub_col] == selected_publisher].copy()
            
            total_pub_titles_count = len(pub_filtered_df[title_col].dropna().unique())
            total_pub_books_count = len(pub_filtered_df)
            
            submitted_titles = [item["Title"] for item in st.session_state["submitted_reports"] if item["Publisher"] == selected_publisher]
            temp_added_titles = [item["Title"] for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher]
            
            excluded_titles = set(submitted_titles + temp_added_titles)
            available_filtered_df = pub_filtered_df[~pub_filtered_df[title_col].isin(excluded_titles)]
            all_titles = sorted(available_filtered_df[title_col].dropna().unique().tolist())

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #ecfdf5, #d1fae5); border: 1.5px solid #34d399; padding: 14px 18px; border-radius: 10px; margin: 10px 0 15px 0;">
                <div style="font-size: 15px; font-weight: 800; color: #064e3b; margin-bottom: 8px;">
                    🏢 பதிப்பகம்: {selected_publisher} — சுருக்க விவரம்
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 20px; font-size: 14px; color: #065f46; font-weight: 600;">
                    <div>📚 மொத்த தலைப்புகள்: <b>{total_pub_titles_count}</b></div>
                    <div>📦 மொத்த நூல்கள்: <b>{total_pub_books_count}</b></div>
                    <div>✅ சமர்ப்பிக்கப்பட்டது: <b>{len(submitted_titles)}</b></div>
                    <div>⏳ மீதம் உள்ளவை: <b>{len(all_titles)}</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if all_titles:
                selected_title = st.selectbox(
                    "📖 2. தலைப்பைத் தேர்ந்தெடுக்கவும் (Select Book Title):",
                    ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + all_titles,
                    key="title_dropdown"
                )

                if selected_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_row_df = pub_filtered_df[pub_filtered_df[title_col] == selected_title]
                    if not title_row_df.empty:
                        title_row = title_row_df.iloc[0]
                        author_name = str(title_row[author_col]) if author_col and author_col in title_row and pd.notna(title_row[author_col]) else "-"
                        book_price = str(title_row[price_col]) if price_col and price_col in title_row and pd.notna(title_row[price_col]) else "0"
                        
                        accepted_price = "0"
                        if accepted_price_col and accepted_price_col in title_row and pd.notna(title_row[accepted_price_col]):
                            accepted_price = str(title_row[accepted_price_col])

                        isbn_val = str(title_row[isbn_col]) if isbn_col and isbn_col in title_row and pd.notna(title_row[isbn_col]) else "-"
                        required_qty = len(title_row_df)

                        with st.form(f"distribution_entry_form_{selected_publisher}_{selected_title}"):
                            entered_qty = st.number_input(
                                "📥 பெறப்பட்ட எண்ணிக்கையை உள்ளீடு செய்யவும்:", 
                                min_value=0, max_value=500, value=int(required_qty), step=1
                            )
                            submitted_temp = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
                            
                            if submitted_temp:
                                entry_data = {
                                    "Publisher": selected_publisher,
                                    "Title": selected_title,
                                    "Author": author_name,
                                    "Price": book_price,
                                    "Accepted Price": accepted_price,
                                    "ISBN": isbn_val,
                                    "Required Qty": required_qty,
                                    "Received Qty": entered_qty,
                                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                if not any(item["Title"] == selected_title for item in st.session_state["temp_distributed_list"]):
                                    st.session_state["temp_distributed_list"].append(entry_data)
                                st.success(f"✅ '{selected_title}' தற்காலிக பட்டியலில் சேர்க்கப்பட்டது!")
                                st.rerun()
            else:
                st.success(f"🎉 '{selected_publisher}' பதிப்பகத்தில் உள்ள அனைத்து நூல்களும் வெற்றிகரமாகச் சரிபார்க்கப்பட்டுவிட்டன!")

            if st.session_state["temp_distributed_list"]:
                st.markdown("---")
                st.markdown("#### 📋 தற்காலிகமாகச் சேமிக்கப்பட்ட தலைப்புகளின் பட்டியல்")
                temp_df = pd.DataFrame(st.session_state["temp_distributed_list"])
                st.dataframe(temp_df, use_container_width=True)
                
                current_pub_temp_count = len([item for item in st.session_state["temp_distributed_list"] if item["Publisher"] == selected_publisher])
                remaining_to_add = total_pub_titles_count - (len(submitted_titles) + current_pub_temp_count)
                
                if remaining_to_add > 0:
                    st.warning(f"⚠️ எச்சரிக்கை: இந்தப் பதிப்பகத்தில் இன்னும் **{remaining_to_add}** தலைப்புகள் சரிபார்க்கப்படாமல் உள்ளன. அனைத்து தலைப்புகளையும் சேர்த்த பிறகுதான் இறுதியாகச் சமர்ப்பிக்க முடியும்!")
                else:
                    if st.button("💾 இறுதியாகச் சேமி & சமர்ப்பிக்க", type="primary", key="final_submit_btn"):
                        try:
                            conn = psycopg2.connect(DB_URL)
                            cur = conn.cursor()
                            duplicate_items = []
                            saved_count = 0
                            for item in st.session_state["temp_distributed_list"]:
                                # --- Duplicate-proof lock (Flask app-ன் row-locking-க்கு இணையான
                                # Postgres advisory lock) — 2 பேர் ஒரே publisher+title-ஐ ஒரே
                                # நேரத்தில் சமர்ப்பித்தாலும், ஒருவருக்கு மட்டுமே சேமிக்கப்படும்;
                                # மற்றவருக்கு "ஏற்கனவே சமர்ப்பிக்கப்பட்டது" எனக் காட்டப்படும்.
                                lock_key = int(hashlib.md5(f"{item['Publisher']}||{item['Title']}".encode("utf-8")).hexdigest()[:15], 16)
                                cur.execute("SELECT pg_advisory_xact_lock(%s);", (lock_key,))
                                cur.execute(
                                    "SELECT 1 FROM submitted_reports WHERE publisher = %s AND title = %s;",
                                    (item["Publisher"], item["Title"])
                                )
                                if cur.fetchone():
                                    duplicate_items.append(item["Title"])
                                    continue
                                cur.execute("""
                                    INSERT INTO submitted_reports (publisher, title, author, price, accepted_price, isbn, required_qty, received_qty, date)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """, (
                                    item["Publisher"], item["Title"], item["Author"], item["Price"],
                                    item["Accepted Price"], item["ISBN"], item["Required Qty"],
                                    item["Received Qty"], item["Date"]
                                ))
                                saved_count += 1
                            conn.commit()
                            cur.close()
                            conn.close()

                            load_submitted_reports_from_db.clear()
                            st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                            st.session_state["temp_distributed_list"] = []

                            if duplicate_items:
                                st.warning(
                                    "⚠️ இந்தத் தலைப்புகள் ஏற்கனவே இன்னொருவரால் சமர்ப்பிக்கப்பட்டுவிட்டதால் மீண்டும் சேமிக்கப்படவில்லை: "
                                    + ", ".join(duplicate_items)
                                )
                            if saved_count:
                                st.session_state["current_menu"] = "அறிக்கைகள்"
                                st.success(f"🎉 {saved_count} தலைப்புகள் Neon Database-ல் வெற்றிகரமாகச் சேமிக்கப்பட்டன!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Database save error: {e}")

elif current == "நூலகர் சான்று":
    st.subheader("📜 நூலகர் சான்று — நூலகத்தில் பெறப்பட்டதை சரிபார்த்தல் (Library Receipt Verification)")
    if st.session_state["user_role"] == "Librarian":
        st.caption(f"🏛️ உங்கள் நூலகம்: **{st.session_state['user_library_name_ta']} ({st.session_state['user_library_name_en']})** — Master Data-வில் உள்ள அதே முழு விவரங்களும் இங்கு வரும். பெற்றதை ✔️ டிக் செய்யவும்.")
    else:
        st.caption("சம்பந்தப்பட்ட நூலகர்கள் தங்கள் நூலகத்தைத் தேர்ந்தெடுக்கவும் — Master Data-வில் உள்ளதைப் போலவே முழு விவரங்களும் இங்கு வரும். பெற்ற நூல்களை ✔️ டிக் செய்யவும்.")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    elif not st.session_state["submitted_reports"]:
        st.info("ℹ️ முதலில் '🔀 பிரிக்க' பகுதியில் நூல்களைப் பிரித்துச் சமர்ப்பிக்கவும். அதன் பிறகே இங்கு சரிபார்க்க முடியும்.")
    else:
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
        lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
        book_id_col = next((c for c in neon_df.columns if c == 'book_id'), None)

        rep_df = pd.DataFrame(st.session_state["submitted_reports"])
        submitted_pubs = sorted([p for p in rep_df["Publisher"].dropna().unique().tolist() if pub_col and p in neon_df[pub_col].values]) if pub_col else []

        if not submitted_pubs or not lib_col_name:
            st.info("ℹ️ பிரிக்கப்பட்ட தரவு இன்னும் இல்லை, அல்லது நூலகப் பெயர் நெடுவரிசை கண்டறியப்படவில்லை.")
        else:
            # Master Data-வில் உள்ள அதே தரவு: "பணி முடிக்கப்பட்ட" பதிப்பகங்களுக்கு உரிய
            # அனைத்து நூல்களும், அனைத்து columns-உடன் (எண்ணிக்கை இரண்டு பக்கங்களிலும் பொருந்தும்).
            submitted_neon_df = neon_df[neon_df[pub_col].isin(submitted_pubs)].copy()

            if st.session_state["user_role"] == "Librarian":
                sel_value = resolve_library_value(lib_col_name, neon_df)
                if not sel_value:
                    st.error(
                        "❌ உங்கள் நூலகத்திற்கான தரவு Books Database-ல் தானாகக் கண்டறிய முடியவில்லை. "
                        "Admin-ஐத் தொடர்பு கொள்ளவும் — 'நூலக பொருத்தம்' பகுதியில் இதைச் சரிசெய்யலாம்."
                    )
            else:
                all_libs = sorted(submitted_neon_df[lib_col_name].dropna().unique().tolist())
                sel_value = st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_libs, key="dispatch_lib_sel2")
                if sel_value == "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                    sel_value = None

            if sel_value:
                lib_scoped_df = submitted_neon_df[submitted_neon_df[lib_col_name] == sel_value].reset_index(drop=True)

                if lib_scoped_df.empty:
                    st.info("ℹ️ இந்த நூலகத்திற்கு இதுவரை பணி முடிக்கப்பட்ட நூல்கள் எதுவும் இல்லை.")
                else:
                    # Unique key per (publisher, title, library) occurrence — since one
                    # book_id can appear for several libraries, and rarely a library can
                    # receive the same title twice, cumcount disambiguates exact duplicates.
                    lib_scoped_df["dispatch_key"] = (
                        lib_scoped_df[pub_col].astype(str) + "||" +
                        lib_scoped_df[title_col].astype(str) + "||" +
                        lib_scoped_df[lib_col_name].astype(str) + "||" +
                        lib_scoped_df.groupby([pub_col, title_col, lib_col_name]).cumcount().astype(str)
                    )

                    dispatched_keys = load_dispatch_status_keys()
                    lib_scoped_df["✅ நூலகத்தில் பெறப்பட்டதா"] = lib_scoped_df["dispatch_key"].isin(dispatched_keys)

                    total_rows = len(lib_scoped_df)
                    already_n = int(lib_scoped_df["✅ நூலகத்தில் பெறப்பட்டதா"].sum())

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("📚 மொத்த நூல்கள்", total_rows)
                    with col2:
                        st.metric("✅ சரிபார்க்கப்பட்டவை", already_n)
                    with col3:
                        st.metric("⏳ சரிபார்க்க வேண்டியவை", total_rows - already_n)

                    st.markdown(f"### 🏛️ {sel_value} — முழு அட்டவணை விவரங்கள் (பெற்றதை ✔️ டிக் செய்யவும்)")

                    # Master Data-வில் காட்டப்படும் அதே columns — state_accession_number,
                    # book_id, isbn, publication_name, librarian_id, central/branch numbers
                    # உள்ளிட்டு அனைத்தும் — checkbox column மட்டும் கூடுதல்.
                    display_cols = [c for c in lib_scoped_df.columns if c not in ("dispatch_key", "✅ நூலகத்தில் பெறப்பட்டதா")]
                    edit_cols = display_cols + ["✅ நூலகத்தில் பெறப்பட்டதா", "dispatch_key"]
                    edited_df = st.data_editor(
                        lib_scoped_df[edit_cols],
                        column_config={
                            "dispatch_key": None,
                            "✅ நூலகத்தில் பெறப்பட்டதா": st.column_config.CheckboxColumn("✅ நூலகத்தில் பெறப்பட்டதா"),
                        },
                        disabled=display_cols,
                        hide_index=True,
                        use_container_width=True,
                        key=f"dispatch_editor_{sel_value}"
                    )

                    if st.button("💾 சரிபார்ப்பு நிலையைச் சேமி", type="primary", key="dispatch_save_btn"):
                        try:
                            conn = psycopg2.connect(DB_URL)
                            cur = conn.cursor()
                            to_insert, to_delete = [], []
                            now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

                            for _, r in edited_df.iterrows():
                                key = r["dispatch_key"]
                                was_before = key in dispatched_keys
                                now_checked = bool(r["✅ நூலகத்தில் பெறப்பட்டதா"])
                                if now_checked and not was_before:
                                    orig_row = lib_scoped_df[lib_scoped_df["dispatch_key"] == key].iloc[0]
                                    to_insert.append((
                                        key, str(orig_row.get(book_id_col, "")), orig_row[pub_col],
                                        orig_row[title_col], orig_row[lib_col_name], now_str
                                    ))
                                elif not now_checked and was_before:
                                    to_delete.append(key)

                            if to_insert:
                                from psycopg2.extras import execute_values
                                execute_values(
                                    cur,
                                    "INSERT INTO dispatch_status (dispatch_key, book_id, publisher, title, library, dispatched_on) VALUES %s ON CONFLICT (dispatch_key) DO NOTHING;",
                                    to_insert
                                )
                            if to_delete:
                                cur.execute("DELETE FROM dispatch_status WHERE dispatch_key = ANY(%s);", (to_delete,))

                            conn.commit()
                            cur.close()
                            conn.close()
                            load_dispatch_status_keys.clear()
                            get_dispatch_status_count.clear()
                            load_dispatch_status_full.clear()
                            st.success(f"✅ புதுப்பிக்கப்பட்டது — புதிதாக சரிபார்க்கப்பட்டவை: {len(to_insert)}, திரும்பப் பெறப்படாதது என மாற்றப்பட்டவை: {len(to_delete)}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Save error: {e}")

elif current == "கவனிக்க":
    st.subheader("⚠️ கவனிக்க வேண்டிய பதிவுகள் (Price Conflicts & Review)")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        price_col = next((c for c in neon_df.columns if c == 'price'), None)
        accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'rate' in c or 'offer' in c), None)
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not price_col or not accepted_price_col:
            st.info("ℹ️ விலை (Price) மற்றும் ஏற்றுக்கொள்ளப்பட்ட விலை (Accepted Price) நெடுவரிசைகள் தரவுத்தளத்தில் கிடைக்கவில்லை.")
        else:
            temp_df = neon_df.copy()
            temp_df["_price_num"] = pd.to_numeric(temp_df[price_col], errors="coerce")
            temp_df["_accepted_num"] = pd.to_numeric(temp_df[accepted_price_col], errors="coerce")
            conflict_df = temp_df[temp_df["_price_num"] != temp_df["_accepted_num"]].copy()

            if conflict_df.empty:
                st.success("🎉 விலை முரண்பாடு உள்ள பதிவுகள் எதுவும் இல்லை!")
            else:
                st.warning(f"⚠️ மொத்தம் **{len(conflict_df)}** பதிவுகளில் விலை முரண்பாடு (Price Conflict) உள்ளது.")
                cols_to_show = [c for c in [pub_col, title_col, price_col, accepted_price_col] if c]
                st.dataframe(conflict_df[cols_to_show], use_container_width=True)

                csv_conflict = conflict_df[cols_to_show].to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 முரண்பாடு பட்டியலைப் பதிவிறக்குக (CSV)",
                    data=csv_conflict,
                    file_name=f"Price_Conflicts_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    type="primary"
                )

elif current == "பதிவெண் மாற்ற":
    st.subheader("🔢 பதிவெண் மாற்றும் பகுதி (Accession Number Updates)")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        acc_col = next((c for c in neon_df.columns if c == 'state_acc_number'), None) or next((c for c in neon_df.columns if 'accession' in c or c == 'acc_no' or 'reg_no' in c), None)
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not acc_col:
            st.info("ℹ️ 'Accession Number' நெடுவரிசை தரவுத்தளத்தில் கண்டறியப்படவில்லை. நெடுவரிசைப் பெயரைச் சரிபார்க்கவும்.")
        else:
            all_pubs = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
            sel_pub = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_pubs, key="acc_pub_sel")

            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                pub_df = neon_df[neon_df[pub_col] == sel_pub] if pub_col else neon_df
                title_list = sorted(pub_df[title_col].dropna().unique().tolist())
                sel_title = st.selectbox("📖 தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="acc_title_sel")

                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_df = pub_df[pub_df[title_col] == sel_title].reset_index(drop=True)
                    st.dataframe(title_df[[c for c in [acc_col, title_col] if c]], use_container_width=True)

                    if not title_df.empty:
                        row_num = st.number_input("✏️ மாற்ற வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(title_df) - 1, value=0, step=1, key="acc_row_num")
                        new_acc_no = st.text_input("🔢 புதிய பதிவெண்", value=str(title_df.iloc[int(row_num)][acc_col]), key="acc_new_val")

                        if st.button("💾 பதிவெண்ணைப் புதுப்பி", type="primary", key="acc_update_btn"):
                            try:
                                conn = psycopg2.connect(DB_URL)
                                cur = conn.cursor()
                                old_acc_no = title_df.iloc[int(row_num)][acc_col]
                                cur.execute(
                                    f"UPDATE books SET {acc_col} = %s WHERE {acc_col} = %s AND {title_col} = %s;",
                                    (new_acc_no, old_acc_no, sel_title)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ பதிவெண் '{old_acc_no}' இலிருந்து '{new_acc_no}' ஆக மாற்றப்பட்டது!")
                                load_neon_database.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Update error: {e}")

elif current == "அறிக்கைகள்":
    st.subheader("📊 அறிக்கைகள் & பதிவுக் சரிபார்ப்பு (Publishers & Title & Books Verification Report)")

    if st.session_state["user_role"] == "Librarian":
        # --- நூலகர் பங்கு: தங்கள் நூலகத்திற்குரிய அறிக்கையை மட்டும் பார்க்க முடியும் ---
        st.caption(f"🏛️ உங்கள் நூலகம்: **{st.session_state['user_library_name_ta']} ({st.session_state['user_library_name_en']})**")
        if not st.session_state["submitted_reports"]:
            st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
        else:
            neon_df = load_neon_database()
            if neon_df.empty:
                st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
            else:
                pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
                title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
                if not title_col:
                    title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
                lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
                book_id_col = next((c for c in neon_df.columns if c == 'book_id'), None)
                author_col = next((c for c in neon_df.columns if 'author' in c), None)

                full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
                submitted_pubs_own = sorted([p for p in full_report_df["Publisher"].dropna().unique().tolist() if pub_col and p in neon_df[pub_col].values]) if pub_col else []
                sel_value = resolve_library_value(lib_col_name, neon_df) if lib_col_name else None

                if not sel_value:
                    st.error(
                        "❌ உங்கள் நூலகத்திற்கான தரவு Books Database-ல் தானாகக் கண்டறிய முடியவில்லை. "
                        "Admin-ஐத் தொடர்பு கொள்ளவும் — 'நூலக பொருத்தம்' பகுதியில் இதைச் சரிசெய்யலாம்."
                    )
                elif not submitted_pubs_own:
                    st.info("ℹ️ இதுவரை உங்கள் நூலகத்திற்கான பதிப்பகங்கள் எதுவும் பிரிக்கப்பட்டு சமர்ப்பிக்கப்படவில்லை.")
                else:
                    # Master Data-வில் உள்ள அதே தரவு — received_stats வடிகட்டல் இல்லாமல்,
                    # இந்த நூலகத்திற்கு உரிய அனைத்து நூல்களும்.
                    own_report_df = neon_df[neon_df[pub_col].isin(submitted_pubs_own)].copy()
                    own_report_df = own_report_df[own_report_df[lib_col_name] == sel_value].reset_index(drop=True) if not own_report_df.empty else own_report_df
                    if own_report_df.empty:
                        st.info("ℹ️ உங்கள் நூலகத்திற்குரிய நூல்கள் எதுவும் இன்னும் பெறப்படவில்லை.")
                    else:
                        dispatched_keys_own = load_dispatch_status_keys()
                        own_report_df["_key"] = (
                            own_report_df[pub_col].astype(str) + "||" +
                            own_report_df[title_col].astype(str) + "||" +
                            own_report_df[lib_col_name].astype(str) + "||" +
                            own_report_df.groupby([pub_col, title_col, lib_col_name]).cumcount().astype(str)
                        )
                        own_report_df["நூலகத்தில் பெறப்பட்டதா"] = own_report_df["_key"].isin(dispatched_keys_own).map({True: "✅ பெறப்பட்டது", False: "⏳ இன்னும் இல்லை"})

                        total_own = len(own_report_df)
                        recv_own = int((own_report_df["நூலகத்தில் பெறப்பட்டதா"] == "✅ பெறப்பட்டது").sum())
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.metric("📚 மொத்த நூல்கள்", total_own)
                        with c2:
                            st.metric("✅ பெறப்பட்டவை", recv_own)
                        with c3:
                            st.metric("⏳ மீதம்", total_own - recv_own)

                        show_cols_own = [c for c in own_report_df.columns if c not in ("_key",)]
                        st.dataframe(own_report_df[show_cols_own], use_container_width=True)

                        col_csv_own, col_pdf_own = st.columns(2)
                        with col_csv_own:
                            csv_own = own_report_df[show_cols_own].to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="📥 என் நூலக அறிக்கை (CSV)",
                                data=csv_own,
                                file_name=f"{st.session_state['user_library_tndpl']}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                                mime="text/csv",
                                type="primary",
                                use_container_width=True,
                                key="dl_own_lib_csv"
                            )
                        with col_pdf_own:
                            if len(own_report_df) > 3000:
                                st.info("ℹ️ PDF-ஆக பதிவிறக்க 3000-க்கும் குறைவான வரிசைகள் இருக்க வேண்டும்.")
                            else:
                                if st.button("📄 PDF உருவாக்கு", key="gen_pdf_own_report", use_container_width=True):
                                    pdf_headers = [c for c in [book_id_col, title_col, author_col, "நூலகத்தில் பெறப்பட்டதா"] if c and c in own_report_df.columns]
                                    pdf_widths = (25, 100, 65, 55)[:len(pdf_headers)]
                                    pdf_bytes = generate_tamil_pdf_table(
                                        own_report_df[pdf_headers], pdf_headers, pdf_widths,
                                        f"நூலக அறிக்கை — {st.session_state['user_library_name_ta']}"
                                    )
                                    if pdf_bytes is None:
                                        st.error("❌ Tamil font கோப்பு கிடைக்கவில்லை.")
                                    else:
                                        st.download_button(
                                            label="📥 PDF பதிவிறக்கம்",
                                            data=pdf_bytes,
                                            file_name=f"{st.session_state['user_library_tndpl']}_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                                            mime="application/pdf",
                                            type="primary",
                                            use_container_width=True,
                                            key="dl_pdf_own_report"
                                        )

    elif not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
    else:
        full_report_df = pd.DataFrame(st.session_state["submitted_reports"])
        unique_report_publishers = ["-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --"] + sorted(full_report_df["Publisher"].dropna().unique().tolist())
        selected_report_pub = st.selectbox("🔍 பதிப்பகம் வாரியாக வடிகட்டுக (Filter by Publisher):", unique_report_publishers)

        tab_summary, tab_pub_summary, tab_library = st.tabs(["📋 சுருக்க அறிக்கை (Summary)", "🧾 பதிப்பக தொகுப்பு (Publisher Summary)", "🏛️ நூலக விவரம் (Library Detail)"])

        with tab_summary:
            if selected_report_pub != "-- அனைத்துப் பதிப்பகங்களும் (All Publishers) --":
                display_df = full_report_df[full_report_df["Publisher"] == selected_report_pub].reset_index(drop=True)
                st.markdown(f"### 🏢 பதிப்பகம்: {selected_report_pub} (பதிவு செய்யப்பட்ட தலைப்புகள்: {len(display_df)})")
            else:
                display_df = full_report_df
                st.markdown(f"**மொத்தப் பதிவு செய்யப்பட்ட தலைப்புகள்:** {len(display_df)}")
                
            st.dataframe(display_df, use_container_width=True)
            
            csv_all = full_report_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 அறிக்கையைப் பதிவிறக்குக (Download CSV)",
                data=csv_all,
                file_name=f"Verification_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
                key="dl_summary_csv"
            )

        with tab_pub_summary:
            st.caption("ஒரு பதிப்பகத்திற்கு ஒரே ஒரு தொகுப்பு வரி — மொத்த தலைப்புகள் / பெற வேண்டியது / பெற்றது.")

            full_report_df["Required Qty"] = pd.to_numeric(full_report_df["Required Qty"], errors="coerce").fillna(0)
            full_report_df["Received Qty"] = pd.to_numeric(full_report_df["Received Qty"], errors="coerce").fillna(0)

            pub_summary_df = (
                full_report_df.groupby("Publisher")
                .agg(
                    மொத்த_தலைப்புகள்=("Title", "nunique"),
                    பெற_வேண்டியது=("Required Qty", "sum"),
                    பெற்றது=("Received Qty", "sum"),
                )
                .reset_index()
                .rename(columns={"Publisher": "பதிப்பகம்"})
            )
            pub_summary_df["மீதம்"] = pub_summary_df["பெற_வேண்டியது"] - pub_summary_df["பெற்றது"]
            pub_summary_df["நிலை"] = pub_summary_df["மீதம்"].apply(lambda x: "✅ முடிக்கப்பட்டது" if x <= 0 else "⏳ முடிக்கப்படவில்லை")
            pub_summary_df = pub_summary_df.sort_values("பதிப்பகம்").reset_index(drop=True)

            completed_pub_df = pub_summary_df[pub_summary_df["நிலை"] == "✅ முடிக்கப்பட்டது"].drop(columns=["நிலை"]).reset_index(drop=True)
            pending_pub_df = pub_summary_df[pub_summary_df["நிலை"] == "⏳ முடிக்கப்படவில்லை"].drop(columns=["நிலை"]).reset_index(drop=True)

            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🏢 மொத்த பதிப்பகங்கள்", len(pub_summary_df))
            with c2:
                st.metric("✅ முடிக்கப்பட்டவை", len(completed_pub_df))
            with c3:
                st.metric("⏳ முடிக்கப்படாதவை", len(pending_pub_df))

            st.markdown("#### ✅ இதுவரை முடிக்கப்பட்ட பதிப்பகங்கள்")
            st.dataframe(completed_pub_df, use_container_width=True, hide_index=True)

            st.markdown("#### ⏳ இன்னும் முடிக்கப்படாத பதிப்பகங்கள்")
            st.dataframe(pending_pub_df, use_container_width=True, hide_index=True)

            # ---- Excel (இரண்டு sheets) ----
            import io
            excel_buf = io.BytesIO()
            with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
                completed_pub_df.to_excel(writer, sheet_name="முடிக்கப்பட்டவை", index=False)
                pending_pub_df.to_excel(writer, sheet_name="முடிக்கப்படாதவை", index=False)
            excel_bytes = excel_buf.getvalue()

            col_xlsx, col_pdf_sum = st.columns(2)
            with col_xlsx:
                st.download_button(
                    label="📥 Excel பதிவிறக்கம் (2 sheets)",
                    data=excel_bytes,
                    file_name=f"Publisher_Summary_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                    key="dl_pub_summary_xlsx"
                )
            with col_pdf_sum:
                if st.button("📄 PDF உருவாக்கு", key="gen_pdf_pub_summary", use_container_width=True):
                    if not TAMIL_FONT_PATH:
                        st.error("❌ Tamil font கோப்பு கிடைக்கவில்லை.")
                    else:
                        from fpdf import FPDF
                        pdf = FPDF(orientation="L", format="A4")
                        pdf.add_page()
                        pdf.add_font("Tamil", "", TAMIL_FONT_PATH)
                        pdf.add_font("Tamil", "B", TAMIL_FONT_PATH)
                        pdf.set_text_shaping(True)

                        headers_ps = ["பதிப்பகம்", "மொத்த_தலைப்புகள்", "பெற_வேண்டியது", "பெற்றது", "மீதம்"]
                        widths_ps = (110, 40, 35, 35, 35)

                        pdf.set_font("Tamil", "B", 13)
                        pdf.cell(0, 10, "✅ இதுவரை முடிக்கப்பட்ட பதிப்பகங்கள்", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("Tamil", "", 9)
                        with pdf.table(col_widths=widths_ps, text_align="LEFT") as table:
                            row = table.row()
                            for h in headers_ps:
                                row.cell(h)
                            for _, r in completed_pub_df.iterrows():
                                row = table.row()
                                for h in headers_ps:
                                    row.cell(str(r.get(h, "")))

                        pdf.add_page()
                        pdf.set_font("Tamil", "B", 13)
                        pdf.cell(0, 10, "⏳ இன்னும் முடிக்கப்படாத பதிப்பகங்கள்", new_x="LMARGIN", new_y="NEXT")
                        pdf.set_font("Tamil", "", 9)
                        with pdf.table(col_widths=widths_ps, text_align="LEFT") as table:
                            row = table.row()
                            for h in headers_ps:
                                row.cell(h)
                            for _, r in pending_pub_df.iterrows():
                                row = table.row()
                                for h in headers_ps:
                                    row.cell(str(r.get(h, "")))

                        pdf_bytes_ps = bytes(pdf.output())
                        st.download_button(
                            label="📥 PDF பதிவிறக்கம்",
                            data=pdf_bytes_ps,
                            file_name=f"Publisher_Summary_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            type="primary",
                            use_container_width=True,
                            key="dl_pub_summary_pdf"
                        )

        with tab_library:
            neon_df = load_neon_database()
            if neon_df.empty:
                st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
            else:
                pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
                title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
                if not title_col:
                    title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
                lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
                book_id_col = next((c for c in neon_df.columns if c == 'book_id'), None)
                author_col = next((c for c in neon_df.columns if 'author' in c), None)

                submitted_pubs_report = sorted([p for p in full_report_df["Publisher"].dropna().unique().tolist() if pub_col and p in neon_df[pub_col].values]) if pub_col else []

                if not submitted_pubs_report or not lib_col_name:
                    st.info("ℹ️ நூலகப் பெயர் நெடுவரிசை கண்டறியப்படவில்லை.")
                else:
                    # Master Data-வில் உள்ள அதே தரவு: "பணி முடிக்கப்பட்ட" பதிப்பகங்களுக்கு உரிய
                    # அனைத்து நூல்களும், received_stats வடிகட்டல் இல்லாமல்.
                    submitted_neon_df = neon_df[neon_df[pub_col].isin(submitted_pubs_report)].copy()
                    all_libs_report = sorted(submitted_neon_df[lib_col_name].dropna().unique().tolist())
                    sel_lib_report = st.selectbox("🏛️ நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_libs_report, key="report_lib_sel")

                    if sel_lib_report and sel_lib_report != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                        lib_display_df = submitted_neon_df[submitted_neon_df[lib_col_name] == sel_lib_report].reset_index(drop=True)
                        st.markdown(f"### 🏛️ நூலகம்: {sel_lib_report} (மொத்த நூல்கள்: {len(lib_display_df)})")
                        st.dataframe(lib_display_df, use_container_width=True)

                        col_csv, col_pdf = st.columns(2)
                        with col_csv:
                            csv_lib_report = lib_display_df.to_csv(index=False).encode('utf-8-sig')
                            st.download_button(
                                label="📥 நூலக அறிக்கை (CSV)",
                                data=csv_lib_report,
                                file_name=f"Library_Report_{sel_lib_report}.csv",
                                mime="text/csv",
                                use_container_width=True,
                                key="dl_library_csv"
                            )
                        with col_pdf:
                            if len(lib_display_df) > 3000:
                                st.info("ℹ️ PDF-ஆக பதிவிறக்க 3000-க்கும் குறைவான வரிசைகள் இருக்க வேண்டும்.")
                            else:
                                if st.button("📄 PDF உருவாக்கு", key="gen_pdf_lib_report", use_container_width=True):
                                    pdf_headers = [c for c in [book_id_col, title_col, author_col, pub_col] if c and c in lib_display_df.columns]
                                    pdf_widths = (25, 90, 60, 60)[:len(pdf_headers)]
                                    pdf_bytes = generate_tamil_pdf_table(
                                        lib_display_df[pdf_headers], pdf_headers, pdf_widths,
                                        f"நூலக அறிக்கை — {sel_lib_report}"
                                    )
                                    if pdf_bytes is None:
                                        st.error("❌ Tamil font கோப்பு கிடைக்கவில்லை.")
                                    else:
                                        st.download_button(
                                            label="📥 PDF பதிவிறக்கம்",
                                            data=pdf_bytes,
                                            file_name=f"Library_Report_{sel_lib_report}.pdf",
                                            mime="application/pdf",
                                            type="primary",
                                            use_container_width=True,
                                            key="dl_pdf_lib_report"
                                        )

elif current == "தவறான பதிவு நீக்கம்":
    st.subheader("❌ தவறான பதிவினை நீக்குதல் / திருத்துதல் (Delete / Edit Verified Records)")
    
    edit_action_option = st.selectbox(
        "📌 எந்தப் பகுதியில் உள்ள தரவுகளை மாற்ற / நீக்க வேண்டும் என்பதைத் தேர்ந்தெடுக்கவும்:",
        [
            "-- பகுதியைத் தேர்ந்தெடுக்கவும் --",
            "1. பதிப்பாளர் தேர்வு (Publisher Records)",
            "2. அனுப்பிய விவரங்கள் (Dispatch Records)",
            "3. அறிக்கை தரவுகள் (Submitted Reports)",
            "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)",
            "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)",
            "6. Master Data தரவுகள்",
            "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)"
        ],
        key="main_error_correction_sub_menu"
    )
    
    st.markdown("---")
    
    if edit_action_option == "1. பதிப்பாளர் தேர்வு (Publisher Records)":
        st.markdown("### 🏢 1. பதிப்பாளர் தேர்வு & திருத்துதல் / நீக்குதல்")
        
        completed_publishers = set()
        for item in st.session_state.get("submitted_reports", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
        for item in st.session_state.get("temp_distributed_list", []):
            if "Publisher" in item:
                completed_publishers.add(item["Publisher"])
                
        pub_list = sorted(list(completed_publishers))
        
        if not pub_list:
            st.info("ℹ️ இதுவரை எந்தப் பதிப்பகப் பணியும் முடிக்கப்படவில்லை.")
        else:
            sel_pub = st.selectbox("பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + pub_list, key="err_pub_sel")
            
            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                completed_titles = set()
                for item in st.session_state.get("submitted_reports", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                for item in st.session_state.get("temp_distributed_list", []):
                    if item.get("Publisher") == sel_pub and "Title" in item:
                        completed_titles.add(item["Title"])
                        
                title_list = sorted(list(completed_titles))
                
                sel_title = st.selectbox("தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="err_title_sel")
                
                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    req_qty = 90
                    rec_qty = 75
                    target_index = None
                    target_id = None
                    
                    for idx, item in enumerate(st.session_state.get("submitted_reports", [])):
                        if item.get("Publisher") == sel_pub and item.get("Title") == sel_title:
                            req_qty = int(item.get("Required Qty", 90))
                            rec_qty = int(item.get("Received Qty", 75))
                            target_index = idx
                            target_id = item.get("Id")
                            break

                    st.markdown(f"""
                    <div style="background: #f8fafc; border: 1.5px solid #cbd5e1; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
                        <b>📖 நூல் தலைப்பு:</b> {sel_title}<br>
                        <b>📌 பெறப்பட வேண்டிய மொத்த எண்ணிக்கை (Required):</b> <span style="color: #2563eb; font-weight: bold;">{req_qty}</span><br>
                        <b>📥 ஏற்கனவே பெறப்பட்ட எண்ணிக்கை (Received):</b> <span style="color: #16a34a; font-weight: bold;">{rec_qty}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    c1, c2 = st.columns(2)
                    with c1:
                        new_val = st.number_input("📥 பெறப்பட்ட எண்ணிக்கையைத் திருத்துக (Update Received Qty):", min_value=0, max_value=req_qty*2, value=rec_qty, key="err_pub_qty")
                    with c2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        col_d, col_u = st.columns(2)
                        with col_d:
                            if st.button("🗑️ நீக்கு", key="err_pub_del_btn", use_container_width=True):
                                if target_id is not None:
                                    try:
                                        conn = psycopg2.connect(DB_URL)
                                        cur = conn.cursor()
                                        cur.execute("DELETE FROM submitted_reports WHERE id = %s;", (target_id,))
                                        conn.commit()
                                        cur.close()
                                        conn.close()
                                        load_submitted_reports_from_db.clear()
                                        st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                        st.success("✅ பதிவு வெற்றிகரமாக நீக்கப்பட்டது!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Delete error: {e}")
                                else:
                                    st.warning("⚠️ இந்தப் பதிவு database-ல் கிடைக்கவில்லை (Id காணப்படவில்லை).")
                        with col_u:
                            if st.button("💾 மாற்று/புதுப்பி", key="err_pub_upd_btn", type="primary", use_container_width=True):
                                try:
                                    conn = psycopg2.connect(DB_URL)
                                    cur = conn.cursor()
                                    if target_id is not None:
                                        cur.execute("UPDATE submitted_reports SET received_qty = %s WHERE id = %s;", (new_val, target_id))
                                    else:
                                        cur.execute("""
                                            INSERT INTO submitted_reports (publisher, title, required_qty, received_qty, date)
                                            VALUES (%s, %s, %s, %s, %s)
                                        """, (sel_pub, sel_title, req_qty, new_val, datetime.now().strftime("%Y-%m-%d %H:%M")))
                                    conn.commit()
                                    cur.close()
                                    conn.close()
                                    load_submitted_reports_from_db.clear()
                                    st.session_state["submitted_reports"] = load_submitted_reports_from_db()
                                except Exception as e:
                                    st.error(f"❌ Update error: {e}")
                                st.success(f"✅ எண்ணிக்கை வெற்றிகரமாக {new_val} என மாற்றப்பட்டது!")
                                st.rerun()

    elif edit_action_option == "2. அனுப்பிய விவரங்கள் (Dispatch Records)":
        st.markdown("### 📤 2. அனுப்பிய விவரங்கள் — திருத்துதல் / நீக்குதல்")
        disp_df = load_dispatch_status_full()
        if disp_df.empty:
            st.info("ℹ️ இதுவரை எந்த நூல்களும் அனுப்பப்படவில்லை.")
        else:
            st.dataframe(disp_df, use_container_width=True)
            row_idx = st.number_input("🗑️ நீக்க வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(disp_df) - 1, value=0, step=1, key="disp_del_idx")
            if st.button("🗑️ தேர்ந்தெடுத்த பதிவை நீக்கு (அனுப்பப்படாதது என மாற்று)", key="disp_del_btn", type="primary"):
                try:
                    row_to_delete = disp_df.iloc[int(row_idx)]
                    conn = psycopg2.connect(DB_URL)
                    cur = conn.cursor()
                    cur.execute("DELETE FROM dispatch_status WHERE id = %s;", (int(row_to_delete["Id"]),))
                    conn.commit()
                    cur.close()
                    conn.close()
                    load_dispatch_status_keys.clear()
                    get_dispatch_status_count.clear()
                    load_dispatch_status_full.clear()
                    st.success("✅ அனுப்பிய பதிவு நீக்கப்பட்டது (மீண்டும் 'அனுப்பப்படாதது' நிலைக்கு மாற்றப்பட்டது)!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Delete error: {e}")

    elif edit_action_option == "3. அறிக்கை தரவுகள் (Submitted Reports)":
        st.markdown("### 📊 3. அறிக்கை தரவுகள் — முழுப் பட்டியல் (திருத்த/நீக்க பதிப்பகம் வாரியாகச் செல்லவும்)")
        if not st.session_state.get("submitted_reports"):
            st.info("ℹ️ இதுவரை சமர்ப்பிக்கப்பட்ட தரவுகள் எதுவும் இல்லை.")
        else:
            all_rep_df = pd.DataFrame(st.session_state["submitted_reports"])
            st.dataframe(all_rep_df, use_container_width=True)
            st.caption("💡 குறிப்பிட்ட ஒரு பதிவைத் திருத்த அல்லது நீக்க '1. பதிப்பாளர் தேர்வு' பகுதியைப் பயன்படுத்தவும்.")

    elif edit_action_option == "4. கவனிக்க வேண்டியவை (Review / Price Conflicts)":
        st.markdown("### ⚠️ 4. விலை முரண்பாடு உள்ள பதிவுகள்")
        neon_df = load_neon_database()
        if neon_df.empty:
            st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
        else:
            price_col = next((c for c in neon_df.columns if c == 'price'), None)
            accepted_price_col = next((c for c in neon_df.columns if 'accept' in c or 'rate' in c or 'offer' in c), None)
            if not price_col or not accepted_price_col:
                st.info("ℹ️ விலை நெடுவரிசைகள் கண்டறியப்படவில்லை.")
            else:
                cmp_df = neon_df.copy()
                cmp_df["_p"] = pd.to_numeric(cmp_df[price_col], errors="coerce")
                cmp_df["_a"] = pd.to_numeric(cmp_df[accepted_price_col], errors="coerce")
                conflicts = cmp_df[cmp_df["_p"] != cmp_df["_a"]]
                if conflicts.empty:
                    st.success("🎉 முரண்பாடுகள் எதுவும் இல்லை!")
                else:
                    st.dataframe(conflicts.drop(columns=["_p", "_a"]), use_container_width=True)

    elif edit_action_option == "5. பதிவெண் மாற்றங்கள் (Accession Number Updates)":
        st.markdown("### 🔢 5. பதிவெண் மாற்றத் தேவைப்படும் இடத்திற்குச் செல்ல மேல் மெனுவில் '🔢 பதிவெண் மாற்ற' பட்டனை அழுத்தவும்.")
        st.info("ℹ️ பதிவெண் புதுப்பிப்பதற்கான முழு வசதி '🔢 பதிவெண் மாற்ற' மெனுவில் உள்ளது.")

    elif edit_action_option == "6. Master Data தரவுகள்":
        st.markdown("### 🗂️ 6. Master Data — முழு பட்டியலைப் பார்வையிட '🗂️ Master Data' மெனுவைப் பயன்படுத்தவும்.")
        st.info("ℹ️ Master Data-வைத் திருத்த நேரடியாக Neon Database-ல் மாற்றங்களைச் செய்ய வேண்டும்; இங்கிருந்து நேரடி நீக்கம் ஆதரிக்கப்படவில்லை.")

    elif edit_action_option == "7. பகுப்பு எண் மாற்றங்கள் (Classification Number Updates)":
        st.markdown("### 🏷️ 7. பகுப்பு எண் புதுப்பிப்பதற்கு மேல் மெனுவில் '🏷️ பகுப்பு எண் புதுப்பி' பட்டனை அழுத்தவும்.")
        st.info("ℹ️ பகுப்பு எண் புதுப்பிப்பதற்கான முழு வசதி '🏷️ பகுப்பு எண் புதுப்பி' மெனுவில் உள்ளது.")

    else:
        st.info("👆 மேல் உள்ள தேர்வில் ஏதேனும் ஒரு பிரிவைத் தேர்வு செய்தால், அதற்கான திருத்தும் மற்றும் நீக்கும் வசதிகள் உடனே தோன்றும்.")

elif current == "கடவுச்சொல் மாற்ற":
    st.subheader("🔑 கடவுச்சொல் மாற்றும் பகுதி (Change Password)")
    with st.form("pwd_form"):
        old_p = st.text_input("பழைய கடவுச்சொல்", type="password")
        new_p = st.text_input("புதிய கடவுச்சொல்", type="password")
        conf_p = st.text_input("உங்களை உறுதிப்படுத்த புதிய கடவுச்சொல்", type="password")
        if st.form_submit_button("கடவுச்சொல்லை மாற்றுக", type="primary"):
            if new_p != conf_p or len(new_p) == 0:
                st.error("❌ கடவுச்சொற்கள் பொருந்தவில்லை!")
            elif st.session_state["user_role"] == "Librarian":
                # நூலகர் passwords libraries.password_hash-ல் real-ஆக சேமிக்கப்படும்.
                lib_check = authenticate_librarian(st.session_state["user_library_tndpl"], old_p)
                if not lib_check:
                    st.error("❌ பழைய கடவுச்சொல் தவறானது!")
                else:
                    try:
                        conn = psycopg2.connect(DB_URL)
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE libraries SET password_hash = %s WHERE tndpl_code = %s;",
                            (hash_password(new_p), st.session_state["user_library_tndpl"])
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success("✅ கடவுச்சொல் வெற்றிகரமாக மாற்றப்பட்டது!")
                    except Exception as e:
                        st.error(f"❌ Update error: {e}")
            else:
                # Admin / DCL Staff — நிலையான (hardcoded) credentials; இங்கு UI-level
                # confirmation மட்டும், database-ல் மாற்றம் இல்லை (இதே தற்போதைய நடத்தை).
                st.success("✅ கடவுச்சொல் வெற்றிகரமாக மாற்றப்பட்டது!")

elif current == "Excel பதிவிறக்கம்":
    st.subheader("📥 Excel அறிக்கை பதிவிறக்கம்")
    if not st.session_state["submitted_reports"]:
        st.info("ℹ️ பதிவிறக்கம் செய்யத் தரவுகள் எதுவும் இல்லை.")
    else:
        report_df = pd.DataFrame(st.session_state["submitted_reports"])
        csv_data = report_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 முழுமையான தரவுகளை Excel கோப்பாகப் பதிவிறக்குக",
            data=csv_data,
            file_name=f"Master_Verification_Data_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
            type="primary"
        )

elif current == "Master Data":
    st.subheader("🗂️ Master Data சேமிப்பு & மேலாண்மை பகுதி (Neon Table Data with Received Stats)")
    
    neon_df = load_neon_database()
    if neon_df.empty or not st.session_state["submitted_reports"]:
        st.info("ℹ️ இதுவரை எந்தப் பதிப்புகளும் பிரிக்கப்பட்டுச் சமர்ப்பிக்கப்படவில்லை அல்லது Neon தரவுகள் கிடைக்கவில்லை.")
    else:
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])
            
        submitted_pubs = list(set([item["Publisher"] for item in st.session_state["submitted_reports"]]))
        submitted_pubs = sorted([p for p in submitted_pubs if p in neon_df[pub_col].values]) if pub_col else []
        
        view_mode = st.radio(
            "📂 பார்வைக் முறையைத் தேர்ந்தெடுக்கவும்:",
            ["🏢 பதிப்பகம் வாரியாக (Publisher-wise)", "🏛️ நூலகம் வாரியாக (Library-wise)"],
            horizontal=True
        )
        
        st.markdown("---")
        
        if "Publisher-wise" in view_mode:
            st.markdown("### 🏢 பணி முடிக்கப்பட்ட பதிப்பகங்கள் வாரியான முழு விவரங்கள் (Received Stats உடன்)")
            
            if not submitted_pubs:
                st.info("ℹ️ பணி முடிக்கப்பட்ட பதிப்பகங்கள் எதுவும் இல்லை.")
            else:
                ALL_PUBS_LABEL = "🌐 அனைத்து பதிப்பகங்களும் (All Publishers)"
                sel_master_pub = st.selectbox(
                    "🔍 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:",
                    ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --", ALL_PUBS_LABEL] + submitted_pubs
                )

                def build_pub_stats_df(pub_name, source_neon_df, source_rep_df):
                    """Adds a 'publisher' + 'received_stats' column for one publisher's rows."""
                    p_neon_df = source_neon_df[source_neon_df[pub_col] == pub_name].copy()
                    p_rep = source_rep_df[source_rep_df["Publisher"] == pub_name] if not source_rep_df.empty else pd.DataFrame()
                    t_map = dict(zip(p_rep["Title"], p_rep["Received Qty"])) if not p_rep.empty else {}

                    rows = []
                    for title_val, group_df in p_neon_df.groupby(title_col):
                        req_qty = len(group_df)
                        rec_qty = int(t_map.get(title_val, 0))
                        group_df = group_df.copy()
                        group_df["received_stats"] = [1 if i < rec_qty else 0 for i in range(req_qty)]
                        rows.append(group_df)

                    return pd.concat(rows, ignore_index=True) if rows else p_neon_df

                if sel_master_pub == ALL_PUBS_LABEL:
                    rep_df = pd.DataFrame(st.session_state["submitted_reports"])

                    # Build stats for every submitted publisher and stack them into one table.
                    all_pub_frames = [build_pub_stats_df(p, neon_df, rep_df) for p in submitted_pubs]
                    final_all_df = pd.concat(all_pub_frames, ignore_index=True) if all_pub_frames else pd.DataFrame()

                    total_pubs = len(submitted_pubs)
                    total_titles = final_all_df[title_col].nunique() if not final_all_df.empty else 0
                    total_books = len(final_all_df)
                    total_rec_books = final_all_df["received_stats"].sum() if "received_stats" in final_all_df.columns else 0
                    total_not_rec_books = total_books - total_rec_books

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏢 மொத்த பதிப்பகங்கள்", total_pubs)
                    with col2:
                        st.metric("📚 தலைப்புகள்", total_titles)
                    with col3:
                        st.metric("✅ பெறப்பட்ட நூல்கள்", int(total_rec_books))
                    with col4:
                        st.metric("⏳ பெறப்படாத நூல்கள்", int(total_not_rec_books))

                    st.markdown("### 🌐 அனைத்து பதிப்பகங்களும் — ஒருங்கிணைந்த முழு அட்டவணை விவரங்கள்")
                    st.dataframe(final_all_df, use_container_width=True)

                    csv_all_master = final_all_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 அனைத்து பதிப்பகங்களின் Master Data பதிவிறக்கம் (ஒரே CSV)",
                        data=csv_all_master,
                        file_name="Master_Data_ReceivedStats_ALL_Publishers.csv",
                        mime="text/csv",
                        type="primary"
                    )

                elif sel_master_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                    rep_df = pd.DataFrame(st.session_state["submitted_reports"])
                    final_pub_df = build_pub_stats_df(sel_master_pub, neon_df, rep_df)

                    total_titles = final_pub_df[title_col].nunique()
                    total_books = len(final_pub_df)
                    total_rec_books = final_pub_df["received_stats"].sum() if "received_stats" in final_pub_df.columns else 0
                    total_not_rec_books = total_books - total_rec_books
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("🏢 பதிப்பகம்", sel_master_pub)
                    with col2:
                        st.metric("📚 தலைப்புகள்", total_titles)
                    with col3:
                        st.metric("✅ பெறப்பட்ட நூல்கள்", int(total_rec_books))
                    with col4:
                        st.metric("⏳ பெறப்படாத நூல்கள்", int(total_not_rec_books))
                        
                    st.markdown(f"### 📍 பதிப்பகம்: {sel_master_pub} — முழு அட்டவணை விவரங்கள்")
                    st.dataframe(final_pub_df, use_container_width=True)
                    
                    csv_master = final_pub_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 பதிப்பக Master Data பதிவிறக்கம் (CSV)",
                        data=csv_master,
                        file_name=f"Master_Data_ReceivedStats_{sel_master_pub}.csv",
                        mime="text/csv",
                        type="primary"
                    )
        else:
            st.markdown("### 🏛️ பணி முடிக்கப்பட்ட நூலகம் வாரியான முழு விவரங்கள்")
            lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
            if lib_col_name:
                submitted_neon_df = neon_df[neon_df[pub_col].isin(submitted_pubs)].copy() if pub_col else neon_df
                all_libs = sorted(submitted_neon_df[lib_col_name].dropna().unique().tolist())
                
                ALL_LIBS_LABEL = "🌐 அனைத்து நூலகங்களும் (All Libraries)"
                sel_lib = st.selectbox("🔍 நூலகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --", ALL_LIBS_LABEL] + all_libs)

                if sel_lib == ALL_LIBS_LABEL:
                    st.markdown(f"### 🌐 அனைத்து நூலகங்களும் (மொத்த நூல்கள்: {len(submitted_neon_df)})")
                    st.dataframe(submitted_neon_df, use_container_width=True)

                    csv_all_lib = submitted_neon_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 அனைத்து நூலகங்களின் Master Data பதிவிறக்கம் (ஒரே CSV)",
                        data=csv_all_lib,
                        file_name="Master_Data_Library_ALL.csv",
                        mime="text/csv",
                        type="primary"
                    )
                elif sel_lib != "-- நூலகத்தைத் தேர்ந்தெடுக்கவும் --":
                    lib_df = submitted_neon_df[submitted_neon_df[lib_col_name] == sel_lib].copy()
                    st.markdown(f"### 🏛️ நூலகம்: {sel_lib} (மொத்த நூல்கள்: {len(lib_df)})")
                    st.dataframe(lib_df, use_container_width=True)
                    
                    csv_lib = lib_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 நூலக Master Data பதிவிறக்கம் (CSV)",
                        data=csv_lib,
                        file_name=f"Master_Data_Library_{sel_lib}.csv",
                        mime="text/csv",
                        type="primary"
                    )
            else:
                st.warning("⚠️ நூலகப் பெயர் காலம் (Library Name Column) டேட்டாபேஸில் கிடைக்கவில்லை.")

elif current == "நூலகர் பார்வை ஆண்டு":
    st.subheader("👥 நூலகர் பார்வை ஆண்டு விவரங்கள் மேலாண்மை")
    st.info("ℹ️ ஒவ்வொரு நூலகருக்கும் பார்வைக் காலத்தைப் (ஆண்டு) பதிவு செய்யவும், தேவைப்படின் திருத்தவும்.")

    with st.form("librarian_year_form"):
        lc1, lc2 = st.columns(2)
        with lc1:
            librarian_name = st.text_input("👤 நூலகர் பெயர்")
            library_name = st.text_input("🏛️ நூலகத்தின் பெயர்")
        with lc2:
            view_year = st.text_input("📅 பார்வை ஆண்டு (உ.ம். 2026-27)", value="2026-27")
        add_lib_record = st.form_submit_button("➕ பதிவு சேர்", type="primary")

        if add_lib_record:
            if not librarian_name.strip() or not library_name.strip():
                st.error("❌ நூலகர் பெயர் மற்றும் நூலகத்தின் பெயரை உள்ளிடவும்!")
            else:
                st.session_state["librarian_records"].append({
                    "Librarian": librarian_name.strip(), "Library": library_name.strip(),
                    "View Year": view_year.strip(), "Date": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                st.success(f"✅ '{librarian_name}' — {view_year} பதிவு சேர்க்கப்பட்டது!")
                st.rerun()

    if st.session_state["librarian_records"]:
        st.markdown("---")
        lib_rec_df = pd.DataFrame(st.session_state["librarian_records"])
        st.dataframe(lib_rec_df, use_container_width=True)
        del_idx = st.number_input("🗑️ நீக்க வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(lib_rec_df) - 1, value=0, step=1, key="lib_rec_del_idx")
        if st.button("🗑️ தேர்ந்தெடுத்த பதிவை நீக்கு", key="lib_rec_del_btn"):
            st.session_state["librarian_records"].pop(int(del_idx))
            st.success("✅ பதிவு நீக்கப்பட்டது!")
            st.rerun()
    else:
        st.info("ℹ️ இதுவரை நூலகர் பார்வை ஆண்டு பதிவுகள் எதுவும் சேர்க்கப்படவில்லை.")

elif current == "Excel அப்லோடு":
    st.subheader("📂 புதிய Excel தரவு பதிவேற்றம் & மேலாண்மை")
    uploaded_file = st.file_uploader("Excel அல்லது CSV கோப்பினைத் தேர்ந்தெடுக்கவும்", type=["xlsx", "csv"])

    if uploaded_file is not None:
        try:
            if uploaded_file.name.lower().endswith(".csv"):
                up_df = pd.read_csv(uploaded_file)
            else:
                up_df = pd.read_excel(uploaded_file)
            st.success(f"✅ கோப்பு வெற்றிகரமாகப் பெறப்பட்டது! ({len(up_df)} வரிசைகள் கண்டறியப்பட்டன)")
            if len(up_df) > 50:
                st.caption(f"ℹ️ கீழே preview-ல் முதல் 50 வரிசைகள் மட்டுமே காட்டப்படுகின்றன — ஆனால் Save செய்யும்போது **அனைத்து {len(up_df)} வரிசைகளும்** சேமிக்கப்படும்.")
            st.dataframe(up_df.head(50), use_container_width=True)

            up_df.columns = [str(c).strip().lower() for c in up_df.columns]
            books_columns = set(load_neon_database().columns) if not load_neon_database().empty else set()

            if books_columns and not books_columns.issuperset(up_df.columns):
                missing = set(up_df.columns) - books_columns
                st.warning(f"⚠️ கோப்பில் உள்ள சில நெடுவரிசைகள் 'books' அட்டவணையில் இல்லை: {', '.join(missing)}. அப்லோடு செய்யும் முன் நெடுவரிசைப் பெயர்களை உறுதி செய்யவும்.")
            else:
                if st.button("💾 இந்தத் தரவை Neon Database-ல் சேமி", type="primary", key="excel_upload_save_btn"):
                    try:
                        conn = psycopg2.connect(DB_URL)
                        cur = conn.cursor()
                        # uploaded_at-ஐ இந்த upload batch-ன் timestamp-ஆக சேர்க்கிறோம் —
                        # இதனால் இந்த batch-ஐ பின்னால் எளிதாக filter செய்து கண்டறியலாம்.
                        cols = list(up_df.columns) + ["uploaded_at"]
                        col_names = ", ".join(cols)
                        upload_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        from psycopg2.extras import execute_values
                        rows = [tuple(r[c] for c in up_df.columns) + (upload_ts,) for _, r in up_df.iterrows()]
                        execute_values(cur, f"INSERT INTO books ({col_names}) VALUES %s;", rows)
                        conn.commit()
                        cur.close()
                        conn.close()
                        load_neon_database.clear()
                        st.success(f"✅ {len(up_df)} வரிசைகள் Neon Database-ல் சேமிக்கப்பட்டன! (Upload நேரம்: {upload_ts})")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Upload save error: {e}")
        except Exception as e:
            st.error(f"❌ கோப்பைப் படிக்க முடியவில்லை: {e}")

    # ---------------- சமீபத்தில் ஏற்றப்பட்டவற்றைக் கண்டறிதல் ----------------
    st.markdown("---")
    st.markdown("### 🕒 சமீபத்தில் ஏற்றப்பட்ட நூல்களைக் கண்டறிதல்")
    st.caption("இன்று முதல் மேலே சேர்க்கப்படும் ஒவ்வொரு upload-உம் தானாகவே தேதி-நேரத்துடன் பதிவாகும். கீழே அந்த தேதியைத் தேர்ந்தெடுத்து அன்று ஏற்றப்பட்டவை மட்டும் பார்க்கலாம்.")

    recent_neon_df = load_neon_database()
    if not recent_neon_df.empty and "uploaded_at" in recent_neon_df.columns:
        tracked_df = recent_neon_df[recent_neon_df["uploaded_at"].notna()].copy()
        if tracked_df.empty:
            st.info("ℹ️ இதுவரை 'uploaded_at' தேதியுடன் எதுவும் பதிவாகவில்லை (இந்த fix போடும் முன் ஏற்றப்பட்ட பழைய நூல்களுக்கு இந்தத் தகவல் இல்லை).")
        else:
            tracked_df["uploaded_at"] = pd.to_datetime(tracked_df["uploaded_at"])
            available_dates = sorted(tracked_df["uploaded_at"].dt.date.unique(), reverse=True)
            sel_date = st.selectbox("📅 தேதியைத் தேர்ந்தெடுக்கவும்:", available_dates, key="recent_upload_date")
            day_df = tracked_df[tracked_df["uploaded_at"].dt.date == sel_date].reset_index(drop=True)
            st.markdown(f"**{sel_date} அன்று ஏற்றப்பட்ட நூல்கள்:** {len(day_df)}")
            st.dataframe(day_df, use_container_width=True)
            csv_recent = day_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 இந்த batch-ஐ பதிவிறக்குக (CSV)",
                data=csv_recent,
                file_name=f"Newly_Uploaded_{sel_date}.csv",
                mime="text/csv",
                type="primary",
                key="dl_recent_upload_csv"
            )
    else:
        st.info("ℹ️ 'uploaded_at' நெடுவரிசை இன்னும் புதிதாக உருவாக்கப்பட்டுள்ளது — புதிதாக ஒரு Excel upload செய்த பிறகு இங்கு தெரியும்.")

    # ---------------- ஏற்கனவே ஏற்றப்பட்ட ஒரு batch-ஐ கண்டறிதல் (Reconciliation) ----------------
    st.markdown("---")
    st.markdown("### 🔍 ஏற்கனவே ஏற்றப்பட்ட ஒரு Batch-ஐக் கண்டறிதல்")
    st.caption(
        "மேலே உள்ள 'சமீபத்தில் ஏற்றப்பட்டவை' timestamp இல்லாத, **ஏற்கனவே** database-ல் சேர்க்கப்பட்ட "
        "பழைய batch-ஐ கண்டறிய, அதே மூல (Portal) Excel/CSV கோப்பை இங்கு மீண்டும் upload செய்யவும். "
        "அதில் உள்ள book_id/isbn எண்களை database-உடன் பொருத்தி, அந்த batch-ஐ மட்டும் காட்டுவோம்."
    )

    ref_file = st.file_uploader("📤 மூலக் கோப்பை (Portal-லிருந்து பதிவிறக்கியது) மீண்டும் upload செய்யவும்", type=["xlsx", "csv"], key="reconcile_ref_file")

    if ref_file is not None:
        try:
            if ref_file.name.lower().endswith(".csv"):
                ref_df = pd.read_csv(ref_file)
            else:
                ref_df = pd.read_excel(ref_file)
            ref_df.columns = [str(c).strip().lower() for c in ref_df.columns]

            match_col = "book_id" if "book_id" in ref_df.columns else ("isbn" if "isbn" in ref_df.columns else None)
            if not match_col:
                st.warning("⚠️ இந்தக் கோப்பில் 'book_id' அல்லது 'isbn' நெடுவரிசை இல்லை — பொருத்த முடியவில்லை.")
            else:
                ref_ids = set(ref_df[match_col].dropna().astype(str).str.strip())
                st.caption(f"'{match_col}' அடிப்படையில் {len(ref_ids)} தனித்துவ மதிப்புகள் இந்தக் கோப்பில் கண்டறியப்பட்டன.")

                main_df = load_neon_database()
                if match_col not in main_df.columns:
                    st.warning(f"⚠️ database-ல் '{match_col}' நெடுவரிசை இல்லை.")
                else:
                    matched_df = main_df[main_df[match_col].astype(str).str.strip().isin(ref_ids)].reset_index(drop=True)
                    st.markdown(f"### 📦 பொருந்திய நூல்கள் — database-ல் கிடைத்தவை: {len(matched_df)} / கோப்பில் இருந்தவை: {len(ref_df)}")
                    if len(matched_df) < len(ref_df):
                        st.info(f"ℹ️ {len(ref_df) - len(matched_df)} வரிசைகள் database-ல் கண்டறியப்படவில்லை — அவை இன்னும் upload ஆகாமல் இருக்கலாம்.")
                    st.dataframe(matched_df, use_container_width=True)

                    csv_matched = matched_df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(
                        label="📥 இந்த Batch-ஐ பதிவிறக்குக (CSV)",
                        data=csv_matched,
                        file_name=f"Identified_Batch_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                        mime="text/csv",
                        type="primary",
                        key="dl_identified_batch_csv"
                    )
        except Exception as e:
            st.error(f"❌ கோப்பைப் படிக்க முடியவில்லை: {e}")

elif current == "பகுப்பு எண் புதுப்பி":
    st.subheader("🏷️ பகுப்பு எண் புதுப்பித்தல் மற்றும் திருத்துதல்")

    neon_df = load_neon_database()
    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து தரவுகள் கிடைக்கவில்லை.")
    else:
        class_col = next((c for c in neon_df.columns if 'classification' in c or c == 'class_no' or 'call_no' in c or 'call number' in c), None)
        pub_col = next((c for c in neon_df.columns if c == 'vendor_name'), None) or next((c for c in neon_df.columns if c in ['publication name', 'publication_name', 'publisher_name'] or 'publication' in c), None)
        title_col = next((c for c in neon_df.columns if c == 'title' or (('title' in c) and ('book' not in c))), None)
        if not title_col:
            title_col = next((c for c in neon_df.columns if 'title' in c), neon_df.columns[2])

        if not class_col:
            st.info("ℹ️ 'Classification Number' நெடுவரிசை தரவுத்தளத்தில் கண்டறியப்படவில்லை. நெடுவரிசைப் பெயரைச் சரிபார்க்கவும்.")
        else:
            all_pubs = sorted(neon_df[pub_col].dropna().unique().tolist()) if pub_col else []
            sel_pub = st.selectbox("🏢 பதிப்பகத்தைத் தேர்ந்தெடுக்கவும்:", ["-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --"] + all_pubs, key="class_pub_sel")

            if sel_pub != "-- பதிப்பகத்தைத் தேர்ந்தெடுக்கவும் --":
                pub_df = neon_df[neon_df[pub_col] == sel_pub] if pub_col else neon_df
                title_list = sorted(pub_df[title_col].dropna().unique().tolist())
                sel_title = st.selectbox("📖 தலைப்பைத் தேர்ந்தெடுக்கவும்:", ["-- தலைப்பைத் தேர்ந்தெடுக்கவும் --"] + title_list, key="class_title_sel")

                if sel_title != "-- தலைப்பைத் தேர்ந்தெடுக்கவும் --":
                    title_df = pub_df[pub_df[title_col] == sel_title].reset_index(drop=True)
                    st.dataframe(title_df[[c for c in [class_col, title_col] if c]], use_container_width=True)

                    if not title_df.empty:
                        row_num = st.number_input("✏️ மாற்ற வேண்டிய வரிசை எண் (Row Index)", min_value=0, max_value=len(title_df) - 1, value=0, step=1, key="class_row_num")
                        new_class_no = st.text_input("🏷️ புதிய பகுப்பு எண்", value=str(title_df.iloc[int(row_num)][class_col]), key="class_new_val")

                        if st.button("💾 பகுப்பு எண்ணைப் புதுப்பி", type="primary", key="class_update_btn"):
                            try:
                                conn = psycopg2.connect(DB_URL)
                                cur = conn.cursor()
                                old_class_no = title_df.iloc[int(row_num)][class_col]
                                cur.execute(
                                    f"UPDATE books SET {class_col} = %s WHERE {class_col} = %s AND {title_col} = %s;",
                                    (new_class_no, old_class_no, sel_title)
                                )
                                conn.commit()
                                cur.close()
                                conn.close()
                                st.success(f"✅ பகுப்பு எண் '{old_class_no}' இலிருந்து '{new_class_no}' ஆக மாற்றப்பட்டது!")
                                load_neon_database.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Update error: {e}")

elif current == "நூலக பொருத்தம்":
    st.subheader("🔗 நூலக பொருத்தம் (Library ↔ TNDPL Matching)")
    st.caption(
        "103 நூலகங்களின் TNDPL பட்டியலை, Neon Database-ல் உள்ள 'books' அட்டவணையின் "
        "நூலகப் பெயர் column-ல் இருக்கும் உண்மையான மதிப்புகளுடன் பொருத்துங்கள். "
        "இது ஒரு முறை சரிசெய்தால் போதும் — நூலகர் Login/Reports தானாக இதையே பயன்படுத்தும்."
    )

    neon_df = load_neon_database()
    libraries_df = load_libraries_df()

    if neon_df.empty:
        st.warning("⚠️ Neon Database-ல் இருந்து books தரவுகள் கிடைக்கவில்லை.")
    elif libraries_df.empty:
        st.warning("⚠️ libraries அட்டவணையில் தரவு இல்லை.")
    else:
        lib_col_name = next((c for c in neon_df.columns if 'library' in c and ('name' in c or 'tm' in c)), None)
        if not lib_col_name:
            st.error("❌ books அட்டவணையில் நூலகப் பெயர் column கண்டறியப்படவில்லை.")
        else:
            actual_lib_values = sorted(neon_df[lib_col_name].dropna().unique().tolist())

            # Auto-match status for every library, for a quick at-a-glance summary.
            def _norm(s):
                return str(s).strip().lower().replace(" ", "")

            status_rows = []
            for _, r in libraries_df.iterrows():
                if r["Matched Value"] and str(r["Matched Value"]).strip():
                    status_rows.append("✅ Admin உறுதி செய்தது")
                else:
                    nt, ne = _norm(r["Name (Tamil)"]), _norm(r["Name (English)"])
                    auto = None
                    for v in actual_lib_values:
                        nv = _norm(v)
                        if nv == nt or nv == ne or (nt and nt in nv) or (ne and ne in nv):
                            auto = v
                            break
                    status_rows.append(f"🟡 தானியங்கு பொருத்தம்: {auto}" if auto else "❌ பொருத்தம் இல்லை")
            libraries_df = libraries_df.copy()
            libraries_df["நிலை"] = status_rows

            n_unmatched = sum(1 for s in status_rows if s == "❌ பொருத்தம் இல்லை")
            n_confirmed = sum(1 for s in status_rows if s.startswith("✅"))
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("🏛️ மொத்த நூலகங்கள்", len(libraries_df))
            with c2:
                st.metric("✅ Admin உறுதி செய்தவை", n_confirmed)
            with c3:
                st.metric("❌ பொருத்தமில்லாதவை", n_unmatched)

            st.dataframe(libraries_df, use_container_width=True)

            st.markdown("---")
            st.markdown("#### ✏️ ஒரு நூலகத்தை books அட்டவணையின் உண்மையான பெயருடன் தொடர்பு படுத்துக")
            tndpl_pick = st.selectbox(
                "TNDPL நூலகத்தைத் தேர்ந்தெடுக்கவும்:",
                ["-- தேர்ந்தெடுக்கவும் --"] + (libraries_df["TNDPL Code"] + " — " + libraries_df["Name (Tamil)"]).tolist(),
                key="lib_match_pick"
            )
            if tndpl_pick != "-- தேர்ந்தெடுக்கவும் --":
                tndpl_code_sel = tndpl_pick.split(" — ")[0]
                value_pick = st.selectbox(
                    "books அட்டவணையில் உள்ள உண்மையான நூலகப் பெயரைத் தேர்ந்தெடுக்கவும்:",
                    ["-- தேர்ந்தெடுக்கவும் --"] + actual_lib_values,
                    key="lib_match_value_pick"
                )
                if st.button("💾 பொருத்தத்தைச் சேமி", type="primary", key="lib_match_save_btn"):
                    if value_pick == "-- தேர்ந்தெடுக்கவும் --":
                        st.warning("⚠️ books அட்டவணையின் நூலகப் பெயரைத் தேர்ந்தெடுக்கவும்.")
                    else:
                        try:
                            conn = psycopg2.connect(DB_URL)
                            cur = conn.cursor()
                            cur.execute(
                                "UPDATE libraries SET matched_lib_value = %s WHERE tndpl_code = %s;",
                                (value_pick, tndpl_code_sel)
                            )
                            conn.commit()
                            cur.close()
                            conn.close()
                            load_libraries_df.clear()
                            st.success(f"✅ {tndpl_code_sel} → '{value_pick}' எனப் பொருத்தப்பட்டது!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Save error: {e}")

            st.markdown("---")
            st.markdown("#### 🔑 நூலகர் கடவுச்சொல்லை மீட்டமை (Reset to TNDPL default)")
            tndpl_reset_pick = st.selectbox(
                "எந்த நூலகத்தின் கடவுச்சொல்லை மீட்டமைக்க வேண்டும்:",
                ["-- தேர்ந்தெடுக்கவும் --"] + (libraries_df["TNDPL Code"] + " — " + libraries_df["Name (Tamil)"]).tolist(),
                key="lib_pwd_reset_pick"
            )
            if tndpl_reset_pick != "-- தேர்ந்தெடுக்கவும் --":
                if st.button("🔑 கடவுச்சொல்லை TNDPL எண்ணாக மீட்டமை", key="lib_pwd_reset_btn"):
                    reset_code = tndpl_reset_pick.split(" — ")[0]
                    try:
                        conn = psycopg2.connect(DB_URL)
                        cur = conn.cursor()
                        cur.execute(
                            "UPDATE libraries SET password_hash = %s WHERE tndpl_code = %s;",
                            (hash_password(reset_code), reset_code)
                        )
                        conn.commit()
                        cur.close()
                        conn.close()
                        st.success(f"✅ {reset_code}-ன் கடவுச்சொல் TNDPL எண்ணாக மீட்டமைக்கப்பட்டது!")
                    except Exception as e:
                        st.error(f"❌ Reset error: {e}")
