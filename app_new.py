"""
Book Verification 2026
----------------------
Fast Streamlit application for publisher-wise book verification.

Required environment variables / Streamlit secrets:
    DATABASE_URL
    AUTH_ADMIN_PASSWORD
    AUTH_DCL_STAFF_PASSWORD
    AUTH_LIBRARIAN_PASSWORD

The application deliberately does not contain database credentials.
"""

from __future__ import annotations

import hashlib
import hmac
import html
import io
import os
import re
import secrets
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterable

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values
from psycopg2.pool import SimpleConnectionPool
import streamlit as st


st.set_page_config(
    page_title="மாவட்ட மைய நூலகம், கிருஷ்ணகிரி",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def secret_value(name: str, default: str = "") -> str:
    """Read a setting from environment first, then Streamlit secrets."""
    value = os.getenv(name)
    if value:
        return value.strip()
    try:
        value = st.secrets.get(name, default)
        return str(value).strip() if value else default
    except Exception:
        return default


DATABASE_URL = secret_value("DATABASE_URL") or secret_value("DB_URL")
BOOKS_TABLE = secret_value("BOOKS_TABLE", "books") or "books"
AUTH_PASSWORDS = {
    "Admin": secret_value("AUTH_ADMIN_PASSWORD"),
    "DCL Staff": secret_value("AUTH_DCL_STAFF_PASSWORD"),
    "Librarian": secret_value("AUTH_LIBRARIAN_PASSWORD"),
}
USER_NAMES = {
    "Admin": "முதன்மை நிர்வாகி (Admin)",
    "DCL Staff": "DCL Staff",
    "Librarian": "Librarian",
}


st.markdown(
    """
<style>
html, body, [class*="css"] {
  font-family: 'Noto Sans Tamil', 'Nirmala UI', Arial, sans-serif !important;
}
.stApp { background: #f8fafc; }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { visibility: hidden; }
.top-header {
  background: linear-gradient(135deg,#064e3b,#022c22); padding:16px 22px;
  border-radius:12px; color:#fff; display:flex; justify-content:space-between;
  align-items:center; box-shadow:0 4px 15px rgba(6,78,59,.2); margin-bottom:16px;
}
.header-title { font-size:20px; font-weight:800; }
.header-subtitle { font-size:13px; color:#a7f3d0; font-weight:600; }
.login-wrap { display:flex; justify-content:center; padding-top:30px; }
.login-card { background:#fff; border-radius:16px; padding:22px 25px;
  box-shadow:0 10px 25px rgba(0,0,0,.25); border:1.5px solid #a7f3d0;
  width:100%; max-width:390px; }
.login-head { text-align:center; background:linear-gradient(135deg,#ecfdf5,#d1fae5);
  border:1.5px solid #a7f3d0; border-radius:10px; padding:10px; margin-bottom:12px; }
.login-title { color:#064e3b; font-size:15px; font-weight:800; }
.ticker { background:linear-gradient(135deg,#f0fdf4,#dcfce7); border:1.5px solid #86efac;
  padding:8px 12px; border-radius:10px; color:#065f46; font-weight:700;
  font-size:13px; margin-bottom:18px; overflow:hidden; white-space:nowrap; }
.ticker-badge { background:#065f46; color:white; padding:3px 10px; border-radius:6px;
  font-size:12px; margin-right:15px; display:inline-block; }
.status-card { background:#ecfdf5; border:1px solid #6ee7b7; border-radius:10px;
  padding:12px 16px; margin:10px 0 16px; color:#065f46; }
.stButton > button { border-radius:10px !important; }
</style>
""",
    unsafe_allow_html=True,
)


def identifier(name: str) -> str:
    """Validate a PostgreSQL identifier before it is interpolated into SQL."""
    value = str(name).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_ ]{0,127}", value):
        raise ValueError(f"Invalid database identifier: {value}")
    return value


BOOKS_TABLE = identifier(BOOKS_TABLE)


@st.cache_resource(show_spinner=False)
def connection_pool() -> SimpleConnectionPool | None:
    if not DATABASE_URL:
        return None
    return SimpleConnectionPool(
        minconn=1,
        maxconn=5,
        dsn=DATABASE_URL,
        connect_timeout=10,
        application_name="book-verification-2026",
    )


@contextmanager
def db_connection():
    pool = connection_pool()
    if pool is None:
        raise RuntimeError(
            "DATABASE_URL அமைக்கப்படவில்லை. Replit Secrets-ல் DATABASE_URL-ஐ சேர்க்கவும்."
        )
    conn = pool.getconn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


