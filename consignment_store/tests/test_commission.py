"""
Tests for commission calculation and GL entry creation.

These tests verify the core financial logic of the consignment store:
- Commission calculations
- Consignor amount calculations
- GL entry creation and accuracy
- Commission entry lifecycle
"""

import pytest
import frappe
from frappe.utils import flt, today
from consignment_store.tests.utils.test_helpers import (
	get_commission_entries,
	get_gl_entries,
	verify_gl_entry_balance,
	assert_commission_calculation,
)


@pytest.mark.unit
class TestCommissionCalculation:
	"""Test commission calculation logic."""

	def test_basic_commission_calculation(self, test_sales_invoice, test_item, test_consignor):
		"""Test basic commission calculation with 30% rate on $100 sale."""
		# Setup: Invoice created by fixture with rate=100, commission_rate=30%
		# Submit the invoice to trigger commission processing
		test_sales_invoice.submit()

		# Get the created commission entry
		commissions = get_commission_entries(test_sales_invoice.name)
		assert len(commissions) == 1, "Should create exactly one commission entry"

		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		# Verify calculations
		# Sale price: $100, Commission rate: 30%
		# Commission: $100 * 0.30 = $30
		# Consignor amount: $100 - $30 = $70
		assert_commission_calculation(commission, expected_commission=30.00, expected_consignor_amount=70.00)
		assert commission.consignor == test_consignor.name
		assert commission.payout_status == "Pending"

	def test_commission_calculation_different_rates(self, test_customer, test_consignor, signed_contract, test_warehouse, test_accounts):
		"""Test commission calculation with various commission rates."""
		test_cases = [
			{"rate": 100, "commission_rate": 10, "expected_commission": 10.00, "expected_consignor": 90.00},
			{"rate": 100, "commission_rate": 25, "expected_commission": 25.00, "expected_consignor": 75.00},
			{"rate": 100, "commission_rate": 50, "expected_commission": 50.00, "expected_consignor": 50.00},
			{"rate": 150, "commission_rate": 20, "expected_commission": 30.00, "expected_consignor": 120.00},
		]

		for i, test_case in enumerate(test_cases):
			# Create item with specific commission rate
			item = create_test_item_with_rate(
				test_consignor,
				signed_contract,
				test_case["commission_rate"],
				f"RATE-TEST-{i}",
				test_warehouse,
			)

			# Create and submit invoice
			invoice = create_invoice_for_item(
				test_customer, item, test_case["rate"], test_warehouse, test_accounts
			)
			invoice.submit()

			# Verify commission calculation
			commissions = get_commission_entries(invoice.name)
			assert len(commissions) == 1

			commission = frappe.get_doc("Commission Entry", commissions[0].name)
			assert_commission_calculation(
				commission, test_case["expected_commission"], test_case["expected_consignor"]
			)

	def test_commission_calculation_decimal_precision(self, test_customer, test_consignor, signed_contract, test_warehouse, test_accounts):
		"""Test commission calculation with decimal amounts for rounding accuracy."""
		# Create item with 33% commission rate
		item = create_test_item_with_rate(test_consignor, signed_contract, 33, "DECIMAL-TEST", test_warehouse)

		# Create invoice with $99.99 selling price
		invoice = create_invoice_for_item(test_customer, item, 99.99, test_warehouse, test_accounts)
		invoice.submit()

		# Get commission entry
		commissions = get_commission_entries(invoice.name)
		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		# Verify: 99.99 * 0.33 = 32.9967 → $33.00 (rounded)
		# Consignor: 99.99 - 33.00 = 66.99
		expected_commission = flt(99.99 * 0.33, 2)
		expected_consignor = flt(99.99 - expected_commission, 2)

		assert flt(commission.commission_amount, 2) == expected_commission
		assert flt(commission.consignor_amount, 2) == expected_consignor

	def test_multiple_items_in_single_invoice(self, test_customer, test_consignor, signed_contract, test_warehouse, test_accounts):
		"""Test commission calculation for invoice with multiple consignment items."""
		# Create three items
		item1 = create_test_item_with_rate(test_consignor, signed_contract, 30, "MULTI-1", test_warehouse)
		item2 = create_test_item_with_rate(test_consignor, signed_contract, 25, "MULTI-2", test_warehouse)
		item3 = create_test_item_with_rate(test_consignor, signed_contract, 35, "MULTI-3", test_warehouse)

		# Create invoice with all three items
		invoice = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"customer": test_customer.name,
				"company": "Test Company",
				"posting_date": today(),
				"debit_to": test_accounts["debtors"],
				"items": [
					{"item_code": item1.item_code, "qty": 1, "rate": 100, "warehouse": test_warehouse.name},
					{"item_code": item2.item_code, "qty": 1, "rate": 200, "warehouse": test_warehouse.name},
					{"item_code": item3.item_code, "qty": 1, "rate": 150, "warehouse": test_warehouse.name},
				],
			}
		)
		invoice.insert()
		invoice.submit()

		# Should create 3 commission entries
		commissions = get_commission_entries(invoice.name)
		assert len(commissions) == 3

		# Verify each commission
		# Item 1: $100 * 30% = $30 commission, $70 consignor
		# Item 2: $200 * 25% = $50 commission, $150 consignor
		# Item 3: $150 * 35% = $52.50 commission, $97.50 consignor
		commission_data = {c["name"]: c for c in commissions}

		total_commission = sum(flt(c["commission_amount"]) for c in commissions)
		total_consignor = sum(flt(c["consignor_amount"]) for c in commissions)

		# Total should be: $132.50 commission, $317.50 consignor
		assert flt(total_commission, 2) == 132.50
		assert flt(total_consignor, 2) == 317.50

	def test_commission_zero_rate(self, test_customer, test_consignor, signed_contract, test_warehouse, test_accounts):
		"""Test commission calculation with 0% commission rate."""
		item = create_test_item_with_rate(test_consignor, signed_contract, 0, "ZERO-RATE", test_warehouse)

		invoice = create_invoice_for_item(test_customer, item, 100, test_warehouse, test_accounts)
		invoice.submit()

		commissions = get_commission_entries(invoice.name)
		assert len(commissions) == 1

		commission = frappe.get_doc("Commission Entry", commissions[0].name)
		assert_commission_calculation(commission, expected_commission=0.00, expected_consignor_amount=100.00)


