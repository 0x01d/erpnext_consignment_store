# consignment_store/install.py
"""
Complete installation script with GL accounts and proper DocTypes
Replace your existing install.py with this
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Run after app installation"""
    create_custom_fields(get_custom_fields())
    create_gl_accounts()  # NEW: Auto-create GL accounts
    create_default_settings()
    create_workspace()
    frappe.db.commit()

def get_custom_fields():
    """Extended custom fields for proper consignment handling"""
    return {
        "Item": [
            dict(
                fieldname='consignment_section',
                label='Consignment',
                fieldtype='Section Break',
                insert_after='stock_section'
            ),
            dict(
                fieldname='is_consignment',
                label='Is Consignment',
                fieldtype='Check',
                insert_after='consignment_section'
            ),
            dict(
                fieldname='consignor',
                label='Consignor',
                fieldtype='Link',
                options='Consignor',
                depends_on='is_consignment',
                insert_after='is_consignment'
            ),
            dict(
                fieldname='consignment_code',
                label='Consignment Code',
                fieldtype='Data',
                unique=1,
                depends_on='is_consignment',
                insert_after='consignor'
            ),
            dict(
                fieldname='commission_rate',
                label='Commission %',
                fieldtype='Percent',
                depends_on='is_consignment',
                insert_after='consignment_code'
            ),
            dict(
                fieldname='consignment_contract',
                label='Consignment Contract',
                fieldtype='Link',
                options='Consignment Contract',
                depends_on='is_consignment',
                read_only=1,
                insert_after='commission_rate'
            ),
            dict(
                fieldname='consignment_expiry_date',
                label='Contract Expiry Date',
                fieldtype='Date',
                depends_on='is_consignment',
                insert_after='consignment_contract'
            ),
            dict(
                fieldname='ownership_transfer_date',
                label='Ownership Transfer Date',
                fieldtype='Date',
                depends_on='is_consignment',
                insert_after='consignment_expiry_date'
            ),
            dict(
                fieldname='consignment_status',
                label='Status',
                fieldtype='Select',
                options='On Consignment\nAwaiting Pickup\nOwned\nSold\nReturned',
                default='On Consignment',
                depends_on='is_consignment',
                insert_after='ownership_transfer_date'
            ),
            dict(
                fieldname='qr_code_data',
                label='QR Code',
                fieldtype='Text',
                hidden=1
            )
        ],
        "Sales Invoice Item": [
            dict(
                fieldname='is_consignment',
                label='Is Consignment',
                fieldtype='Check',
                read_only=1
            ),
            dict(
                fieldname='consignor',
                label='Consignor',
                fieldtype='Link',
                options='Consignor',
                read_only=1
            ),
            dict(
                fieldname='commission_rate',
                label='Commission %',
                fieldtype='Percent',
                read_only=1
            ),
            dict(
                fieldname='commission_amount',
                label='Commission',
                fieldtype='Currency',
                read_only=1
            ),
            dict(
                fieldname='consignor_amount',
                label='Consignor Amount',
                fieldtype='Currency',
                read_only=1
            )
        ],
        "POS Invoice Item": [
            dict(
                fieldname='is_consignment',
                label='Is Consignment',
                fieldtype='Check',
                read_only=1
            ),
            dict(
                fieldname='consignor',
                label='Consignor',
                fieldtype='Link',
                options='Consignor',
                read_only=1
            ),
            dict(
                fieldname='commission_rate',
                label='Commission %',
                fieldtype='Percent',
                read_only=1
            ),
            dict(
                fieldname='commission_amount',
                label='Commission',
                fieldtype='Currency',
                read_only=1
            ),
            dict(
                fieldname='consignor_amount',
                label='Consignor Amount',
                fieldtype='Currency',
                read_only=1
            )
        ],
        "Supplier": [
            dict(
                fieldname='is_consignor',
                label='Is Consignor',
                fieldtype='Check',
                insert_after='supplier_name'
            )
        ]
    }

def create_gl_accounts():
    """Create required GL accounts for consignment"""
    company = frappe.db.get_single_value('Global Defaults', 'default_company')
    if not company:
        print("⚠ No default company found, skipping GL account creation")
        return

    accounts_to_create = [
        {
            'account_name': 'Consignment Payable',
            'parent_account': 'Current Liabilities',
            'account_type': 'Payable',
            'root_type': 'Liability'
        },
        {
            'account_name': 'Commission Income',
            'parent_account': 'Direct Income',
            'account_type': 'Income Account',
            'root_type': 'Income'
        },
        {
            'account_name': 'Consignment Inventory (Memo)',
            'parent_account': 'Current Assets',
            'account_type': '',
            'root_type': 'Asset',
            'is_group': 0,
            'description': 'Memo account for tracking consignment items (not on balance sheet)'
        }
    ]

    for acc in accounts_to_create:
        account_name = f"{acc['account_name']} - {frappe.db.get_value('Company', company, 'abbr')}"

        if not frappe.db.exists('Account', {'account_name': acc['account_name'], 'company': company}):
            try:
                # Find parent account
                parent = frappe.db.get_value('Account', {
                    'account_name': acc['parent_account'],
                    'company': company,
                    'is_group': 1
                })

                if parent:
                    account = frappe.new_doc('Account')
                    account.account_name = acc['account_name']
                    account.parent_account = parent
                    account.company = company
                    account.account_type = acc.get('account_type', '')
                    account.root_type = acc['root_type']
                    account.is_group = acc.get('is_group', 0)
                    account.insert(ignore_permissions=True)
                    print(f"✓ Created GL Account: {acc['account_name']}")
                else:
                    print(f"⚠ Parent account {acc['parent_account']} not found")

            except Exception as e:
                print(f"⚠ Error creating account {acc['account_name']}: {str(e)}")

