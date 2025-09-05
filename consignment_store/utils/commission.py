# consignment_store/utils/commission.py
"""
Fixed commission processing that only affects accounting after sale
Replace your existing commission.py with this
"""
import frappe
from frappe import _
from frappe.utils import flt, nowdate, get_link_to_form
from erpnext.accounts.general_ledger import make_gl_entries

def validate_consignment_item(doc, method=None):
    """Validate consignment item fields - NO STOCK VALUE"""
    if doc.is_consignment:
        if not doc.consignor:
            frappe.throw(_("Consignor is required for consignment items"))

        # Set commission rate from consignor if not set
        if not doc.commission_rate:
            doc.commission_rate = frappe.db.get_value(
                'Consignor',
                doc.consignor,
                'default_commission_rate'
            ) or 50

        # IMPORTANT: Consignment items are NOT stock items until we own them
        doc.is_stock_item = 0
        doc.maintain_stock = 0

def validate_consignment_items(doc, method=None):
    """Validate consignment items in invoice"""
    for item in doc.items:
        item_doc = frappe.get_cached_doc('Item', item.item_code)

        if item_doc.is_consignment:
            item.is_consignment = 1
            item.consignor = item_doc.consignor
            item.commission_rate = item_doc.commission_rate

            # Calculate commission split
            item.commission_amount = flt(item.amount) * flt(item.commission_rate) / 100
            item.consignor_amount = flt(item.amount) - item.commission_amount

def process_commission(doc, method=None):
    """
    Process commission for sold items
    This is where accounting happens - ONLY after sale
    """
    # Skip if no consignment items
    if not any(item.is_consignment for item in doc.items):
        return

    company = doc.company
    abbr = frappe.db.get_value('Company', company, 'abbr')

    # Get GL accounts
    commission_income_account = frappe.db.get_value('Account', {
        'account_name': 'Commission Income',
        'company': company
    })

    consignment_payable_account = frappe.db.get_value('Account', {
        'account_name': 'Consignment Payable',
        'company': company
    })

    if not commission_income_account or not consignment_payable_account:
        frappe.throw(_("Please create Commission Income and Consignment Payable GL accounts"))

    # Process each consignment item
    for item in doc.items:
        if not item.is_consignment:
            continue

        # Calculate amounts
        sale_amount = flt(item.amount)
        commission_amount = flt(item.commission_amount) or (sale_amount * flt(item.commission_rate) / 100)
        consignor_amount = sale_amount - commission_amount

        # Create Commission Entry
        ce = frappe.new_doc('Commission Entry')
        ce.consignor = item.consignor
        ce.sales_invoice = doc.name
        ce.item_code = item.item_code
        ce.posting_date = doc.posting_date
        ce.sale_amount = sale_amount
        ce.commission_rate = item.commission_rate
        ce.commission_amount = commission_amount
        ce.consignor_liability = consignor_amount
        ce.status = 'Pending'
        ce.insert(ignore_permissions=True)

        # Update item status
        frappe.db.set_value('Item', item.item_code, 'consignment_status', 'Sold')

        # Update contract if exists
        contract = frappe.db.get_value('Item', item.item_code, 'consignment_contract')
        if contract:
            update_contract_item_status(contract, item.item_code, sale_amount, commission_amount)

        # Update consignor stats
        update_consignor_stats(item.consignor)

    # Create proper GL entries for the entire invoice
    create_consignment_gl_entries(doc, commission_income_account, consignment_payable_account)

