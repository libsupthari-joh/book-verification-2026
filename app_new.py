import hashlib
import hmac
import io
import os
import re
import time
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from gspread.cell import Cell
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

st.set_page_config(page_title="2026 நூல்கள் கொள்முதல்", page_icon="📚", layout="wide")

# -----------------------------
# CONFIGURATION
# -----------------------------
EXCEL_FILE = "Book Supply-2026.xlsx"
SPREADSHEET_ID = "1LNogKaLvdqkoITSLE971jTBIy9QO4s90j1WDxY1cDrc"
DRIVE_FOLDER_ID = "1XOTSn8f6ntfrG8rI0iSk0QVwDujGqs1f"

# -----------------------------
# TAMIL FONT REGISTRATION
# -----------------------------
def register_pdf_fonts():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    regular_candidates = [
        os.path.join(base_dir, "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "fonts", "NotoSansTamil-Regular.ttf"),
        os.path.join(base_dir, "NotoSansTamil[wght].ttf"),
    ]
    bold_candidates = [
        os.path.join(base_dir, "NotoSansTamil-Bold.ttf"),
        os.path.join(base_dir, "fonts", "NotoSansTamil-Bold.ttf"),
        os.path.join(base_dir, "NotoSansTamil[wght].ttf"),
    ]

    regular = next((p for p in regular_candidates if os.path.exists(p)), None)
    bold = next((p for p in bold_candidates if os.path.exists(p)), None)

    if regular:
        try:
            pdfmetrics.registerFont(TTFont("TamilRegular", regular))
            if bold:
                pdfmetrics.registerFont(TTFont("TamilBold", bold))
            else:
                pdfmetrics.registerFont(TTFont("TamilBold", regular))
            return "TamilRegular", "TamilBold", True
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold", False

PDF_REGULAR, PDF_BOLD, TAMIL_FONT_AVAILABLE = register_pdf_fonts()

# -----------------------------
# TEXT AND FILE HELPERS
# -----------------------------
def safe_name(value):
    value = re.sub(r"[^\w\u0B80-\u0BFF -]", "", str(value)).strip()
    return value[:80] or "Report"

def vendor_number(vendor_id_name, vendor_name):
    text = str(vendor_id_name or vendor_name).strip()
    match = re.search(r"\d+", text)
    return match.group(0) if match else "000"

def make_pdf(df, title):
    """தமிழ் font உடன் PDF உருவாக்கும் Function."""
    output = io.BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=7 * mm,
        leftMargin=7 * mm,
        topMargin=7 * mm,
        bottomMargin=7 * mm,
    )

    title_style = ParagraphStyle(
        "TamilTitle",
        fontName=PDF_BOLD,
        fontSize=14,
        leading=18,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#071a38"),
    )
    body_style = ParagraphStyle(
        "TamilBody",
        fontName=PDF_REGULAR,
        fontSize=7,
        leading=9,
    )
    header_style = ParagraphStyle(
        "TamilHeader",
        fontName=PDF_BOLD,
        fontSize=7,
        leading=9,
        textColor=colors.white,
    )

    columns = list(df.columns)
    table_data = [[Paragraph(str(column), header_style) for column in columns]]
    for row in df.fillna("").astype(str).values.tolist():
        table_data.append([Paragraph(str(value)[:120], body_style) for value in row])

    widths = []
    for column in columns:
        values = [str(column)] + [str(value) for value in df[column].head(25).tolist()]
        max_len = max([len(value) for value in values], default=10)
        widths.append(max(20 * mm, min(58 * mm, (max_len + 2) * 1.1 * mm)))

    table = Table(table_data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b3d91")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#9db6d5")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef5ff")]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
    ]))

    document.build([
        Paragraph(str(title), title_style),
        Spacer(1, 4 * mm),
        table,
    ])
    return output.getvalue()

# -----------------------------
# GOOGLE DRIVE AUTHENTICATION
# -----------------------------
@st.cache_resource
def get_drive_service():
    """Streamlit secrets மூலம் Google Drive API service உருவாக்கும் Function."""
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError(".streamlit/secrets.toml-ல் gcp_service_account இல்லை.")

    service_account_info = dict(st.secrets["gcp_service_account"])
    required_keys = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [key for key in required_keys if not service_account_info.get(key)]
    if missing:
        raise RuntimeError(f"Service Account secrets-ல் இவை இல்லை: {', '.join(missing)}")

    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)

def upload_pdf_to_drive(pdf_data, vendor_id_name, vendor_name):
    """PDF-ஐ குறிப்பிட்ட Drive Folder-ல் சேமிக்கும் Function."""
    if not DRIVE_FOLDER_ID:
        raise RuntimeError("DRIVE_FOLDER_ID காலியாக உள்ளது.")

    number = vendor_number(vendor_id_name, vendor_name)
    file_name = f"{number}_{safe_name(vendor_name).replace(' ', '_')}_Physical_Verification.pdf"

    service = get_drive_service()
    metadata = {
        "name": file_name,
        "mimeType": "application/pdf",
        "parents": [DRIVE_FOLDER_ID],
    }
    media = MediaIoBaseUpload(
        io.BytesIO(pdf_data),
        mimetype="application/pdf",
        resumable=True,
    )

    created = service.files().create(
        body=metadata,
        media_body=media,
        fields="id,name,parents,webViewLink",
        supportsAllDrives=True,
    ).execute()
    return created