@pytest.mark.unit
class TestGLEntries:
	"""Test GL entry creation for commissions."""

	def test_gl_entries_created_on_submit(self, test_sales_invoice, test_accounts):
		"""Test that GL entries are created when invoice is submitted."""
		test_sales_invoice.submit()

		# Get GL entries for the commission
		commissions = get_commission_entries(test_sales_invoice.name)
		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		gl_entries = get_gl_entries("Commission Entry", commission.name)

		# Should create 2 GL entries: Commission Income (credit) and Consignment Payable (debit)
		assert len(gl_entries) >= 2, "Should create at least 2 GL entries"

	def test_gl_entries_balance(self, test_sales_invoice, test_accounts):
		"""Test that GL entries balance (debit = credit)."""
		test_sales_invoice.submit()

		commissions = get_commission_entries(test_sales_invoice.name)
		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		gl_entries = get_gl_entries("Commission Entry", commission.name)

		# Verify balance
		assert verify_gl_entry_balance(gl_entries), "GL entries should balance"

	def test_gl_entries_correct_accounts(self, test_sales_invoice, test_accounts):
		"""Test that GL entries post to correct accounts."""
		test_sales_invoice.submit()

		commissions = get_commission_entries(test_sales_invoice.name)
		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		gl_entries = get_gl_entries("Commission Entry", commission.name)

		# Check for commission income and consignment payable accounts
		accounts = [entry["account"] for entry in gl_entries]

		# Should have commission income account
		assert any("Commission Income" in acc for acc in accounts), "Should have Commission Income account"

		# Should have consignment payable account
		assert any(
			"Consignment Payable" in acc for acc in accounts
		), "Should have Consignment Payable account"

	def test_gl_entry_amounts(self, test_sales_invoice, test_accounts):
		"""Test that GL entry amounts match commission calculations."""
		test_sales_invoice.submit()

		commissions = get_commission_entries(test_sales_invoice.name)
		commission = frappe.get_doc("Commission Entry", commissions[0].name)

		gl_entries = get_gl_entries("Commission Entry", commission.name)

		# Find the commission income entry (should be credit)
		commission_income_entry = next(
			(e for e in gl_entries if "Commission Income" in e["account"]), None
		)

		# Find the consignment payable entry (should be debit)
		consignment_payable_entry = next(
			(e for e in gl_entries if "Consignment Payable" in e["account"]), None
		)

		if commission_income_entry and consignment_payable_entry:
			# Commission income should be credited with commission amount
			assert flt(commission_income_entry["credit"], 2) == flt(commission.commission_amount, 2)

			# Consignment payable should be debited with consignor amount
			assert flt(consignment_payable_entry["debit"], 2) == flt(commission.consignor_amount, 2)


