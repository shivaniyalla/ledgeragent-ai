import streamlit as st
import tempfile
import os
import pandas as pd
import sqlite3
import json
from datetime import datetime

from dotenv import load_dotenv

from read_invoice import extract_text_from_pdf
from invoice_processor import extract_invoice_details
from ai_extract import extract_invoice_data, classify_document
from validate_invoice import validate_invoice

from database import (
    create_database,
    save_invoice,
    get_accountant_clients,
    get_client_accountant,
    get_accountant_documents,
    get_client_documents,
    is_client_of_accountant
)

from auth.authentication import authenticate_user
from auth.permissions import has_permission


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="LedgerAgent",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded"
)


# =========================================================
# LOAD ENVIRONMENT
# =========================================================

load_dotenv()


# =========================================================
# DATABASE
# =========================================================

create_database()

DB_NAME = "ledgeragent.db"


# =========================================================
# SESSION STATE
# =========================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

if "selected_invoice_id" not in st.session_state:
    st.session_state.selected_invoice_id = None

if "selected_review_document_id" not in st.session_state:
    st.session_state.selected_review_document_id = None


# =========================================================
# HELPER
# =========================================================

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# ROLE HELPERS
# =========================================================

def is_admin():
    return current_role == "admin"


def is_accountant():
    return current_role == "accountant"


def is_client():
    return current_role == "client"


def can_upload():
    return current_role in ["admin", "accountant", "client"]


def can_view_documents():
    return current_role in ["admin", "accountant", "client"]


def can_review():
    return current_role in ["admin", "accountant"]


# =========================================================
# PREMIUM GLOBAL CSS
# =========================================================

st.markdown(
    """
<style>

.stApp {
    background:
        radial-gradient(
            circle at 85% 5%,
            rgba(79, 70, 229, 0.10),
            transparent 28%
        ),
        radial-gradient(
            circle at 10% 90%,
            rgba(37, 99, 235, 0.06),
            transparent 25%
        ),
        #070a10;
    color: #f8fafc;
}

.main {
    background: #070a10;
}

.block-container {
    max-width: 1450px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}

h1, h2, h3, h4 {
    color: #f8fafc !important;
    letter-spacing: -0.5px;
}

p, label {
    color: #a8b0c0;
}

section[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #0c1018 0%,
            #090c13 100%
        );
    border-right: 1px solid #1c2330;
}

section[data-testid="stSidebar"] > div {
    padding-top: 1.3rem;
}

section[data-testid="stSidebar"] .stRadio label {
    color: #aab2c2 !important;
}

section[data-testid="stSidebar"] .stRadio label:hover {
    color: #ffffff !important;
}

.brand-wrapper {
    padding: 10px 8px 18px 8px;
}

.brand-mark {
    width: 38px;
    height: 38px;
    border-radius: 11px;

    display: inline-flex;
    align-items: center;
    justify-content: center;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #2563eb
        );

    color: white;
    font-size: 20px;
    font-weight: 800;

    margin-right: 10px;

    box-shadow:
        0 8px 25px rgba(79,70,229,0.30);
}

.brand-title {
    color: #ffffff;
    font-size: 23px;
    font-weight: 800;
    letter-spacing: -0.7px;
}

.brand-subtitle {
    color: #687386;
    font-size: 11px;
    margin-top: 6px;
    letter-spacing: 0.2px;
}

.page-eyebrow {
    color: #818cf8;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.page-title {
    color: #ffffff;
    font-size: 34px;
    font-weight: 800;
    letter-spacing: -1.2px;
    margin-bottom: 6px;
}

.page-description {
    color: #7f899b;
    font-size: 14px;
    line-height: 1.6;
    max-width: 850px;
}

.hero {
    position: relative;
    overflow: hidden;

    background:
        linear-gradient(
            135deg,
            rgba(25,31,48,0.96),
            rgba(12,16,24,0.98)
        );

    border: 1px solid #252d3d;
    border-radius: 26px;

    padding: 48px 50px;

    margin-bottom: 34px;

    box-shadow:
        0 25px 70px rgba(0,0,0,0.30);
}

.hero:before {
    content: "";
    position: absolute;

    width: 280px;
    height: 280px;

    right: -90px;
    top: -120px;

    background: rgba(79,70,229,0.16);

    filter: blur(70px);

    border-radius: 50%;
}

.hero-badge {
    display: inline-block;

    padding: 7px 12px;

    border-radius: 30px;

    background: rgba(99,102,241,0.10);

    border: 1px solid rgba(129,140,248,0.22);

    color: #a5b4fc;

    font-size: 10px;
    font-weight: 800;

    letter-spacing: 1.2px;

    margin-bottom: 18px;
}

.hero-title {
    position: relative;

    color: #ffffff;

    font-size: 48px;

    font-weight: 850;

    line-height: 1.08;

    letter-spacing: -2px;

    max-width: 800px;

    margin-bottom: 17px;
}

.hero-text {
    position: relative;

    color: #9da7b8;

    font-size: 16px;

    line-height: 1.75;

    max-width: 850px;
}

.feature-card {
    background:
        linear-gradient(
            145deg,
            rgba(20,25,36,0.95),
            rgba(11,15,22,0.95)
        );

    border: 1px solid #222a38;

    border-radius: 20px;

    padding: 26px;

    min-height: 190px;

    box-shadow:
        0 12px 35px rgba(0,0,0,0.18);
}

.feature-icon {
    width: 44px;
    height: 44px;

    display: flex;
    align-items: center;
    justify-content: center;

    border-radius: 13px;

    background: rgba(99,102,241,0.10);

    border: 1px solid rgba(129,140,248,0.15);

    font-size: 21px;

    margin-bottom: 20px;
}

.feature-title {
    color: #ffffff;
    font-size: 17px;
    font-weight: 700;
    margin-bottom: 9px;
}

.feature-text {
    color: #7f899b;
    font-size: 13px;
    line-height: 1.7;
}

.section-heading {
    color: #ffffff;
    font-size: 22px;
    font-weight: 750;
    letter-spacing: -0.5px;
    margin-bottom: 18px;
}

.workflow-card {
    background: #0f141d;
    border: 1px solid #202837;
    border-radius: 17px;
    padding: 20px;
    min-height: 110px;
    position: relative;
}

.workflow-number {
    color: #6366f1;
    font-size: 10px;
    font-weight: 850;
    letter-spacing: 1px;
    margin-bottom: 10px;
}

.workflow-title {
    color: #f8fafc;
    font-size: 15px;
    font-weight: 700;
}

.kpi-card {
    background:
        linear-gradient(
            145deg,
            #121823,
            #0d1119
        );

    border: 1px solid #222b3a;

    border-radius: 19px;

    padding: 23px;

    min-height: 125px;

    box-shadow:
        0 10px 30px rgba(0,0,0,0.20);
}

.kpi-top {
    color: #778196;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 13px;
}

.kpi-value {
    color: #ffffff;
    font-size: 30px;
    font-weight: 800;
    letter-spacing: -1px;
}

.kpi-icon {
    float: right;
    width: 34px;
    height: 34px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 10px;
    background: rgba(99,102,241,0.10);
    color: #a5b4fc;
    font-size: 15px;
}

.tech-card {
    background: #0e131b;
    border: 1px solid #202837;
    border-radius: 17px;
    padding: 23px;
    text-align: center;
    min-height: 120px;
}

.tech-icon {
    font-size: 24px;
    margin-bottom: 11px;
}

.tech-name {
    color: #ffffff;
    font-size: 14px;
    font-weight: 700;
}

.login-shell {
    max-width: 480px;
    margin: 70px auto 0 auto;
    text-align: center;
}

.login-brand {
    width: 58px;
    height: 58px;

    margin: 0 auto 18px auto;

    display: flex;
    align-items: center;
    justify-content: center;

    border-radius: 17px;

    background:
        linear-gradient(
            135deg,
            #6366f1,
            #2563eb
        );

    color: white;

    font-size: 27px;
    font-weight: 800;

    box-shadow:
        0 15px 35px rgba(79,70,229,0.25);
}

.login-title {
    color: #ffffff;
    font-size: 34px;
    font-weight: 850;
    letter-spacing: -1px;
}

.login-subtitle {
    color: #727d91;
    font-size: 13px;
    margin-top: 7px;
    margin-bottom: 30px;
}

.analysis-panel {
    background:
        linear-gradient(
            145deg,
            rgba(20,26,39,0.98),
            rgba(11,15,23,0.98)
        );

    border: 1px solid #29334a;

    border-radius: 20px;

    padding: 25px;

    margin-top: 20px;

    box-shadow:
        0 15px 40px rgba(0,0,0,0.20);
}

.analysis-title {
    color: #ffffff;
    font-size: 21px;
    font-weight: 800;
}

.analysis-subtitle {
    color: #7d889b;
    font-size: 13px;
    line-height: 1.7;
    margin-top: 6px;
}

.invoice-label {
    color: #667287;
    font-size: 9px;
    font-weight: 750;
    letter-spacing: 1px;
    text-transform: uppercase;
    margin-bottom: 5px;
}

.invoice-value {
    color: #f1f5f9;
    font-size: 14px;
    font-weight: 700;
}

.status-valid,
.status-review,
.status-approved,
.status-rejected {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 20px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

.status-valid {
    background: rgba(34,197,94,0.09);
    border: 1px solid rgba(34,197,94,0.20);
    color: #86efac;
}

.status-review {
    background: rgba(245,158,11,0.09);
    border: 1px solid rgba(245,158,11,0.20);
    color: #fcd34d;
}

.status-approved {
    background: rgba(34,197,94,0.10);
    border: 1px solid rgba(34,197,94,0.25);
    color: #86efac;
}

.status-rejected {
    background: rgba(239,68,68,0.10);
    border: 1px solid rgba(239,68,68,0.25);
    color: #fca5a5;
}

.audit-card {
    background: #0d121a;
    border: 1px solid #222c3b;
    border-radius: 13px;
    padding: 15px;
    margin-bottom: 10px;
}

.audit-action {
    color: #ffffff;
    font-size: 13px;
    font-weight: 750;
}

.audit-meta {
    color: #6f7b8f;
    font-size: 11px;
    margin-top: 5px;
}

.audit-details {
    color: #aeb7c7;
    font-size: 12px;
    margin-top: 8px;
    line-height: 1.6;
}

.stButton > button {
    border-radius: 10px !important;
    border: 1px solid #293449 !important;
    background: #121925 !important;
    color: #dce3ee !important;
    font-weight: 700 !important;
}

.stButton > button:hover {
    border-color: #5869a0 !important;
    background: #172033 !important;
    color: #ffffff !important;
    transform: translateY(-1px);
}

.stButton > button[kind="primary"] {
    background:
        linear-gradient(
            135deg,
            #6366f1,
            #3b82f6
        ) !important;

    border: none !important;
    color: #ffffff !important;

    box-shadow:
        0 8px 25px rgba(79,70,229,0.20);
}

div[data-baseweb="input"] {
    background: #0d121b !important;
    border: 1px solid #283244 !important;
    border-radius: 10px !important;
}

div[data-baseweb="input"]:focus-within {
    border-color: #5968a1 !important;
}

div[data-baseweb="select"] {
    background: #0d121b !important;
    border-radius: 10px !important;
}

[data-testid="stFileUploader"] {
    background:
        linear-gradient(
            145deg,
            #111722,
            #0d1118
        );

    border: 1px dashed #354158;
    border-radius: 18px;
    padding: 12px;
}

[data-testid="stDataFrame"] {
    border: 1px solid #222c3b;
    border-radius: 14px;
    overflow: hidden;
}

[data-testid="stMetric"] {
    background: #0f141d;
    border: 1px solid #222c3b;
    border-radius: 16px;
    padding: 18px;
}

[data-testid="stExpander"] {
    background: #0e131b;
    border: 1px solid #222c3b;
    border-radius: 14px;
}

hr {
    border-color: #202735 !important;
}

div[data-testid="stAlert"] {
    border-radius: 13px;
}

#MainMenu {
    visibility: hidden;
}

footer {
    visibility: hidden;
}

header[data-testid="stHeader"] {
    background: transparent;
}

</style>
""",
    unsafe_allow_html=True
)


