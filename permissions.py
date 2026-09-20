ROLE_PERMISSIONS = {

    "admin": [
        "upload_document",
        "view_documents",
        "process_document",
        "review_document",
        "approve_document",
        "reject_document",
        "view_reports",
        "export_data",
        "manage_users"
    ],

    "accountant": [
        "upload_document",
        "view_documents",
        "process_document",
        "review_document",
        "approve_document",
        "reject_document",
        "view_reports",
        "export_data"
    ]
}


def has_permission(role, permission):
    permissions = ROLE_PERMISSIONS.get(role, [])
    return permission in permissions


def get_permissions(role):
    return ROLE_PERMISSIONS.get(role, [])