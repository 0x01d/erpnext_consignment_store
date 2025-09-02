# consignment_store/api/intake.py
"""
Fixed intake process that creates contracts and doesn't affect stock value
Replace your existing intake.py with this
"""
import frappe
from frappe import _
from frappe.utils import nowdate, add_days, cint, flt
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
    """
    Process consignment intake with contract creation
    NO STOCK ENTRIES - items are not our inventory yet
    """
    if isinstance(items, str):
        items = json.loads(items)

    if not items:
        frappe.throw(_("No items to process"))

    # Create Consignment Contract
    contract = frappe.new_doc('Consignment Contract')
    contract.consignor = consignor
    contract.contract_date = nowdate()
    contract.contract_duration_days = 60  # 2 months default
    contract.grace_period_days = 14  # 2 weeks grace

    created_items = []

    # Create items WITHOUT stock value
    for item_data in items:
        item = create_consignment_item(consignor, item_data)
        created_items.append(item)

        # Add to contract
        contract.append('items', {
            'item_code': item.name,
            'item_name': item.item_name,
            'retail_price': item.standard_rate,
            'commission_rate': item.commission_rate,
            'status': 'Active'
        })

    # Submit contract
    contract.insert()
    contract.submit()

    # Generate labels
    from consignment_store.utils.qr_generator import QRGenerator
    qr_gen = QRGenerator()
    labels_html = qr_gen.generate_batch_labels(created_items)

    # Generate contract for signing
    contract_html = generate_contract_html(contract, created_items)

    # Send notification (optional)
    # from consignment_store.utils.notifications import send_intake_confirmation
    # send_intake_confirmation(consignor, created_items)

    return {
        'success': True,
        'contract_id': contract.name,
        'items_count': len(created_items),
        'labels_html': labels_html,
        'contract_html': contract_html
    }

def create_consignment_item(consignor, item_data):
    """
    Create a consignment item WITHOUT stock value
    Item is NOT stock item until we own it
    """
    # Generate item code
    consignor_code = frappe.db.get_value('Consignor', consignor, 'consignor_code')
    count = frappe.db.count('Item', {'consignor': consignor}) + 1
    item_code = f"{consignor_code}-{str(count).zfill(5)}"

    item = frappe.new_doc('Item')
    item.item_code = item_code
    item.item_name = item_data.get('description')
    item.item_group = 'Consignment'
    item.stock_uom = 'Nos'

    # CRITICAL: Not a stock item until we own it
    item.is_stock_item = 0  # NO STOCK VALUE
    item.maintain_stock = 0  # NO INVENTORY TRACKING

    # Consignment fields
    item.is_consignment = 1
    item.consignor = consignor
    item.consignment_code = item_code
    item.commission_rate = flt(item_data.get('commission_rate', 50))
    item.consignment_status = 'On Consignment'
    item.consignment_expiry_date = add_days(nowdate(), 60)
    item.ownership_transfer_date = add_days(nowdate(), 74)

    # Item details
    item.brand = item_data.get('brand', '')
    item.standard_rate = flt(item_data.get('price', 0))

    # Custom fields
    custom_fields = {}
    if item_data.get('size'):
        custom_fields['size'] = item_data.get('size')
    if item_data.get('color'):
        custom_fields['color'] = item_data.get('color')
    if item_data.get('condition'):
        custom_fields['condition'] = item_data.get('condition')

    item.insert()

    # Set custom fields after insert
    if custom_fields:
        for field, value in custom_fields.items():
            frappe.db.set_value('Item', item.name, field, value)

    return item

