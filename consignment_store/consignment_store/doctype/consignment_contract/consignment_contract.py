# consignment_store/consignment_store/doctype/consignment_contract/consignment_contract.py
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, flt
from frappe import _

class ConsignmentContract(Document):
    def validate(self):
        self.set_dates()
        self.calculate_totals()

    def set_dates(self):
        """Set contract end and ownership transfer dates"""
        if self.contract_date and self.contract_duration_days:
            self.contract_end_date = add_days(self.contract_date, self.contract_duration_days)
            self.ownership_transfer_date = add_days(
                self.contract_end_date,
                self.grace_period_days or 14
            )

    def calculate_totals(self):
        """Calculate contract totals"""
        self.total_items = len(self.items)
        self.total_retail_value = sum(flt(item.retail_price) for item in self.items)
        self.expected_commission = sum(
            flt(item.retail_price) * flt(item.commission_rate) / 100
            for item in self.items
        )

        # Calculate expected commission for each item
        for item in self.items:
            item.expected_commission = flt(item.retail_price) * flt(item.commission_rate) / 100

    def on_submit(self):
        """Link items to this contract"""
        for item in self.items:
            frappe.db.set_value('Item', item.item_code, {
                'consignment_contract': self.name,
                'consignment_expiry_date': self.contract_end_date,
                'ownership_transfer_date': self.ownership_transfer_date,
                'consignment_status': 'On Consignment'
            })

    def on_cancel(self):
        """Unlink items from contract"""
        for item in self.items:
            frappe.db.set_value('Item', item.item_code, {
                'consignment_contract': None,
                'consignment_status': 'Cancelled'
            })

    @frappe.whitelist()
    def process_ownership_transfer(self):
        """Transfer ownership of all unsold items to store"""
        if self.contract_status != 'Awaiting Pickup':
            frappe.throw(_("Can only transfer ownership for contracts awaiting pickup"))

        company = frappe.db.get_single_value('Global Defaults', 'default_company')
        abbr = frappe.db.get_value('Company', company, 'abbr')
        warehouse = f'Stores - {abbr}'

        # Create stock entry for ownership transfer
        stock_entry = frappe.new_doc('Stock Entry')
        stock_entry.stock_entry_type = 'Material Receipt'
        stock_entry.purpose = 'Material Receipt'
        stock_entry.remarks = f"Ownership transfer from contract {self.name}"

        items_transferred = []

        for item in self.items:
            if item.status == 'Active':  # Only transfer unsold items
                # Update item to become stock item at markdown price
                markdown_price = flt(item.retail_price) * 0.3  # 30% of original

                frappe.db.set_value('Item', item.item_code, {
                    'is_stock_item': 1,  # NOW it becomes stock item
                    'is_consignment': 0,  # No longer consignment
                    'consignment_status': 'Owned',
                    'standard_rate': markdown_price,
                    'item_group': 'Clearance'
                })

                # Add to stock entry at markdown value
                stock_entry.append('items', {
                    'item_code': item.item_code,
                    't_warehouse': warehouse,
                    'qty': 1,
                    'basic_rate': markdown_price,
                    'valuation_rate': markdown_price
                })

                # Update contract item status
                item.db_set('status', 'Ownership Transferred')
                items_transferred.append(item.item_code)

        if items_transferred:
            stock_entry.insert()
            stock_entry.submit()

            # Update contract status
            self.db_set('contract_status', 'Ownership Transferred')

            # Notify consignor
            self.notify_ownership_transfer(items_transferred)

            frappe.msgprint(f"Transferred ownership of {len(items_transferred)} items")
        else:
            frappe.msgprint("No items to transfer")

    def notify_ownership_transfer(self, items):
        """Send notification to consignor"""
        consignor = frappe.get_doc('Consignor', self.consignor)

        if consignor.email:
            items_list = '<ul>'
            for item_code in items:
                item_name = frappe.db.get_value('Item', item_code, 'item_name')
                items_list += f'<li>{item_name} ({item_code})</li>'
            items_list += '</ul>'

            frappe.sendmail(
                recipients=[consignor.email],
                subject=f"Ownership Transfer - Contract {self.name}",
                message=f"""
                <p>Dear {consignor.consignor_name},</p>

                <p>As per our consignment agreement, ownership of the following
                uncollected items has been transferred to the store:</p>

                {items_list}

                <p>Contract: {self.name}<br>
                Transfer Date: {nowdate()}</p>

                <p>Thank you for consigning with us.</p>
                """
            )
