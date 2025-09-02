# consignment_store/utils/consignment_accounting.py
"""
Proper consignment accounting that doesn't pollute the balance sheet
"""
import frappe
from frappe import _
from frappe.utils import nowdate, add_days, date_diff, flt
from datetime import datetime

class ConsignmentAccountingManager:
    """Manages consignment accounting without affecting balance sheet"""

    def __init__(self):
        self.setup_accounts()

    def setup_accounts(self):
        """Ensure required GL accounts exist"""
        self.accounts = {
            'consignment_liability': 'Consignment Payable',  # Liability account
            'consignment_memo': 'Consignment Inventory (Memo)',  # Off-balance sheet
            'commission_income': 'Commission Income',
            'consignment_clearing': 'Consignment Clearing'
        }

    def create_consignment_receipt(self, items, consignor):
        """
        Create receipt for consignment items WITHOUT affecting inventory value
        Uses memo/tracking only - no balance sheet impact
        """
        # Create a Consignment Receipt (custom doctype we'll create)
        receipt = frappe.new_doc('Consignment Receipt')
        receipt.consignor = consignor
        receipt.receipt_date = nowdate()
        receipt.contract_duration_days = 60  # 2 months standard
        receipt.grace_period_days = 14  # 2 weeks after expiry

        total_retail_value = 0

        for item in items:
            # DO NOT create stock entry with value!
            # Instead, track items in a memo account or custom doctype

            receipt.append('items', {
                'item_code': item.name,
                'item_name': item.item_name,
                'retail_price': item.standard_rate,
                'commission_rate': item.commission_rate,
                'consignment_end_date': add_days(nowdate(), 60),
                'ownership_transfer_date': add_days(nowdate(), 74)  # 60 + 14 days
            })

            total_retail_value += item.standard_rate

            # Set item tracking fields
            frappe.db.set_value('Item', item.name, {
                'consignment_status': 'On Consignment',
                'consignment_end_date': add_days(nowdate(), 60),
                'ownership_transfer_date': add_days(nowdate(), 74),
                'consignment_contract': receipt.name
            })

        receipt.total_retail_value = total_retail_value
        receipt.insert()
        receipt.submit()

        # Create MEMO entry only (not affecting GL)
        self.create_memo_entry(receipt)

        return receipt

    def create_memo_entry(self, receipt):
        """Create off-balance sheet memo for tracking"""
        # This could be a custom doctype that tracks consignment inventory
        # without affecting GL accounts
        memo = frappe.new_doc('Consignment Memo')
        memo.receipt = receipt.name
        memo.consignor = receipt.consignor
        memo.total_value = receipt.total_retail_value
        memo.status = 'Active'
        memo.insert()
        return memo

    def process_consignment_sale(self, sales_invoice):
        """
        Process sale of consignment items correctly:
        - Recognize only commission as revenue
        - Create liability to consignor for their portion
        """
        for item in sales_invoice.items:
            if not item.is_consignment:
                continue

            item_doc = frappe.get_doc('Item', item.item_code)

            # Calculate splits
            sale_amount = item.amount
            commission = sale_amount * (item.commission_rate / 100)
            consignor_portion = sale_amount - commission

            # Create Commission Entry (your existing)
            ce = frappe.new_doc('Commission Entry')
            ce.consignor = item.consignor
            ce.sales_invoice = sales_invoice.name
            ce.item_code = item.item_code
            ce.posting_date = sales_invoice.posting_date
            ce.sale_amount = sale_amount
            ce.commission_rate = item.commission_rate
            ce.commission_amount = commission
            ce.consignor_liability = consignor_portion
            ce.status = 'Pending'
            ce.insert(ignore_permissions=True)

            # Create proper GL entries
            self.create_sale_gl_entries(sales_invoice, item, commission, consignor_portion)

            # Update item status
            frappe.db.set_value('Item', item.item_code, {
                'consignment_status': 'Sold',
                'sale_date': sales_invoice.posting_date
            })

    def create_sale_gl_entries(self, invoice, item, commission, consignor_portion):
        """Create correct GL entries for consignment sale"""
        from erpnext.accounts.general_ledger import make_gl_entries

        gl_entries = []

        # Debit: Cash/Receivables (full amount)
        gl_entries.append({
            'account': invoice.debit_to,
            'debit': item.amount,
            'credit': 0,
            'against': self.accounts['commission_income'],
            'voucher_type': 'Sales Invoice',
            'voucher_no': invoice.name
        })

        # Credit: Commission Income (our portion only)
        gl_entries.append({
            'account': self.accounts['commission_income'],
            'debit': 0,
            'credit': commission,
            'against': invoice.debit_to,
            'voucher_type': 'Sales Invoice',
            'voucher_no': invoice.name
        })

        # Credit: Consignment Payable (consignor's portion)
        gl_entries.append({
            'account': self.accounts['consignment_liability'],
            'debit': 0,
            'credit': consignor_portion,
            'party_type': 'Supplier',
            'party': item.consignor,
            'against': invoice.debit_to,
            'voucher_type': 'Sales Invoice',
            'voucher_no': invoice.name
        })

        # make_gl_entries(gl_entries)

    def check_contract_expiry(self):
        """
        Daily task to check contract expiry and ownership transfers
        Runs via scheduler
        """
        today = nowdate()

        # Check for items reaching end of consignment period
        expiring_items = frappe.db.sql("""
            SELECT name, consignor, consignment_end_date, ownership_transfer_date
            FROM `tabItem`
            WHERE is_consignment = 1
            AND consignment_status = 'On Consignment'
            AND consignment_end_date = %s
        """, today, as_dict=True)

        for item in expiring_items:
            # Send notification to consignor
            self.notify_contract_expiry(item)

            # Update status to "Awaiting Pickup"
            frappe.db.set_value('Item', item.name,
                'consignment_status', 'Awaiting Pickup')

        # Check for items reaching ownership transfer date
        transfer_items = frappe.db.sql("""
            SELECT name, consignor, standard_rate
            FROM `tabItem`
            WHERE is_consignment = 1
            AND consignment_status = 'Awaiting Pickup'
            AND ownership_transfer_date = %s
        """, today, as_dict=True)

        for item in transfer_items:
            self.transfer_ownership(item)

    def transfer_ownership(self, item):
        """
        Transfer ownership from consignor to store
        This is when we actually recognize the inventory
        """
        # Now we create a proper stock entry with value
        stock_entry = frappe.new_doc('Stock Entry')
        stock_entry.stock_entry_type = 'Material Receipt'
        stock_entry.remarks = f"Ownership transfer after contract expiry - {item.name}"

        # Value at markdown price (e.g., 30% of original)
        markdown_rate = item.standard_rate * 0.3

        stock_entry.append('items', {
            'item_code': item.name,
            't_warehouse': 'Stores - CS',
            'qty': 1,
            'basic_rate': markdown_rate  # Now we own it at markdown value
        })

        stock_entry.insert()
        stock_entry.submit()

        # Update item
        frappe.db.set_value('Item', item.name, {
            'is_consignment': 0,  # No longer consignment
            'consignment_status': 'Owned',
            'ownership_transfer_date': nowdate(),
            'standard_rate': markdown_rate,  # Update to markdown price
            'item_group': 'Clearance'  # Move to clearance category
        })

        # Notify consignor of ownership transfer
        self.notify_ownership_transfer(item)

    def notify_contract_expiry(self, item):
        """Send expiry notification to consignor"""
        consignor = frappe.get_doc('Consignor', item.consignor)

        if consignor.email:
            frappe.sendmail(
                recipients=[consignor.email],
                subject="Consignment Contract Expiring - Action Required",
                message=f"""
                <p>Dear {consignor.consignor_name},</p>

                <p>Your consignment contract for the following item expires today:</p>
                <ul>
                    <li>Item: {item.name}</li>
                    <li>Contract End: {item.consignment_end_date}</li>
                </ul>

                <p><strong>Important:</strong> You have 14 days to collect this item.
                After {item.ownership_transfer_date}, ownership will automatically
                transfer to the store per our agreement.</p>

                <p>Please contact us to arrange pickup.</p>
                """
            )

    def notify_ownership_transfer(self, item):
        """Notify consignor of ownership transfer"""
        consignor = frappe.get_doc('Consignor', item.consignor)

        if consignor.email:
            frappe.sendmail(
                recipients=[consignor.email],
                subject="Ownership Transfer Complete",
                message=f"""
                <p>Dear {consignor.consignor_name},</p>

                <p>As per our consignment agreement, ownership of the following
                uncollected item has been transferred to the store:</p>

                <ul>
                    <li>Item: {item.name}</li>
                    <li>Transfer Date: {nowdate()}</li>
                </ul>

                <p>Thank you for consigning with us.</p>
                """
            )


# Scheduler functions
def daily_contract_check():
    """Daily scheduled task for contract management"""
    manager = ConsignmentAccountingManager()
    manager.check_contract_expiry()


# Hook functions for sales processing
def process_consignment_sale_properly(doc, method=None):
    """Hook for sales invoice submission"""
    if any(item.is_consignment for item in doc.items):
        manager = ConsignmentAccountingManager()
        manager.process_consignment_sale(doc)
