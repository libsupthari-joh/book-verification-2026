import streamlit as st
import pandas as pd
import io

# உங்கள் நூலகத் தரவு (DataFrame)
# df = ... 

st.subheader("பதிவிறக்க தேர்வுகள் (Download Options)")

# 1. CSV கோப்பாக பதிவிறக்கம் செய்ய
csv_data = df.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="📥 CSV கோப்பாக பதிவிறக்கவும்",
    data=csv_data,
    file_name="library_books_distribution.csv",
    mime="text/csv",
)

# 2. Excel கோப்பாக பதிவிறக்கம் செய்ய (openpyxl நூலகம் தேவை)
output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name="Books Distribution")
excel_data = output.getvalue()

st.download_button(
    label="📊 Excel கோப்பாக பதிவிறக்கவும்",
    data=excel_data,
    file_name="library_books_distribution.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
