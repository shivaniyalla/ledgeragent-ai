import sqlite3
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_NAME = "ledgeragent.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# CURRENT TIMESTAMP
# =========================================================

def current_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# =========================================================
# ADD COLUMN IF MISSING
# =========================================================

def add_column_if_missing(
    cursor,
    table_name,
    column_name,
    column_definition
):
    cursor.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = [
        row[1]
        for row in cursor.fetchall()
    ]

    if column_name not in columns:
        cursor.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_name}
            {column_definition}
            """
        )


# =========================================================
# CREATE / UPGRADE DATABASE
# =========================================================

def create_database():

    conn = get_db_connection()
    cursor = conn.cursor()

    # =====================================================
    # INVOICES TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            invoice_number TEXT,

            invoice_date TEXT,

            seller_name TEXT,

            seller_gstin TEXT,

            customer_name TEXT,

            items TEXT,

            subtotal REAL,

            cgst REAL,

            sgst REAL,

            total REAL,

            payment_status TEXT,

            validation_status TEXT
        )
    """)

    # -----------------------------------------------------
    # PHASE 2 COLUMNS
    # -----------------------------------------------------

    add_column_if_missing(
        cursor,
        "invoices",
        "document_type",
        "TEXT DEFAULT 'INVOICE'"
    )

    add_column_if_missing(
        cursor,
        "invoices",
        "workflow_status",
        "TEXT DEFAULT 'REVIEW_REQUIRED'"
    )

    add_column_if_missing(
        cursor,
        "invoices",
        "uploaded_by",
        "TEXT DEFAULT 'admin'"
    )

    add_column_if_missing(
        cursor,
        "invoices",
        "created_at",
        "TEXT"
    )

    add_column_if_missing(
        cursor,
        "invoices",
        "updated_at",
        "TEXT"
    )

    # -----------------------------------------------------
    # CLIENT / ACCOUNTANT COLUMNS
    # -----------------------------------------------------

    add_column_if_missing(
        cursor,
        "invoices",
        "client_id",
        "INTEGER"
    )

    add_column_if_missing(
        cursor,
        "invoices",
        "accountant_id",
        "INTEGER"
    )

    # =====================================================
    # USERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password_hash TEXT NOT NULL,

            role TEXT NOT NULL,

            created_at TEXT
        )
    """)

    # =====================================================
    # ACCOUNTANT - CLIENT RELATIONSHIP
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accountant_clients (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            accountant_id INTEGER NOT NULL,

            client_id INTEGER NOT NULL,

            created_at TEXT,

            UNIQUE(accountant_id, client_id),

            FOREIGN KEY(accountant_id)
                REFERENCES users(id),

            FOREIGN KEY(client_id)
                REFERENCES users(id)
        )
    """)

    # =====================================================
    # DOCUMENTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            invoice_id INTEGER,

            source_filename TEXT,

            document_type TEXT,

            workflow_status TEXT,

            validation_status TEXT,

            uploaded_by TEXT,

            client_id INTEGER,

            accountant_id INTEGER,

            created_at TEXT,

            updated_at TEXT,

            FOREIGN KEY(invoice_id)
                REFERENCES invoices(id),

            FOREIGN KEY(client_id)
                REFERENCES users(id),

            FOREIGN KEY(accountant_id)
                REFERENCES users(id)
        )
    """)

    # -----------------------------------------------------
    # OLD DATABASE UPGRADE
    # -----------------------------------------------------

    add_column_if_missing(
        cursor,
        "documents",
        "client_id",
        "INTEGER"
    )

    add_column_if_missing(
        cursor,
        "documents",
        "accountant_id",
        "INTEGER"
    )

    # =====================================================
    # APPROVALS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS approvals (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id INTEGER,

            action TEXT,

            user_id INTEGER,

            comment TEXT,

            created_at TEXT,

            FOREIGN KEY(document_id)
                REFERENCES documents(id),

            FOREIGN KEY(user_id)
                REFERENCES users(id)
        )
    """)

    # =====================================================
    # AUDIT LOGS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            document_id INTEGER,

            user_id INTEGER,

            action TEXT,

            details TEXT,

            created_at TEXT,

            FOREIGN KEY(document_id)
                REFERENCES documents(id),

            FOREIGN KEY(user_id)
                REFERENCES users(id)
        )
    """)

    # =====================================================
    # CREATE ADMIN USER
    # =====================================================

    admin_username = os.getenv(
        "LEDGER_USERNAME",
        "admin"
    )

    admin_password = os.getenv(
        "LEDGER_PASSWORD",
        "ledger123"
    )

    import hashlib

    password_hash = hashlib.sha256(
        admin_password.encode()
    ).hexdigest()

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (
            username,
            password_hash,
            role,
            created_at
        )

        VALUES (?, ?, ?, ?)
    """, (
        admin_username,
        password_hash,
        "admin",
        current_timestamp()
    ))

    # =====================================================
    # UPGRADE OLD INVOICE RECORDS
    # =====================================================

    cursor.execute("""
        UPDATE invoices

        SET

            document_type =
                COALESCE(
                    document_type,
                    'INVOICE'
                ),

            workflow_status =
                CASE

                    WHEN workflow_status IN (
                        'APPROVED',
                        'REJECTED'
                    )
                        THEN workflow_status

                    WHEN validation_status = 'VALID'
                        THEN 'VALIDATED'

                    ELSE
                        'REVIEW_REQUIRED'

                END,

            uploaded_by =
                COALESCE(
                    uploaded_by,
                    'admin'
                ),

            created_at =
                COALESCE(
                    created_at,
                    ?
                ),

            updated_at =
                COALESCE(
                    updated_at,
                    ?
                )
    """, (
        current_timestamp(),
        current_timestamp()
    ))

    conn.commit()
    conn.close()

    print(
        "✅ LedgerAgent database upgraded successfully!"
    )


