# consignment_store/api/commission.py
import frappe
from frappe import _
from frappe.utils import flt, nowdate

@frappe.whitelist()
def get_pending_commissions(consignor=None):
    """Get pending commission entries"""
    filters = {'status': 'Pending'}
    if consignor:
        filters['consignor'] = consignor

    return frappe.get_all('Commission Entry',
        filters=filters,
        fields=['*'],
        order_by='posting_date desc'
    )

@frappe.whitelist()
def create_payout(consignor, commission_entries=None):
    """Create payout for consignor"""
    if not commission_entries:
        commission_entries = get_pending_commissions(consignor)

    if not commission_entries:
        frappe.throw(_("No pending commissions"))

    total = sum(flt(ce.get('commission_amount')) for ce in commission_entries)
    min_payout = frappe.db.get_value('Consignor', consignor, 'minimum_payout')

    if total < min_payout:
        frappe.throw(_(f"Total amount {total} is below minimum payout {min_payout}"))

    payout = frappe.new_doc('Consignment Payout')
    payout.consignor = consignor
    payout.payout_date = nowdate()
    payout.total_amount = total

    for ce in commission_entries:
        payout.append('commission_entries', {
            'commission_entry': ce.get('name'),
            'amount': ce.get('commission_amount')
        })

    payout.insert()
    payout.submit()

    # Update commission entries
    for ce in commission_entries:
        frappe.db.set_value('Commission Entry', ce.get('name'), {
            'status': 'Processed',
            'payout_reference': payout.name
        })

    return payout