def create_consignment_gl_entries(doc, commission_account, payable_account):
    """
    Create GL entries that properly reflect consignment accounting
    Only commission is revenue, rest is liability to consignor
    """
    gl_entries = []

    # Group by consignor for cleaner GL entries
    consignor_totals = {}
    total_commission = 0

    for item in doc.items:
        if item.is_consignment:
            if item.consignor not in consignor_totals:
                consignor_totals[item.consignor] = {
                    'commission': 0,
                    'payable': 0
                }

            commission = flt(item.commission_amount) or (flt(item.amount) * flt(item.commission_rate) / 100)
            payable = flt(item.amount) - commission

            consignor_totals[item.consignor]['commission'] += commission
            consignor_totals[item.consignor]['payable'] += payable
            total_commission += commission

    if not total_commission:
        return

    # Get the debit account (usually Debtors for credit sales or Cash for cash sales)
    debit_account = doc.debit_to if doc.doctype == 'Sales Invoice' else doc.account_for_change_amount

    # Create GL entries for commission income
    if total_commission:
        # Credit: Commission Income (our revenue)
        gl_entries.append(
            doc.get_gl_dict({
                'account': commission_account,
                'credit': total_commission,
                'credit_in_account_currency': total_commission,
                'against': debit_account,
                'remarks': f'Commission income from {doc.name}',
                'cost_center': doc.cost_center if hasattr(doc, 'cost_center') else None
            })
        )

    # Create GL entries for consignor payables
    for consignor, amounts in consignor_totals.items():
        if amounts['payable']:
            supplier = frappe.db.get_value('Consignor', consignor, 'supplier_link')

            # Credit: Consignment Payable (liability to consignor)
            gl_entries.append(
                doc.get_gl_dict({
                    'account': payable_account,
                    'credit': amounts['payable'],
                    'credit_in_account_currency': amounts['payable'],
                    'against': debit_account,
                    'party_type': 'Supplier',
                    'party': supplier if supplier else None,
                    'remarks': f'Payable to consignor {consignor} from {doc.name}'
                })
            )

    # Make GL entries
    if gl_entries:
        # Cancel existing GL entries for this invoice (if any)
        frappe.db.sql("""
            DELETE FROM `tabGL Entry`
            WHERE voucher_type = %s AND voucher_no = %s
            AND account IN (%s, %s)
        """, (doc.doctype, doc.name, commission_account, payable_account))

        # Create new GL entries
        make_gl_entries(gl_entries, cancel=False, adv_adj=False)

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

            # Update contract item status back to Active
            contract = frappe.db.get_value('Item', item.item_code, 'consignment_contract')
            if contract:
                frappe.db.sql("""
                    UPDATE `tabConsignment Contract Item`
                    SET status = 'Active',
                        sale_date = NULL,
                        sale_price = NULL,
                        actual_commission = NULL
                    WHERE parent = %s AND item_code = %s
                """, (contract, item.item_code))

    # Cancel GL entries
    cancel_consignment_gl_entries(doc)

def cancel_consignment_gl_entries(doc):
    """Cancel GL entries for consignment items"""
    company = doc.company

    # Get GL accounts
    commission_account = frappe.db.get_value('Account', {
        'account_name': 'Commission Income',
        'company': company
    })

    payable_account = frappe.db.get_value('Account', {
        'account_name': 'Consignment Payable',
        'company': company
    })

    # Delete GL entries
    if commission_account and payable_account:
        frappe.db.sql("""
            DELETE FROM `tabGL Entry`
            WHERE voucher_type = %s AND voucher_no = %s
            AND account IN (%s, %s)
        """, (doc.doctype, doc.name, commission_account, payable_account))

def update_contract_item_status(contract_name, item_code, sale_price, commission):
    """Update contract item when sold"""
    frappe.db.sql("""
        UPDATE `tabConsignment Contract Item`
        SET status = 'Sold',
            sale_date = %s,
            sale_price = %s,
            actual_commission = %s
        WHERE parent = %s AND item_code = %s
    """, (nowdate(), sale_price, commission, contract_name, item_code))

    # Update contract totals
    contract = frappe.get_doc('Consignment Contract', contract_name)
    actual_sales = sum(flt(item.sale_price) for item in contract.items if item.sale_price)
    actual_commission = sum(flt(item.actual_commission) for item in contract.items if item.actual_commission)

    contract.db_set('actual_sales', actual_sales)
    contract.db_set('actual_commission', actual_commission)

def update_consignor_stats(consignor):
    """Update consignor statistics"""
    stats = frappe.db.sql("""
        SELECT
            COUNT(DISTINCT CASE WHEN consignment_status = 'On Consignment' THEN name END) as active,
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

# Daily scheduled task for contract management
@frappe.whitelist()
def check_contracts_daily():
    """Check and update contract statuses daily"""
    today = nowdate()

    # Mark expired contracts
    frappe.db.sql("""
        UPDATE `tabConsignment Contract`
        SET contract_status = 'Expired'
        WHERE contract_status = 'Active'
        AND contract_end_date <= %s
    """, today)

    # Mark contracts awaiting pickup
    frappe.db.sql("""
        UPDATE `tabConsignment Contract`
        SET contract_status = 'Awaiting Pickup'
        WHERE contract_status = 'Expired'
        AND ownership_transfer_date > %s
    """, today)

    # Get contracts ready for ownership transfer
    contracts_to_transfer = frappe.db.sql("""
        SELECT name
        FROM `tabConsignment Contract`
        WHERE contract_status = 'Awaiting Pickup'
        AND ownership_transfer_date <= %s
    """, today, pluck='name')

    # Process ownership transfers
    for contract_name in contracts_to_transfer:
        try:
            contract = frappe.get_doc('Consignment Contract', contract_name)
            contract.process_ownership_transfer()
            frappe.db.commit()
        except Exception as e:
            frappe.log_error(f"Failed to transfer ownership for {contract_name}: {str(e)}")
