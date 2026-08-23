import pandas as pd
import streamlit as st

# பக்க அமைவு (Page Configuration)
st.set_page_config(
    page_title="Library Book Verification Portal",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title(
    "📚 தமிழ்நாடு நூலகத்துறை - நூல்கள் சரிபார்ப்பு மற்றும் பதிப்பாளர் மேலாண்மை"
    " செயலி"
)

# கோப்பு பதிவேற்றம் (File Uploader)
uploaded_file = st.sidebar.file_uploader(
    "Excel அல்லது CSV கோப்பினைப் பதிவேற்றவும்", type=["xlsx", "csv"]
)

# தரவை ஏற்றுதல்
@st.cache_data
def load_data(file):
  if file.name.endswith(".csv"):
    return pd.read_csv(file)
  else:
    return pd.read_excel(file, sheet_name="BOOK_PURCHASED_DATA")


df = None
if uploaded_file is not None:
  try:
    df = load_data(uploaded_file)
    st.sidebar.success("கோப்பு வெற்றிகரமாக ஏற்றப்பட்டது!")
  except Exception as e:
    st.sidebar.error(f"கோப்பு ஏற்றுவதில் பிழை: {e}")

if df is not None:
  # பக்கவாட்டுப்பட்டை மூலம் பணிகளைத் தேர்ந்தெடுத்தல் (Task Selection)
  task_option = st.sidebar.selectbox(
      "செயல்பாட்டைத் தேர்ந்தெடுக்கவும் (Select Task):",
      [
          "Task 1: அனைத்து பதிப்பாளர்கள் சுருக்கம் (All Publishers Summary)",
          "Task 2: தனிப்பட்ட பதிப்பாளர் தேடல் (Individual Publisher Search)",
          "Task 3: முழுமையான தரவுச் சரிபார்ப்பு (Complete Data Verification)",
      ],
  )

  vendor_col = (
      "Vendor Name" if "Vendor Name" in df.columns else "Publication Name"
  )

  # ---------------------------------------------------------
  # TASK 1: அனைத்து பதிப்பாளர்கள் சுருக்கம் (All Publishers View)
  # ---------------------------------------------------------
  if "Task 1" in task_option:
    st.header("📋 Task 1: அனைத்து பதிப்பாளர்கள் பொது விவரங்கள் மற்றும் சுருக்கம்")

    if vendor_col in df.columns:
      # பதிப்பாளர் வாரியாக நூல்களின் எண்ணிக்கை மற்றும் மொத்த மதிப்பைத் தொகுத்தல்
      price_col = (
          "Accepted Price" if "Accepted Price" in df.columns else "Original Price"
      )
      summary_df = (
          df.groupby(vendor_col)
          .agg(
              Total_Titles=("Title", "count"),
              Total_Quantity=("Quantity", "sum")
              if "Quantity" in df.columns
              else ("Title", "count"),
              Total_Value=(price_col, "sum"),
          )
          .reset_index()
      )

      col1, col2 = st.columns(2)
      with col1:
        st.metric(label="மொத்த பதிப்பாளர்கள்", value=len(summary_df))
      with col2:
        st.metric(
            label="மொத்த நூல் பதிவுகள்", value=int(summary_df["Total_Titles"].sum())
        )

      st.subheader("அனைத்து பதிப்பாளர்களுமான பட்டியல்:")
      st.dataframe(summary_df, use_container_width=True)

      # CSV பதிவிறக்க பொத்தான்
      st.download_button(
          label="📥 அனைத்து பதிப்பாளர்கள் சுருக்கத்தைப் CSV-ஆக பதிவிறக்குக",
          data=summary_df.to_csv(index=False).encode("utf-8"),
          file_name="All_Publishers_Summary.csv",
          mime="text/csv",
      )
    else:
      st.error(
          "கோப்பில் பதிப்பாளர் பெயர் (Vendor Name / Publication Name)"
     " நெடுவரிசை காணப்படவில்லை."
      )

  # ---------------------------------------------------------
  # TASK 2: தனிப்பட்ட பதிப்பாளர் தேடல் (Individual Publisher Search)
  # ---------------------------------------------------------
  elif "Task 2" in task_option:
    st.header("🔍 Task 2: தனிப்பட்ட பதிப்பாளர் வாரியான தேடல் மற்றும் விவரங்கள்")

    if vendor_col in df.columns:
      publishers = sorted(df[vendor_col].dropna().unique().tolist())

      # தனித்தனியாகத் தேடும் அல்லது தேர்ந்தெடுக்கும் வசதி (Selectbox / Search)
      selected_pub = st.selectbox(
          "சரிபார்க்க வேண்டிய பதிப்பாளரைத் தேர்ந்தெடுக்கவும்:", options=publishers
      )

      filtered_pub_df = df[df[vendor_col] == selected_pub]

      st.success(
          f"'{selected_pub}' பதிப்பாளரின் கீழ் உள்ள நூல்களின் விவரங்கள் (மொத்தப்"
          f" பதிவுகள்: {len(filtered_pub_df)})"
      )
      st.dataframe(filtered_pub_df, use_container_width=True)

      # குறிப்பிட்ட பதிப்பாளர் தரவை மட்டும் பதிவிறக்கம் செய்ய
      st.download_button(
          label=f"📥 '{selected_pub}' தரவைப் பதிவிறக்குக",
          data=filtered_pub_df.to_csv(index=False).encode("utf-8"),
          file_name=f"{selected_pub}_Publisher_Details.csv",
          mime="text/csv",
      )
    else:
      st.error("பதிப்பாளர் நெடுவரிசை கோப்பில் இல்லை.")

  # ---------------------------------------------------------
  # TASK 3: முழுமையான தரவுச் சரிபார்ப்பு & வடிகட்டுதல் (Full Verification)
  # ---------------------------------------------------------
  elif "Task 3" in task_option:
    st.header("📊 Task 3: முழுமையான தரவுச் சரிபார்ப்பு மற்றும் தேடல் வடிகட்டி")

    col_a, col_b = st.columns(2)
    with col_a:
      search_title = st.text_input("நூல் தலைப்பு (Title) மூலம் தேடுக:")
    with col_b:
      search_lib = st.text_input("நூலகப் பெயர் (Library Name) மூலம் தேடுக:")

    working_df = df.copy()

    if search_title and "Title" in working_df.columns:
      working_df = working_df[
          working_df["Title"].str.contains(search_title, case=False, na=False)
      ]

    if search_lib and "Library Name" in working_df.columns:
      working_df = working_df[
          working_df["Library Name"]
          .str.contains(search_lib, case=False, na=False)
      ]

    st.info(f"தேடல் முடிவுகள் - பொருத்தமான பதிவுகள்: {len(working_df)}")
    st.dataframe(working_df, use_container_width=True)

    # வடிகட்டப்பட்ட இறுதித் தரவைப் பதிவிறக்க
    st.download_button(
        label="📥 வடிகட்டப்பட்ட முழு தரவைப் பதிவிறக்குக",
        data=working_df.to_csv(index=False).encode("utf-8"),
        file_name="Filtered_Verification_Data.csv",
        mime="text/csv",
    )

else:
  st.warning(
      "⚠️ செயலியைத் தொடங்க தயவுசெய்து இடதுபுறப் பக்கவாட்டுப்பட்டையில் (Sidebar)"
      " உங்களது எக்செல் அல்லது சிஎஸ்வி கோப்பினைப் பதிவேற்றவும் ஐயா."
  )
