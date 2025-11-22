"""
End-to-end workflow tests.

These tests verify complete business processes:
- Complete consignment lifecycle (registration → intake → sale → payout)
- Contract expiry and ownership transfer
- Multiple sales and payouts
- Real-world scenarios
"""

import pytest
import frappe
from frappe.utils import today, add_days, flt
from consignment_store.api.commission import get_pending_commissions, create_payout
from consignment_store.api.portal import sign_contract
from consignment_store.tests.utils.test_helpers import (
	create_consignment_item,
	create_and_submit_invoice,
	get_pending_commission_count,
)


@pytest.mark.integration
@pytest.mark.slow
class TestCompleteConsignmentLifecycle:
	"""Test complete consignment lifecycle from start to finish."""

	def test_full_consignment_workflow(self, test_customer, test_warehouse, test_accounts):
		"""
		Test complete workflow:
		1. Consignor registration
		2. Contract creation
		3. Contract signing
		4. Item intake
		5. Item sale
		6. Commission creation
		7. Payout generation
		"""
		# Step 1: Create consignor
		consignor = frappe.get_doc(
			{
				"doctype": "Consignor",
				"first_name": "Complete",
				"last_name": "Workflow",
				"email": "complete.workflow@example.com",
				"phone": "555-0400",
			}
		)
		consignor.insert()
		assert consignor.name
		assert consignor.consignor_code

		# Step 2: Create contract
		contract = frappe.get_doc(
			{
				"doctype": "Consignment Contract",
				"consignor": consignor.name,
				"start_date": today(),
				"end_date": add_days(today(), 90),
				"commission_rate": 30.0,
			}
		)
		contract.insert()
		assert contract.status == "Pending"
		assert contract.signature_token

		# Step 3: Sign contract
		sign_contract(contract.name, contract.signature_token, ip_address="192.168.1.100")
		contract.reload()
		assert contract.status == "Active"

		# Step 4: Create items (intake)
		items_created = []
		for i in range(3):
			item = create_consignment_item(
				consignor.name, contract.name, contract.commission_rate, f"FULL-WORKFLOW-{i}"
			)
			items_created.append(item)

		assert len(items_created) == 3

		# Step 5: Sell items
		invoices = []
		for item in items_created:
			invoice = create_and_submit_invoice(item, 100)
			invoices.append(invoice)

		assert len(invoices) == 3

		# Step 6: Verify commissions created
		assert get_pending_commission_count(consignor.name) == 3

		# Step 7: Create payout
		pending = get_pending_commissions(consignor.name)
		payout = create_payout(consignor.name, pending_commissions=pending)

		assert payout.consignor == consignor.name
		assert len(payout.items) == 3
		assert flt(payout.total_amount, 2) == 210.00  # 3 * $70

		# Step 8: Verify workflow completion
		assert get_pending_commission_count(consignor.name) == 0

		# Verify all commission entries reference the payout
		for item in payout.items:
			commission = frappe.get_doc("Commission Entry", item.commission_entry)
			assert commission.payout_status == "Processed"
			assert commission.payout_reference == payout.name

	def test_multiple_consignors_parallel_workflow(self, test_customer):
		"""Test handling multiple consignors with parallel sales."""
		# Create two consignors
		consignor1 = frappe.get_doc(
			{
				"doctype": "Consignor",
				"first_name": "Parallel",
				"last_name": "One",
				"email": "parallel1@example.com",
				"phone": "555-0401",
			}
		)
		consignor1.insert()

		consignor2 = frappe.get_doc(
			{
				"doctype": "Consignor",
				"first_name": "Parallel",
				"last_name": "Two",
				"email": "parallel2@example.com",
				"phone": "555-0402",
			}
		)
		consignor2.insert()

		# Create contracts for both
		contract1 = frappe.get_doc(
			{
				"doctype": "Consignment Contract",
				"consignor": consignor1.name,
				"start_date": today(),
				"end_date": add_days(today(), 90),
				"commission_rate": 30.0,
				"status": "Active",
			}
		)
		contract1.insert()

		contract2 = frappe.get_doc(
			{
				"doctype": "Consignment Contract",
				"consignor": consignor2.name,
				"start_date": today(),
				"end_date": add_days(today(), 90),
				"commission_rate": 25.0,
				"status": "Active",
			}
		)
		contract2.insert()

		# Create and sell items for both consignors
		item1 = create_consignment_item(consignor1.name, contract1.name, contract1.commission_rate, "PAR1")
		item2 = create_consignment_item(consignor2.name, contract2.name, contract2.commission_rate, "PAR2")

		create_and_submit_invoice(item1, 100)
		create_and_submit_invoice(item2, 200)

		# Verify commissions for each consignor
		pending1 = get_pending_commissions(consignor1.name)
		pending2 = get_pending_commissions(consignor2.name)

		assert len(pending1) == 1
		assert len(pending2) == 1

		# Consignor 1: $100 * 0.7 = $70
		assert flt(pending1[0]["consignor_amount"], 2) == 70.00

		# Consignor 2: $200 * 0.75 = $150
		assert flt(pending2[0]["consignor_amount"], 2) == 150.00

		# Create separate payouts
		payout1 = create_payout(consignor1.name, pending_commissions=pending1)
		payout2 = create_payout(consignor2.name, pending_commissions=pending2)

		assert flt(payout1.total_amount, 2) == 70.00
		assert flt(payout2.total_amount, 2) == 150.00