# =========================================================
# LOGIN PAGE
# =========================================================

def login_page():

    # =====================================================
    # LOGIN PAGE STYLING
    # =====================================================

    st.markdown(
        """
        <style>

        /* ===== MAIN BACKGROUND ===== */

        .stApp {
            background:
                radial-gradient(
                    circle at 8% 8%,
                    rgba(59, 130, 246, 0.28),
                    transparent 24%
                ),
                radial-gradient(
                    circle at 92% 88%,
                    rgba(99, 102, 241, 0.25),
                    transparent 28%
                ),
                radial-gradient(
                    circle at 85% 12%,
                    rgba(37, 99, 235, 0.16),
                    transparent 22%
                ),
                linear-gradient(
                    135deg,
                    #050914 0%,
                    #09132e 48%,
                    #111a45 100%
                );

            min-height: 100vh;
        }


        /* ===== REMOVE DEFAULT TOP SPACE ===== */

        .block-container {
            padding-top: 3rem !important;
            padding-bottom: 2rem !important;
        }


        /* ===== DECORATIVE BACKGROUND ===== */

        .login-background {
            position: fixed;
            inset: 0;
            pointer-events: none;
            overflow: hidden;
            z-index: 0;
        }

        .glow-one {
            position: absolute;
            width: 420px;
            height: 420px;
            top: -180px;
            left: -160px;
            border-radius: 50%;
            background: rgba(37, 99, 235, 0.22);
            filter: blur(70px);
        }

        .glow-two {
            position: absolute;
            width: 380px;
            height: 380px;
            bottom: -160px;
            right: -120px;
            border-radius: 50%;
            background: rgba(79, 70, 229, 0.28);
            filter: blur(75px);
        }

        .glow-three {
            position: absolute;
            width: 250px;
            height: 250px;
            top: 25%;
            right: 5%;
            border-radius: 50%;
            background: rgba(59, 130, 246, 0.10);
            filter: blur(65px);
        }


        /* ===== BRAND ===== */

        .login-shell {
            text-align: center;
            position: relative;
            z-index: 2;
            margin-bottom: 30px;
        }

        .login-brand {
            width: 72px;
            height: 72px;
            margin: 0 auto 18px auto;

            display: flex;
            align-items: center;
            justify-content: center;

            border-radius: 18px;

            background:
                linear-gradient(
                    135deg,
                    #6366f1,
                    #2563eb
                );

            color: white;

            font-size: 38px;
            font-weight: 700;

            box-shadow:
                0 12px 35px rgba(37, 99, 235, 0.40);
        }

        .login-title {
            font-size: 38px;
            font-weight: 800;
            letter-spacing: -1.2px;
            color: #ffffff;
        }

        .login-subtitle {
            margin-top: 7px;
            font-size: 14px;
            color: #8fa3c7;
            letter-spacing: 0.2px;
        }


        /* ===== LOGIN CARD ===== */

        div[data-testid="stVerticalBlock"] {
            position: relative;
            z-index: 2;
        }

        .login-card {
            max-width: 680px;
            margin: 0 auto 22px auto;

            padding: 34px 38px;

            border-radius: 24px;

            background:
                linear-gradient(
                    145deg,
                    rgba(24, 36, 65, 0.82),
                    rgba(8, 16, 35, 0.88)
                );

            border: 1px solid rgba(96, 165, 250, 0.28);

            box-shadow:
                0 25px 70px rgba(0, 0, 0, 0.38),
                inset 0 1px 0 rgba(255,255,255,0.05);

            backdrop-filter: blur(18px);
        }

        .welcome-title {
            text-align: center;
            color: #ffffff;
            font-size: 25px;
            font-weight: 750;
        }

        .welcome-subtitle {
            text-align: center;
            color: #8fa3c7;
            font-size: 13px;
            margin-top: 7px;
        }


        /* ===== INPUT LABELS ===== */

        .stTextInput label {
            color: #b9c9e5 !important;
            font-size: 14px !important;
            font-weight: 600 !important;
        }


        /* ===== INPUT BOXES ===== */

        .stTextInput input {
            height: 52px !important;

            border-radius: 11px !important;

            background:
                rgba(15, 27, 52, 0.88) !important;

            border: 1px solid
                rgba(96, 165, 250, 0.30) !important;

            color: #ffffff !important;

            font-size: 14px !important;

            padding-left: 15px !important;
        }

        .stTextInput input::placeholder {
            color: #7185a8 !important;
        }

        .stTextInput input:focus {
            border-color:
                #4f8df7 !important;

            box-shadow:
                0 0 0 1px #4f8df7,
                0 0 18px rgba(59,130,246,0.18) !important;
        }


        /* ===== SIGN IN BUTTON ===== */

        .stButton > button {
            height: 52px !important;

            border-radius: 11px !important;

            border: none !important;

            background:
                linear-gradient(
                    90deg,
                    #6366f1,
                    #3b82f6
                ) !important;

            color: white !important;

            font-size: 15px !important;
            font-weight: 650 !important;

            box-shadow:
                0 10px 28px
                rgba(59, 130, 246, 0.25);

            transition:
                transform 0.2s ease,
                box-shadow 0.2s ease;
        }

        .stButton > button:hover {
            transform: translateY(-1px);

            box-shadow:
                0 14px 35px
                rgba(59, 130, 246, 0.38);
        }


        /* ===== ERROR MESSAGE ===== */

        div[data-testid="stAlert"] {
            border-radius: 10px !important;
        }

        </style>
        """,
        unsafe_allow_html=True
    )


    # =====================================================
    # BACKGROUND GLOW ELEMENTS
    # =====================================================

    st.html(
        """
        <div class="login-background">

            <div class="glow-one"></div>

            <div class="glow-two"></div>

            <div class="glow-three"></div>

        </div>
        """
    )


    # =====================================================
    # BRAND
    # =====================================================

    st.html(
        """
        <div class="login-shell">

            <div class="login-brand">
                ◈
            </div>

            <div class="login-title">
                LedgerAgent
            </div>

            <div class="login-subtitle">
                Intelligent Accounting Operations
            </div>

        </div>
        """
    )


    # =====================================================
    # LOGIN CARD
    # =====================================================

    left, center, right = st.columns(
        [0.55, 1.9, 0.55]
    )


    with center:

        st.html(
            """
            <div class="login-card">

                <div class="welcome-title">
                    Welcome back
                </div>

                <div class="welcome-subtitle">
                    Sign in to access your accounting workspace.
                </div>

            </div>
            """
        )


        # =================================================
        # USERNAME
        # =================================================

        username = st.text_input(
            "Username",
            placeholder="Enter your username"
        )


        # =================================================
        # PASSWORD
        # =================================================

        password = st.text_input(
            "Password",
            type="password",
            placeholder="Enter your password"
        )


        st.write("")


        # =================================================
        # SIGN IN
        # =================================================

        if st.button(
            "Sign In  →",
            type="primary",
            use_container_width=True
        ):

            user = authenticate_user(
                username,
                password
            )

            if user:

                st.session_state.logged_in = True

                st.session_state.user = user

                st.rerun()

            else:

                st.error(
                    "Incorrect username or password."
                )

# =========================================================
# LOGIN CHECK
# =========================================================

if not st.session_state.logged_in:

    login_page()
    st.stop()


# =========================================================
# CURRENT USER
# =========================================================

current_user = st.session_state.user

current_username = current_user["username"]

current_role = current_user["role"]

current_user_id = current_user["id"]


# =========================================================
# ACCOUNTANT / CLIENT RELATIONSHIP
# =========================================================

assigned_accountant = None

if current_role == "client":

    assigned_accountant = get_client_accountant(
        current_user_id
    )


# =========================================================
# DOCUMENT ACCESS CONTROL
# =========================================================

def accountant_has_document_access(document_id):
    if current_role == "admin":
        return True
    if current_role != "accountant":
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM documents d
        JOIN accountant_clients ac
          ON ac.client_id = d.client_id
         AND ac.accountant_id = ?
        WHERE d.id = ?
          AND d.accountant_id = ?
        LIMIT 1
        """,
        (current_user_id, document_id, current_user_id)
    )
    allowed = cursor.fetchone() is not None
    conn.close()
    return allowed


def accountant_has_invoice_access(invoice_id):
    if current_role == "admin":
        return True
    if current_role != "accountant":
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 1
        FROM invoices i
        JOIN accountant_clients ac
          ON ac.client_id = i.client_id
         AND ac.accountant_id = ?
        WHERE i.id = ?
          AND i.accountant_id = ?
        LIMIT 1
        """,
        (current_user_id, invoice_id, current_user_id)
    )
    allowed = cursor.fetchone() is not None
    conn.close()
    return allowed


# =========================================================
# GET INVOICES
# =========================================================

