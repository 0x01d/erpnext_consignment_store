# consignment_store/install.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Run after app installation"""
    create_custom_fields(get_custom_fields())
    create_default_settings()
    create_workspace()
    frappe.db.commit()

def get_custom_fields():
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
                fieldname='consignment_expiry_date',
                label='Expiry Date',
                fieldtype='Date',
                depends_on='is_consignment',
                insert_after='commission_rate'
            ),
            dict(
                fieldname='consignment_status',
                label='Status',
                fieldtype='Select',
                options='Active\nSold\nExpired\nReturned',
                default='Active',
                depends_on='is_consignment',
                insert_after='consignment_expiry_date'
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
                fieldtype='Data',
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
                fieldtype='Data',
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

    # Create supplier group
    if not frappe.db.exists('Supplier Group', 'Individual Consignor'):
        doc = frappe.new_doc('Supplier Group')
        doc.supplier_group_name = 'Individual Consignor'
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Created Individual Consignor supplier group")

    # Create role if not exists
    if not frappe.db.exists('Role', 'Consignor Portal'):
        doc = frappe.new_doc('Role')
        doc.role_name = 'Consignor Portal'
        doc.desk_access = 0
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Created Consignor Portal role")

def create_workspace():
    """Create or update workspace"""
    try:
        # Check if workspace exists
        if frappe.db.exists("Workspace", "Consignment Store"):
            workspace = frappe.get_doc("Workspace", "Consignment Store")
            print("✓ Found existing Consignment Store workspace")
        else:
            # Create new workspace
            workspace = frappe.new_doc("Workspace")
            workspace.name = "Consignment Store"

        # Set workspace properties
        workspace.title = "Consignment Store"  # This was missing!
        workspace.label = "Consignment Store"
        workspace.module = "Consignment Store"
        workspace.icon = "package"
        workspace.is_hidden = 0
        workspace.public = 1
        workspace.extends_another_page = 0
        workspace.is_default = 0
        workspace.indicator_color = "green"

        # Set content with shortcuts
        workspace.content = """[{
            "id": "header_main",
            "type": "header",
            "data": {"text": "<span class='h4'>Consignment Store</span>", "col": 12}
        }, {
            "id": "shortcut_consignor",
            "type": "shortcut",
            "data": {"shortcut_name": "Consignor", "col": 3}
        }, {
            "id": "shortcut_batch",
            "type": "shortcut",
            "data": {"shortcut_name": "Consignment Batch", "col": 3}
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

        # Clear and add shortcuts
        workspace.shortcuts = []

        shortcuts = [
            {
                "label": "Consignor",
                "link_to": "Consignor",
                "type": "DocType",
                "color": "Green",
                "doc_view": "List",
                "is_query_report": 0
            },
            {
                "label": "Consignment Batch",
                "link_to": "Consignment Batch",
                "type": "DocType",
                "color": "Blue",
                "doc_view": "List",
                "is_query_report": 0
            },
            {
                "label": "Commission Entry",
                "link_to": "Commission Entry",
                "type": "DocType",
                "color": "Orange",
                "doc_view": "List",
                "is_query_report": 0
            },
            {
                "label": "Consignment Payout",
                "link_to": "Consignment Payout",
                "type": "DocType",
                "color": "Red",
                "doc_view": "List",
                "is_query_report": 0
            },
            {
                "label": "Quick Intake",
                "link_to": "quick-intake",
                "type": "Page",
                "color": "Teal",
                "doc_view": "",
                "is_query_report": 0
            }
        ]

        for shortcut in shortcuts:
            workspace.append("shortcuts", shortcut)

        # Save workspace
        if workspace.is_new():
            workspace.insert(ignore_permissions=True)
            print("✓ Created Consignment Store workspace")
        else:
            workspace.save(ignore_permissions=True)
            print("✓ Updated Consignment Store workspace")

        frappe.db.commit()

    except Exception as e:
        print(f"⚠ Error creating workspace: {str(e)}")
        print("You may need to create the workspace manually in ERPNext")

def fix_page_permissions():
    """Fix permissions for Quick Intake page"""
    try:
        if frappe.db.exists("Page", "quick-intake"):
            page = frappe.get_doc("Page", "quick-intake")

            # Clear existing roles
            page.roles = []

            # Add required roles
            roles = ["System Manager", "Sales User", "Sales Manager", "Stock User"]
            for role in roles:
                if frappe.db.exists("Role", role):
                    page.append("roles", {"role": role})

            page.save(ignore_permissions=True)
            frappe.db.commit()
            print("✓ Fixed Quick Intake page permissions")

    except Exception as e:
        print(f"⚠ Error fixing page permissions: {str(e)}")

# Optional: Add a function to be called manually if needed
def execute_fixes():
    """Execute all fixes - can be called manually"""
    print("\n🔧 Running Consignment Store fixes...\n")

    # Clear cache first
    frappe.clear_cache()

    # Run all setup functions
    create_custom_fields(get_custom_fields())
    create_default_settings()
    create_workspace()
    fix_page_permissions()

    # Commit all changes
    frappe.db.commit()

    print("\n✅ All fixes applied successfully!")
    print("\nNext steps:")
    print("1. Run: bench --site yoursite.local clear-cache")
    print("2. Run: bench build --app consignment_store")
    print("3. Run: bench restart")
    print("4. Clear browser cache (Ctrl+Shift+R)")
    print("5. Navigate to: /app/consignment-store")
    print("6. For Quick Intake: /app/quick-intake")

    return "Success"