@pytest.mark.integration
class TestRecurringWorkflows:
	"""Test recurring business workflows."""

	def test_weekly_sales_monthly_payout(self, test_consignor, signed_contract):
		"""Simulate weekly sales with monthly payout."""
		# Week 1: 2 sales
		for i in range(2):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"WEEK1-{i}"
			)
			create_and_submit_invoice(item, 100)

		assert get_pending_commission_count(test_consignor.name) == 2

		# Week 2: 3 sales
		for i in range(3):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"WEEK2-{i}"
			)
			create_and_submit_invoice(item, 150)

		assert get_pending_commission_count(test_consignor.name) == 5

		# Week 3: 1 sale
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "WEEK3-1"
		)
		create_and_submit_invoice(item, 200)

		assert get_pending_commission_count(test_consignor.name) == 6

		# Month end: Create payout for all sales
		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Total: 2*$100 + 3*$150 + 1*$200 = $850 sales
		# Commission @ 30%: $255
		# Consignor: $595
		expected_total = (2 * 100 + 3 * 150 + 1 * 200) * 0.7
		assert flt(payout.total_amount, 2) == flt(expected_total, 2)
		assert len(payout.items) == 6

		# All commissions processed
		assert get_pending_commission_count(test_consignor.name) == 0

	def test_multiple_payout_cycles(self, test_consignor, signed_contract):
		"""Test multiple payout cycles over time."""
		all_payouts = []

		# Cycle 1
		for i in range(2):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"CYCLE1-{i}"
			)
			create_and_submit_invoice(item, 100)

		pending1 = get_pending_commissions(test_consignor.name)
		payout1 = create_payout(test_consignor.name, pending_commissions=pending1)
		all_payouts.append(payout1)

		# Cycle 2
		for i in range(3):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"CYCLE2-{i}"
			)
			create_and_submit_invoice(item, 150)

		pending2 = get_pending_commissions(test_consignor.name)
		payout2 = create_payout(test_consignor.name, pending_commissions=pending2)
		all_payouts.append(payout2)

		# Cycle 3
		for i in range(4):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"CYCLE3-{i}"
			)
			create_and_submit_invoice(item, 200)

		pending3 = get_pending_commissions(test_consignor.name)
		payout3 = create_payout(test_consignor.name, pending_commissions=pending3)
		all_payouts.append(payout3)

		# Verify all three payouts
		assert len(all_payouts) == 3
		assert flt(payout1.total_amount, 2) == 140.00  # 2 * $70
		assert flt(payout2.total_amount, 2) == 315.00  # 3 * $105
		assert flt(payout3.total_amount, 2) == 560.00  # 4 * $140