def get_invoices():
    conn = sqlite3.connect(DB_NAME)

    query = """
        SELECT
            i.id,
            i.invoice_number,
            i.invoice_date,
            i.seller_name,
            i.customer_name,
            i.subtotal,
            i.cgst,
            i.sgst,
            i.total,
            i.payment_status,
            i.validation_status,
            i.workflow_status,
            i.uploaded_by,
            i.client_id,
            i.accountant_id,
            c.username AS client_name,
            a.username AS accountant_name
        FROM invoices i
        LEFT JOIN users c ON i.client_id = c.id
        LEFT JOIN users a ON i.accountant_id = a.id
    """

    params = []

    if current_role == "client":
        query += " WHERE i.client_id = ?"
        params.append(current_user_id)

    elif current_role == "accountant":
        query += """
            JOIN accountant_clients ac
              ON ac.client_id = i.client_id
             AND ac.accountant_id = ?
            WHERE i.accountant_id = ?
        """
        params.extend([current_user_id, current_user_id])

    elif current_role == "admin":
        pass

    else:
        query += " WHERE 1 = 0"

    query += " ORDER BY i.id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_invoice_details(invoice_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = """
        SELECT
            i.id,
            i.invoice_number,
            i.invoice_date,
            i.seller_name,
            i.seller_gstin,
            i.customer_name,
            i.items,
            i.subtotal,
            i.cgst,
            i.sgst,
            i.total,
            i.payment_status,
            i.validation_status,
            i.workflow_status,
            i.uploaded_by,
            i.client_id,
            i.accountant_id,
            c.username AS client_name,
            a.username AS accountant_name
        FROM invoices i
        LEFT JOIN users c ON i.client_id = c.id
        LEFT JOIN users a ON i.accountant_id = a.id
        WHERE i.id = ?
    """
    params = [invoice_id]

    if current_role == "client":
        query += " AND i.client_id = ?"
        params.append(current_user_id)
    elif current_role == "accountant":
        query += """
            AND i.accountant_id = ?
            AND EXISTS (
                SELECT 1
                FROM accountant_clients ac
                WHERE ac.accountant_id = ?
                  AND ac.client_id = i.client_id
            )
        """
        params.extend([current_user_id, current_user_id])
    elif current_role != "admin":
        query += " AND 1 = 0"

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "invoice_number": row[1],
        "invoice_date": row[2],
        "seller_name": row[3],
        "seller_gstin": row[4],
        "customer_name": row[5],
        "items": row[6],
        "subtotal": row[7],
        "cgst": row[8],
        "sgst": row[9],
        "total": row[10],
        "payment_status": row[11],
        "validation_status": row[12],
        "workflow_status": row[13],
        "uploaded_by": row[14],
        "client_id": row[15],
        "accountant_id": row[16],
        "client_name": row[17],
        "accountant_name": row[18]
    }

def get_review_queue():
    conn = sqlite3.connect(DB_NAME)

    query = """
        SELECT
            d.id AS document_id,
            d.invoice_id,
            d.source_filename,
            d.document_type,
            d.workflow_status,
            d.validation_status,
            d.uploaded_by,
            d.created_at,
            d.client_id,
            d.accountant_id,
            i.invoice_number,
            i.invoice_date,
            i.seller_name,
            i.customer_name,
            i.total,
            c.username AS client_name,
            a.username AS accountant_name
        FROM documents d
        LEFT JOIN invoices i ON d.invoice_id = i.id
        LEFT JOIN users c ON d.client_id = c.id
        LEFT JOIN users a ON d.accountant_id = a.id
        WHERE d.workflow_status IN ('REVIEW_REQUIRED', 'IN_REVIEW')
    """
    params = []

    if current_role == "accountant":
        query += """
            AND d.accountant_id = ?
            AND EXISTS (
                SELECT 1
                FROM accountant_clients ac
                WHERE ac.accountant_id = ?
                  AND ac.client_id = d.client_id
            )
        """
        params.extend([current_user_id, current_user_id])
    elif current_role == "client":
        query += " AND d.client_id = ?"
        params.append(current_user_id)
    elif current_role != "admin":
        query += " AND 1 = 0"

    query += " ORDER BY d.id DESC"

    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    return df

def get_document_details(document_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    query = """
        SELECT
            d.id,
            d.invoice_id,
            d.source_filename,
            d.document_type,
            d.workflow_status,
            d.validation_status,
            d.uploaded_by,
            d.created_at,
            d.updated_at,
            d.client_id,
            d.accountant_id,
            i.invoice_number,
            c.username AS client_name,
            a.username AS accountant_name
        FROM documents d
        LEFT JOIN invoices i ON d.invoice_id = i.id
        LEFT JOIN users c ON d.client_id = c.id
        LEFT JOIN users a ON d.accountant_id = a.id
        WHERE d.id = ?
    """
    params = [document_id]

    if current_role == "accountant":
        query += """
            AND d.accountant_id = ?
            AND EXISTS (
                SELECT 1
                FROM accountant_clients ac
                WHERE ac.accountant_id = ?
                  AND ac.client_id = d.client_id
            )
        """
        params.extend([current_user_id, current_user_id])
    elif current_role == "client":
        query += " AND d.client_id = ?"
        params.append(current_user_id)
    elif current_role != "admin":
        query += " AND 1 = 0"

    cursor.execute(query, params)
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "document_id": row[0],
        "invoice_id": row[1],
        "source_filename": row[2],
        "document_type": row[3],
        "workflow_status": row[4],
        "validation_status": row[5],
        "uploaded_by": row[6],
        "created_at": row[7],
        "updated_at": row[8],
        "client_id": row[9],
        "accountant_id": row[10],
        "invoice_number": row[11],
        "client_name": row[12],
        "accountant_name": row[13]
    }

def start_document_review(document_id, user_id):
    if current_role not in ["admin", "accountant"]:
        return False

    if user_id != current_user_id:
        return False

    if current_role == "accountant" and not accountant_has_document_access(document_id):
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = current_timestamp()

    cursor.execute(
        "SELECT invoice_id, accountant_id FROM documents WHERE id = ?",
        (document_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False

    invoice_id, accountant_id = row

    if current_role == "accountant" and accountant_id != current_user_id:
        conn.close()
        return False

    cursor.execute(
        """
        UPDATE documents
        SET workflow_status = 'IN_REVIEW', updated_at = ?
        WHERE id = ? AND workflow_status = 'REVIEW_REQUIRED'
        """,
        (now, document_id)
    )

    if cursor.rowcount != 1:
        conn.close()
        return False

    if invoice_id is not None:
        cursor.execute(
            """
            UPDATE invoices
            SET workflow_status = 'IN_REVIEW', updated_at = ?
            WHERE id = ?
            """,
            (now, invoice_id)
        )

    cursor.execute(
        """
        INSERT INTO audit_logs (document_id, user_id, action, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, user_id, "REVIEW_STARTED", "Accountant started reviewing the document.", now)
    )

    conn.commit()
    conn.close()
    return True


# =========================================================
# APPROVE DOCUMENT
# =========================================================

