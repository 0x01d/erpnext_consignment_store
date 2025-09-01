# consignment_store/config/consignment_store.py
from frappe import _

def get_data():
    return [
        {
            "label": _("Documents"),
            "icon": "fa fa-star",
            "items": [
                {
                    "type": "doctype",
                    "name": "Consignor",
                    "description": _("Manage Consignors"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Consignment Batch",
                    "description": _("Consignment Batches"),
                    "onboard": 1,
                },
                {
                    "type": "doctype",
                    "name": "Commission Entry",
                    "description": _("Commission Entries"),
                },
                {
                    "type": "doctype",
                    "name": "Consignment Payout",
                    "description": _("Payouts"),
                },
            ]
        },
        {
            "label": _("Tools"),
            "icon": "fa fa-wrench",
            "items": [
                {
                    "type": "page",
                    "name": "quick-intake",
                    "label": _("Quick Intake"),
                    "description": _("Quick Consignment Intake"),
                    "onboard": 1,
                }
            ]
        },
        {
            "label": _("Reports"),
            "icon": "fa fa-list",
            "items": [
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Commission Summary",
                    "doctype": "Commission Entry",
                    "onboard": 1,
                },
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Consignor Performance",
                    "doctype": "Consignor",
                    "onboard": 1,
                }
            ]
        },
        {
            "label": _("Setup"),
            "icon": "fa fa-cog",
            "items": [
                {
                    "type": "doctype",
                    "name": "Item",
                    "description": _("Item Master with Consignment Fields"),
                    "onboard": 1,
                }
            ]
        }
    ]
