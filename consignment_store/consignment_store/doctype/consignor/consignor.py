# consignment_store/consignment_store/doctype/consignor/consignor.py
import frappe
from frappe.model.document import Document
import random
import string

class Consignor(Document):
    def validate(self):
        if not self.consignor_code:
            self.consignor_code = self.generate_code()

        if not self.supplier_link:
            self.create_supplier()

    def generate_code(self):
        initials = ''.join([n[0].upper() for n in self.consignor_name.split()[:3]])
        while True:
            suffix = ''.join(random.choices(string.digits, k=4))
            code = f"{initials}{suffix}"
            if not frappe.db.exists('Consignor', {'consignor_code': code}):
                return code

    def create_supplier(self):
        supplier = frappe.new_doc('Supplier')
        supplier.supplier_name = self.consignor_name
        supplier.supplier_group = 'Individual Consignor'  # Fixed: Changed from 'Individual' to match install.py
        supplier.flags.ignore_permissions = True
        supplier.insert()
        self.supplier_link = supplier.name
