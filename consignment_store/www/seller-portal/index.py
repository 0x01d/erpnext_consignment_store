# consignment_store/www/seller-portal/index.py
import frappe

def get_context(context):
    from consignment_store.api.portal import get_portal_data

    context.no_cache = 1
    context.show_sidebar = False

    data = get_portal_data()
    context.data = data

    return context