def approve_document(document_id, user_id, comment=""):
    if not has_permission(current_role, "approve_document"):
        return False

    if user_id != current_user_id:
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = current_timestamp()

    cursor.execute(
        "SELECT invoice_id, accountant_id, client_id FROM documents WHERE id = ?",
        (document_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False

    invoice_id, accountant_id, client_id = row

    if current_role == "accountant":
        if accountant_id != current_user_id or not accountant_has_document_access(document_id):
            conn.close()
            return False

    cursor.execute(
        """
        UPDATE documents
        SET workflow_status = 'APPROVED', updated_at = ?
        WHERE id = ?
          AND workflow_status IN ('REVIEW_REQUIRED', 'IN_REVIEW')
        """,
        (now, document_id)
    )

    if cursor.rowcount != 1:
        conn.close()
        return False

    if invoice_id is not None:
        cursor.execute(
            """
            UPDATE invoices
            SET workflow_status = 'APPROVED', updated_at = ?
            WHERE id = ?
            """,
            (now, invoice_id)
        )

    cursor.execute(
        """
        INSERT INTO approvals (document_id, action, user_id, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, "APPROVED", user_id, comment, now)
    )

    details = "Document approved by accountant."
    if comment.strip():
        details += f" Accountant comment: {comment.strip()}"

    cursor.execute(
        """
        INSERT INTO audit_logs (document_id, user_id, action, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, user_id, "APPROVED", details, now)
    )

    conn.commit()
    conn.close()
    return True


# =========================================================
# REJECT DOCUMENT
# =========================================================

def reject_document(document_id, user_id, comment=""):
    if not has_permission(current_role, "reject_document"):
        return False

    if user_id != current_user_id:
        return False

    if not comment.strip():
        return False

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    now = current_timestamp()

    cursor.execute(
        "SELECT invoice_id, accountant_id, client_id FROM documents WHERE id = ?",
        (document_id,)
    )
    row = cursor.fetchone()

    if row is None:
        conn.close()
        return False

    invoice_id, accountant_id, client_id = row

    if current_role == "accountant":
        if accountant_id != current_user_id or not accountant_has_document_access(document_id):
            conn.close()
            return False

    cursor.execute(
        """
        UPDATE documents
        SET workflow_status = 'REJECTED', updated_at = ?
        WHERE id = ?
          AND workflow_status IN ('REVIEW_REQUIRED', 'IN_REVIEW')
        """,
        (now, document_id)
    )

    if cursor.rowcount != 1:
        conn.close()
        return False

    if invoice_id is not None:
        cursor.execute(
            """
            UPDATE invoices
            SET workflow_status = 'REJECTED', updated_at = ?
            WHERE id = ?
            """,
            (now, invoice_id)
        )

    cursor.execute(
        """
        INSERT INTO approvals (document_id, action, user_id, comment, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, "REJECTED", user_id, comment, now)
    )

    details = "Document rejected by accountant."
    details += f" Accountant comment: {comment.strip()}"

    cursor.execute(
        """
        INSERT INTO audit_logs (document_id, user_id, action, details, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (document_id, user_id, "REJECTED", details, now)
    )

    conn.commit()
    conn.close()
    return True


# =========================================================
# AUDIT TRAIL
# =========================================================

def get_audit_logs(
    document_id
):

    conn = sqlite3.connect(
        DB_NAME
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            a.action,
            a.details,
            a.created_at,
            u.username,
            u.role

        FROM audit_logs a

        LEFT JOIN users u
            ON a.user_id = u.id

        WHERE a.document_id = ?

        ORDER BY a.id DESC
        """,
        (document_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# =========================================================
# APPROVAL HISTORY
# =========================================================

def get_approval_history(
    document_id
):

    conn = sqlite3.connect(
        DB_NAME
    )

    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            a.action,
            a.comment,
            a.created_at,
            u.username,
            u.role

        FROM approvals a

        LEFT JOIN users u
            ON a.user_id = u.id

        WHERE a.document_id = ?

        ORDER BY a.id DESC
        """,
        (document_id,)
    )

    rows = cursor.fetchall()

    conn.close()

    return rows


# =========================================================
# PREPARE INVOICE
# =========================================================

def prepare_invoice_for_validation(
    invoice
):

    try:

        items = json.loads(
            invoice.get("items") or "[]"
        )

    except (
        json.JSONDecodeError,
        TypeError
    ):

        items = []

    return {

        "invoice_number":
            invoice.get("invoice_number"),

        "invoice_date":
            invoice.get("invoice_date"),

        "seller_name":
            invoice.get("seller_name"),

        "seller_gstin":
            invoice.get("seller_gstin"),

        "customer_name":
            invoice.get("customer_name"),

        "items":
            items,

        "subtotal":
            invoice.get("subtotal"),

        "cgst":
            invoice.get("cgst"),

        "sgst":
            invoice.get("sgst"),

        "total":
            invoice.get("total"),

        "payment_status":
            invoice.get("payment_status")
    }


# =========================================================
# INVOICE SUMMARY
# =========================================================

def generate_invoice_summary(
    invoice,
    issues
):

    if issues:

        issue_count = len(
            issues
        )

        if issue_count == 1:

            issue_text = (
                "1 inconsistency was detected."
            )

        else:

            issue_text = (
                f"{issue_count} inconsistencies were detected."
            )

        return (
            "This invoice requires accountant review. "
            "LedgerAgent extracted the invoice information "
            f"and {issue_text} "
            "The detected issue(s) should be verified "
            "by an accountant before the record is finalized."
        )

    return (
        "This invoice was processed successfully. "
        "LedgerAgent extracted the financial information "
        "and no calculation inconsistencies were detected. "
        "The record can proceed to accountant review."
    )


# =========================================================
# SIDEBAR
# =========================================================

st.markdown(
    """
    <style>

    /* ===== SIDEBAR WIDTH ===== */
    section[data-testid="stSidebar"] {
        width: 300px !important;
        min-width: 300px !important;
    }

    section[data-testid="stSidebar"] > div {
        width: 300px !important;
    }

    /* ===== BRAND ===== */
    .brand-wrapper {
        padding: 8px 4px 12px 4px;
    }

    .brand-mark {
        width: 42px;
        height: 42px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        font-weight: 700;
        margin-right: 12px;
        background: linear-gradient(
            135deg,
            #6d5dfc,
            #3b82f6
        );
        color: white;
        box-shadow: 0 6px 18px rgba(79, 70, 229, 0.25);
    }

    .brand-title {
        font-size: 23px;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .brand-subtitle {
        font-size: 12px;
        opacity: 0.65;
        margin-top: 10px;
        line-height: 1.5;
    }

    /* ===== NAVIGATION ===== */

    section[data-testid="stSidebar"] .stRadio > label {
        font-size: 13px;
        font-weight: 600;
        margin-bottom: 10px;
        opacity: 0.65;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] {
        gap: 7px;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label {
        padding: 12px 14px;
        border-radius: 10px;
        font-size: 15px;
        font-weight: 500;
        transition: all 0.2s ease;
    }

    section[data-testid="stSidebar"] .stRadio div[role="radiogroup"] > label:hover {
        background: rgba(127, 127, 127, 0.10);
    }

    /* ===== ACCOUNT ===== */

    .account-section {
        margin-top: 8px;
        padding: 14px;
        border-radius: 12px;
        background: rgba(127, 127, 127, 0.08);
        border: 1px solid rgba(127, 127, 127, 0.12);
    }

    .account-label {
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1px;
        opacity: 0.55;
        margin-bottom: 8px;
    }

    .account-name {
        font-size: 16px;
        font-weight: 650;
    }

    .account-role {
        font-size: 12px;
        opacity: 0.60;
        margin-top: 3px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


with st.sidebar:

    st.html(
        """
        <div class="brand-wrapper">

            <div style="
                display:flex;
                align-items:center;
            ">

                <div class="brand-mark">
                    ◈
                </div>

                <div class="brand-title">
                    LedgerAgent
                </div>

            </div>

            <div class="brand-subtitle">
                Intelligent Accounting Operations
            </div>

        </div>
        """
    )

    st.divider()

    available_pages = [
        "🏠 Home"
    ]

    if can_view_documents():

        available_pages.append(
            "📋 Overview"
        )

    if can_upload():

        available_pages.append(
            "🔍 Analysis"
        )

    if can_review():

        available_pages.append(
            "📥 Accountant Review"
        )

    if can_view_documents():

        available_pages.append(
            "🕘 History"
        )

    if current_role in ["admin", "accountant"]:

        available_pages.append(
            "📊 Dashboard"
        )

    page = st.radio(
        "Navigation",
        available_pages,
        label_visibility="collapsed"
    )

    st.divider()

    st.html(
        f"""
        <div class="account-section">

            <div class="account-label">
                ACCOUNT
            </div>

            <div class="account-name">
                {current_username}
            </div>

            <div class="account-role">
                Role: {current_role.title()}
            </div>

        </div>
        """
    )

    # -----------------------------------------------------
    # CLIENT CONNECTION
    # -----------------------------------------------------

    if current_role == "client":

        if assigned_accountant:

            st.caption(
                f"Accountant: {assigned_accountant['username']}"
            )

        else:

            st.warning(
                "No accountant assigned yet."
            )

    elif current_role == "accountant":

        try:

            clients = get_accountant_clients(
                current_user_id
            )

            st.caption(
                f"Assigned Clients: {len(clients)}"
            )

        except Exception:

            pass

    if st.button(
        "↪  Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False
        st.session_state.user = None
        st.session_state.selected_invoice_id = None
        st.session_state.selected_review_document_id = None

        st.rerun()


# =========================================================
# HOME
# =========================================================

if page == "🏠 Home":

    st.html(
        """
        <div class="hero">

            <div class="hero-badge">
                AI-POWERED ACCOUNTING OPERATIONS
            </div>

            <div class="hero-title">
                Accounting,<br>
                intelligently automated.
            </div>

            <div class="hero-text">
                LedgerAgent transforms unstructured financial
                documents into structured accounting information,
                validates transaction consistency, and organizes
                records for efficient accounting operations —
                while keeping accountants in control.
            </div>

        </div>
        """
    )

    # -----------------------------------------------------
    # CLIENT ACCOUNTANT CONNECTION
    # -----------------------------------------------------

    if current_role == "client":

        if assigned_accountant:

            st.success(
                f"Your documents are connected to "
                f"Accountant: {assigned_accountant['username']}"
            )

        else:

            st.warning(
                "No accountant has been assigned to your account yet."
            )

    elif current_role == "accountant":

        try:

            clients = get_accountant_clients(
                current_user_id
            )

            if clients:

                st.info(
                    f"You currently have {len(clients)} assigned client(s)."
                )

                st.html(
                    """
                    <div class="section-heading">
                        My Clients & Documents
                    </div>
                    """
                )

                accountant_documents = get_accountant_documents(
                    current_user_id
                )

                for client in clients:

                    client_id = client["id"]
                    client_username = client["username"]

                    st.subheader(
                        f"👤 {client_username}"
                    )

                    client_documents = [
                        doc
                        for doc in accountant_documents
                        if doc["client_id"] == client_id
                    ]

                    if client_documents:

                        for doc in client_documents:

                            st.write(
                                f"📄 **{doc['source_filename']}**"
                            )

                            st.caption(
                                f"Document Type: {doc['document_type']} | "
                                f"Status: {doc['workflow_status']} | "
                                f"Validation: {doc['validation_status']}"
                            )

                    else:

                        st.info(
                            "No documents uploaded by this client yet."
                        )

                    st.divider()

            else:

                st.warning(
                    "No clients are currently assigned to you."
                )

        except Exception as e:

            st.error(
                f"Unable to load client documents: {e}"
            )

    st.html(
        """
        <div class="section-heading">
            What LedgerAgent Does
        </div>
        """
    )

    col1, col2, col3 = st.columns(3)

    with col1:

        st.html(
            """
            <div class="feature-card">

                <div class="feature-icon">
                    ◫
                </div>

                <div class="feature-title">
                    Document Intelligence
                </div>

                <div class="feature-text">
                    Extract structured information from invoices
                    and financial documents using AI.
                </div>

            </div>
            """
        )

    with col2:

        st.html(
            """
            <div class="feature-card">

                <div class="feature-icon">
                    ◇
                </div>

                <div class="feature-title">
                    Intelligent Validation
                </div>

                <div class="feature-text">
                    Detect missing information, calculation
                    inconsistencies and suspicious records.
                </div>

            </div>
            """
        )

    with col3:

        st.html(
            """
            <div class="feature-card">

                <div class="feature-icon">
                    ◎
                </div>

                <div class="feature-title">
                    Accountant-in-the-Loop
                </div>

                <div class="feature-text">
                    Flag important issues for accountant review
                    instead of making autonomous financial decisions.
                </div>

            </div>
            """
        )

    st.write("")

    st.html(
        """
        <div class="section-heading">
            How It Works
        </div>
        """
    )

    workflow = [
        ("01", "Upload"),
        ("02", "Extract"),
        ("03", "Understand"),
        ("04", "Validate"),
        ("05", "Accountant Review"),
        ("06", "Store")
    ]

    workflow_cols = st.columns(6)

    for col, (number, title) in zip(
        workflow_cols,
        workflow
    ):

        with col:

            st.html(
                f"""
                <div class="workflow-card">

                    <div class="workflow-number">
                        {number}
                    </div>

                    <div class="workflow-title">
                        {title}
                    </div>

                </div>
                """
            )


# =========================================================
# OVERVIEW
# =========================================================

elif page == "📋 Overview":

    if not can_view_documents():

        st.error(
            "You do not have permission to view the system overview."
        )

        st.stop()

    st.html(
        """
        <div class="page-eyebrow">
            PLATFORM
        </div>

        <div class="page-title">
            System Overview
        </div>

        <div class="page-description">
            An AI-powered accounting operations platform
            designed to reduce repetitive document-processing
            work for finance teams and accounting professionals.
        </div>
        """
    )

    st.divider()

    st.html(
        """
        <div class="section-heading">
            Core Workflow
        </div>
        """
    )

    steps = [
        (
            "01",
            "Document Intake",
            "Receive invoices and financial documents."
        ),
        (
            "02",
            "Text Extraction",
            "Extract readable content from uploaded documents."
        ),
        (
            "03",
            "AI Understanding",
            "Convert unstructured information into structured data."
        ),
        (
            "04",
            "Validation",
            "Check calculations and identify inconsistencies."
        ),
        (
            "05",
            "Accountant Review",
            "Flag issues for accountant verification."
        ),
        (
            "06",
            "Record Storage",
            "Store processed accounting information in the database."
        )
    ]

    for number, title, description in steps:

        with st.container(border=True):

            col1, col2, col3 = st.columns(
                [1, 3, 6]
            )

            with col1:

                st.markdown(
                    f"**{number}**"
                )

            with col2:

                st.markdown(
                    f"**{title}**"
                )

            with col3:

                st.write(
                    description
                )

    st.divider()

    st.html(
        """
        <div class="section-heading">
            Technology Stack
        </div>
        """
    )

    tech_cols = st.columns(4)

    technologies = [
        ("🐍", "Python"),
        ("◈", "OpenAI"),
        ("▣", "SQLite"),
        ("◫", "Streamlit")
    ]

    for col, (icon, name) in zip(
        tech_cols,
        technologies
    ):

        with col:

            st.html(
                f"""
                <div class="tech-card">

                    <div class="tech-icon">
                        {icon}
                    </div>

                    <div class="tech-name">
                        {name}
                    </div>

                </div>
                """
            )


# =========================================================
# ANALYSIS
# =========================================================

elif page == "🔍 Analysis":

    if not can_upload():

        st.error(
            "You do not have permission to upload documents."
        )

        st.stop()

    st.html(
        """
        <div class="page-eyebrow">
            AI WORKSPACE
        </div>

        <div class="page-title">
            Invoice Analysis
        </div>

        <div class="page-description">
            Upload an invoice and let LedgerAgent extract,
            structure and validate its financial information.
        </div>
        """
    )

    st.divider()

    # -----------------------------------------------------
    # CLIENT ROUTING INFORMATION
    # -----------------------------------------------------

    if current_role == "client":

        if assigned_accountant:

            st.info(
                f"Your uploaded documents will automatically "
                f"be routed to **{assigned_accountant['username']}**."
            )

        else:

            st.warning(
                "You currently have no assigned accountant. "
                "Please contact the administrator."
            )

    elif current_role == "accountant":

        st.info(
            "Documents uploaded from this account will be "
            "associated with your accountant workspace."
        )

    # -----------------------------------------------------
    # FILE UPLOADER
    # -----------------------------------------------------

    uploaded_file = st.file_uploader(
        "Upload Invoice",
        type=[
            "pdf",
            "jpg",
            "jpeg",
            "png"
        ]
    )

    if uploaded_file is not None:

        st.success(
            f"✓ {uploaded_file.name} uploaded successfully."
        )

        if current_role == "client" and not assigned_accountant:

            st.error(
                "Cannot process the document because "
                "no accountant is assigned to your account."
            )

        else:

            if st.button(
                "Analyze Invoice  →",
                type="primary",
                use_container_width=True
            ):

                file_extension = os.path.splitext(
                    uploaded_file.name
                )[1].lower()

                temp_path = None

                try:

                    # =================================================
                    # SAVE TEMP FILE
                    # =================================================

                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=file_extension
                    ) as temp_file:

                        temp_file.write(
                            uploaded_file.getvalue()
                        )

                        temp_path = temp_file.name

                    # =================================================
                    # TEXT EXTRACTION
                    # =================================================

                    with st.spinner(
                        "Reading invoice..."
                    ):

                        if file_extension == ".pdf":

                            invoice_text = extract_text_from_pdf(
                                temp_path
                            )

                        else:

                            st.warning(
                                "Image invoice detected. "
                                "Image OCR/vision processing will be "
                                "connected in the next processing layer."
                            )

                            invoice_text = ""

                    if not invoice_text.strip():

                        if file_extension != ".pdf":

                            st.error(
                                "Image processing is not connected yet. "
                                "For the current MVP, please upload a "
                                "text-based PDF invoice."
                            )

                        else:

                            st.error(
                                "Could not extract text from this PDF."
                            )

                        st.stop()

                    # =================================================
                    # AI EXTRACTION
                    # =================================================

                    with st.spinner(
                        "AI is understanding the invoice..."
                    ):

                        invoice_data = extract_invoice_data(
                            invoice_text
                        )

                        if invoice_data is None:
                            st.error(
                                "AI extraction failed."
                            )
                            st.stop()

                        document_type = classify_document(
                            invoice_text
                        )

                        extracted_details = {}

                        if file_extension == ".pdf":
                            extracted_details = extract_invoice_details(
                                temp_path
                            ) or {}

                        invoice_data.update(extracted_details)

                    if invoice_data is None:

                        st.error(
                            "AI extraction failed."
                        )

                        st.stop()

                    # =================================================
                    # VALIDATION
                    # =================================================

                    with st.spinner(
                        "Validating financial information..."
                    ):

                        status, issues = validate_invoice(
                            invoice_data
                        )
                        # =================================================
                        # DUPLICATE DETECTION
                        # =================================================

                        conn = sqlite3.connect(DB_NAME)

                        duplicate_query = """
                        SELECT id, invoice_number, seller_name, total
                        FROM invoices
                        WHERE invoice_number = ?
                        AND seller_name = ?
                                                    """

                        duplicate_df = pd.read_sql_query(
                        duplicate_query,
                        conn,
                        params=[
                        invoice_data.get("invoice_number"),
                        invoice_data.get("seller_name")
                        ]
                        )

                        conn.close()

                        if not duplicate_df.empty:
                            status = "REVIEW REQUIRED"

                            issues.append(
                                f"Possible duplicate invoice detected: "
                                f"{invoice_data.get('invoice_number')}"
                            )

                            st.warning(
                                f"⚠️ Possible duplicate invoice detected: "
                                f"{invoice_data.get('invoice_number')}"
                            )
                    # =================================================
                    # DETERMINE CLIENT + ACCOUNTANT
                    # =================================================

                    client_id = None
                    accountant_id = None

                    # CLIENT UPLOAD
                    # The client ID always comes from the authenticated session.
                    # Never trust a client_id supplied by the UI.
                    if current_role == "client":

                        client_id = current_user_id

                        assigned_accountant = get_client_accountant(
                            current_user_id
                        )

                        if not assigned_accountant:
                            st.error(
                                "❌ No accountant is assigned to your account. "
                                "Please contact the administrator before uploading."
                            )
                            st.stop()

                        accountant_id = assigned_accountant["id"]

                    # ACCOUNTANT UPLOAD
                    elif current_role == "accountant":

                        accountant_id = current_user_id

                    # ADMIN UPLOAD
                    elif current_role == "admin":

                        client_id = None
                        accountant_id = None

                    else:

                        st.error("❌ Unauthorized user role.")
                        st.stop()

                    # =================================================
                    # SAVE INVOICE
                    # =================================================

                    invoice_id, document_id = save_invoice(
                        invoice_data,
                        status,
                        uploaded_by=current_username,
                        source_filename=uploaded_file.name,
                        client_id=client_id,
                        accountant_id=accountant_id,
                        document_type=document_type,
                    )

                    st.success(
                        "Invoice processed and saved successfully."
                    )

                    # =================================================
                    # ROUTING SUCCESS
                    # =================================================

                    if current_role == "client":

                        st.info(
                            f"Document routed to accountant: "
                            f"**{assigned_accountant['username']}**"
                        )

                    elif current_role == "accountant":

                        st.info(
                            "Document has been added to your "
                            "accounting workspace."
                        )

                    st.divider()

                    # =================================================
                    # STATUS
                    # =================================================

                    if status == "VALID":

                        st.success(
                            "✓ Invoice Status: VALID"
                        )

                    else:

                        st.warning(
                            "⚠ Invoice Status: REVIEW REQUIRED"
                        )

                    # =================================================
                    # INVOICE INFORMATION
                    # =================================================

                    st.html(
                        """
                        <div class="section-heading">
                            Invoice Information
                        </div>
                        """
                    )

                    st.info(
                        f"📄 Document Type: {document_type}"
                    )

                    info1, info2 = st.columns(2)

                    with info1:

                        st.write(
                            "**Invoice Number:**",
                            invoice_data.get(
                                "invoice_number"
                            )
                        )

                        st.write(
                            "**Invoice Date:**",
                            invoice_data.get(
                                "invoice_date"
                            )
                        )

                        st.write(
                            "**Seller:**",
                            invoice_data.get(
                                "seller_name"
                            )
                        )

                        st.write(
                            "**GSTIN:**",
                            invoice_data.get(
                                "seller_gstin"
                            )
                        )

                    with info2:

                        st.write(
                            "**Customer:**",
                            invoice_data.get(
                                "customer_name"
                            )
                        )

                        st.write(
                            "**Payment Status:**",
                            invoice_data.get(
                                "payment_status"
                            )
                        )

                        st.write(
                            "**Subtotal:**",
                            f"₹{invoice_data.get('subtotal', 0):,.2f}"
                        )

                        st.write(
                            "**Total:**",
                          f"₹{float(invoice_data.get('total', 0) or 0):,.2f}"
                        )

                    # =================================================
                    # LINE ITEMS
                    # =================================================

                    st.html(
                        """
                        <div class="section-heading">
                            Line Items
                        </div>
                        """
                    )

                    items = invoice_data.get(
                        "items",
                        []
                    )

                    rows = []

                    for item in items:

                        quantity = item.get(
                            "quantity",
                            0
                        )

                        unit_price = item.get(
                            "unit_price",
                            0
                        )

                        amount = item.get(
                            "amount",
                            quantity * unit_price
                        )

                        rows.append(
                            {
                                "Description":
                                    item.get(
                                        "description",
                                        item.get(
                                            "name",
                                            "Unknown"
                                        )
                                    ),

                                "Quantity":
                                    quantity,

                                "Unit Price":
                                    f"₹{unit_price:,.2f}",

                                "Amount":
                                    f"₹{amount:,.2f}"
                            }
                        )

                    if rows:

                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True
                        )

                    else:

                        st.info(
                            "No line items detected."
                        )

                    # =================================================
                    # FINANCIAL BREAKDOWN
                    # =================================================

                    st.html(
                        """
                        <div class="section-heading">
                            Financial Breakdown
                        </div>
                        """
                    )

                    tax1, tax2, tax3, tax4 = st.columns(4)

                    with tax1:

                        st.metric(
                            "Subtotal",
                            f"₹{invoice_data.get('subtotal', 0):,.2f}"
                        )

                    with tax2:

                        st.metric(
                            "CGST",
                            f"₹{invoice_data.get('cgst', 0):,.2f}"
                        )

                    with tax3:

                        st.metric(
                            "SGST",
                            f"₹{invoice_data.get('sgst', 0):,.2f}"
                        )

                    with tax4:

                        st.metric(
                            "Total",
                         f"₹{float(invoice_data.get('total', 0) or 0):,.2f}"                        )

                    # =================================================
                    # VALIDATION FINDINGS
                    # =================================================

                    if issues:

                        st.html(
                            """
                            <div class="section-heading">
                                Validation Findings
                            </div>
                            """
                        )

                        for issue in issues:

                            st.error(
                                issue
                            )

                        st.info(
                            "Accountant review is required before approval."
                        )

                    else:

                        st.success(
                            "No validation issues detected."
                        )

                    # =================================================
                    # ROUTING DETAILS
                    # =================================================

                    st.html(
                        """
                        <div class="section-heading">
                            Workflow Routing
                        </div>
                        """
                    )

                    route1, route2 = st.columns(2)

                    with route1:

                        st.write(
                            "**Uploaded By:**",
                            current_username
                        )

                    with route2:

                        if current_role == "client":

                            st.write(
                                "**Assigned Accountant:**",
                                assigned_accountant["username"]
                            )

                        elif current_role == "accountant":

                            st.write(
                                "**Accountant:**",
                                current_username
                            )

                        else:

                            st.write(
                                "**Accountant:**",
                                "Not assigned"
                            )

                    # =================================================
                    # AI DATA
                    # =================================================

                    with st.expander(
                        "View AI Extracted Data"
                    ):

                        st.json(
                            invoice_data
                        )

                finally:

                    if temp_path and os.path.exists(
                        temp_path
                    ):

                        os.remove(
                            temp_path
                        )


# =========================================================
# ACCOUNTANT REVIEW
# =========================================================

elif page == "📥 Accountant Review":

    if not can_review():

        st.error(
            "You do not have permission to review documents."
        )

        st.stop()

    st.html(
        """
        <div class="page-eyebrow">
            ACCOUNTANT WORKSPACE
        </div>

        <div class="page-title">
            Accountant Review Queue
        </div>

        <div class="page-description">
            Review invoices flagged by LedgerAgent,
            verify extracted information and make the
            final accounting workflow decision.
        </div>
        """
    )

    st.divider()

    review_df = get_review_queue()

    if review_df.empty:

        st.success(
            "✓ No documents currently require accountant review."
        )

        st.info(
            "When LedgerAgent detects an inconsistency, "
            "the document will appear here."
        )

    else:

        st.html(
            f"""
            <div class="section-heading">
                Documents Requiring Review
                <span style="
                    color:#69758a;
                    font-size:12px;
                    font-weight:500;
                    margin-left:8px;
                ">
                    {len(review_df)} pending
                </span>
            </div>
            """
        )

        for _, row in review_df.iterrows():

            document_id = int(
                row["document_id"]
            )

            invoice_number = row["invoice_number"]

            invoice_date = row["invoice_date"]

            customer_name = row["customer_name"]

            client_name = row["client_name"]

            total = row["total"]

            workflow_status = row["workflow_status"]

            with st.container(
                border=True
            ):

                col1, col2, col3, col4, col5, col6 = st.columns(
                    [2, 1.3, 2.2, 2, 1.6, 1.7]
                )

                with col1:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Invoice
                        </div>

                        <div class="invoice-value">
                            {invoice_number}
                        </div>
                        """
                    )

                with col2:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Date
                        </div>

                        <div class="invoice-value">
                            {invoice_date}
                        </div>
                        """
                    )

                with col3:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Client
                        </div>

                        <div class="invoice-value">
                            {client_name or "Direct Upload"}
                        </div>
                        """
                    )

                with col4:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Customer
                        </div>

                        <div class="invoice-value">
                            {customer_name}
                        </div>
                        """
                    )

                with col5:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Amount
                        </div>

                        <div class="invoice-value">
                            ₹{total:,.2f}
                        </div>
                        """
                    )

                with col6:

                    if workflow_status == "IN_REVIEW":

                        st.html(
                            """
                            <div class="status-review">
                                IN REVIEW
                            </div>
                            """
                        )

                    else:

                        st.html(
                            """
                            <div class="status-review">
                                REVIEW REQUIRED
                            </div>
                            """
                        )

                    st.write("")

                    if st.button(
                        "Review  →",
                        key=f"review_{document_id}",
                        use_container_width=True
                    ):

                        st.session_state.selected_review_document_id = (
                            document_id
                        )

                        st.rerun()

        # =================================================
        # SELECTED DOCUMENT
        # =================================================

        selected_document_id = (
            st.session_state.selected_review_document_id
        )

        if selected_document_id is not None:

            selected_row = review_df[
                review_df["document_id"]
                ==
                selected_document_id
            ]

            if selected_row.empty:

                st.warning(
                    "This document is no longer waiting for review."
                )

                st.session_state.selected_review_document_id = None

            else:

                row = selected_row.iloc[0]

                document_id = int(
                    row["document_id"]
                )

                invoice_id = int(
                    row["invoice_id"]
                )

                invoice = get_invoice_details(
                    invoice_id
                )

                document = get_document_details(
                    document_id
                )

                if invoice is None:

                    st.error(
                        "Invoice could not be found."
                    )

                elif document is None:

                    st.error(
                        "Document could not be found."
                    )

                else:

                    st.divider()

                    st.html(
                        """
                        <div class="analysis-panel">

                            <div class="analysis-title">
                                ◈ Accountant Workspace
                            </div>

                            <div class="analysis-subtitle">
                                Verify LedgerAgent's extracted data
                                and validation findings before making
                                the final workflow decision.
                            </div>

                        </div>
                        """
                    )

                    # -------------------------------------------------
                    # DOCUMENT STATUS
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Document Status
                        </div>
                        """
                    )

                    status_col1, status_col2, status_col3 = st.columns(3)

                    with status_col1:

                        st.write(
                            "**Workflow Status:**"
                        )

                        if document["workflow_status"] == "IN_REVIEW":

                            st.html(
                                """
                                <div class="status-review">
                                    IN REVIEW
                                </div>
                                """
                            )

                        else:

                            st.html(
                                """
                                <div class="status-review">
                                    ⚠ REVIEW REQUIRED
                                </div>
                                """
                            )

                    with status_col2:

                        st.write(
                            "**Validation Status:**"
                        )

                        st.write(
                            invoice.get(
                                "validation_status"
                            )
                        )

                    with status_col3:

                        st.write(
                            "**Client:**"
                        )

                        st.write(
                            document.get(
                                "client_name"
                            ) or "Direct Accountant Upload"
                        )

                    # -------------------------------------------------
                    # ACCOUNTANT ROUTING
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Workflow Assignment
                        </div>
                        """
                    )

                    routing1, routing2 = st.columns(2)

                    with routing1:

                        st.write(
                            "**Assigned Accountant:**",
                            document.get(
                                "accountant_name"
                            ) or "Unassigned"
                        )

                    with routing2:

                        st.write(
                            "**Uploaded By:**",
                            document.get(
                                "uploaded_by"
                            )
                        )

                    # -------------------------------------------------
                    # AI SUMMARY
                    # -------------------------------------------------

                    invoice_for_validation = (
                        prepare_invoice_for_validation(
                            invoice
                        )
                    )

                    status, issues = validate_invoice(
                        invoice_for_validation
                    )

                    st.html(
                        """
                        <div class="section-heading">
                            AI Review Summary
                        </div>
                        """
                    )

                    summary = generate_invoice_summary(
                        invoice_for_validation,
                        issues
                    )

                    if issues:

                        st.warning(
                            summary
                        )

                    else:

                        st.success(
                            summary
                        )


                    # =================================================
                    # DOCUMENT TYPE
                    # =================================================

                    st.info(
                        f"📄 Document Type: {document.get('document_type', 'Unknown')}"
                    )

                    # -------------------------------------------------
                    # INVOICE INFORMATION
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Invoice Information
                        </div>
                        """
                    )

                    info1, info2 = st.columns(2)

                    with info1:

                        st.write(
                            "**Invoice Number:**",
                            invoice.get(
                                "invoice_number"
                            )
                        )

                        st.write(
                            "**Invoice Date:**",
                            invoice.get(
                                "invoice_date"
                            )
                        )

                        st.write(
                            "**Seller:**",
                            invoice.get(
                                "seller_name"
                            )
                        )

                        st.write(
                            "**Seller GSTIN:**",
                            invoice.get(
                                "seller_gstin"
                            )
                        )

                    with info2:

                        st.write(
                            "**Customer:**",
                            invoice.get(
                                "customer_name"
                            )
                        )

                        st.write(
                            "**Payment Status:**",
                            invoice.get(
                                "payment_status"
                            )
                        )

                        st.write(
                            "**Subtotal:**",
                            f"₹{invoice.get('subtotal', 0):,.2f}"
                        )

                        st.write(
                            "**Total:**",
                            f"₹{invoice.get('total', 0):,.2f}"
                        )

                    # -------------------------------------------------
                    # LINE ITEMS
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Line Items
                        </div>
                        """
                    )

                    items = invoice_for_validation.get(
                        "items",
                        []
                    )

                    rows = []

                    for item in items:

                        quantity = item.get(
                            "quantity",
                            0
                        )

                        unit_price = item.get(
                            "unit_price",
                            0
                        )

                        amount = item.get(
                            "amount",
                            quantity * unit_price
                        )

                        calculated_amount = (
                            quantity * unit_price
                        )

                        rows.append(
                            {
                                "Description":
                                    item.get(
                                        "description",
                                        item.get(
                                            "name",
                                            "Unknown"
                                        )
                                    ),

                                "Quantity":
                                    quantity,

                                "Unit Price":
                                    f"₹{unit_price:,.2f}",

                                "Invoice Amount":
                                    f"₹{amount:,.2f}",

                                "Calculated":
                                    f"₹{calculated_amount:,.2f}"
                            }
                        )

                    if rows:

                        st.dataframe(
                            pd.DataFrame(rows),
                            use_container_width=True,
                            hide_index=True
                        )

                    else:

                        st.info(
                            "No line items available."
                        )

                    # -------------------------------------------------
                    # FINANCIAL BREAKDOWN
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Financial Breakdown
                        </div>
                        """
                    )

                    financial1, financial2, financial3, financial4 = (
                        st.columns(4)
                    )

                    with financial1:

                        st.metric(
                            "Subtotal",
                            f"₹{invoice.get('subtotal', 0):,.2f}"
                        )

                    with financial2:

                        st.metric(
                            "CGST",
                            f"₹{invoice.get('cgst', 0):,.2f}"
                        )

                    with financial3:

                        st.metric(
                            "SGST",
                            f"₹{invoice.get('sgst', 0):,.2f}"
                        )

                    with financial4:

                        st.metric(
                            "Total",
                            f"₹{invoice.get('total', 0):,.2f}"
                        )

                    # -------------------------------------------------
                    # VALIDATION FINDINGS
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Validation Findings
                        </div>
                        """
                    )

                    if issues:

                        for issue in issues:

                            st.error(
                                issue
                            )

                    else:

                        st.success(
                            "✓ No validation issues detected."
                        )

                    # -------------------------------------------------
                    # START REVIEW
                    # -------------------------------------------------

                    if document["workflow_status"] == "REVIEW_REQUIRED":

                        if st.button(
                            "🔎 Start Accountant Review",
                            type="primary",
                            use_container_width=True,
                            key=f"start_review_{document_id}"
                        ):

                            success = start_document_review(
                                document_id=document_id,
                                user_id=current_user_id
                            )

                            if success:

                                st.success(
                                    "Accountant review started."
                                )

                                st.rerun()

                            else:

                                st.error(
                                    "Could not start review."
                                )

                    # -------------------------------------------------
                    # ACCOUNTANT DECISION
                    # -------------------------------------------------

                    st.html(
                        """
                        <div class="section-heading">
                            Accountant Decision
                        </div>
                        """
                    )

                    if has_permission(
                        current_role,
                        "approve_document"
                    ) or has_permission(
                        current_role,
                        "reject_document"
                    ):

                        accountant_comment = st.text_area(
                            "Accountant Comment",
                            placeholder=(
                                "Enter your review comment, "
                                "reason for approval or rejection..."
                            ),
                            key=f"comment_{document_id}"
                        )

                        approve_col, reject_col = st.columns(2)

                        with approve_col:

                            if has_permission(
                                current_role,
                                "approve_document"
                            ):

                                if st.button(
                                    "✅ Approve Document",
                                    type="primary",
                                    use_container_width=True,
                                    key=f"approve_{document_id}"
                                ):

                                    success = approve_document(
                                        document_id=document_id,
                                        user_id=current_user_id,
                                        comment=accountant_comment
                                    )

                                    if success:

                                        st.session_state.selected_review_document_id = None

                                        st.success(
                                            "Document approved successfully."
                                        )

                                        st.rerun()

                                    else:

                                        st.error(
                                            "Could not approve this document."
                                        )

                        with reject_col:

                            if has_permission(
                                current_role,
                                "reject_document"
                            ):

                                if st.button(
                                    "❌ Reject Document",
                                    use_container_width=True,
                                    key=f"reject_{document_id}"
                                ):

                                    if not accountant_comment.strip():

                                        st.warning(
                                            "Please enter a reason before rejecting the document."
                                        )

                                    else:

                                        success = reject_document(
                                            document_id=document_id,
                                            user_id=current_user_id,
                                            comment=accountant_comment
                                        )

                                        if success:

                                            st.session_state.selected_review_document_id = None

                                            st.success(
                                                "Document rejected."
                                            )

                                            st.rerun()

                                        else:

                                            st.error(
                                                "Could not reject this document."
                                            )

                    # -------------------------------------------------
                    # AUDIT TRAIL
                    # -------------------------------------------------

                    st.divider()

                    st.html(
                        """
                        <div class="section-heading">
                            Audit Trail
                        </div>
                        """
                    )

                    audit_logs = get_audit_logs(
                        document_id
                    )

                    if audit_logs:

                        for (
                            action,
                            details,
                            created_at,
                            username,
                            role
                        ) in audit_logs:

                            st.html(
                                f"""
                                <div class="audit-card">

                                    <div class="audit-action">
                                        {action}
                                    </div>

                                    <div class="audit-meta">
                                        {username or "System"}
                                        ·
                                        {role or "system"}
                                        ·
                                        {created_at}
                                    </div>

                                    <div class="audit-details">
                                        {details or ""}
                                    </div>

                                </div>
                                """
                            )

                    else:

                        st.info(
                            "No audit events recorded yet."
                        )

                    # -------------------------------------------------
                    # APPROVAL HISTORY
                    # -------------------------------------------------

                    approval_history = get_approval_history(
                        document_id
                    )

                    if approval_history:

                        st.html(
                            """
                            <div class="section-heading">
                                Approval History
                            </div>
                            """
                        )

                        for (
                            action,
                            comment,
                            created_at,
                            username,
                            role
                        ) in approval_history:

                            st.html(
                                f"""
                                <div class="audit-card">

                                    <div class="audit-action">
                                        {action}
                                    </div>

                                    <div class="audit-meta">
                                        {username or "Unknown"}
                                        ·
                                        {role or "Unknown"}
                                        ·
                                        {created_at}
                                    </div>

                                    <div class="audit-details">
                                        {comment or "No comment provided."}
                                    </div>

                                </div>
                                """
                            )

                    # -------------------------------------------------
                    # EXTRACTED DATA
                    # -------------------------------------------------

                    with st.expander(
                        "View Extracted Structured Data"
                    ):

                        st.json(
                            invoice_for_validation
                        )


