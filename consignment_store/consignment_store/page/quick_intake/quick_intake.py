# consignment_store/consignment_store/page/quick_intake/quick_intake.py
import frappe

def get_context(context):
    context.no_cache = 1
    context.show_sidebar = True
    context.title = "Quick Intake"