@st.cache_resource(show_spinner=False)
def initialize_database() -> str:
    """Create small application tables only once per server process."""
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS submitted_reports (
                    id BIGSERIAL PRIMARY KEY,
                    publisher TEXT NOT NULL,
                    title TEXT NOT NULL,
                    author TEXT,
                    price TEXT,
                    accepted_price TEXT,
                    isbn TEXT,
                    required_qty INTEGER NOT NULL DEFAULT 0,
                    received_qty INTEGER NOT NULL DEFAULT 0,
                    date TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_submitted_publisher
                    ON submitted_reports (publisher);
                CREATE TABLE IF NOT EXISTS dispatch_records (
                    id BIGSERIAL PRIMARY KEY,
                    publisher TEXT NOT NULL,
                    title TEXT NOT NULL,
                    library TEXT NOT NULL,
                    dispatched_qty INTEGER NOT NULL DEFAULT 0,
                    date TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_dispatch_title
                    ON dispatch_records (publisher, title);
                CREATE TABLE IF NOT EXISTS librarian_records (
                    id BIGSERIAL PRIMARY KEY,
                    librarian TEXT NOT NULL,
                    library TEXT NOT NULL,
                    view_year TEXT NOT NULL,
                    date TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS app_users (
                    role TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL
                );
                """
            )
            for role, password in AUTH_PASSWORDS.items():
                if password:
                    cur.execute(
                        """
                        INSERT INTO app_users(role, display_name, password_hash)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (role) DO NOTHING
                        """,
                        (role, USER_NAMES[role], hash_password(password)),
                    )
    return "ok"


def hash_password(password: str, salt: bytes | None = None) -> str:
    """PBKDF2 password hash; unlike the old SHA-256-only scheme it is salted."""
    salt = salt or secrets.token_bytes(16)
    iterations = 240_000
    digest = hashlib.pbkdf2_hmac(
        "sha256", str(password).encode("utf-8"), salt, iterations
    )
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = hashlib.pbkdf2_hmac(
            "sha256",
            str(password).encode("utf-8"),
            bytes.fromhex(salt_hex),
            int(iterations),
        ).hex()
        return hmac.compare_digest(expected, digest_hex)
    except (ValueError, TypeError):
        return False


def authenticate_user(role: str, password: str) -> dict[str, str] | None:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT display_name, password_hash FROM app_users WHERE role=%s",
                (role,),
            )
            row = cur.fetchone()
    if row and verify_password(password, row[1]):
        return {"role": role, "name": row[0]}
    return None


@st.cache_data(ttl=30, show_spinner=False)
def load_submitted_reports() -> pd.DataFrame:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS "Id", publisher AS "Publisher", title AS "Title",
                       author AS "Author", price AS "Price",
                       accepted_price AS "Accepted Price", isbn AS "ISBN",
                       required_qty AS "Required Qty",
                       received_qty AS "Received Qty", date AS "Date"
                FROM submitted_reports ORDER BY id DESC
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=180, max_entries=1, show_spinner="நூல் தரவுகள் ஏற்றப்படுகின்றன...")
def load_books() -> pd.DataFrame:
    """Load once and keep the large books table in Streamlit's server cache."""
    with db_connection() as conn:
        with conn.cursor() as cur:
            query = sql.SQL("SELECT * FROM {}").format(sql.Identifier(BOOKS_TABLE))
            cur.execute(query)
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    frame = pd.DataFrame(rows, columns=columns)
    frame.columns = [str(col).strip().lower() for col in frame.columns]
    return frame


@st.cache_data(ttl=30, show_spinner=False)
def load_dispatch_records() -> pd.DataFrame:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS "Id", publisher AS "Publisher", title AS "Title",
                       library AS "Library", dispatched_qty AS "Dispatched Qty",
                       date AS "Date"
                FROM dispatch_records ORDER BY id DESC
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=columns)


@st.cache_data(ttl=30, show_spinner=False)
def load_librarian_records() -> pd.DataFrame:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id AS "Id", librarian AS "Librarian", library AS "Library",
                       view_year AS "View Year", date AS "Date"
                FROM librarian_records ORDER BY id DESC
                """
            )
            rows = cur.fetchall()
            columns = [desc[0] for desc in cur.description]
    return pd.DataFrame(rows, columns=columns)


def refresh_caches() -> None:
    load_submitted_reports.clear()
    load_dispatch_records.clear()
    load_librarian_records.clear()
    load_books.clear()


def get_col(frame: pd.DataFrame, exact: Iterable[str], contains: Iterable[str] = ()) -> str | None:
    columns = list(frame.columns)
    exact_lower = {str(item).lower() for item in exact}
    for col in columns:
        if str(col).lower() in exact_lower:
            return col
    for col in columns:
        name = str(col).lower()
        if any(part in name for part in contains):
            return col
    return None


def book_columns(frame: pd.DataFrame) -> dict[str, str | None]:
    return {
        "publisher": get_col(
            frame,
            ["publication name", "publication_name", "publisher_name", "vendor_name"],
            ["publication", "publisher", "vendor"],
        ),
        "title": get_col(frame, ["title", "book_title"], ["title"]),
        "author": get_col(frame, ["author", "author_name"], ["author"]),
        "price": get_col(frame, ["price"], ["price"]),
        "accepted": get_col(
            frame,
            ["accepted price", "accepted_price"],
            ["accepted", "offer", "rate"],
        ),
        "isbn": get_col(frame, ["isbn", "isbn_no"], ["isbn"]),
        "accession": get_col(
            frame,
            ["accession number", "accession_number", "acc_no", "reg_no"],
            ["accession", "acc_no", "reg_no"],
        ),
        "classification": get_col(
            frame,
            ["classification number", "classification_number", "class_no", "call_no"],
            ["classification", "call_no", "call number"],
        ),
        "library": get_col(
            frame,
            ["library name", "library_name", "library_name_tm"],
            ["library"],
        ),
    }


def safe_text(value: Any, fallback: str = "-") -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return fallback
    return str(value)


def report_records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    return frame.to_dict("records") if not frame.empty else []


def show_login_page() -> None:
    st.markdown(
        """
        <style>.stApp { background:linear-gradient(135deg,#064e3b,#022c22) !important; }</style>
        <div class="login-wrap"><div class="login-card">
        <div class="login-head"><div style="font-size:22px">📚</div>
        <div class="login-title">மாவட்ட மைய நூலகம்<br>கிருஷ்ணகிரி</div></div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("secure_login_form"):
        role = st.selectbox("பயனர் வகை", ["-- தேர்ந்தெடுக்கவும் --", *USER_NAMES])
        password = st.text_input("🔑 கடவுச்சொல்", type="password")
        submitted = st.form_submit_button("உள்நுழை", use_container_width=True, type="primary")
    st.markdown("</div></div>", unsafe_allow_html=True)
    if submitted:
        if role == "-- தேர்ந்தெடுக்கவும் --":
            st.warning("பயனர் வகையைத் தேர்ந்தெடுக்கவும்.")
            return
        try:
            user = authenticate_user(role, password)
        except Exception:
            st.error("Database இணைப்பு தோல்வியடைந்தது. DATABASE_URL மற்றும் Neon status-ஐ சரிபார்க்கவும்.")
            return
        if not user:
            st.error("தவறான பயனர் அல்லது கடவுச்சொல்.")
            return
        st.session_state.update(
            logged_in=True, user_role=user["role"], user_name=user["name"]
        )
        st.rerun()


def show_header(reports: pd.DataFrame) -> None:
    total_received = (
        pd.to_numeric(reports.get("Received Qty", pd.Series(dtype=float)), errors="coerce")
        .fillna(0)
        .sum()
    )
    st.markdown(
        f"""
        <div class="top-header"><div><div class="header-title">📚 மாவட்ட மைய நூலகம்</div>
        <div class="header-subtitle">கிருஷ்ணகிரி — புதிய நூல்கள் பகிர்மானம் 2026-27</div></div>
        <div>👤 {html.escape(st.session_state['user_name'])}
        ({html.escape(st.session_state['user_role'])})</div></div>
        <div class="ticker"><span class="ticker-badge">🔴 Live</span>
        பெறப்பட்ட நூல்கள்: <b>45,305</b> ◆ பிரிக்கப்பட்டது:
        <b>{int(total_received):,}</b> ◆ மீதம்:
        <b>{max(0, 45305-int(total_received)):,}</b>
        ◆ இன்று: <b>{datetime.now().strftime('%d/%m/%Y')}</b></div>
        """,
        unsafe_allow_html=True,
    )


MENU = [
    ("🔀", "பிரிக்க"),
    ("📤", "அனுப்ப"),
    ("📊", "அறிக்கைகள்"),
    ("⚠️", "கவனிக்க"),
    ("🔢", "பதிவெண் மாற்ற"),
    ("🗂️", "Master Data"),
    ("❌", "தவறான பதிவு நீக்கம்"),
    ("🔑", "கடவுச்சொல் மாற்ற"),
    ("📥", "Excel பதிவிறக்கம்"),
    ("👥", "நூலகர் பார்வை ஆண்டு"),
    ("📂", "Excel அப்லோடு"),
    ("🏷️", "பகுப்பு எண் புதுப்பி"),
]


def show_menu() -> str | None:
    if "current_menu" not in st.session_state:
        st.session_state.current_menu = None
    for start in (0, 6):
        cols = st.columns(6)
        for col, index in zip(cols, range(start, min(start + 6, len(MENU)))):
            icon, label = MENU[index]
            with col:
                if st.button(
                    f"{icon}\n{label}",
                    key=f"menu_{index}",
                    use_container_width=True,
                    type="primary" if st.session_state.current_menu == label else "secondary",
                ):
                    st.session_state.current_menu = label
                    st.rerun()
    return st.session_state.current_menu


def show_distribution(books: pd.DataFrame, reports: pd.DataFrame) -> None:
    st.subheader("🔀 நூல்களைப் பிரிக்கும் பகுதி")
    cols = book_columns(books)
    if not cols["publisher"] or not cols["title"]:
        st.error("Publisher / Title columns books table-ல் கிடைக்கவில்லை.")
        return
    publisher_col, title_col = cols["publisher"], cols["title"]
    publishers = sorted(books[publisher_col].dropna().astype(str).unique())
    publisher = st.selectbox("1. பதிப்பாளரைத் தேர்ந்தெடுக்கவும்", ["-- தேர்வு --", *publishers])
    if publisher == "-- தேர்வு --":
        return

    pub_books = books[books[publisher_col].astype(str) == publisher].copy()
    done = set(
        reports.loc[reports["Publisher"] == publisher, "Title"].astype(str).tolist()
    ) if not reports.empty else set()
    temporary = st.session_state.get("temp_distributed", [])
    temp_done = {str(item["Title"]) for item in temporary if item["Publisher"] == publisher}
    available = sorted(
        set(pub_books[title_col].dropna().astype(str)) - done - temp_done
    )
    st.markdown(
        f"""<div class="status-card">🏢 <b>{html.escape(publisher)}</b> —
        தலைப்புகள்: <b>{pub_books[title_col].nunique()}</b> |
        நூல்கள்: <b>{len(pub_books)}</b> |
        முடிந்தது: <b>{len(done)}</b> |
        மீதம்: <b>{len(available)}</b></div>""",
        unsafe_allow_html=True,
    )
    if available:
        title = st.selectbox("2. நூல் தலைப்பைத் தேர்ந்தெடுக்கவும்", ["-- தேர்வு --", *available])
        if title != "-- தேர்வு --":
            title_rows = pub_books[pub_books[title_col].astype(str) == title]
            first = title_rows.iloc[0]
            key = hashlib.md5(f"{publisher}|{title}".encode()).hexdigest()[:10]
            with st.form(f"distribution_{key}"):
                st.write(
                    f"**ஆசிரியர்:** {safe_text(first.get(cols['author'])) if cols['author'] else '-'}  \n"
                    f"**விலை:** {safe_text(first.get(cols['price']), '0') if cols['price'] else '0'}  \n"
                    f"**தேவையான எண்ணிக்கை:** {len(title_rows)}"
                )
                received = st.number_input(
                    "பெறப்பட்ட எண்ணிக்கை", min_value=0, max_value=500,
                    value=len(title_rows), step=1,
                )
                add = st.form_submit_button("➕ தற்காலிக பட்டியலில் சேமி", type="primary")
            if add:
                item = {
                    "Publisher": publisher,
                    "Title": title,
                    "Author": safe_text(first.get(cols["author"])) if cols["author"] else "-",
                    "Price": safe_text(first.get(cols["price"]), "0") if cols["price"] else "0",
                    "Accepted Price": safe_text(first.get(cols["accepted"]), "0") if cols["accepted"] else "0",
                    "ISBN": safe_text(first.get(cols["isbn"])) if cols["isbn"] else "-",
                    "Required Qty": len(title_rows),
                    "Received Qty": int(received),
                    "Date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                }
                st.session_state.setdefault("temp_distributed", []).append(item)
                st.rerun()
    else:
        st.success("இந்தப் பதிப்பகத்தின் அனைத்து தலைப்புகளும் சரிபார்க்கப்பட்டன.")

    temp = st.session_state.get("temp_distributed", [])
    if temp:
        st.divider()
        st.markdown("#### 📋 தற்காலிக பட்டியல்")
        st.dataframe(pd.DataFrame(temp), use_container_width=True, hide_index=True)
        current_count = sum(item["Publisher"] == publisher for item in temp)
        remaining = len(set(pub_books[title_col].dropna().astype(str))) - len(done) - current_count
        if remaining > 0:
            st.warning(f"இந்த பதிப்பகத்தில் இன்னும் {remaining} தலைப்புகள் மீதம் உள்ளன.")
        elif st.button("💾 அனைத்தையும் Neon-ல் சேமி & சமர்ப்பிக்க", type="primary"):
            values = [
                (
                    item["Publisher"], item["Title"], item["Author"], item["Price"],
                    item["Accepted Price"], item["ISBN"], item["Required Qty"],
                    item["Received Qty"], item["Date"],
                )
                for item in temp
            ]
            with db_connection() as conn:
                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO submitted_reports
                        (publisher,title,author,price,accepted_price,isbn,required_qty,received_qty,date)
                        VALUES %s
                        """,
                        values,
                        page_size=500,
                    )
            load_submitted_reports.clear()
            st.session_state.temp_distributed = []
            st.session_state.current_menu = "அறிக்கைகள்"
            st.success("தரவு வேகமாக bulk insert மூலம் சேமிக்கப்பட்டது.")
            st.rerun()


def show_dispatch(reports: pd.DataFrame) -> None:
    st.subheader("📤 நூல்கள் அனுப்பும் பகுதி")
    if reports.empty:
        st.info("முதலில் நூல் பிரிப்பு பதிவைச் சமர்ப்பிக்கவும்.")
        return
    dispatch = load_dispatch_records()
    publishers = sorted(reports["Publisher"].dropna().astype(str).unique())
    publisher = st.selectbox("பதிப்பாளர்", ["-- தேர்வு --", *publishers], key="dispatch_pub")
    if publisher == "-- தேர்வு --":
        if not dispatch.empty:
            st.dataframe(dispatch, use_container_width=True, hide_index=True)
        return
    titles = sorted(reports.loc[reports["Publisher"] == publisher, "Title"].astype(str).unique())
    title = st.selectbox("தலைப்பு", ["-- தேர்வு --", *titles], key="dispatch_title")
    if title != "-- தேர்வு --":
        row = reports[(reports["Publisher"] == publisher) & (reports["Title"] == title)].iloc[0]
        received = int(pd.to_numeric(row["Received Qty"], errors="coerce") or 0)
        already = 0 if dispatch.empty else int(pd.to_numeric(
            dispatch.loc[
                (dispatch["Publisher"] == publisher) & (dispatch["Title"] == title),
                "Dispatched Qty",
            ], errors="coerce").fillna(0).sum())
        remaining = max(0, received - already)
        with st.form("dispatch_form"):
            library = st.text_input("நூலகத்தின் பெயர்")
            quantity = st.number_input("அனுப்பப்படும் எண்ணிக்கை", 0, remaining, 0, 1)
            save = st.form_submit_button("📤 அனுப்புதலைப் பதிவு செய்", type="primary")
        if save:
            if not library.strip():
                st.error("நூலகத்தின் பெயரை உள்ளிடவும்.")
            elif quantity == 0:
                st.error("அனுப்பப்படும் எண்ணிக்கை 0-வை விட அதிகமாக இருக்க வேண்டும்.")
            else:
                with db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO dispatch_records
                            (publisher,title,library,dispatched_qty,date)
                            VALUES (%s,%s,%s,%s,%s)
                            """,
                            (publisher, title, library.strip(), int(quantity),
                             datetime.now().strftime("%Y-%m-%d %H:%M")),
                        )
                load_dispatch_records.clear()
                st.success("அனுப்பல் பதிவு சேமிக்கப்பட்டது.")
                st.rerun()
        st.caption(f"பெறப்பட்டது: {received} | ஏற்கனவே அனுப்பியது: {already} | மீதம்: {remaining}")
    if not dispatch.empty:
        st.divider()
        st.dataframe(dispatch, use_container_width=True, hide_index=True)


def show_review(books: pd.DataFrame) -> None:
    st.subheader("⚠️ விலை முரண்பாடு உள்ள பதிவுகள்")
    cols = book_columns(books)
    if not cols["price"] or not cols["accepted"]:
        st.info("Price / Accepted Price columns கிடைக்கவில்லை.")
        return
    view = books.copy()
    view["_price_num"] = pd.to_numeric(view[cols["price"]], errors="coerce")
    view["_accepted_num"] = pd.to_numeric(view[cols["accepted"]], errors="coerce")
    conflicts = view[
        view["_price_num"].notna()
        & view["_accepted_num"].notna()
        & (view["_price_num"] != view["_accepted_num"])
    ].drop(columns=["_price_num", "_accepted_num"])
    if conflicts.empty:
        st.success("விலை முரண்பாடுகள் எதுவும் இல்லை.")
    else:
        st.warning(f"{len(conflicts):,} பதிவுகளில் விலை முரண்பாடு உள்ளது.")
        st.dataframe(conflicts, use_container_width=True, hide_index=True)
        st.download_button(
            "📥 CSV பதிவிறக்கம்",
            conflicts.to_csv(index=False).encode("utf-8-sig"),
            f"Price_Conflicts_{datetime.now():%Y%m%d}.csv",
            "text/csv",
        )


def update_book_value(column: str, old_value: Any, new_value: str, title_col: str,
                      title: str, publisher_col: str | None, publisher: str | None) -> int:
    column = identifier(column)
    title_col = identifier(title_col)
    query = sql.SQL("UPDATE {} SET {}=%s WHERE {}=%s AND {}=%s").format(
        sql.Identifier(BOOKS_TABLE), sql.Identifier(column),
        sql.Identifier(column), sql.Identifier(title_col),
    )
    params: list[Any] = [new_value, old_value, title]
    if publisher_col and publisher is not None:
        query += sql.SQL(" AND {}=%s").format(sql.Identifier(identifier(publisher_col)))
        params.append(publisher)
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            count = cur.rowcount
    return count


def show_book_update(books: pd.DataFrame, kind: str) -> None:
    is_accession = kind == "accession"
    st.subheader("🔢 பதிவெண் மாற்றம்" if is_accession else "🏷️ பகுப்பு எண் புதுப்பித்தல்")
    cols = book_columns(books)
    target_col = cols["accession"] if is_accession else cols["classification"]
    if not target_col or not cols["title"]:
        st.info("தேவையான columns books table-ல் இல்லை.")
        return
    pub_col, title_col = cols["publisher"], cols["title"]
    publishers = sorted(books[pub_col].dropna().astype(str).unique()) if pub_col else []
    publisher = st.selectbox("பதிப்பாளர்", ["-- தேர்வு --", *publishers],
                             key=f"{kind}_publisher")
    if publisher == "-- தேர்வு --":
        return
    subset = books[books[pub_col].astype(str) == publisher] if pub_col else books
    titles = sorted(subset[title_col].dropna().astype(str).unique())
    title = st.selectbox("தலைப்பு", ["-- தேர்வு --", *titles], key=f"{kind}_title")
    if title == "-- தேர்வு --":
        return
    rows = subset[subset[title_col].astype(str) == title].reset_index(drop=True)
    st.dataframe(rows[[target_col, title_col]], use_container_width=True, hide_index=True)
    row_number = st.number_input("மாற்ற வேண்டிய Row Index", 0, len(rows) - 1, 0, 1,
                                 key=f"{kind}_row")
    old = rows.iloc[int(row_number)][target_col]
    new = st.text_input("புதிய மதிப்பு", safe_text(old, ""), key=f"{kind}_new")
    if st.button("💾 புதுப்பி", type="primary", key=f"{kind}_save"):
        count = update_book_value(
            target_col, old, new.strip(), title_col, title, pub_col, publisher
        )
        load_books.clear()
        st.success(f"{count} row(s) புதுப்பிக்கப்பட்டது.")
        st.rerun()


def show_reports(reports: pd.DataFrame) -> None:
    st.subheader("📊 சரிபார்ப்பு அறிக்கைகள்")
    if reports.empty:
        st.info("இதுவரை சமர்ப்பிக்கப்பட்ட பதிவுகள் இல்லை.")
        return
    publishers = ["-- அனைத்தும் --", *sorted(reports["Publisher"].dropna().astype(str).unique())]
    selected = st.selectbox("பதிப்பாளர் filter", publishers, key="report_publisher")
    view = reports if selected == "-- அனைத்தும் --" else reports[reports["Publisher"] == selected]
    st.metric("பதிவுகள்", len(view))
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 CSV பதிவிறக்கம்",
        reports.to_csv(index=False).encode("utf-8-sig"),
        f"Verification_Report_{datetime.now():%Y%m%d_%H%M}.csv",
        "text/csv",
        type="primary",
    )


def show_master_data(books: pd.DataFrame, reports: pd.DataFrame) -> None:
    st.subheader("🗂️ Master Data")
    if books.empty or reports.empty:
        st.info("Master Data பார்க்க books மற்றும் submitted reports இரண்டும் தேவை.")
        return
    cols = book_columns(books)
    if not cols["publisher"] or not cols["title"]:
        st.error("Publisher / Title columns இல்லை.")
        return
    publishers = sorted(reports["Publisher"].dropna().astype(str).unique())
    publisher = st.selectbox("முடிக்கப்பட்ட பதிப்பாளர்", ["-- தேர்வு --", *publishers],
                             key="master_publisher")
    if publisher == "-- தேர்வு --":
        return
    subset = books[books[cols["publisher"]].astype(str) == publisher].copy()
    received = reports[reports["Publisher"] == publisher].groupby("Title")["Received Qty"].sum()
    subset["received_status"] = 0
    for title, amount in received.items():
        mask = subset[cols["title"]].astype(str) == str(title)
        subset.loc[mask, "received_status"] = [
            1 if index < int(amount) else 0 for index in range(int(mask.sum()))
        ]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("தலைப்புகள்", subset[cols["title"]].nunique())
    c2.metric("நூல்கள்", len(subset))
    c3.metric("பெறப்பட்டது", int(subset["received_status"].sum()))
    c4.metric("மீதம்", int(len(subset) - subset["received_status"].sum()))
    st.dataframe(subset, use_container_width=True, hide_index=True)
    st.download_button(
        "📥 Master CSV பதிவிறக்கம்",
        subset.to_csv(index=False).encode("utf-8-sig"),
        f"Master_Data_{publisher}.csv",
        "text/csv",
    )


def show_corrections(reports: pd.DataFrame) -> None:
    st.subheader("❌ தவறான பதிவு நீக்கம் / திருத்தம்")
    tab1, tab2 = st.tabs(["Submitted Reports", "Dispatch Records"])
    with tab1:
        if reports.empty:
            st.info("பதிவுகள் இல்லை.")
        else:
            st.dataframe(reports, use_container_width=True, hide_index=True)
            record_id = st.number_input("நீக்க வேண்டிய Report Id", 0, 10**12, 0, 1)
            if st.button("🗑️ Report-ஐ நீக்கு", type="primary", key="delete_report"):
                if record_id <= 0:
                    st.error("சரியான Id-ஐ உள்ளிடவும்.")
                else:
                    with db_connection() as conn:
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM submitted_reports WHERE id=%s", (int(record_id),))
                    load_submitted_reports.clear()
                    st.success("பதிவு நீக்கப்பட்டது.")
                    st.rerun()
    with tab2:
        dispatch = load_dispatch_records()
        if dispatch.empty:
            st.info("Dispatch records இல்லை.")
        else:
            st.dataframe(dispatch, use_container_width=True, hide_index=True)
            record_id = st.number_input("நீக்க வேண்டிய Dispatch Id", 0, 10**12, 0, 1)
            if st.button("🗑️ Dispatch-ஐ நீக்கு", type="primary", key="delete_dispatch"):
                with db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("DELETE FROM dispatch_records WHERE id=%s", (int(record_id),))
                load_dispatch_records.clear()
                st.success("Dispatch பதிவு நீக்கப்பட்டது.")
                st.rerun()


def show_password_change() -> None:
    st.subheader("🔑 கடவுச்சொல் மாற்றம்")
    st.info("இந்த மாற்றம் app_users table-ல் பாதுகாப்பாக சேமிக்கப்படும்.")
    with st.form("password_change"):
        old = st.text_input("பழைய கடவுச்சொல்", type="password")
        new = st.text_input("புதிய கடவுச்சொல்", type="password")
        confirm = st.text_input("புதிய கடவுச்சொல்லை மீண்டும் உள்ளிடவும்", type="password")
        save = st.form_submit_button("கடவுச்சொல்லை மாற்றுக", type="primary")
    if save:
        if len(new) < 8:
            st.error("புதிய கடவுச்சொல் குறைந்தது 8 எழுத்துகள் இருக்க வேண்டும்.")
        elif new != confirm:
            st.error("புதிய கடவுச்சொற்கள் பொருந்தவில்லை.")
        elif not authenticate_user(st.session_state.user_role, old):
            st.error("பழைய கடவுச்சொல் தவறாக உள்ளது.")
        else:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE app_users SET password_hash=%s WHERE role=%s",
                        (hash_password(new), st.session_state.user_role),
                    )
            st.success("கடவுச்சொல் மாற்றப்பட்டது.")


def show_download(reports: pd.DataFrame) -> None:
    st.subheader("📥 Excel பதிவிறக்கம்")
    if reports.empty:
        st.info("பதிவிறக்கம் செய்ய data இல்லை.")
        return
    csv = reports.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📄 CSV பதிவிறக்கம்", csv, "verification_report.csv", "text/csv")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        reports.to_excel(writer, index=False, sheet_name="Verification Report")
    st.download_button(
        "📊 உண்மையான Excel பதிவிறக்கம்",
        output.getvalue(),
        f"Verification_Report_{datetime.now():%Y%m%d}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def show_librarian_year() -> None:
    st.subheader("👥 நூலகர் பார்வை ஆண்டு")
    with st.form("librarian_year_form"):
        c1, c2 = st.columns(2)
        with c1:
            librarian = st.text_input("நூலகர் பெயர்")
            library = st.text_input("நூலகத்தின் பெயர்")
        with c2:
            year = st.text_input("பார்வை ஆண்டு", "2026-27")
        save = st.form_submit_button("➕ பதிவு சேர்", type="primary")
    if save:
        if not librarian.strip() or not library.strip() or not year.strip():
            st.error("அனைத்து விவரங்களையும் உள்ளிடவும்.")
        else:
            with db_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO librarian_records(librarian,library,view_year,date)
                        VALUES (%s,%s,%s,%s)
                        """,
                        (librarian.strip(), library.strip(), year.strip(),
                         datetime.now().strftime("%Y-%m-%d %H:%M")),
                    )
            load_librarian_records.clear()
            st.success("பதிவு சேமிக்கப்பட்டது.")
            st.rerun()
    records = load_librarian_records()
    if not records.empty:
        st.dataframe(records, use_container_width=True, hide_index=True)


def table_columns() -> list[str]:
    with db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name=%s
                ORDER BY ordinal_position
                """,
                (BOOKS_TABLE,),
            )
            return [row[0] for row in cur.fetchall()]


def bulk_upload(frame: pd.DataFrame) -> int:
    frame = frame.copy()
    frame.columns = [str(c).strip().lower() for c in frame.columns]
    frame = frame.loc[:, ~frame.columns.duplicated()]
    if frame.empty or not len(frame.columns):
        return 0
    existing = table_columns()
    with db_connection() as conn:
        with conn.cursor() as cur:
            if not existing:
                defs = sql.SQL(", ").join(
                    sql.SQL("{} TEXT").format(sql.Identifier(identifier(col)))
                    for col in frame.columns
                )
                cur.execute(
                    sql.SQL("CREATE TABLE IF NOT EXISTS {} ({})").format(
                        sql.Identifier(BOOKS_TABLE), defs
                    )
                )
                existing = list(frame.columns)
            columns = [col for col in frame.columns if col in existing]
            if not columns:
                raise ValueError("Excel columns-ல் books table columns எதுவும் பொருந்தவில்லை.")
            values = []
            for row in frame[columns].itertuples(index=False, name=None):
                values.append(tuple(None if pd.isna(value) else value for value in row))
            insert = sql.SQL("INSERT INTO {} ({}) VALUES %s").format(
                sql.Identifier(BOOKS_TABLE),
                sql.SQL(", ").join(sql.Identifier(identifier(col)) for col in columns),
            )
            execute_values(cur, insert.as_string(conn), values, page_size=1000)
    return len(values)


def show_upload() -> None:
    st.subheader("📂 Excel / CSV அப்லோடு")
    st.caption("பெரிய கோப்புகளும் row-by-row இல்லாமல் bulk insert முறையில் சேமிக்கப்படும்.")
    uploaded = st.file_uploader("கோப்பைத் தேர்ந்தெடுக்கவும்", type=["xlsx", "xls", "csv"])
    if uploaded is None:
        return
    try:
        frame = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
        st.write(f"Rows: **{len(frame):,}** | Columns: **{len(frame.columns)}**")
        st.dataframe(frame.head(50), use_container_width=True, hide_index=True)
        if st.button("💾 books table-ல் bulk upload செய்", type="primary"):
            count = bulk_upload(frame)
            refresh_caches()
            st.success(f"{count:,} rows வேகமாக சேமிக்கப்பட்டன.")
            st.rerun()
    except Exception as exc:
        st.error(f"Upload error: {exc}")


def main() -> None:
    if not DATABASE_URL:
        st.error("DATABASE_URL அமைக்கப்படவில்லை.")
        st.code(
            "DATABASE_URL=postgresql://...\n"
            "AUTH_ADMIN_PASSWORD=...\n"
            "AUTH_DCL_STAFF_PASSWORD=...\n"
            "AUTH_LIBRARIAN_PASSWORD=...",
            language="text",
        )
        st.stop()
    try:
        initialize_database()
    except Exception:
        st.error("Neon database இணைப்பு தோல்வியடைந்தது. DATABASE_URL / database status-ஐ சரிபார்க்கவும்.")
        st.stop()

    for key, default in {
        "logged_in": False,
        "user_role": None,
        "user_name": "",
        "current_menu": None,
        "temp_distributed": [],
    }.items():
        st.session_state.setdefault(key, default)

    if not st.session_state.logged_in:
        show_login_page()
        st.stop()

    try:
        reports = load_submitted_reports()
    except Exception:
        st.error("Submitted reports ஏற்ற முடியவில்லை.")
        st.stop()
    show_header(reports)
    left, right = st.columns([11, 1])
    with right:
        if st.button("🚪 வெளியேறு", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_role = None
            st.rerun()
    current = show_menu()
    st.divider()
    if current is None:
        st.info("மேலுள்ள மெனுவில் ஒரு பிரிவைத் தேர்ந்தெடுக்கவும்.")
        return
    if current in {"பிரிக்க", "அனுப்ப", "கவனிக்க", "பதிவெண் மாற்ற",
                   "Master Data", "பகுப்பு எண் புதுப்பி", "Excel அப்லோடு"}:
        try:
            books = load_books()
        except Exception as exc:
            st.error(f"books table ஏற்ற முடியவில்லை: {exc}")
            return
    if current == "பிரிக்க":
        show_distribution(books, reports)
    elif current == "அனுப்ப":
        show_dispatch(reports)
    elif current == "அறிக்கைகள்":
        show_reports(reports)
    elif current == "கவனிக்க":
        show_review(books)
    elif current == "பதிவெண் மாற்ற":
        show_book_update(books, "accession")
    elif current == "Master Data":
        show_master_data(books, reports)
    elif current == "தவறான பதிவு நீக்கம்":
        show_corrections(reports)
    elif current == "கடவுச்சொல் மாற்ற":
        show_password_change()
    elif current == "Excel பதிவிறக்கம்":
        show_download(reports)
    elif current == "நூலகர் பார்வை ஆண்டு":
        show_librarian_year()
    elif current == "Excel அப்லோடு":
        show_upload()
    elif current == "பகுப்பு எண் புதுப்பி":
        show_book_update(books, "classification")


if __name__ == "__main__":
    main()