"""
Pytest configuration and fixtures for consignment_store tests.

This module provides reusable test fixtures for testing the consignment store application.
"""

import frappe
import pytest
from datetime import datetime, timedelta
from frappe.utils import today, add_days, nowdate, flt


@pytest.fixture(scope="session", autouse=True)
def frappe_session():
	"""Initialize Frappe session for testing."""
	try:
		frappe.init(site="test_site")
		frappe.connect()
		yield
	finally:
		frappe.destroy()


@pytest.fixture(autouse=True)
def clear_test_data():
	"""Clear test data before each test."""
	frappe.set_user("Administrator")
	yield
	frappe.db.rollback()
	frappe.clear_cache()


@pytest.fixture
def test_customer():
	"""Create a test customer for invoices."""
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "Test Customer",
			"customer_type": "Individual",
			"customer_group": "Individual",
			"territory": "All Territories",
		}
	)
	customer.insert(ignore_if_duplicate=True)
	frappe.db.commit()
	return customer


@pytest.fixture
def test_warehouse():
	"""Get or create a test warehouse."""
	warehouse_name = "Test Warehouse - TC"
	if not frappe.db.exists("Warehouse", warehouse_name):
		warehouse = frappe.get_doc(
			{
				"doctype": "Warehouse",
				"warehouse_name": "Test Warehouse",
				"company": get_test_company(),
			}
		)
		warehouse.insert()
		frappe.db.commit()
		return warehouse
	return frappe.get_doc("Warehouse", warehouse_name)


@pytest.fixture
def test_accounts():
	"""Create or get test accounts needed for consignment operations."""
	company = get_test_company()

	accounts = {
		"commission_income": get_or_create_account("Commission Income - TC", "Income Account", company),
		"consignment_payable": get_or_create_account(
			"Consignment Payable - TC", "Current Liability", company
		),
		"debtors": get_or_create_account("Debtors - TC", "Receivable", company),
	}

	frappe.db.commit()
	return accounts


@pytest.fixture
def test_consignor(test_accounts):
	"""Create a test consignor with linked supplier."""
	# Create a unique consignor for each test
	import random

	suffix = random.randint(1000, 9999)

	consignor = frappe.get_doc(
		{
			"doctype": "Consignor",
			"first_name": f"Test_{suffix}",
			"last_name": "Consignor",
			"email": f"test{suffix}@example.com",
			"phone": "555-0100",
		}
	)
	consignor.insert()
	frappe.db.commit()
	return consignor


@pytest.fixture
def test_contract(test_consignor):
	"""Create a test consignment contract."""
	contract = frappe.get_doc(
		{
			"doctype": "Consignment Contract",
			"consignor": test_consignor.name,
			"start_date": today(),
			"end_date": add_days(today(), 90),
			"commission_rate": 30.0,
			"status": "Pending",
			"items": [],
		}
	)
	contract.insert()
	frappe.db.commit()
	return contract


@pytest.fixture
def signed_contract(test_contract):
	"""Create a signed (active) consignment contract."""
	test_contract.status = "Active"
	test_contract.signature_date = nowdate()
	test_contract.signature_ip = "127.0.0.1"
	test_contract.save()
	frappe.db.commit()
	return test_contract


@pytest.fixture
def test_item(test_consignor, signed_contract, test_warehouse):
	"""Create a test consignment item."""
	import random

	item_code = f"TEST-ITEM-{random.randint(1000, 9999)}"

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
			"consignor": test_consignor.name,
			"consignment_contract": signed_contract.name,
			"commission_rate": signed_contract.commission_rate,
			"consignment_expiry_date": signed_contract.end_date,
			"consignment_status": "Active",
			"valuation_rate": 0,
		}
	)
	item.insert()

	# Create stock entry to add stock
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": get_test_company(),
			"items": [
				{
					"item_code": item.item_code,
					"qty": 1,
					"t_warehouse": test_warehouse.name,
					"basic_rate": 0,
					"valuation_rate": 0,
				}
			],
		}
	)
	stock_entry.insert()
	stock_entry.submit()

	frappe.db.commit()
	return item


@pytest.fixture
def test_sales_invoice(test_customer, test_item, test_accounts):
	"""Create a test sales invoice with a consignment item."""
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": test_customer.name,
			"company": get_test_company(),
			"posting_date": today(),
			"due_date": add_days(today(), 30),
			"debit_to": test_accounts["debtors"],
			"items": [
				{
					"item_code": test_item.item_code,
					"qty": 1,
					"rate": 100.0,
					"warehouse": frappe.db.get_value("Stock Entry Detail", {"item_code": test_item.item_code}, "t_warehouse"),
				}
			],
		}
	)
	invoice.insert()
	frappe.db.commit()
	return invoice


# Helper functions


def get_test_company():
	"""Get or create a test company."""
	company_name = "Test Company"
	if not frappe.db.exists("Company", company_name):
		company = frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": company_name,
				"abbr": "TC",
				"default_currency": "USD",
				"country": "United States",
			}
		)
		company.insert()
		frappe.db.commit()
	return company_name


def get_or_create_account(account_name, account_type, company):
	"""Get or create a test account."""
	if frappe.db.exists("Account", account_name):
		return account_name

	# Get the root account for this type
	root_account = frappe.db.get_value(
		"Account", {"company": company, "account_type": account_type, "is_group": 1}, "name"
	)

	if not root_account:
		# Create root group if it doesn't exist
		root_account = frappe.get_doc(
			{
				"doctype": "Account",
				"account_name": account_type,
				"is_group": 1,
				"company": company,
				"account_type": account_type,
				"root_type": get_root_type(account_type),
			}
		)
		root_account.insert()
		root_account = root_account.name

	account = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name.replace(f" - {company}", ""),
			"parent_account": root_account,
			"company": company,
			"account_type": account_type,
			"is_group": 0,
		}
	)
	account.insert()
	return account.name


def get_root_type(account_type):
	"""Get root type for account type."""
	mapping = {
		"Income Account": "Income",
		"Current Liability": "Liability",
		"Receivable": "Asset",
		"Payable": "Liability",
	}
	return mapping.get(account_type, "Asset")


def create_test_commission_entry(consignor, invoice, item, commission_amount, consignor_amount):
	"""Helper to create a commission entry for testing."""
	commission = frappe.get_doc(
		{
			"doctype": "Commission Entry",
			"consignor": consignor,
			"sales_invoice": invoice,
			"item_code": item,
			"commission_amount": commission_amount,
			"consignor_amount": consignor_amount,
			"payout_status": "Pending",
			"posting_date": today(),
		}
	)
	commission.insert()
	frappe.db.commit()
	return commission
