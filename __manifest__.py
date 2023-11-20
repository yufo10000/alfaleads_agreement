{
    "name": "Alfaleads Agreement",
    "summary": """
        Alfaleads extension to Accounting for Agreements
    """,
    "description": """""",
    "author": "",
    "website": "",
    "category": "Accounting/Accounting",
    "license": "LGPL-3",
    "version": "16.0.1.1",
    "depends": [
        "alfaleads",
        "web",
        "base",
        "mail",
        "odoo_rest",
        "queue_job",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/agreement_views.xml",
    ],
    "demo": [],
    "application": True,
}
