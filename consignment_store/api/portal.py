# consignment_store/api/portal.py
import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def get_portal_data():
    """Get seller portal data"""
    if frappe.session.user == 'Guest':
        return None

    consignor = frappe.db.get_value('Consignor',
        {'email': frappe.session.user},
        'name'
    )

    if not consignor:
        return None

    # Get statistics
    stats = frappe.db.sql("""
        SELECT
            COUNT(CASE WHEN consignment_status = 'Active' THEN 1 END) as active_items,
            COUNT(CASE WHEN consignment_status = 'Sold' THEN 1 END) as sold_items,
            COUNT(*) as total_items
        FROM `tabItem`
        WHERE consignor = %s AND is_consignment = 1
    """, consignor, as_dict=True)[0]

    # Get earnings
    earnings = frappe.db.sql("""
        SELECT
            COALESCE(SUM(commission_amount), 0) as total_earnings,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN commission_amount END), 0) as pending_payout
        FROM `tabCommission Entry`
        WHERE consignor = %s
    """, consignor, as_dict=True)[0]

    stats.update(earnings)

    # Get active items
    active_items = frappe.db.sql("""
        SELECT
            item_code,
            item_name,
            standard_rate as price,
            consignment_expiry_date as expiry_date,
            DATEDIFF(CURDATE(), creation) as days_active
        FROM `tabItem`
        WHERE consignor = %s
        AND is_consignment = 1
        AND consignment_status = 'Active'
        ORDER BY creation DESC
        LIMIT 20
    """, consignor, as_dict=True)

    # Get recent sales
    recent_sales = frappe.db.sql("""
        SELECT
            ce.posting_date as date,
            i.item_name,
            ce.sale_amount as sale_price,
            ce.commission_amount as commission,
            ce.status
        FROM `tabCommission Entry` ce
        JOIN `tabItem` i ON i.name = ce.item_code
        WHERE ce.consignor = %s
        ORDER BY ce.posting_date DESC
        LIMIT 20
    """, consignor, as_dict=True)

    return {
        'consignor': frappe.get_doc('Consignor', consignor),
        'stats': stats,
        'active_items': active_items,
        'recent_sales': recent_sales
    }
