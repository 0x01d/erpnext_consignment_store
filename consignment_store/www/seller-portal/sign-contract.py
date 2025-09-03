# consignment_store/www/seller-portal/sign-contract.py
import frappe

def get_context(context):
    """Context for the contract signing page"""
    context.no_cache = 1
    context.show_sidebar = False

    # Get token from request
    token = frappe.form_dict.get('token')

    if not token:
        context.error = "Invalid contract link"
        return context

    # Verify token and get contract
    contract = frappe.db.get_value('Consignment Contract',
        {'signature_token': token, 'docstatus': 1},
        ['name', 'consignor', 'consignor_signed'],
        as_dict=True
    )

    if not contract:
        context.error = "Contract not found or link has expired"
        return context

    # Set page title
    context.title = f"Sign Contract {contract.name}"

    return context