# =========================================================
# CHECK USER
# =========================================================

def get_user_by_id(user_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            username,
            role,
            created_at

        FROM users

        WHERE id = ?
    """, (
        user_id,
    ))

    user = cursor.fetchone()

    conn.close()

    return user


# =========================================================
# CHECK USER ROLE
# =========================================================

def get_user_role(user_id):

    user = get_user_by_id(user_id)

    if not user:
        return None

    return user["role"]


# =========================================================
# SAVE INVOICE / DOCUMENT
# =========================================================

def save_invoice(
    invoice,
    validation_status,
    uploaded_by="admin",
    source_filename=None,
    client_id=None,
    accountant_id=None,
    document_type="INVOICE"
):

    conn = get_db_connection()
    cursor = conn.cursor()

    now = current_timestamp()

    # -----------------------------------------------------
    # SAFETY
    # -----------------------------------------------------

    if not document_type:
        document_type = "INVOICE"

    # =====================================================
    # ACCESS VALIDATION
    # =====================================================

    # If a client is specified, make sure that client exists.
    if client_id is not None:

        cursor.execute("""
            SELECT id, role
            FROM users
            WHERE id = ?
        """, (
            client_id,
        ))

        client = cursor.fetchone()

        if not client:
            conn.close()
            raise ValueError(
                "Invalid client ID."
            )

        if client["role"] != "client":
            conn.close()
            raise ValueError(
                "Selected user is not a client."
            )

    # -----------------------------------------------------
    # VERIFY ACCOUNTANT - CLIENT RELATIONSHIP
    # -----------------------------------------------------

    if client_id is not None and accountant_id is not None:

        cursor.execute("""
            SELECT id

            FROM accountant_clients

            WHERE accountant_id = ?

            AND client_id = ?
        """, (
            accountant_id,
            client_id
        ))

        relationship = cursor.fetchone()

        if not relationship:
            conn.close()
            raise PermissionError(
                "This client is not assigned to this accountant."
            )

    # =====================================================
    # INITIAL WORKFLOW STATUS
    # =====================================================

    if validation_status == "VALID":
        workflow_status = "VALIDATED"
    else:
        workflow_status = "REVIEW_REQUIRED"

    # =====================================================
    # SAVE INVOICE
    # =====================================================

    cursor.execute("""
        INSERT INTO invoices (

            invoice_number,

            invoice_date,

            seller_name,

            seller_gstin,

            customer_name,

            items,

            subtotal,

            cgst,

            sgst,

            total,

            payment_status,

            validation_status,

            document_type,

            workflow_status,

            uploaded_by,

            client_id,

            accountant_id,

            created_at,

            updated_at

        )

        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """, (

        invoice.get("invoice_number"),

        invoice.get("invoice_date"),

        invoice.get("seller_name"),

        invoice.get("seller_gstin"),

        invoice.get("customer_name"),

        json.dumps(
            invoice.get("items", [])
        ),

        invoice.get("subtotal"),

        invoice.get("cgst"),

        invoice.get("sgst"),

        invoice.get("total"),

        invoice.get("payment_status"),

        validation_status,

        document_type,

        workflow_status,

        uploaded_by,

        client_id,

        accountant_id,

        now,

        now
    ))

    invoice_id = cursor.lastrowid

    # =====================================================
    # SAVE DOCUMENT
    # =====================================================

    cursor.execute("""
        INSERT INTO documents (

            invoice_id,

            source_filename,

            document_type,

            workflow_status,

            validation_status,

            uploaded_by,

            client_id,

            accountant_id,

            created_at,

            updated_at

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (

        invoice_id,

        source_filename,

        document_type,

        workflow_status,

        validation_status,

        uploaded_by,

        client_id,

        accountant_id,

        now,

        now
    ))

    document_id = cursor.lastrowid

    # =====================================================
    # FIND UPLOADING USER
    # =====================================================

    cursor.execute("""
        SELECT id

        FROM users

        WHERE username = ?
    """, (
        uploaded_by,
    ))

    user = cursor.fetchone()

    if user:
        user_id = user["id"]
    else:
        user_id = None

    # =====================================================
    # AUDIT LOG
    # =====================================================

    cursor.execute("""
        INSERT INTO audit_logs (

            document_id,

            user_id,

            action,

            details,

            created_at

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        document_id,

        user_id,

        "DOCUMENT_PROCESSED",

        f"{document_type} processed with validation status: {validation_status}",

        now
    ))

    conn.commit()
    conn.close()

    return invoice_id, document_id


# =========================================================
# GET DOCUMENT DETAILS
# =========================================================

def get_document_details(document_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            d.*,

            u.username AS client_username,

            a.username AS accountant_username

        FROM documents d

        LEFT JOIN users u
            ON d.client_id = u.id

        LEFT JOIN users a
            ON d.accountant_id = a.id

        WHERE d.id = ?
    """, (
        document_id,
    ))

    document = cursor.fetchone()

    conn.close()

    return document


# =========================================================
# CHECK ACCOUNTANT ACCESS TO DOCUMENT
# =========================================================

def accountant_can_access_document(
    accountant_id,
    document_id
):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT d.id

        FROM documents d

        INNER JOIN accountant_clients ac
            ON d.client_id = ac.client_id

        WHERE d.id = ?

        AND ac.accountant_id = ?

        AND d.accountant_id = ?
    """, (
        document_id,
        accountant_id,
        accountant_id
    ))

    result = cursor.fetchone()

    conn.close()

    return result is not None


# =========================================================
# CHECK CLIENT ACCESS TO DOCUMENT
# =========================================================

def client_can_access_document(
    client_id,
    document_id
):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id

        FROM documents

        WHERE id = ?

        AND client_id = ?
    """, (
        document_id,
        client_id
    ))

    result = cursor.fetchone()

    conn.close()

    return result is not None