# =========================================================
# HISTORY
# =========================================================

elif page == "🕘 History":

    if not can_view_documents():

        st.error(
            "You do not have permission to view invoice history."
        )

        st.stop()

    st.html(
        """
        <div class="page-eyebrow">
            RECORDS
        </div>

        <div class="page-title">
            Invoice History
        </div>

        <div class="page-description">
            Review previously processed invoices and open
            AI-assisted analysis for any individual record.
        </div>
        """
    )

    st.divider()

    df = get_invoices()

    if df.empty:

        st.info(
            "No invoice records available."
        )

    else:

        st.html(
            f"""
            <div class="section-heading">
                Processed Invoices
                <span style="
                    color:#69758a;
                    font-size:12px;
                    font-weight:500;
                    margin-left:8px;
                ">
                    {len(df)} records
                </span>
            </div>
            """
        )

        for _, row in df.iterrows():

            invoice_id = int(
                row["id"]
            )

            invoice_number = row["invoice_number"]

            invoice_date = row["invoice_date"]

            customer_name = row["customer_name"]

            client_name = row["client_name"]

            total = row["total"]

            workflow_status = row["workflow_status"]

            with st.container(
                border=True
            ):

                col1, col2, col3, col4, col5, col6 = st.columns(
                    [2, 1.3, 2, 2, 1.6, 1.8]
                )

                with col1:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Invoice
                        </div>

                        <div class="invoice-value">
                            {invoice_number}
                        </div>
                        """
                    )

                with col2:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Date
                        </div>

                        <div class="invoice-value">
                            {invoice_date}
                        </div>
                        """
                    )

                with col3:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Client
                        </div>

                        <div class="invoice-value">
                            {client_name or "Direct Upload"}
                        </div>
                        """
                    )

                with col4:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Customer
                        </div>

                        <div class="invoice-value">
                            {customer_name}
                        </div>
                        """
                    )

                with col5:

                    st.html(
                        f"""
                        <div class="invoice-label">
                            Total
                        </div>

                        <div class="invoice-value">
                            ₹{total:,.2f}
                        </div>
                        """
                    )

                with col6:

                    if workflow_status == "APPROVED":

                        st.html(
                            """
                            <div class="status-approved">
                                ✓ APPROVED
                            </div>
                            """
                        )

                    elif workflow_status == "REJECTED":

                        st.html(
                            """
                            <div class="status-rejected">
                                ✕ REJECTED
                            </div>
                            """
                        )

                    elif workflow_status == "REVIEW_REQUIRED":

                        st.html(
                            """
                            <div class="status-review">
                                ⚠ REVIEW
                            </div>
                            """
                        )

                    elif workflow_status == "IN_REVIEW":

                        st.html(
                            """
                            <div class="status-review">
                                IN REVIEW
                            </div>
                            """
                        )

                    else:

                        st.html(
                            f"""
                            <div class="status-valid">
                                {workflow_status}
                            </div>
                            """
                        )

                    st.write("")

                    if st.button(
                        "AI Invoice  →",
                        key=f"history_ai_{invoice_id}",
                        use_container_width=True
                    ):

                        st.session_state.selected_invoice_id = (
                            invoice_id
                        )

                        st.rerun()

        # =================================================
        # SELECTED HISTORY RECORD
        # =================================================

        selected_invoice_id = (
            st.session_state.selected_invoice_id
        )

        if selected_invoice_id is not None:

            invoice = get_invoice_details(
                selected_invoice_id
            )

            if invoice is None:

                st.error(
                    "Invoice record could not be found."
                )

            else:

                st.divider()

                st.html(
                    """
                    <div class="analysis-panel">

                        <div class="analysis-title">
                            ◈ AI Invoice Analysis
                        </div>

                        <div class="analysis-subtitle">
                            AI-assisted review of the selected
                            invoice with deterministic accounting
                            validation checks.
                        </div>

                    </div>
                    """
                )

                if st.button(
                    "Close Analysis"
                ):

                    st.session_state.selected_invoice_id = None

                    st.rerun()

                invoice_for_validation = (
                    prepare_invoice_for_validation(
                        invoice
                    )
                )

                status, issues = validate_invoice(
                    invoice_for_validation
                )

                # -------------------------------------------------
                # SUMMARY
                # -------------------------------------------------

                st.html(
                    """
                    <div class="section-heading">
                        Analysis Summary
                    </div>
                    """
                )

                summary = generate_invoice_summary(
                    invoice_for_validation,
                    issues
                )

                actual_workflow = invoice.get(
                    "workflow_status"
                )

                if actual_workflow == "APPROVED":

                    st.success(
                        f"✓ APPROVED\n\n{summary}"
                    )

                elif actual_workflow == "REJECTED":

                    st.error(
                        f"✕ REJECTED\n\n{summary}"
                    )

                elif actual_workflow == "IN_REVIEW":

                    st.warning(
                        f"◉ IN REVIEW\n\n{summary}"
                    )

                elif status == "VALID":

                    st.success(
                        f"✓ VALID\n\n{summary}"
                    )

                else:

                    st.warning(
                        f"⚠ REVIEW REQUIRED\n\n{summary}"
                    )

                # -------------------------------------------------
                # INFORMATION
                # -------------------------------------------------

                st.html(
                    """
                    <div class="section-heading">
                        Invoice Information
                    </div>
                    """
                )

                info1, info2 = st.columns(2)

                with info1:

                    st.write(
                        "**Invoice Number:**",
                        invoice.get(
                            "invoice_number"
                        )
                    )

                    st.write(
                        "**Invoice Date:**",
                        invoice.get(
                            "invoice_date"
                        )
                    )

                    st.write(
                        "**Seller:**",
                        invoice.get(
                            "seller_name"
                        )
                    )

                    st.write(
                        "**Seller GSTIN:**",
                        invoice.get(
                            "seller_gstin"
                        )
                    )

                with info2:

                    st.write(
                        "**Customer:**",
                        invoice.get(
                            "customer_name"
                        )
                    )

                    st.write(
                        "**Payment Status:**",
                        invoice.get(
                            "payment_status"
                        )
                    )

                    st.write(
                        "**Validation Status:**",
                        invoice.get(
                            "validation_status"
                        )
                    )

                    st.write(
                        "**Workflow Status:**",
                        invoice.get(
                            "workflow_status"
                        )
                    )

                    st.write(
                        "**Client:**",
                        invoice.get(
                            "client_name"
                        ) or "Direct Upload"
                    )

                    st.write(
                        "**Accountant:**",
                        invoice.get(
                            "accountant_name"
                        ) or "Unassigned"
                    )

                # -------------------------------------------------
                # LINE ITEMS
                # -------------------------------------------------

                st.html(
                    """
                    <div class="section-heading">
                        Line Items
                    </div>
                    """
                )

                items = invoice_for_validation.get(
                    "items",
                    []
                )

                rows = []

                for item in items:

                    quantity = item.get(
                        "quantity",
                        0
                    )

                    unit_price = item.get(
                        "unit_price",
                        0
                    )

                    amount = item.get(
                        "amount",
                        quantity * unit_price
                    )

                    calculated_amount = (
                        quantity * unit_price
                    )

                    rows.append(
                        {
                            "Description":
                                item.get(
                                    "description",
                                    item.get(
                                        "name",
                                        "Unknown"
                                    )
                                ),

                            "Quantity":
                                quantity,

                            "Unit Price":
                                f"₹{unit_price:,.2f}",

                            "Invoice Amount":
                                f"₹{amount:,.2f}",

                            "Calculated":
                                f"₹{calculated_amount:,.2f}"
                        }
                    )

                if rows:

                    st.dataframe(
                        pd.DataFrame(rows),
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "No line items available."
                    )

                # -------------------------------------------------
                # FINANCIAL
                # -------------------------------------------------

                st.html(
                    """
                    <div class="section-heading">
                        Financial Breakdown
                    </div>
                    """
                )

                financial1, financial2, financial3, financial4 = (
                    st.columns(4)
                )

                with financial1:

                    st.metric(
                        "Subtotal",
                        f"₹{invoice.get('subtotal', 0):,.2f}"
                    )

                with financial2:

                    st.metric(
                        "CGST",
                        f"₹{invoice.get('cgst', 0):,.2f}"
                    )

                with financial3:

                    st.metric(
                        "SGST",
                        f"₹{invoice.get('sgst', 0):,.2f}"
                    )

                with financial4:

                    st.metric(
                        "Total",
                        f"₹{invoice.get('total', 0):,.2f}"
                    )

                # -------------------------------------------------
                # VALIDATION
                # -------------------------------------------------

                if issues:

                    st.html(
                        """
                        <div class="section-heading">
                            Validation Findings
                        </div>
                        """
                    )

                    for issue in issues:

                        st.error(
                            issue
                        )

                else:

                    st.success(
                        "✓ No calculation inconsistencies detected."
                    )

                # -------------------------------------------------
                # AUDIT TRAIL
                # -------------------------------------------------

                conn = sqlite3.connect(
                    DB_NAME
                )

                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT id
                    FROM documents
                    WHERE invoice_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (selected_invoice_id,)
                )

                document_row = cursor.fetchone()

                conn.close()

                if document_row:

                    history_document_id = document_row[0]

                    st.divider()

                    st.html(
                        """
                        <div class="section-heading">
                            Audit Trail
                        </div>
                        """
                    )

                    audit_logs = get_audit_logs(
                        history_document_id
                    )

                    if audit_logs:

                        for (
                            action,
                            details,
                            created_at,
                            username,
                            role
                        ) in audit_logs:

                            st.html(
                                f"""
                                <div class="audit-card">

                                    <div class="audit-action">
                                        {action}
                                    </div>

                                    <div class="audit-meta">
                                        {username or "System"}
                                        ·
                                        {role or "system"}
                                        ·
                                        {created_at}
                                    </div>

                                    <div class="audit-details">
                                        {details or ""}
                                    </div>

                                </div>
                                """
                            )

                    else:

                        st.info(
                            "No audit events recorded."
                        )

                with st.expander(
                    "View Stored Structured Data"
                ):

                    st.json(
                        invoice_for_validation
                    )