# -----------------------------
# TASK 1 INTEGRATION
# -----------------------------
# உங்கள் முழு கோட்டில் Task 1-ன் temporary records உருவான பிறகு,
# கீழே உள்ள பகுதியை அப்படியே பயன்படுத்தவும்.

def render_task1_pdf_and_drive(records, completed_vendor_name, vendor_id_map):
    if not records:
        return

    pdf_df = pd.DataFrame(records)
    display_cols = [
        "Title", "Author Name", "Language", "Total Qty",
        "Received", "Not Received", "Short / Extra", "Date",
    ]
    pdf_df = pdf_df[[column for column in display_cols if column in pdf_df.columns]]
    pdf_data = make_pdf(pdf_df, f"{completed_vendor_name} - Physical Verification")
    number = vendor_number(vendor_id_map.get(completed_vendor_name), completed_vendor_name)
    prefix = f"{number}_{safe_name(completed_vendor_name).replace(' ', '_')}_Physical_Verification"

    st.markdown("### 📥 பதிப்பக அறிக்கை")
    if not TAMIL_FONT_AVAILABLE:
        st.warning("⚠️ NotoSansTamil Font கிடைக்கவில்லை. PDF-ல் தமிழ் எழுத்துகள் சரியாக வர, NotoSansTamil-Regular.ttf கோப்பை Python கோப்புடன் வைக்கவும்.")

    st.download_button(
        "🧾 PDF பதிவிறக்கம்",
        data=pdf_data,
        file_name=f"{prefix}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key=f"pdf_download_{number}",
    )

    if st.button("☁️ PDF-ஐ Google Drive-ல் சேமிக்கவும்", use_container_width=True, key=f"drive_save_{number}"):
        try:
            with st.spinner("Google Drive-ல் PDF சேமிக்கப்படுகிறது..."):
                uploaded = upload_pdf_to_drive(
                    pdf_data,
                    vendor_id_map.get(completed_vendor_name, completed_vendor_name),
                    completed_vendor_name,
                )
            st.success(f"✅ Drive-ல் வெற்றிகரமாக சேமிக்கப்பட்டது: {uploaded.get('name', prefix + '.pdf')}")
            if uploaded.get("webViewLink"):
                st.markdown(f"[📂 Drive கோப்பைத் திறக்கவும்]({uploaded['webViewLink']})")
        except Exception as error:
            st.error("❌ Google Drive சேமிப்பு தோல்வியடைந்தது.")
            st.code(str(error))
            st.info("Service Account Email-ஐ Google Drive Folder-ல் Editor ஆக Share செய்துள்ளீர்களா என்பதைச் சரிபார்க்கவும்.")

# ============================================================
# FULL APP INTEGRATION NOTE
# ============================================================
# உங்கள் தற்போதைய முழு application-ல் உள்ள Task 1 பகுதியில்:
#
# 1. பழைய pdf_bytes() Function-ஐ நீக்கி, மேலுள்ள make_pdf() Function-ஐ பயன்படுத்தவும்.
# 2. பழைய upload_pdf_to_drive() Function-ஐ நீக்கி, மேலுள்ள Function-ஐ பயன்படுத்தவும்.
# 3. temporary records காட்டும் இடத்தில்:
#
# render_task1_pdf_and_drive(
#     st.session_state["temp_verified_records"],
#     completed_vendor_name,
#     vendor_id_map,
# )
#
# என்பதைச் சேர்க்கவும்.
# 4. Google Sheet-ல் சேமித்த பிறகு Drive-ல் தானாக சேமிக்க வேண்டுமெனில்,
#    upload_pdf_to_drive() அழைப்பை Save block-க்குள் வைக்கலாம்.
#    தனி Button வேண்டுமெனில் மேலுள்ள Button போதுமானது.

# ============================================================
# GOOGLE CLOUD / DRIVE CHECKLIST
# ============================================================
# 1. Google Cloud Console-ல் Google Drive API Enable செய்யவும்.
# 2. Service Account Email-ஐ Drive Folder-ல் Editor ஆக Share செய்யவும்.
# 3. secrets.toml-ல் முழுமையான Service Account JSON values இருக்க வேண்டும்:
#
# [gcp_service_account]
# type = "service_account"
# project_id = "..."
# private_key_id = "..."
# private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
# client_email = "...iam.gserviceaccount.com"
# client_id = "..."
# auth_uri = "https://accounts.google.com/o/oauth2/auth"
# token_uri = "https://oauth2.googleapis.com/token"
# auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
# client_x509_cert_url = "..."
#
# 4. PDF-ல் தமிழ் எழுத்துகளுக்கு NotoSansTamil-Regular.ttf அவசியம்.