# =========================================================
# APPROVE DOCUMENT
# =========================================================

def approve_document(
    document_id,
    user_id,
    comment=""
):

    conn = get_db_connection()
    cursor = conn.cursor()

    now = current_timestamp()

    # -----------------------------------------------------
    # CHECK USER
    # -----------------------------------------------------

    cursor.execute("""
        SELECT id, role

        FROM users

        WHERE id = ?
    """, (
        user_id,
    ))

    user = cursor.fetchone()

    if not user:
        conn.close()
        return False

    # -----------------------------------------------------
    # CHECK DOCUMENT
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            invoice_id,
            accountant_id,
            client_id

        FROM documents

        WHERE id = ?
    """, (
        document_id,
    ))

    document = cursor.fetchone()

    if not document:
        conn.close()
        return False

    # -----------------------------------------------------
    # ACCESS CONTROL
    # -----------------------------------------------------

    if user["role"] == "admin":

        allowed = True

    elif user["role"] == "accountant":

        allowed = (
            document["accountant_id"] == user_id
            and accountant_can_access_document(
                user_id,
                document_id
            )
        )

    else:

        allowed = False

    if not allowed:

        conn.close()

        raise PermissionError(
            "You do not have permission to approve this document."
        )

    # -----------------------------------------------------
    # UPDATE DOCUMENT
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE documents

        SET

            workflow_status = 'APPROVED',

            updated_at = ?

        WHERE id = ?
    """, (
        now,
        document_id
    ))

    # -----------------------------------------------------
    # UPDATE INVOICE
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE invoices

        SET

            workflow_status = 'APPROVED',

            updated_at = ?

        WHERE id = ?
    """, (
        now,
        document["invoice_id"]
    ))

    # -----------------------------------------------------
    # APPROVAL RECORD
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO approvals (

            document_id,

            action,

            user_id,

            comment,

            created_at

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        document_id,

        "APPROVED",

        user_id,

        comment,

        now
    ))

    # -----------------------------------------------------
    # AUDIT LOG
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO audit_logs (

            document_id,

            user_id,

            action,

            details,

            created_at

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        document_id,

        user_id,

        "DOCUMENT_APPROVED",

        comment,

        now
    ))

    conn.commit()
    conn.close()

    return True


# =========================================================
# REJECT DOCUMENT
# =========================================================

def reject_document(
    document_id,
    user_id,
    comment=""
):

    conn = get_db_connection()
    cursor = conn.cursor()

    now = current_timestamp()

    # -----------------------------------------------------
    # CHECK USER
    # -----------------------------------------------------

    cursor.execute("""
        SELECT id, role

        FROM users

        WHERE id = ?
    """, (
        user_id,
    ))

    user = cursor.fetchone()

    if not user:
        conn.close()
        return False

    # -----------------------------------------------------
    # CHECK DOCUMENT
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            invoice_id,
            accountant_id,
            client_id

        FROM documents

        WHERE id = ?
    """, (
        document_id,
    ))

    document = cursor.fetchone()

    if not document:
        conn.close()
        return False

    # -----------------------------------------------------
    # ACCESS CONTROL
    # -----------------------------------------------------

    if user["role"] == "admin":

        allowed = True

    elif user["role"] == "accountant":

        allowed = (
            document["accountant_id"] == user_id
            and accountant_can_access_document(
                user_id,
                document_id
            )
        )

    else:

        allowed = False

    if not allowed:

        conn.close()

        raise PermissionError(
            "You do not have permission to reject this document."
        )

    # -----------------------------------------------------
    # UPDATE DOCUMENT
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE documents

        SET

            workflow_status = 'REJECTED',

            updated_at = ?

        WHERE id = ?
    """, (
        now,
        document_id
    ))

    # -----------------------------------------------------
    # UPDATE INVOICE
    # -----------------------------------------------------

    cursor.execute("""
        UPDATE invoices

        SET

            workflow_status = 'REJECTED',

            updated_at = ?

        WHERE id = ?
    """, (
        now,
        document["invoice_id"]
    ))

    # -----------------------------------------------------
    # REJECTION RECORD
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO approvals (

            document_id,

            action,

            user_id,

            comment,

            created_at

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        document_id,

        "REJECTED",

        user_id,

        comment,

        now
    ))

    # -----------------------------------------------------
    # AUDIT LOG
    # -----------------------------------------------------

    cursor.execute("""
        INSERT INTO audit_logs (

            document_id,

            user_id,

            action,

            details,

            created_at

        )

        VALUES (?, ?, ?, ?, ?)
    """, (

        document_id,

        user_id,

        "DOCUMENT_REJECTED",

        comment,

        now
    ))

    conn.commit()
    conn.close()

    return True


# =========================================================
# CREATE CLIENT
# =========================================================

def create_client(
    username,
    password,
    accountant_id
):

    conn = get_db_connection()
    cursor = conn.cursor()

    import hashlib

    password_hash = hashlib.sha256(
        password.encode()
    ).hexdigest()

    # -----------------------------------------------------
    # VERIFY ACCOUNTANT
    # -----------------------------------------------------

    cursor.execute("""
        SELECT id

        FROM users

        WHERE id = ?

        AND role = 'accountant'
    """, (
        accountant_id,
    ))

    accountant = cursor.fetchone()

    if not accountant:

        conn.close()

        return None

    try:

        cursor.execute("""
            INSERT INTO users (
                username,
                password_hash,
                role,
                created_at
            )

            VALUES (?, ?, ?, ?)
        """, (

            username,

            password_hash,

            "client",

            current_timestamp()
        ))

        client_id = cursor.lastrowid

        # -------------------------------------------------
        # CONNECT CLIENT TO ACCOUNTANT
        # -------------------------------------------------

        cursor.execute("""
            INSERT INTO accountant_clients (

                accountant_id,

                client_id,

                created_at

            )

            VALUES (?, ?, ?)
        """, (

            accountant_id,

            client_id,

            current_timestamp()
        ))

        conn.commit()

        return client_id

    except sqlite3.IntegrityError:

        conn.rollback()

        return None

    finally:

        conn.close()


# =========================================================
# GET ACCOUNTANT CLIENTS
# =========================================================

def get_accountant_clients(accountant_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.id,
            u.username,
            u.created_at

        FROM users u

        INNER JOIN accountant_clients ac
            ON u.id = ac.client_id

        WHERE ac.accountant_id = ?

        AND u.role = 'client'

        ORDER BY u.username
    """, (
        accountant_id,
    ))

    clients = cursor.fetchall()

    conn.close()

    return clients


