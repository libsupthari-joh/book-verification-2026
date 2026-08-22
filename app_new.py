import streamlit as st

st.markdown("""
<style>
    /* 1. பதிப்பகத்தை மாற்றுக (ஆரஞ்சு நிறம்) */
    div.stButton > button[key="change_vendor"] {
        background: linear-gradient(to bottom, #ff7e5f, #feb47b) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 0px #d9534f, 0px 5px 10px rgba(0,0,0,0.3) !important;
        font-weight: bold !important;
    }
    div.stButton > button[key="change_vendor"]:active {
        box-shadow: 0px 1px 0px #d9534f !important;
        transform: translateY(3px) !important;
    }

    /* 2. கூகுள் ஷீட்டில் சேமி (பச்சை நிறம் 3D Button) */
    div.stButton > button[key="save_sheet"] {
        background: linear-gradient(to bottom, #28a745, #218838) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 0px #1e7e34, 0px 5px 10px rgba(0,0,0,0.3) !important;
        font-weight: bold !important;
    }
    div.stButton > button[key="save_sheet"]:active {
        box-shadow: 0px 1px 0px #1e7e34 !important;
        transform: translateY(3px) !important;
    }

    /* 3. பட்டியலை அழி (சிவப்பு நிறம் 3D Button) */
    div.stButton > button[key="clear_list"] {
        background: linear-gradient(to bottom, #dc3545, #c82333) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 0px #bd2130, 0px 5px 10px rgba(0,0,0,0.3) !important;
        font-weight: bold !important;
    }
    div.stButton > button[key="clear_list"]:active {
        box-shadow: 0px 1px 0px #bd2130 !important;
        transform: translateY(3px) !important;
    }
</style>
""", unsafe_allow_html=True)

# Streamlit Buttons (key கட்டாயம் சேர்க்க வேண்டும்)
col1, col2 = st.columns([3, 1])
with col2:
    st.button("🔄 பதிப்பகத்தை மாற்றுக", key="change_vendor")

col_a, col_b = st.columns(2)
with col_a:
    st.button("💾 கூகுள் ஷீட்டில் சேமி (Save All to Sheet)", key="save_sheet")
with col_b:
    st.button("🗑️ பட்டியலை அழி (Clear)", key="clear_list")
