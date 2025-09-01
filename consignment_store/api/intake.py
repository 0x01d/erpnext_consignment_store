import frappe
from frappe import _
from frappe.utils import nowdate, cint, flt
import json

@frappe.whitelist()
def search_consignor(query):
    """Search for existing consignors"""
    if not query:
        return []

    return frappe.db.sql("""
        SELECT name, consignor_code, consignor_name, email, phone
        FROM `tabConsignor`
        WHERE (
            consignor_name LIKE %(q)s
            OR email LIKE %(q)s
            OR phone LIKE %(q)s
            OR consignor_code LIKE %(q)s
        )
        AND status = 'Active'
        LIMIT 10
    """, {'q': f'%{query}%'}, as_dict=True)

@frappe.whitelist()
def create_consignor(**kwargs):
    """Create new consignor"""
    consignor = frappe.new_doc('Consignor')
    consignor.update(kwargs)
    consignor.insert()
    return consignor

@frappe.whitelist()
def process_intake(consignor, items):
    """Process consignment intake"""
    if isinstance(items, str):
        items = json.loads(items)

    # Validate
    if not items:
        frappe.throw(_("No items to process"))

    # Create batch
    batch = frappe.new_doc('Consignment Batch')
    batch.consignor = consignor
    batch.intake_date = nowdate()

    created_items = []

    # Create items
    for item_data in items:
        item = create_consignment_item(consignor, item_data)
        created_items.append(item)

        # Add to batch
        batch.append('items', {
            'item_code': item.name,
            'item_name': item.item_name,
            'price': item.standard_rate,
            'commission_rate': item.commission_rate
        })

    batch.insert()
    batch.submit()

    # Create stock entry
    create_stock_entry(created_items)

    # Generate labels
    from consignment_store.utils.qr_generator import QRGenerator
    qr_gen = QRGenerator()
    labels_html = qr_gen.generate_batch_labels(created_items)

    # Send notification
    from consignment_store.utils.notifications import send_intake_confirmation
    send_intake_confirmation(consignor, created_items)

    return {
        'success': True,
        'batch_id': batch.name,
        'items_count': len(created_items),
        'labels_html': labels_html
    }

def create_consignment_item(consignor, item_data):
    """Create a consignment item"""
    # Generate item code
    consignor_code = frappe.db.get_value('Consignor', consignor, 'consignor_code')
    count = frappe.db.count('Item', {'consignor': consignor}) + 1
    item_code = f"{consignor_code}-{str(count).zfill(5)}"

    item = frappe.new_doc('Item')
    item.item_code = item_code
    item.item_name = item_data.get('description')
    item.item_group = 'Consignment'
    item.stock_uom = 'Nos'
    item.is_stock_item = 1

    # Consignment fields
    item.is_consignment = 1
    item.consignor = consignor
    item.consignment_code = item_code
    item.commission_rate = flt(item_data.get('commission_rate', 50))
    item.consignment_status = 'Active'
    item.consignment_expiry_date = frappe.utils.add_days(nowdate(), 60)

    # Item details
    item.brand = item_data.get('brand', '')
    item.standard_rate = flt(item_data.get('price', 0))

    # Custom fields
    if item_data.get('size'):
        item.db_set('size', item_data.get('size'), update_modified=False)
    if item_data.get('color'):
        item.db_set('color', item_data.get('color'), update_modified=False)
    if item_data.get('condition'):
        item.db_set('condition', item_data.get('condition'), update_modified=False)

    item.insert()

    return item

def create_stock_entry(items):
    """Create stock entry for consignment items"""
    if not items:
        return

    stock_entry = frappe.new_doc('Stock Entry')
    stock_entry.stock_entry_type = 'Material Receipt'

    warehouse = frappe.db.get_single_value('Stock Settings', 'default_warehouse') or 'Stores - CS'

    for item in items:
        stock_entry.append('items', {
            'item_code': item.name,
            't_warehouse': warehouse,
            'qty': 1,
            'basic_rate': item.standard_rate * 0.5  # 50% valuation
        })

    stock_entry.insert()
    stock_entry.submit()

    return stock_entry

@frappe.whitelist()
def search_with_consignment_info(search_term):
    """Enhanced search for POS that includes consignment info"""
    # Check if it's a QR code
    if search_term and (search_term.startswith('CONS-') or '-' in search_term):
        item = frappe.db.get_value('Item',
            {'consignment_code': search_term},
            ['name', 'item_name', 'standard_rate', 'consignor', 'commission_rate'],
            as_dict=True
        )

        if item:
            return [{
                'item_code': item.name,
                'item_name': f"[CONSIGNMENT] {item.item_name}",
                'rate': item.standard_rate,
                'is_consignment': 1
            }]

    # Regular search
    return []
