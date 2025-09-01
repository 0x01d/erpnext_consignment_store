# consignment_store/install.py
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def after_install():
    """Run after app installation"""
    create_custom_fields(get_custom_fields())
    create_default_settings()
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
        doc.insert()

    # Create supplier group
    if not frappe.db.exists('Supplier Group', 'Individual Consignor'):
        doc = frappe.new_doc('Supplier Group')
        doc.supplier_group_name = 'Individual Consignor'
        doc.insert()

    # Create role
    if not frappe.db.exists('Role', 'Consignor Portal'):
        doc = frappe.new_doc('Role')
        doc.role_name = 'Consignor Portal'
        doc.desk_access = 0
        doc.insert()