# =========================================================
# GET CLIENT'S ACCOUNTANT
# =========================================================

def get_client_accountant(client_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            u.id,
            u.username

        FROM users u

        INNER JOIN accountant_clients ac
            ON u.id = ac.accountant_id

        WHERE ac.client_id = ?

        AND u.role = 'accountant'
    """, (
        client_id,
    ))

    accountant = cursor.fetchone()

    conn.close()

    return accountant


# =========================================================
# CHECK CLIENT - ACCOUNTANT CONNECTION
# =========================================================

def is_client_of_accountant(
    client_id,
    accountant_id
):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id

        FROM accountant_clients

        WHERE client_id = ?

        AND accountant_id = ?
    """, (
        client_id,
        accountant_id
    ))

    result = cursor.fetchone()

    conn.close()

    return result is not None


# =========================================================
# GET ACCOUNTANT DOCUMENTS
#
# IMPORTANT:
# Returns ONLY documents belonging to the
# logged-in accountant's assigned clients.
# =========================================================

def get_accountant_documents(accountant_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            d.id,

            d.invoice_id,

            d.source_filename,

            d.document_type,

            d.workflow_status,

            d.validation_status,

            d.uploaded_by,

            d.client_id,

            d.accountant_id,

            d.created_at,

            d.updated_at,

            u.username AS client_username

        FROM documents d

        INNER JOIN accountant_clients ac
            ON d.client_id = ac.client_id

        LEFT JOIN users u
            ON d.client_id = u.id

        WHERE ac.accountant_id = ?

        AND d.accountant_id = ?

        ORDER BY d.created_at DESC
    """, (
        accountant_id,
        accountant_id
    ))

    documents = cursor.fetchall()

    conn.close()

    return documents


# =========================================================
# GET CLIENT DOCUMENTS
#
# IMPORTANT:
# Returns ONLY documents owned by this client.
# =========================================================

def get_client_documents(client_id):

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            d.id,

            d.invoice_id,

            d.source_filename,

            d.document_type,

            d.workflow_status,

            d.validation_status,

            d.uploaded_by,

            d.client_id,

            d.accountant_id,

            d.created_at,

            d.updated_at

        FROM documents d

        WHERE d.client_id = ?

        ORDER BY d.created_at DESC
    """, (
        client_id,
    ))

    documents = cursor.fetchall()

    conn.close()

    return documents


