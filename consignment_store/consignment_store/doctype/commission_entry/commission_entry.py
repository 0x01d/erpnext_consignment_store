# consignment_store/consignment_store/doctype/commission_entry/commission_entry.py
import frappe
from frappe.model.document import Document

class CommissionEntry(Document):
    def validate(self):
        if self.commission_amount < 0:
            frappe.throw("Commission amount cannot be negative")
