# consignment_store/config/consignment_store.py
from frappe import _

def get_data():
    return [
        {
            "label": _("Documents"),
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
            "items": [
                {
                    "type": "page",
                    "name": "quick-intake",
                    "label": _("Quick Intake"),
                    "description": _("Quick Consignment Intake"),
                    "onboard": 1,
                }
            ]
        }
    ]
