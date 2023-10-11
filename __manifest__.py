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
    "version": "15.0.1.1",
    "depends": [
        "web",
        "base",
        "mail",
        "odoo_rest",
        "queue_job",
        "alfaleads_utils",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/menus.xml",
        "views/agreement_views.xml",
    ],
    "demo": [],
    "application": True,
}
