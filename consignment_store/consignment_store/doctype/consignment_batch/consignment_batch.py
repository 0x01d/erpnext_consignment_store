# consignment_store/consignment_store/doctype/consignment_batch/consignment_batch.py
import frappe
from frappe.model.document import Document

class ConsignmentBatch(Document):
    def validate(self):
        self.calculate_totals()

    def calculate_totals(self):
        self.total_items = len(self.items)
        self.total_value = sum(item.price or 0 for item in self.items)
        self.expected_commission = sum(
            (item.price or 0) * (item.commission_rate or 0) / 100
            for item in self.items
        )