# =========================================================
# GET ALL DOCUMENTS
#
# ADMIN ONLY FUNCTION
# =========================================================

def get_all_documents():

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT

            d.id,

            d.invoice_id,

            d.source_filename,

            d.document_type,

            d.workflow_status,

            d.validation_status,

            d.uploaded_by,

            d.client_id,

            d.accountant_id,

            d.created_at,

            d.updated_at,

            c.username AS client_username,

            a.username AS accountant_username

        FROM documents d

        LEFT JOIN users c
            ON d.client_id = c.id

        LEFT JOIN users a
            ON d.accountant_id = a.id

        ORDER BY d.created_at DESC
    """)

    documents = cursor.fetchall()

    conn.close()

    return documents


# =========================================================
# GET DOCUMENT FOR AUTHORIZED USER
#
# This is the safest function for app.py to use when
# opening a particular document.
# =========================================================

def get_authorized_document(
    document_id,
    user_id
):

    conn = get_db_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # GET USER
    # -----------------------------------------------------

    cursor.execute("""
        SELECT
            id,
            role

        FROM users

        WHERE id = ?
    """, (
        user_id,
    ))

    user = cursor.fetchone()

    if not user:

        conn.close()

        return None

    # -----------------------------------------------------
    # ADMIN
    # -----------------------------------------------------

    if user["role"] == "admin":

        cursor.execute("""
            SELECT
                d.*,
                c.username AS client_username,
                a.username AS accountant_username

            FROM documents d

            LEFT JOIN users c
                ON d.client_id = c.id

            LEFT JOIN users a
                ON d.accountant_id = a.id

            WHERE d.id = ?
        """, (
            document_id,
        ))

    # -----------------------------------------------------
    # ACCOUNTANT
    # -----------------------------------------------------

    elif user["role"] == "accountant":

        cursor.execute("""
            SELECT
                d.*,
                c.username AS client_username,
                a.username AS accountant_username

            FROM documents d

            INNER JOIN accountant_clients ac
                ON d.client_id = ac.client_id

            LEFT JOIN users c
                ON d.client_id = c.id

            LEFT JOIN users a
                ON d.accountant_id = a.id

            WHERE d.id = ?

            AND ac.accountant_id = ?

            AND d.accountant_id = ?
        """, (
            document_id,
            user_id,
            user_id
        ))

    # -----------------------------------------------------
    # CLIENT
    # -----------------------------------------------------

    elif user["role"] == "client":

        cursor.execute("""
            SELECT
                d.*,
                c.username AS client_username,
                a.username AS accountant_username

            FROM documents d

            LEFT JOIN users c
                ON d.client_id = c.id

            LEFT JOIN users a
                ON d.accountant_id = a.id

            WHERE d.id = ?

            AND d.client_id = ?
        """, (
            document_id,
            user_id
        ))

    # -----------------------------------------------------
    # UNKNOWN ROLE
    # -----------------------------------------------------

    else:

        conn.close()

        return None

    document = cursor.fetchone()

    conn.close()

    return document


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    create_database()

    print(
        "\n===== DATABASE TABLES =====\n"
    )

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name

        FROM sqlite_master

        WHERE type = 'table'

        ORDER BY name
    """)

    tables = cursor.fetchall()

    for table in tables:

        print(
            "•",
            table["name"]
        )

    print(
        "\n===== USERS =====\n"
    )

    cursor.execute("""
        SELECT
            id,
            username,
            role

        FROM users

        ORDER BY id
    """)

    users = cursor.fetchall()

    for user in users:

        print(
            f"• {user['id']} | "
            f"{user['username']} | "
            f"{user['role']}"
        )

    print(
        "\n===== ACCOUNTANT - CLIENT CONNECTIONS =====\n"
    )

    cursor.execute("""
        SELECT

            ac.id,

            a.username AS accountant,

            c.username AS client

        FROM accountant_clients ac

        JOIN users a
            ON ac.accountant_id = a.id

        JOIN users c
            ON ac.client_id = c.id

        ORDER BY ac.id
    """)

    connections = cursor.fetchall()

    if connections:

        for connection in connections:

            print(
                f"• {connection['accountant']} "
                f"→ {connection['client']}"
            )

    else:

        print(
            "• No accountant-client connections yet."
        )

    conn.close()