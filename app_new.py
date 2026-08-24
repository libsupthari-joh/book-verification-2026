import hashlib
import hmac
import io
import os
import re
import secrets as py_secrets
import time
from datetime import datetime
from xml.sax.saxutils import escape as xml_escape
import gspread
from gspread.cell import Cell
import pandas as pd
import streamlit as st
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

PDF_FONT_REGULAR = None
PDF_FONT_BOLD = None
PDF_FONT_ERROR = None


def _find_font(font_dir, names):
    candidates = []
    for name in names:
        candidates.extend(
            [
                os.path.join(font_dir, name),
                os.path.join(os.getcwd(), "fonts", name),
                os.path.join("/usr/share/fonts/truetype/noto", name),
                os.path.join("/usr/share/fonts/truetype/freefont", name),
            ]
        )
    return next((path for path in candidates if os.path.isfile(path)), None)


def _load_pdf_fonts():
    global PDF_FONT_REGULAR, PDF_FONT_BOLD
    font_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
    font_pairs = [
        (("NotoSansTamil-Regular.ttf",), ("NotoSansTamil-Bold.ttf",)),
        (("FreeSans.ttf",), ("FreeSansBold.ttf",)),
    ]
    regular_path = bold_path = None
    for regular_names, bold_names in font_pairs:
        regular_path = _find_font(font_dir, regular_names)
        if regular_path:
            bold_path = _find_font(font_dir, bold_names)
            break

    if not regular_path:
        raise FileNotFoundError(
            "Tamil PDF font missing. Add fonts/NotoSansTamil-Regular.ttf "
            "or fonts/FreeSans.ttf to the application."
        )

    pdfmetrics.registerFont(TTFont("TamilUI", regular_path))
    PDF_FONT_REGULAR = "TamilUI"
    PDF_FONT_BOLD = PDF_FONT_REGULAR

    pdfmetrics.registerFontFamily(
        "TamilUI",
        normal=PDF_FONT_REGULAR,
        bold=PDF_FONT_BOLD,
        italic=PDF_FONT_REGULAR,
        boldItalic=PDF_FONT_BOLD,
    )


try:
    _load_pdf_fonts()
except Exception as font_error:
    PDF_FONT_ERROR = font_error

st.set_page_config(
    page_title="2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, maximum-scale=5\">\n"
    "<style>\n"
    ":root{--navy:#071a38;--blue:#1565c0;--cyan:#00acc1;--gold:#f59e0b}\n"
    "</style>",
    unsafe_allow_html=True
)

def main():
    st.title("2026ஆம் ஆண்டு வெளிப்படைத் தன்மை நூல்கள் கொள்முதல்")
    st.write("வணக்கம்! பயன்பாடு வெற்றிகரமாக தொடங்கWeirது.")

if __name__ == "__main__":
    main()