# =========================================================
# DASHBOARD
# =========================================================

elif page == "📊 Dashboard":

    if current_role not in ["admin", "accountant"]:

        st.error(
            "You do not have permission to view the dashboard."
        )

        st.stop()

    st.html(
        """
        <div class="page-eyebrow">
            ANALYTICS
        </div>

        <div class="page-title">
            Accounting Dashboard
        </div>

        <div class="page-description">
            A high-level view of processed invoices,
            validation status and accounting workflow activity.
        </div>
        """
    )

    st.divider()

    df = get_invoices()

    if df.empty:

        st.info(
            "No invoice records available for dashboard."
        )

    else:

        total_invoices = len(
            df
        )

        valid_invoices = len(
            df[
                df["validation_status"] == "VALID"
            ]
        )

        review_invoices = len(
            df[
                df["workflow_status"] == "REVIEW_REQUIRED"
            ]
        )

        approved_invoices = len(
            df[
                df["workflow_status"] == "APPROVED"
            ]
        )

        rejected_invoices = len(
            df[
                df["workflow_status"] == "REJECTED"
            ]
        )

        in_review_invoices = len(
            df[
                df["workflow_status"] == "IN_REVIEW"
            ]
        )

        total_amount = (
            df["total"]
            .fillna(0)
            .sum()
        )

        metric1, metric2, metric3, metric4 = st.columns(4)

        with metric1:

            st.html(
                f"""
                <div class="kpi-card">

                    <div class="kpi-top">
                        <span class="kpi-icon">▣</span>
                        Total Invoices
                    </div>

                    <div class="kpi-value">
                        {total_invoices}
                    </div>

                </div>
                """
            )

        with metric2:

            st.html(
                f"""
                <div class="kpi-card">

                    <div class="kpi-top">
                        <span class="kpi-icon">✓</span>
                        Valid
                    </div>

                    <div class="kpi-value">
                        {valid_invoices}
                    </div>

                </div>
                """
            )

        with metric3:

            st.html(
                f"""
                <div class="kpi-card">

                    <div class="kpi-top">
                        <span class="kpi-icon">!</span>
                        Review Required
                    </div>

                    <div class="kpi-value">
                        {review_invoices}
                    </div>

                </div>
                """
            )

        with metric4:

            st.html(
                f"""
                <div class="kpi-card">

                    <div class="kpi-top">
                        <span class="kpi-icon">₹</span>
                        Total Amount
                    </div>

                    <div class="kpi-value">
                        ₹{total_amount:,.0f}
                    </div>

                </div>
                """
            )

        st.write("")
        st.write("")

        workflow1, workflow2, workflow3 = st.columns(3)

        with workflow1:

            st.metric(
                "Approved Documents",
                approved_invoices
            )

        with workflow2:

            st.metric(
                "Rejected Documents",
                rejected_invoices
            )

        with workflow3:

            st.metric(
                "In Review",
                in_review_invoices
            )

        st.write("")

        # -----------------------------------------------------
        # ACCOUNTANT CLIENT SUMMARY
        # -----------------------------------------------------

        if current_role == "accountant":

            st.html(
                """
                <div class="section-heading">
                    Assigned Clients
                </div>
                """
            )

            try:

                clients = get_accountant_clients(
                    current_user_id
                )

                if clients:

                    client_rows = []

                    for client in clients:

                        client_rows.append(
                            {
                                "Client":
                                    client["username"],

                                "Client ID":
                                    client["id"]
                            }
                        )

                    st.dataframe(
                        pd.DataFrame(client_rows),
                        use_container_width=True,
                        hide_index=True
                    )

                else:

                    st.info(
                        "No clients are currently assigned."
                    )

            except Exception:

                st.info(
                    "Client assignment information unavailable."
                )

        st.html(
            """
            <div class="section-heading">
                Workflow Overview
            </div>
            """
        )

        workflow_chart = pd.DataFrame(
            {
                "Status": [
                    "Valid",
                    "Review Required",
                    "In Review",
                    "Approved",
                    "Rejected"
                ],

                "Invoices": [
                    valid_invoices,
                    review_invoices,
                    in_review_invoices,
                    approved_invoices,
                    rejected_invoices
                ]
            }
        )

        st.bar_chart(
            workflow_chart.set_index(
                "Status"
            )
        )

        st.divider()

        st.html(
            """
            <div class="section-heading">
                Recent Invoice Records
            </div>
            """
        )

        recent_columns = [
            "invoice_number",
            "invoice_date",
            "client_name",
            "seller_name",
            "customer_name",
            "total",
            "payment_status",
            "validation_status",
            "workflow_status"
        ]

        recent_columns = [
            column
            for column in recent_columns
            if column in df.columns
        ]

        recent_df = df[
            recent_columns
        ].head(10)

        st.dataframe(
            recent_df,
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        st.html(
            """
            <div class="section-heading">
                Workflow Insight
            </div>
            """
        )

        review_percentage = (
            review_invoices
            /
            total_invoices
        ) * 100

        if review_percentage > 50:

            st.warning(
                f"""
                {review_percentage:.1f}% of processed invoices
                currently require accountant review. Human
                verification should therefore remain an important
                part of the accounting workflow.
                """
            )

        else:

            st.info(
                f"""
                {review_percentage:.1f}% of processed invoices
                currently require review. LedgerAgent helps
                accounting teams focus their attention on
                flagged records instead of manually checking
                every invoice.
                """
            )
