# consignment_store/utils/notifications.py
import frappe
from frappe import _
from frappe.utils import nowdate, add_days

def notify_items_sold(doc, method=None):
    """Send notification when items are sold"""
    for item in doc.items:
        if item.is_consignment:
            consignor = frappe.get_doc('Consignor', item.consignor)

            if consignor.email:
                frappe.sendmail(
                    recipients=[consignor.email],
                    subject=f"Item Sold: {item.item_name}",
                    message=f"""
                    <p>Dear {consignor.consignor_name},</p>
                    <p>Great news! Your item has been sold:</p>
                    <ul>
                        <li>Item: {item.item_name}</li>
                        <li>Sale Price: ${item.amount:.2f}</li>
                        <li>Your Commission ({item.commission_rate}%): ${item.amount * item.commission_rate / 100:.2f}</li>
                    </ul>
                    <p>This amount will be included in your next payout.</p>
                    <p>View your dashboard: {frappe.utils.get_url()}/seller-portal</p>
                    """
                )

def send_intake_confirmation(consignor, items):
    """Send confirmation after intake"""
    consignor_doc = frappe.get_doc('Consignor', consignor)

    if not consignor_doc.email:
        return

    items_html = '<ul>'
    for item in items:
        items_html += f'<li>{item.item_name} - ${item.standard_rate:.2f}</li>'
    items_html += '</ul>'

    frappe.sendmail(
        recipients=[consignor_doc.email],
        subject=f"Consignment Receipt - {len(items)} items",
        message=f"""
        <p>Dear {consignor_doc.consignor_name},</p>
        <p>We've received the following items for consignment:</p>
        {items_html}
        <p>Track your items at: {frappe.utils.get_url()}/seller-portal</p>
        <p>Your access code: {consignor_doc.consignor_code}</p>
        """
    )

def check_expiring_items():
    """Daily task to check expiring items"""
    expiring = frappe.db.sql("""
        SELECT
            i.name, i.item_name, i.consignor, i.consignment_expiry_date,
            c.email, c.consignor_name
        FROM `tabItem` i
        JOIN `tabConsignor` c ON c.name = i.consignor
        WHERE i.is_consignment = 1
        AND i.consignment_status = 'Active'
        AND i.consignment_expiry_date = %s
    """, add_days(nowdate(), 7), as_dict=True)

    # Group by consignor
    by_consignor = {}
    for item in expiring:
        if item.consignor not in by_consignor:
            by_consignor[item.consignor] = {
                'email': item.email,
                'name': item.consignor_name,
                'items': []
            }
        by_consignor[item.consignor]['items'].append(item)

    # Send notifications
    for consignor, data in by_consignor.items():
        if data['email']:
            items_list = '<ul>'
            for item in data['items']:
                items_list += f'<li>{item.item_name} - Expires {item.consignment_expiry_date}</li>'
            items_list += '</ul>'

            frappe.sendmail(
                recipients=[data['email']],
                subject="Items Expiring Soon",
                message=f"""
                <p>Dear {data['name']},</p>
                <p>The following items will expire in 7 days:</p>
                {items_list}
                <p>Please contact us if you'd like to extend or collect these items.</p>
                """
            )

def send_daily_summary():
    """Send daily sales summary to consignors who had sales"""
    yesterday = add_days(nowdate(), -1)

    sales = frappe.db.sql("""
        SELECT
            ce.consignor,
            c.consignor_name,
            c.email,
            COUNT(*) as items_sold,
            SUM(ce.sale_amount) as total_sales,
            SUM(ce.commission_amount) as total_commission
        FROM `tabCommission Entry` ce
        JOIN `tabConsignor` c ON c.name = ce.consignor
        WHERE DATE(ce.posting_date) = %s
        GROUP BY ce.consignor
    """, yesterday, as_dict=True)

    for sale in sales:
        if sale.email:
            frappe.sendmail(
                recipients=[sale.email],
                subject=f"Daily Sales Summary - {yesterday}",
                message=f"""
                <p>Dear {sale.consignor_name},</p>
                <p>Yesterday's sales summary:</p>
                <ul>
                    <li>Items Sold: {sale.items_sold}</li>
                    <li>Total Sales: ${sale.total_sales:.2f}</li>
                    <li>Your Earnings: ${sale.total_commission:.2f}</li>
                </ul>
                <p>View details at: {frappe.utils.get_url()}/seller-portal</p>
                """
            )
