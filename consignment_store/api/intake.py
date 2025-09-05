# consignment_store/api/intake.py
"""
Updated intake process with digital signature support
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
def process_intake(consignor, items, contract_duration=60, grace_period=14):
    """
    Process consignment intake with digital contract
    Creates contract and sends for digital signature
    """
    if isinstance(items, str):
        items = json.loads(items)

    if not items:
        frappe.throw(_("No items to process"))

    # Validate consignor has email for digital signature
    consignor_doc = frappe.get_doc('Consignor', consignor)
    if not consignor_doc.email:
        frappe.throw(_("Consignor email is required for digital signature"))

    # Create Consignment Contract
    contract = frappe.new_doc('Consignment Contract')
    contract.consignor = consignor
    contract.contract_date = nowdate()
    contract.contract_duration_days = int(contract_duration)
    contract.grace_period_days = int(grace_period)
    contract.contract_status = 'Pending Signature'

    created_items = []

    # Create items WITHOUT stock value (not our inventory yet)
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

    # Insert and submit contract to trigger signature request
    contract.insert()
    contract.submit()  # This will send the signature email

    # Generate labels for printing
    from consignment_store.utils.qr_generator import QRGenerator
    qr_gen = QRGenerator()
    labels_html = qr_gen.generate_batch_labels(created_items)

    # Generate preview HTML
    preview_html = generate_contract_preview(contract, created_items)

    return {
        'success': True,
        'contract_id': contract.name,
        'items_count': len(created_items),
        'labels_html': labels_html,
        'preview_html': preview_html,
        'signature_sent': True,
        'consignor_email': consignor_doc.email
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
    item.item_name = item_data.get('description', '')
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
    item.consignment_status = 'Pending Signature'

    # Item details
    item.brand = item_data.get('brand', '')
    item.standard_rate = flt(item_data.get('price', 0))

    # Custom fields if they exist
    if item_data.get('size'):
        item.size = item_data.get('size')
    if item_data.get('color'):
        item.color = item_data.get('color')
    if item_data.get('condition'):
        item.condition = item_data.get('condition')

    item.insert()

    return item

def generate_contract_preview(contract, items):
    """Generate preview HTML for contract confirmation"""
    consignor = frappe.get_doc('Consignor', contract.consignor)
    company = frappe.db.get_single_value('Global Defaults', 'default_company')

    items_rows = ''
    for item in items:
        items_rows += f"""
        <tr>
            <td>{item.item_code}</td>
            <td>{item.item_name}</td>
            <td class="text-right">€{item.standard_rate:.2f}</td>
            <td class="text-center">{item.commission_rate}%</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {{ size: A4; margin: 15mm; }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }}
            .success-header {{
                background: linear-gradient(135deg, #98FB98 0%, #87CEEB 100%);
                color: white;
                padding: 30px;
                border-radius: 15px;
                text-align: center;
                margin-bottom: 30px;
            }}
            .success-icon {{
                font-size: 60px;
                margin-bottom: 20px;
            }}
            h1 {{
                margin: 0;
                font-size: 28pt;
            }}
            .info-card {{
                background: #F8F9FA;
                border-radius: 10px;
                padding: 20px;
                margin-bottom: 20px;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 20px 0;
            }}
            .info-item {{
                padding: 15px;
                background: white;
                border-radius: 8px;
                border-left: 4px solid #DDA0DD;
            }}
            .info-label {{
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }}
            .info-value {{
                font-size: 20px;
                font-weight: 600;
                color: #333;
                margin-top: 5px;
            }}
            .items-table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                border-radius: 10px;
                overflow: hidden;
                margin: 20px 0;
            }}
            .items-table th {{
                background: #E6E6FA;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                color: #666;
            }}
            .items-table td {{
                padding: 12px;
                border-top: 1px solid #F0F0F0;
            }}
            .text-right {{ text-align: right; }}
            .text-center {{ text-align: center; }}
            .next-steps {{
                background: linear-gradient(135deg, #FFB6C1 0%, #FFDAB9 100%);
                border-radius: 10px;
                padding: 25px;
                margin: 30px 0;
                color: #333;
            }}
            .next-steps h3 {{
                margin-top: 0;
                color: #C71585;
            }}
            .next-steps ol {{
                margin: 10px 0;
                padding-left: 20px;
            }}
            .next-steps li {{
                margin: 8px 0;
            }}
            .signature-notice {{
                background: #FFF3E0;
                border: 2px solid #FFB300;
                border-radius: 10px;
                padding: 20px;
                text-align: center;
                margin: 30px 0;
            }}
            .signature-notice-icon {{
                font-size: 40px;
                margin-bottom: 10px;
            }}
            .signature-notice-text {{
                font-size: 18px;
                font-weight: 600;
                color: #E65100;
                margin-bottom: 10px;
            }}
            .signature-notice-email {{
                color: #666;
                font-size: 14px;
            }}
            .print-button {{
                background: linear-gradient(135deg, #87CEEB 0%, #B0E0E6 100%);
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 25px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                margin: 20px auto;
                display: block;
                box-shadow: 0 5px 15px rgba(135, 206, 235, 0.3);
            }}
            .print-button:hover {{
                box-shadow: 0 8px 20px rgba(135, 206, 235, 0.4);
            }}
            @media print {{
                .no-print {{ display: none; }}
                body {{ margin: 0; }}
            }}
        </style>
    </head>
    <body>
        <div class="success-header">
            <div class="success-icon">✅</div>
            <h1>Contract Created Successfully!</h1>
            <p style="font-size: 18px; margin: 10px 0 0 0;">Contract #{contract.name}</p>
        </div>

        <div class="signature-notice">
            <div class="signature-notice-icon">✉️</div>
            <div class="signature-notice-text">Digital Signature Request Sent</div>
            <div class="signature-notice-email">
                An email has been sent to <strong>{consignor.email}</strong> with a link to digitally sign this contract.
            </div>
        </div>

        <div class="info-card">
            <h2 style="color: #7B68EE; margin-top: 0;">Contract Summary</h2>

            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Consignor</div>
                    <div class="info-value">{consignor.consignor_name}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Code</div>
                    <div class="info-value">{consignor.consignor_code}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Contract Period</div>
                    <div class="info-value">{contract.contract_duration_days} days</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Grace Period</div>
                    <div class="info-value">{contract.grace_period_days} days</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Total Items</div>
                    <div class="info-value">{contract.total_items}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Total Value</div>
                    <div class="info-value">€{contract.total_retail_value:.2f}</div>
                </div>
            </div>
        </div>

        <div class="info-card">
            <h3 style="color: #7B68EE;">Consigned Items</h3>
            <table class="items-table">
                <thead>
                    <tr>
                        <th>Item Code</th>
                        <th>Description</th>
                        <th>Retail Price</th>
                        <th>Commission</th>
                    </tr>
                </thead>
                <tbody>
                    {items_rows}
                </tbody>
            </table>
        </div>

        <div class="next-steps">
            <h3>📋 Next Steps</h3>
            <ol>
                <li><strong>Consignor signs contract:</strong> Check email for signature link</li>
                <li><strong>Print labels:</strong> Use the label printing function to tag items</li>
                <li><strong>Display items:</strong> Place items on the sales floor</li>
                <li><strong>Track in portal:</strong> Monitor sales and performance online</li>
            </ol>
        </div>

        <div style="text-align: center; margin: 40px 0;">
            <button onclick="window.print()" class="print-button no-print">
                🖨️ Print This Summary
            </button>
        </div>
    </body>
    </html>
    """

    return html

@frappe.whitelist()
def resend_signature_request(contract_name):
    """Resend signature request email for a contract"""
    contract = frappe.get_doc('Consignment Contract', contract_name)

    if contract.consignor_signed:
        frappe.throw(_("Contract has already been signed"))

    if contract.docstatus != 1:
        frappe.throw(_("Contract must be submitted before sending signature request"))

    # Send signature request
    contract.send_signature_request()

    return {
        'success': True,
        'message': f'Signature request sent to {frappe.db.get_value("Consignor", contract.consignor, "email")}'
    }

@frappe.whitelist()
def get_unsigned_contracts(consignor=None):
    """Get list of contracts pending signature"""
    filters = {
        'docstatus': 1,
        'consignor_signed': 0
    }

    if consignor:
        filters['consignor'] = consignor

    contracts = frappe.db.get_all('Consignment Contract',
        filters=filters,
        fields=['name', 'consignor', 'contract_date', 'total_items',
                'total_retail_value', 'signature_token'],
        order_by='contract_date desc'
    )

    # Add consignor details
    for contract in contracts:
        contract['consignor_details'] = frappe.db.get_value('Consignor',
            contract['consignor'],
            ['consignor_name', 'email', 'phone'],
            as_dict=True
        )

    return contracts

@frappe.whitelist()
def batch_create_items(consignor, item_data_list):
    """Create multiple items in batch for a consignor"""
    if isinstance(item_data_list, str):
        item_data_list = json.loads(item_data_list)

    created_items = []

    for item_data in item_data_list:
        try:
            item = create_consignment_item(consignor, item_data)
            created_items.append({
                'success': True,
                'item_code': item.name,
                'item_name': item.item_name
            })
        except Exception as e:
            created_items.append({
                'success': False,
                'error': str(e),
                'item_data': item_data
            })

    return {
        'total': len(item_data_list),
        'successful': len([i for i in created_items if i.get('success')]),
        'failed': len([i for i in created_items if not i.get('success')]),
        'items': created_items
    }

@frappe.whitelist()
def get_intake_statistics(days=30):
    """Get intake statistics for dashboard"""
    from_date = add_days(nowdate(), -days)

    stats = {
        'contracts_created': frappe.db.count('Consignment Contract', {
            'contract_date': ['>=', from_date]
        }),
        'contracts_pending_signature': frappe.db.count('Consignment Contract', {
            'docstatus': 1,
            'consignor_signed': 0
        }),
        'items_added': frappe.db.count('Item', {
            'creation': ['>=', from_date],
            'is_consignment': 1
        }),
        'new_consignors': frappe.db.count('Consignor', {
            'registration_date': ['>=', from_date]
        })
    }

    # Get daily intake trend
    daily_trend = frappe.db.sql("""
        SELECT
            DATE(contract_date) as date,
            COUNT(*) as contracts,
            SUM(total_items) as items,
            SUM(total_retail_value) as value
        FROM `tabConsignment Contract`
        WHERE contract_date >= %s
        GROUP BY DATE(contract_date)
        ORDER BY date
    """, from_date, as_dict=True)

    stats['daily_trend'] = daily_trend

    # Get top consignors by items
    top_consignors = frappe.db.sql("""
        SELECT
            c.consignor_name,
            c.consignor_code,
            COUNT(i.name) as item_count,
            SUM(i.standard_rate) as total_value
        FROM `tabConsignor` c
        JOIN `tabItem` i ON i.consignor = c.name
        WHERE i.creation >= %s
        AND i.is_consignment = 1
        GROUP BY c.name
        ORDER BY item_count DESC
        LIMIT 10
    """, from_date, as_dict=True)

    stats['top_consignors'] = top_consignors

    return stats

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