def generate_contract_html(contract, items):
    """Generate printable contract HTML"""
    consignor = frappe.get_doc('Consignor', contract.consignor)
    company = frappe.db.get_single_value('Global Defaults', 'default_company')

    items_rows = ''
    for item in items:
        items_rows += f"""
        <tr>
            <td>{item.item_code}</td>
            <td>{item.item_name}</td>
            <td style="text-align: right;">€{item.standard_rate:.2f}</td>
            <td style="text-align: center;">{item.commission_rate}%</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{
                font-family: 'Segoe UI', Arial, sans-serif;
                line-height: 1.6;
                color: #333;
            }}
            .header {{
                text-align: center;
                border-bottom: 2px solid #333;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }}
            h1 {{
                margin: 0;
                font-size: 24pt;
                color: #000;
            }}
            .contract-info {{
                text-align: center;
                margin: 10px 0;
                font-size: 11pt;
            }}
            .parties {{
                display: flex;
                justify-content: space-between;
                margin: 30px 0;
                padding: 20px;
                background: #f9f9f9;
                border-radius: 8px;
            }}
            .party {{
                width: 45%;
            }}
            .party h3 {{
                margin-top: 0;
                color: #444;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }}
            th {{
                background: #444;
                color: white;
                padding: 10px;
                text-align: left;
            }}
            td {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
            tr:nth-child(even) {{
                background: #f9f9f9;
            }}
            .totals {{
                background: #e9e9e9;
                font-weight: bold;
            }}
            .terms {{
                margin: 30px 0;
                padding: 20px;
                background: #f0f8ff;
                border-radius: 8px;
                border: 1px solid #4CAF50;
            }}
            .terms h3 {{
                color: #4CAF50;
                margin-top: 0;
            }}
            .terms ol {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .terms li {{
                margin: 8px 0;
            }}
            .signatures {{
                display: flex;
                justify-content: space-between;
                margin-top: 60px;
                page-break-inside: avoid;
            }}
            .signature {{
                width: 40%;
                text-align: center;
            }}
            .signature-line {{
                border-top: 2px solid #333;
                margin-top: 50px;
                padding-top: 10px;
            }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0; }}
            }}
            .print-button {{
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 12px 24px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 14pt;
                cursor: pointer;
                box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            }}
            .print-button:hover {{
                background: #45a049;
            }}
        </style>
    </head>
    <body>
        <button class="no-print print-button" onclick="window.print()">
            📄 Print Contract
        </button>

        <div class="header">
            <h1>CONSIGNMENT AGREEMENT</h1>
            <div class="contract-info">
                Contract No: <strong>{contract.name}</strong> |
                Date: <strong>{contract.contract_date}</strong>
            </div>
        </div>

        <div class="parties">
            <div class="party">
                <h3>CONSIGNOR</h3>
                <p>
                    <strong>{consignor.consignor_name}</strong><br>
                    Code: {consignor.consignor_code}<br>
                    Email: {consignor.email}<br>
                    Phone: {consignor.phone}<br>
                    {f'ID: {consignor.id_number}' if consignor.id_number else ''}
                </p>
            </div>
            <div class="party">
                <h3>CONSIGNEE</h3>
                <p>
                    <strong>{company or 'Your Store Name'}</strong><br>
                    [Store Address]<br>
                    [Store Phone]<br>
                    [Store Email]
                </p>
            </div>
        </div>

        <h3>CONSIGNED ITEMS</h3>
        <table>
            <thead>
                <tr>
                    <th width="20%">Item Code</th>
                    <th width="50%">Description</th>
                    <th width="15%">Retail Price</th>
                    <th width="15%">Commission</th>
                </tr>
            </thead>
            <tbody>
                {items_rows}
            </tbody>
            <tfoot>
                <tr class="totals">
                    <td colspan="2">TOTAL ({contract.total_items} items)</td>
                    <td style="text-align: right;">€{contract.total_retail_value:.2f}</td>
                    <td style="text-align: center;">€{contract.expected_commission:.2f}</td>
                </tr>
            </tfoot>
        </table>

        <div class="terms">
            <h3>TERMS AND CONDITIONS</h3>
            <ol>
                <li><strong>Consignment Period:</strong> Items will be displayed for {contract.contract_duration_days} days from {contract.contract_date} until {contract.contract_end_date}.</li>
                <li><strong>Commission:</strong> Consignee retains the agreed commission percentage on actual sale price.</li>
                <li><strong>Pricing:</strong> Items priced as agreed. Store may offer promotions with consignor notification.</li>
                <li><strong>Payment:</strong> Net proceeds paid monthly after minimum payout threshold is met.</li>
                <li><strong>Collection Period:</strong> Unsold items must be collected within {contract.grace_period_days} days after contract end ({contract.contract_end_date} to {contract.ownership_transfer_date}).</li>
                <li><strong>Ownership Transfer:</strong> Items not collected by {contract.ownership_transfer_date} automatically become property of the consignee at 30% of retail value.</li>
                <li><strong>Liability:</strong> Consignee is not liable for theft, damage from normal wear, or force majeure events.</li>
                <li><strong>Termination:</strong> Either party may terminate with 7 days written notice.</li>
            </ol>
        </div>

        <p><strong>By signing below, both parties agree to the terms and conditions stated above.</strong></p>

        <div class="signatures">
            <div class="signature">
                <div class="signature-line">
                    <strong>CONSIGNOR</strong><br>
                    {consignor.consignor_name}<br>
                    Date: _______________
                </div>
            </div>
            <div class="signature">
                <div class="signature-line">
                    <strong>CONSIGNEE</strong><br>
                    Store Representative<br>
                    Date: _______________
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    return html

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

    return []
