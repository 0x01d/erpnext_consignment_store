# consignment_store/utils/commission.py
import frappe
from frappe import _
from frappe.utils import flt, nowdate

def validate_consignment_item(doc, method=None):
    """Validate consignment item fields"""
    if doc.is_consignment:
        if not doc.consignor:
            frappe.throw(_("Consignor is required for consignment items"))

        if not doc.commission_rate:
            doc.commission_rate = frappe.db.get_value(
                'Consignor',
                doc.consignor,
                'default_commission_rate'
            ) or 50

def validate_consignment_items(doc, method=None):
    """Validate consignment items in invoice"""
    for item in doc.items:
        item_doc = frappe.get_cached_doc('Item', item.item_code)
        if item_doc.is_consignment:
            item.is_consignment = 1
            item.consignor = item_doc.consignor
            item.commission_rate = item_doc.commission_rate

def process_commission(doc, method=None):
    """Process commission for sold items"""
    for item in doc.items:
        if item.is_consignment:
            # Calculate commission
            commission_amount = flt(item.amount) * flt(item.commission_rate) / 100

            # Create commission entry
            ce = frappe.new_doc('Commission Entry')
            ce.consignor = item.consignor
            ce.sales_invoice = doc.name
            ce.item_code = item.item_code
            ce.posting_date = doc.posting_date
            ce.sale_amount = item.amount
            ce.commission_rate = item.commission_rate
            ce.commission_amount = commission_amount
            ce.status = 'Pending'
            ce.insert(ignore_permissions=True)

            # Update item status
            frappe.db.set_value('Item', item.item_code,
                'consignment_status', 'Sold'
            )

            # Update consignor stats
            update_consignor_stats(item.consignor)

def cancel_commission(doc, method=None):
    """Cancel commission entries when invoice is cancelled"""
    # Delete commission entries
    frappe.db.delete('Commission Entry', {
        'sales_invoice': doc.name
    })

    # Restore item status
    for item in doc.items:
        if item.is_consignment:
            frappe.db.set_value('Item', item.item_code,
                'consignment_status', 'Active'
            )

def update_consignor_stats(consignor):
    """Update consignor statistics"""
    stats = frappe.db.sql("""
        SELECT
            COUNT(DISTINCT CASE WHEN consignment_status = 'Active' THEN name END) as active,
            COUNT(DISTINCT CASE WHEN consignment_status = 'Sold' THEN name END) as sold,
            (SELECT COALESCE(SUM(commission_amount), 0)
             FROM `tabCommission Entry`
             WHERE consignor = %s) as earnings
        FROM `tabItem`
        WHERE consignor = %s AND is_consignment = 1
    """, (consignor, consignor), as_dict=True)[0]

    frappe.db.set_value('Consignor', consignor, {
        'total_items_active': stats.active,
        'total_items_sold': stats.sold,
        'lifetime_earnings': stats.earnings
    })

def process_monthly_payouts():
    """Scheduled task to process monthly payouts"""
    # Get consignors with pending commission above minimum
    consignors = frappe.db.sql("""
        SELECT
            c.name,
            c.minimum_payout,
            SUM(ce.commission_amount) as pending_amount
        FROM `tabConsignor` c
        JOIN `tabCommission Entry` ce ON ce.consignor = c.name
        WHERE ce.status = 'Pending'
        GROUP BY c.name
        HAVING pending_amount >= c.minimum_payout
    """, as_dict=True)

    for consignor in consignors:
        from consignment_store.api.commission import create_payout
        try:
            create_payout(consignor.name)
        except Exception as e:
            frappe.log_error(f"Failed to create payout for {consignor.name}: {str(e)}")