@pytest.mark.integration
class TestErrorRecoveryWorkflows:
	"""Test error recovery and edge case workflows."""

	def test_invoice_cancellation_recovery(self, test_consignor, signed_contract):
		"""Test workflow when invoice is cancelled and corrected."""
		# Create and submit invoice
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "CANCEL-RECOVERY"
		)
		invoice = create_and_submit_invoice(item, 100)

		# Verify commission created
		assert get_pending_commission_count(test_consignor.name) == 1

		# Cancel invoice (e.g., customer returned item)
		invoice.cancel()

		# Commission should be cancelled
		assert get_pending_commission_count(test_consignor.name) == 0

		# Create new sale for same item (after return processing)
		# Note: In real scenario, would need to receive item back to stock first
		# For test purposes, simulating re-sale
		item2 = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "CANCEL-RECOVERY-2"
		)
		invoice2 = create_and_submit_invoice(item2, 100)

		# New commission created
		assert get_pending_commission_count(test_consignor.name) == 1

		# Can create payout with new commission
		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		assert flt(payout.total_amount, 2) == 70.00

	def test_partial_payout_workflow(self, test_consignor, signed_contract):
		"""Test creating partial payouts (selective commissions)."""
		# Create 5 sales
		items = []
		for i in range(5):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"PARTIAL-{i}"
			)
			create_and_submit_invoice(item, 100)
			items.append(item)

		# Get all pending
		all_pending = get_pending_commissions(test_consignor.name)
		assert len(all_pending) == 5

		# Create payout with first 3 only
		partial_pending = all_pending[:3]
		payout1 = create_payout(test_consignor.name, pending_commissions=partial_pending)

		assert len(payout1.items) == 3
		assert flt(payout1.total_amount, 2) == 210.00  # 3 * $70

		# Should still have 2 pending
		remaining = get_pending_commissions(test_consignor.name)
		assert len(remaining) == 2

		# Create second payout with remaining
		payout2 = create_payout(test_consignor.name, pending_commissions=remaining)

		assert len(payout2.items) == 2
		assert flt(payout2.total_amount, 2) == 140.00  # 2 * $70

		# Now all processed
		assert get_pending_commission_count(test_consignor.name) == 0


@pytest.mark.integration
@pytest.mark.slow
class TestComplexScenarios:
	"""Test complex real-world scenarios."""

	def test_mixed_commission_rates_workflow(self, test_consignor):
		"""Test consignor with multiple contracts at different rates."""
		# Contract 1: 30% commission
		contract1 = frappe.get_doc(
			{
				"doctype": "Consignment Contract",
				"consignor": test_consignor.name,
				"start_date": today(),
				"end_date": add_days(today(), 90),
				"commission_rate": 30.0,
				"status": "Active",
			}
		)
		contract1.insert()

		# Contract 2: 25% commission
		contract2 = frappe.get_doc(
			{
				"doctype": "Consignment Contract",
				"consignor": test_consignor.name,
				"start_date": today(),
				"end_date": add_days(today(), 60),
				"commission_rate": 25.0,
				"status": "Active",
			}
		)
		contract2.insert()

		# Create items under different contracts
		item1 = create_consignment_item(test_consignor.name, contract1.name, 30.0, "RATE30")
		item2 = create_consignment_item(test_consignor.name, contract2.name, 25.0, "RATE25")

		# Sell both
		create_and_submit_invoice(item1, 100)  # $70 consignor (30% commission)
		create_and_submit_invoice(item2, 100)  # $75 consignor (25% commission)

		# Create single payout for both
		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Total: $70 + $75 = $145
		assert flt(payout.total_amount, 2) == 145.00
		assert len(payout.items) == 2

	def test_high_volume_sales_workflow(self, test_consignor, signed_contract):
		"""Test high volume of sales (stress test)."""
		# Create 50 sales
		num_sales = 50
		for i in range(num_sales):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"VOLUME-{i}"
			)
			create_and_submit_invoice(item, 100)

		# Verify all commissions created
		assert get_pending_commission_count(test_consignor.name) == num_sales

		# Create payout
		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Verify totals
		assert len(payout.items) == num_sales
		assert flt(payout.total_amount, 2) == flt(num_sales * 70, 2)  # 50 * $70 = $3,500

	def test_varying_price_points_workflow(self, test_consignor, signed_contract):
		"""Test items at various price points."""
		price_points = [10, 25, 50, 100, 250, 500, 1000]

		for i, price in enumerate(price_points):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"PRICE-{i}"
			)
			create_and_submit_invoice(item, price)

		# Calculate expected total
		# Each at 70% (30% commission)
		expected_total = sum(price * 0.7 for price in price_points)

		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		assert len(payout.items) == len(price_points)
		assert flt(payout.total_amount, 2) == flt(expected_total, 2)
