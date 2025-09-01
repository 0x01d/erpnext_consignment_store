# consignment_store/consignment_store/doctype/consignment_payout/consignment_payout.py
import frappe
from frappe.model.document import Document

class ConsignmentPayout(Document):
    def validate(self):
        self.calculate_total()

    def calculate_total(self):
        self.total_amount = sum(item.amount or 0 for item in self.commission_entries)

    def on_submit(self):
        # Update commission entries status
        for item in self.commission_entries:
            frappe.db.set_value('Commission Entry', item.commission_entry, {
                'status': 'Processed',
                'payout_reference': self.name
            })
