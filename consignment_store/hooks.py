app_name = "consignment_store"
app_title = "Consignment Store"
app_publisher = "rbn.dev"
app_description = "Custom app for running our consignment store"
app_email = "work@rbn.dev"
app_license = "gpl-2.0"
app_icon = "octicon octicon-package"
app_color = "#4CAF50"

# Apps
# ------------------

# Required Apps
required_apps = ["frappe", "erpnext"]

# DocTypes to be created
doctype_js = {
    "Sales Invoice": "public/js/sales_invoice.js",
    "POS Invoice": "public/js/pos_invoice.js"
}

# Document Events
doc_events = {
    "Sales Invoice": {
        "validate": "consignment_store.utils.commission.validate_consignment_items",
        "on_submit": [
            "consignment_store.utils.commission.process_commission",
            "consignment_store.utils.notifications.notify_items_sold"
        ],
        "on_cancel": "consignment_store.utils.commission.cancel_commission"
    },
    "POS Invoice": {
        "validate": "consignment_store.utils.commission.validate_consignment_items",
        "on_submit": "consignment_store.utils.commission.process_commission"
    },
    "Item": {
        "after_insert": "consignment_store.utils.qr_generator.generate_qr_for_item",
        "validate": "consignment_store.utils.commission.validate_consignment_item"
    }
}

scheduler_events = {
    "daily": [
        "consignment_store.utils.notifications.check_expiring_items",
        "consignment_store.utils.notifications.send_daily_summary"
    ],
    "monthly": [
        "consignment_store.utils.commission.process_monthly_payouts"
    ]
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["name", "in", [
                "Item-consignment_section",
                "Item-is_consignment",
                "Item-consignor",
                "Item-consignment_code",
                "Item-commission_rate",
                "Item-consignment_expiry_date",
                "Item-consignment_status",
                "Item-qr_code_data",
                "Sales Invoice Item-is_consignment",
                "Sales Invoice Item-consignor",
                "Sales Invoice Item-commission_amount",
                "Supplier-is_consignor"
            ]]
        ]
    }
]

# Override whitelisted methods
override_whitelisted_methods = {
    "erpnext.selling.page.point_of_sale.point_of_sale.search_by_term":
        "consignment_store.api.intake.search_with_consignment_info"
}

# Jinja
# jinja = {
#     "methods": [
#         "consignment_store.utils.get_consignment_badge"
#     ]
# }

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "consignment_store",
# 		"logo": "/assets/consignment_store/logo.png",
# 		"title": "Consignment Store",
# 		"route": "/consignment_store",
# 		"has_permission": "consignment_store.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/consignment_store/css/consignment_store.css"
# app_include_js = "/assets/consignment_store/js/consignment_store.js"

# include js, css files in header of web template
# web_include_css = "/assets/consignment_store/css/consignment_store.css"
# web_include_js = "/assets/consignment_store/js/consignment_store.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "consignment_store/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "consignment_store/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "consignment_store.utils.jinja_methods",
# 	"filters": "consignment_store.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "consignment_store.install.before_install"
# after_install = "consignment_store.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "consignment_store.uninstall.before_uninstall"
# after_uninstall = "consignment_store.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "consignment_store.utils.before_app_install"
# after_app_install = "consignment_store.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "consignment_store.utils.before_app_uninstall"
# after_app_uninstall = "consignment_store.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "consignment_store.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"consignment_store.tasks.all"
# 	],
# 	"daily": [
# 		"consignment_store.tasks.daily"
# 	],
# 	"hourly": [
# 		"consignment_store.tasks.hourly"
# 	],
# 	"weekly": [
# 		"consignment_store.tasks.weekly"
# 	],
# 	"monthly": [
# 		"consignment_store.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "consignment_store.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "consignment_store.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "consignment_store.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["consignment_store.utils.before_request"]
# after_request = ["consignment_store.utils.after_request"]

# Job Events
# ----------
# before_job = ["consignment_store.utils.before_job"]
# after_job = ["consignment_store.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"consignment_store.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

