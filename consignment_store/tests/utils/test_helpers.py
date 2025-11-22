"""
Helper utilities for consignment store tests.
"""

import frappe
from frappe.utils import today, add_days, flt


def create_test_invoice_with_items(customer, items_data, test_accounts):
	"""
	Create a test sales invoice with multiple items.

	Args:
		customer: Customer document
		items_data: List of dicts with {item_code, qty, rate, warehouse}
		test_accounts: Dict with account names

	Returns:
		Sales Invoice document
	"""
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer.name,
			"company": frappe.defaults.get_defaults().get("company") or "Test Company",
			"posting_date": today(),
			"due_date": add_days(today(), 30),
			"debit_to": test_accounts["debtors"],
			"items": items_data,
		}
	)
	invoice.insert()
	return invoice


def get_commission_entries(invoice_name):
	"""Get all commission entries for an invoice."""
	return frappe.get_all(
		"Commission Entry",
		filters={"sales_invoice": invoice_name},
		fields=["name", "consignor", "commission_amount", "consignor_amount", "payout_status"],
	)


def get_gl_entries(voucher_type, voucher_no):
	"""Get all GL entries for a voucher."""
	return frappe.get_all(
		"GL Entry",
		filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
		fields=["account", "debit", "credit", "against"],
		order_by="account",
	)


def verify_gl_entry_balance(gl_entries):
	"""Verify that GL entries balance (total debit = total credit)."""
	total_debit = sum(flt(entry.get("debit", 0)) for entry in gl_entries)
	total_credit = sum(flt(entry.get("credit", 0)) for entry in gl_entries)
	return flt(total_debit, 2) == flt(total_credit, 2)


def get_pending_commission_count(consignor_name):
	"""Get count of pending commissions for a consignor."""
	return frappe.db.count(
		"Commission Entry", {"consignor": consignor_name, "payout_status": "Pending"}
	)


def get_total_pending_commission(consignor_name):
	"""Get total pending commission amount for a consignor."""
	result = frappe.db.sql(
		"""
		SELECT SUM(consignor_amount) as total
		FROM `tabCommission Entry`
		WHERE consignor = %s AND payout_status = 'Pending'
	""",
		consignor_name,
		as_dict=True,
	)
	return flt(result[0].total if result and result[0].total else 0, 2)


def create_multiple_sales(consignor, contract, num_sales=3, price_per_sale=100):
	"""
	Create multiple sales for testing payout aggregation.

	Returns:
		List of invoice names
	"""
	invoices = []
	for i in range(num_sales):
		# Create item
		item = create_consignment_item(
			consignor=consignor.name,
			contract=contract.name,
			commission_rate=contract.commission_rate,
			item_suffix=f"MULTI-{i}",
		)

		# Create and submit invoice
		invoice = create_and_submit_invoice(item, price_per_sale)
		invoices.append(invoice.name)

	return invoices


def create_consignment_item(consignor, contract, commission_rate, item_suffix="TEST"):
	"""Create a consignment item for testing."""
	import random

	item_code = f"TEST-{item_suffix}-{random.randint(1000, 9999)}"

	item = frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item_code,
			"item_name": f"Test Item {item_code}",
			"item_group": "Products",
			"stock_uom": "Nos",
			"is_stock_item": 1,
			"is_sales_item": 1,
			"is_consignment": 1,
			"consignor": consignor,
			"consignment_contract": contract,
			"commission_rate": commission_rate,
			"consignment_status": "Active",
			"valuation_rate": 0,
		}
	)
	item.insert()
	frappe.db.commit()
	return item


def create_and_submit_invoice(item, rate):
	"""Create and submit a sales invoice for an item."""
	from consignment_store.tests.conftest import get_test_company

	# Get customer
	customer = frappe.get_doc("Customer", {"customer_name": "Test Customer"})

	# Get warehouse with stock
	warehouse = frappe.db.get_value(
		"Stock Entry Detail", {"item_code": item.item_code}, "t_warehouse"
	) or frappe.db.get_value("Warehouse", {"company": get_test_company()}, "name")

	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer.name,
			"company": get_test_company(),
			"posting_date": today(),
			"items": [{"item_code": item.item_code, "qty": 1, "rate": rate, "warehouse": warehouse}],
		}
	)
	invoice.insert()
	invoice.submit()
	frappe.db.commit()
	return invoice


def assert_commission_calculation(commission_entry, expected_commission, expected_consignor_amount):
	"""Assert that commission calculation is correct."""
	assert flt(commission_entry.commission_amount, 2) == flt(expected_commission, 2), (
		f"Commission amount mismatch: "
		f"expected {expected_commission}, got {commission_entry.commission_amount}"
	)
	assert flt(commission_entry.consignor_amount, 2) == flt(expected_consignor_amount, 2), (
		f"Consignor amount mismatch: "
		f"expected {expected_consignor_amount}, got {commission_entry.consignor_amount}"
	)
