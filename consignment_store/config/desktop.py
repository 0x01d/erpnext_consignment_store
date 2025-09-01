# consignment_store/config/desktop.py
from frappe import _

def get_data():
    return [
        {
            "module_name": "Consignment Store",
            "category": "Modules",
            "label": _("Consignment Store"),
            "color": "#4CAF50",
            "icon": "octicon octicon-package",
            "type": "module",
            "description": "Manage consignment store operations",
            "onboard_present": 1,
            "link": "Modules/Consignment Store"  # Add this line
        }
    ]