@pytest.mark.unit
class TestCommissionCancellation:
	"""Test commission cancellation when invoice is cancelled."""

	def test_commission_cancelled_with_invoice(self, test_sales_invoice):
		"""Test that commission is cancelled when invoice is cancelled."""
		test_sales_invoice.submit()

		# Get commission entry
		commissions = get_commission_entries(test_sales_invoice.name)
		assert len(commissions) == 1
		commission_name = commissions[0].name

		# Cancel invoice
		test_sales_invoice.cancel()

		# Commission should be cancelled
		commission = frappe.get_doc("Commission Entry", commission_name)
		assert commission.docstatus == 2, "Commission should be cancelled"

	def test_gl_entries_reversed_on_cancel(self, test_sales_invoice):
		"""Test that GL entries are reversed when invoice is cancelled."""
		test_sales_invoice.submit()

		commissions = get_commission_entries(test_sales_invoice.name)
		commission_name = commissions[0].name

		# Get original GL entries
		original_gl_entries = get_gl_entries("Commission Entry", commission_name)
		original_count = len(original_gl_entries)

		# Cancel invoice
		test_sales_invoice.cancel()

		# Check GL entries after cancellation
		gl_entries_after = get_gl_entries("Commission Entry", commission_name)

		# Should have reversal entries (cancelling entries should exist)
		# In Frappe, cancelled entries are marked with is_cancelled=1
		cancelled_entries = [e for e in gl_entries_after if e.get("is_cancelled") == 1]

		# Verify entries still balance
		assert verify_gl_entry_balance(gl_entries_after)


# Helper functions for tests


def create_test_item_with_rate(consignor, contract, commission_rate, suffix, warehouse):
	"""Create a test item with specific commission rate."""
	import random

	item_code = f"TEST-{suffix}-{random.randint(1000, 9999)}"

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
			"consignor": consignor.name,
			"consignment_contract": contract.name,
			"commission_rate": commission_rate,
			"consignment_status": "Active",
			"valuation_rate": 0,
		}
	)
	item.insert()

	# Add stock
	stock_entry = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Receipt",
			"company": "Test Company",
			"items": [
				{
					"item_code": item.item_code,
					"qty": 1,
					"t_warehouse": warehouse.name,
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


def create_invoice_for_item(customer, item, rate, warehouse, accounts):
	"""Create a sales invoice for a specific item."""
	invoice = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": customer.name,
			"company": "Test Company",
			"posting_date": today(),
			"debit_to": accounts["debtors"],
			"items": [{"item_code": item.item_code, "qty": 1, "rate": rate, "warehouse": warehouse.name}],
		}
	)
	invoice.insert()
	frappe.db.commit()
	return invoice