def create_default_settings():
    """Create default settings"""
    # Create item group
    if not frappe.db.exists('Item Group', 'Consignment'):
        doc = frappe.new_doc('Item Group')
        doc.item_group_name = 'Consignment'
        doc.parent_item_group = 'All Item Groups'
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Created Consignment item group")

    # Create clearance item group
    if not frappe.db.exists('Item Group', 'Clearance'):
        doc = frappe.new_doc('Item Group')
        doc.item_group_name = 'Clearance'
        doc.parent_item_group = 'All Item Groups'
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Created Clearance item group")

    # Create supplier group
    if not frappe.db.exists('Supplier Group', 'Individual Consignor'):
        doc = frappe.new_doc('Supplier Group')
        doc.supplier_group_name = 'Individual Consignor'
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Created Individual Consignor supplier group")

    # Create warehouse for consignment (virtual, no stock value)
    if not frappe.db.exists('Warehouse', {'warehouse_name': 'Consignment Area'}):
        company = frappe.db.get_single_value('Global Defaults', 'default_company')
        if company:
            warehouse = frappe.new_doc('Warehouse')
            warehouse.warehouse_name = 'Consignment Area'
            warehouse.parent_warehouse = f'All Warehouses - {frappe.db.get_value("Company", company, "abbr")}'
            warehouse.company = company
            warehouse.insert(ignore_permissions=True)
            frappe.db.commit()
            print("✓ Created Consignment Area warehouse")

def create_workspace():
    """Create or update workspace"""
    try:
        if frappe.db.exists("Workspace", "Consignment Store"):
            workspace = frappe.get_doc("Workspace", "Consignment Store")
        else:
            workspace = frappe.new_doc("Workspace")
            workspace.name = "Consignment Store"

        workspace.title = "Consignment Store"
        workspace.label = "Consignment Store"
        workspace.module = "Consignment Store"
        workspace.icon = "package"
        workspace.is_hidden = 0
        workspace.public = 1

        workspace.content = """[{
            "id": "header_main",
            "type": "header",
            "data": {"text": "<span class='h4'>Consignment Store</span>", "col": 12}
        }, {
            "id": "shortcut_consignor",
            "type": "shortcut",
            "data": {"shortcut_name": "Consignor", "col": 3}
        }, {
            "id": "shortcut_contract",
            "type": "shortcut",
            "data": {"shortcut_name": "Consignment Contract", "col": 3}
        }, {
            "id": "shortcut_commission",
            "type": "shortcut",
            "data": {"shortcut_name": "Commission Entry", "col": 3}
        }, {
            "id": "shortcut_payout",
            "type": "shortcut",
            "data": {"shortcut_name": "Consignment Payout", "col": 3}
        }, {
            "id": "header_tools",
            "type": "header",
            "data": {"text": "<span class='h4'>Tools</span>", "col": 12}
        }, {
            "id": "shortcut_intake",
            "type": "shortcut",
            "data": {"shortcut_name": "Quick Intake", "col": 3}
        }]"""

        workspace.shortcuts = []
        shortcuts = [
            {
                "label": "Consignor",
                "link_to": "Consignor",
                "type": "DocType",
                "color": "Green",
                "doc_view": "List"
            },
            {
                "label": "Consignment Contract",
                "link_to": "Consignment Contract",
                "type": "DocType",
                "color": "Blue",
                "doc_view": "List"
            },
            {
                "label": "Commission Entry",
                "link_to": "Commission Entry",
                "type": "DocType",
                "color": "Orange",
                "doc_view": "List"
            },
            {
                "label": "Consignment Payout",
                "link_to": "Consignment Payout",
                "type": "DocType",
                "color": "Red",
                "doc_view": "List"
            },
            {
                "label": "Quick Intake",
                "link_to": "quick-intake",
                "type": "Page",
                "color": "Teal"
            }
        ]

        for shortcut in shortcuts:
            workspace.append("shortcuts", shortcut)

        if workspace.is_new():
            workspace.insert(ignore_permissions=True)
            print("✓ Created Consignment Store workspace")
        else:
            workspace.save(ignore_permissions=True)
            print("✓ Updated Consignment Store workspace")

        frappe.db.commit()

    except Exception as e:
        print(f"⚠ Error creating workspace: {str(e)}")
