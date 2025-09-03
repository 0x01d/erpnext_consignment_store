# consignment_store/api/portal.py
import frappe
from frappe import _
from frappe.utils import nowdate, flt, getdate

@frappe.whitelist(allow_guest=True)
def get_portal_data():
    """Get seller portal data - updated for contracts"""
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
            COUNT(CASE WHEN consignment_status = 'On Consignment' THEN 1 END) as active_items,
            COUNT(CASE WHEN consignment_status = 'Sold' THEN 1 END) as sold_items,
            COUNT(CASE WHEN consignment_status = 'Awaiting Pickup' THEN 1 END) as expiring_items,
            COUNT(*) as total_items
        FROM `tabItem`
        WHERE consignor = %s AND is_consignment = 1
    """, consignor, as_dict=True)[0]

    # Get earnings
    earnings = frappe.db.sql("""
        SELECT
            COALESCE(SUM(commission_amount), 0) as total_earnings,
            COALESCE(SUM(CASE WHEN status = 'Pending' THEN commission_amount END), 0) as pending_payout,
            COALESCE(SUM(CASE WHEN MONTH(posting_date) = MONTH(CURDATE())
                         THEN commission_amount END), 0) as this_month_earnings
        FROM `tabCommission Entry`
        WHERE consignor = %s
    """, consignor, as_dict=True)[0]

    stats.update(earnings)

    # Get active contracts
    contracts = frappe.db.sql("""
        SELECT
            cc.name,
            cc.contract_date,
            cc.contract_end_date,
            cc.total_items,
            cc.total_retail_value,
            cc.contract_status,
            cc.consignor_signed,
            cc.consignor_signed_date,
            cc.actual_sales,
            cc.actual_commission,
            cc.signature_token,
            DATEDIFF(cc.contract_end_date, CURDATE()) as days_remaining,
            (SELECT COUNT(*) FROM `tabConsignment Contract Item`
             WHERE parent = cc.name AND status = 'Sold') as items_sold
        FROM `tabConsignment Contract` cc
        WHERE cc.consignor = %s
        AND cc.docstatus = 1
        ORDER BY cc.contract_date DESC
        LIMIT 10
    """, consignor, as_dict=True)

    # Get active items with more details
    active_items = frappe.db.sql("""
        SELECT
            i.item_code,
            i.item_name,
            i.standard_rate as price,
            i.consignment_expiry_date as expiry_date,
            i.consignment_contract,
            i.brand,
            DATEDIFF(i.consignment_expiry_date, CURDATE()) as days_until_expiry,
            DATEDIFF(CURDATE(), i.creation) as days_active
        FROM `tabItem` i
        WHERE i.consignor = %s
        AND i.is_consignment = 1
        AND i.consignment_status IN ('On Consignment', 'Awaiting Pickup')
        ORDER BY i.creation DESC
        LIMIT 50
    """, consignor, as_dict=True)

    # Get recent sales with more details
    recent_sales = frappe.db.sql("""
        SELECT
            ce.posting_date as date,
            i.item_name,
            i.brand,
            ce.sale_amount as sale_price,
            ce.commission_amount as commission,
            ce.commission_rate,
            ce.status,
            ce.payout_reference
        FROM `tabCommission Entry` ce
        JOIN `tabItem` i ON i.name = ce.item_code
        WHERE ce.consignor = %s
        ORDER BY ce.posting_date DESC
        LIMIT 30
    """, consignor, as_dict=True)

    # Get payout history
    payouts = frappe.db.sql("""
        SELECT
            name,
            payout_date,
            total_amount,
            payment_method,
            payment_reference,
            status
        FROM `tabConsignment Payout`
        WHERE consignor = %s
        ORDER BY payout_date DESC
        LIMIT 10
    """, consignor, as_dict=True)

    # Get upcoming pickups (items expiring soon)
    upcoming_pickups = frappe.db.sql("""
        SELECT
            cc.name as contract,
            cc.contract_end_date,
            cc.ownership_transfer_date,
            COUNT(cci.name) as items_count,
            DATEDIFF(cc.ownership_transfer_date, CURDATE()) as days_until_transfer
        FROM `tabConsignment Contract` cc
        JOIN `tabConsignment Contract Item` cci ON cci.parent = cc.name
        WHERE cc.consignor = %s
        AND cc.contract_status IN ('Expired', 'Awaiting Pickup')
        AND cci.status = 'Active'
        GROUP BY cc.name
        ORDER BY cc.ownership_transfer_date ASC
    """, consignor, as_dict=True)

    # Calculate performance metrics
    performance = calculate_performance_metrics(consignor)

    return {
        'consignor': frappe.get_doc('Consignor', consignor),
        'stats': stats,
        'contracts': contracts,
        'active_items': active_items,
        'recent_sales': recent_sales,
        'payouts': payouts,
        'upcoming_pickups': upcoming_pickups,
        'performance': performance
    }

def calculate_performance_metrics(consignor):
    """Calculate seller performance metrics"""
    # Get sales by month for chart
    monthly_sales = frappe.db.sql("""
        SELECT
            DATE_FORMAT(posting_date, '%%Y-%%m') as month,
            SUM(commission_amount) as earnings,
            COUNT(*) as items_sold
        FROM `tabCommission Entry`
        WHERE consignor = %s
        AND posting_date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
        GROUP BY DATE_FORMAT(posting_date, '%%Y-%%m')
        ORDER BY month
    """, consignor, as_dict=True)

    # Get top selling categories
    top_categories = frappe.db.sql("""
        SELECT
            i.item_group,
            COUNT(*) as items_sold,
            SUM(ce.commission_amount) as total_commission
        FROM `tabCommission Entry` ce
        JOIN `tabItem` i ON i.name = ce.item_code
        WHERE ce.consignor = %s
        GROUP BY i.item_group
        ORDER BY items_sold DESC
        LIMIT 5
    """, consignor, as_dict=True)

    # Calculate average days to sell
    avg_days_to_sell = frappe.db.sql("""
        SELECT AVG(DATEDIFF(ce.posting_date, i.creation)) as avg_days
        FROM `tabCommission Entry` ce
        JOIN `tabItem` i ON i.name = ce.item_code
        WHERE ce.consignor = %s
    """, consignor)[0][0] or 0

    return {
        'monthly_sales': monthly_sales,
        'top_categories': top_categories,
        'avg_days_to_sell': round(avg_days_to_sell, 1)
    }

@frappe.whitelist(allow_guest=True)
def get_contract_for_signing(token):
    """Get contract details for signing page"""
    if not token:
        return None

    contract = frappe.db.get_value('Consignment Contract',
        {'signature_token': token, 'docstatus': 1},
        ['name', 'consignor', 'contract_date', 'contract_end_date',
         'total_items', 'total_retail_value', 'expected_commission',
         'contract_duration_days', 'grace_period_days', 'ownership_transfer_date',
         'consignor_signed', 'consignor_signed_date', 'contract_terms'],
        as_dict=True
    )

    if not contract:
        return None

    # Get consignor details
    consignor = frappe.db.get_value('Consignor', contract.consignor,
        ['consignor_name', 'consignor_code', 'email', 'phone'],
        as_dict=True
    )

    # Get items
    items = frappe.db.get_all('Consignment Contract Item',
        filters={'parent': contract.name},
        fields=['item_code', 'item_name', 'retail_price', 'commission_rate',
               'expected_commission']
    )

    contract['consignor_details'] = consignor
    contract['items'] = items

    return contract

@frappe.whitelist(allow_guest=True)
def sign_contract(token, signature_data, signer_name):
    """Sign a contract digitally"""
    if not token or not signature_data:
        frappe.throw(_("Missing required data"))

    # Get contract
    contract_name = frappe.db.get_value('Consignment Contract',
        {'signature_token': token, 'docstatus': 1},
        'name'
    )

    if not contract_name:
        frappe.throw(_("Invalid or expired contract link"))

    contract = frappe.get_doc('Consignment Contract', contract_name)

    # Get IP address
    signer_ip = frappe.local.request_ip if hasattr(frappe.local, 'request_ip') else None

    # Process signature
    result = contract.sign_contract(signature_data, signer_name, signer_ip)

    return result

@frappe.whitelist()
def get_item_details(item_code):
    """Get detailed information about a specific item"""
    if frappe.session.user == 'Guest':
        return None

    consignor = frappe.db.get_value('Consignor',
        {'email': frappe.session.user},
        'name'
    )

    if not consignor:
        return None

    item = frappe.db.get_value('Item',
        {'item_code': item_code, 'consignor': consignor},
        ['*'],
        as_dict=True
    )

    if not item:
        return None

    # Get sale history if sold
    sale_info = None
    if item.consignment_status == 'Sold':
        sale_info = frappe.db.get_value('Commission Entry',
            {'item_code': item_code},
            ['posting_date', 'sale_amount', 'commission_amount', 'status'],
            as_dict=True
        )

    item['sale_info'] = sale_info

    return item

@frappe.whitelist()
def request_payout():
    """Request a payout for pending commissions"""
    if frappe.session.user == 'Guest':
        return {'success': False, 'message': 'Not logged in'}

    consignor = frappe.db.get_value('Consignor',
        {'email': frappe.session.user},
        'name'
    )

    if not consignor:
        return {'success': False, 'message': 'Consignor not found'}

    # Check pending amount
    pending = frappe.db.sql("""
        SELECT SUM(commission_amount) as total
        FROM `tabCommission Entry`
        WHERE consignor = %s AND status = 'Pending'
    """, consignor)[0][0] or 0

    min_payout = frappe.db.get_value('Consignor', consignor, 'minimum_payout') or 50

    if pending < min_payout:
        return {
            'success': False,
            'message': f'Minimum payout amount is €{min_payout}. Current pending: €{pending:.2f}'
        }

    # Create payout request (simplified - in production, this might need approval)
    from consignment_store.api.commission import create_payout

    try:
        payout = create_payout(consignor)
        return {
            'success': True,
            'message': f'Payout request created: {payout.name}',
            'payout_id': payout.name,
            'amount': payout.total_amount
        }
    except Exception as e:
        return {
            'success': False,
            'message': str(e)
        }
