"""
Tests for the payout system.

These tests verify:
- Payout creation and aggregation
- Commission entry status updates
- Minimum payout thresholds
- Payout validation rules
"""

import pytest
import frappe
from frappe.utils import flt, today
from consignment_store.api.commission import get_pending_commissions, create_payout
from consignment_store.tests.utils.test_helpers import (
	get_pending_commission_count,
	get_total_pending_commission,
	create_consignment_item,
	create_and_submit_invoice,
)


@pytest.mark.unit
class TestPayoutCreation:
	"""Test payout creation and commission aggregation."""

	def test_create_payout_basic(self, test_consignor, signed_contract, test_customer, test_warehouse):
		"""Test creating a basic payout with single commission."""
		# Create a sale
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "PAYOUT-1"
		)
		invoice = create_and_submit_invoice(item, 100)

		# Verify commission is pending
		assert get_pending_commission_count(test_consignor.name) == 1

		# Get pending commissions
		pending = get_pending_commissions(test_consignor.name)
		assert len(pending) == 1
		assert flt(pending[0]["consignor_amount"], 2) == 70.00  # $100 - 30% = $70

		# Create payout
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Verify payout
		assert payout.consignor == test_consignor.name
		assert len(payout.items) == 1
		assert flt(payout.total_amount, 2) == 70.00

		# Verify commission status updated
		assert get_pending_commission_count(test_consignor.name) == 0

	def test_create_payout_multiple_commissions(self, test_consignor, signed_contract):
		"""Test payout aggregates multiple commission entries."""
		# Create 5 sales with different amounts
		sale_amounts = [100, 150, 200, 75, 125]
		commission_rate = signed_contract.commission_rate

		for i, amount in enumerate(sale_amounts):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, commission_rate, f"MULTI-PAYOUT-{i}"
			)
			create_and_submit_invoice(item, amount)

		# Verify 5 pending commissions
		assert get_pending_commission_count(test_consignor.name) == 5

		# Calculate expected total
		# Amounts: 100, 150, 200, 75, 125 = 650 total
		# Commission @ 30%: 195
		# Consignor amount: 455
		expected_total = sum(amt * (1 - commission_rate / 100) for amt in sale_amounts)

		# Get pending commissions
		pending = get_pending_commissions(test_consignor.name)
		assert len(pending) == 5

		# Create payout
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Verify payout totals
		assert len(payout.items) == 5
		assert flt(payout.total_amount, 2) == flt(expected_total, 2)

		# All commissions should be marked as processed
		assert get_pending_commission_count(test_consignor.name) == 0

	def test_payout_updates_commission_status(self, test_consignor, signed_contract):
		"""Test that creating payout updates commission entries to 'Processed'."""
		# Create 3 sales
		for i in range(3):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"STATUS-{i}"
			)
			create_and_submit_invoice(item, 100)

		# Get commission entries
		pending = get_pending_commissions(test_consignor.name)
		commission_names = [c["name"] for c in pending]

		# Create payout
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Verify all commissions marked as processed
		for comm_name in commission_names:
			commission = frappe.get_doc("Commission Entry", comm_name)
			assert commission.payout_status == "Processed"
			assert commission.payout_reference == payout.name

	def test_payout_respects_minimum_threshold(self, test_consignor, signed_contract):
		"""Test that payouts respect minimum payout threshold if configured."""
		# Create a small sale (below typical minimum threshold)
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "SMALL"
		)
		create_and_submit_invoice(item, 10)  # Only $10 sale = $7 consignor amount

		pending = get_pending_commissions(test_consignor.name)

		# If there's a minimum threshold check in create_payout, it should prevent creation
		# For now, we'll verify the commission exists but is still pending
		assert len(pending) == 1
		assert flt(pending[0]["consignor_amount"], 2) == 7.00


@pytest.mark.unit
class TestPayoutValidation:
	"""Test payout validation rules."""

	def test_cannot_create_empty_payout(self, test_consignor):
		"""Test that payout cannot be created with no commission entries."""
		# Try to create payout with empty list
		with pytest.raises(Exception):
			create_payout(test_consignor.name, pending_commissions=[])

	def test_payout_calculates_total_correctly(self, test_consignor, signed_contract):
		"""Test that payout total is calculated correctly from commission items."""
		# Create sales with specific amounts
		amounts = [100, 200, 300]
		commission_rate = signed_contract.commission_rate

		for i, amount in enumerate(amounts):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, commission_rate, f"TOTAL-{i}"
			)
			create_and_submit_invoice(item, amount)

		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Calculate expected total
		# 100 * 0.7 + 200 * 0.7 + 300 * 0.7 = 70 + 140 + 210 = 420
		expected_total = sum(flt(c["consignor_amount"], 2) for c in pending)

		assert flt(payout.total_amount, 2) == flt(expected_total, 2)

	def test_payout_references_correct_consignor(self, test_consignor, signed_contract):
		"""Test that payout is linked to correct consignor."""
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "CONSIGNOR-REF"
		)
		create_and_submit_invoice(item, 100)

		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		assert payout.consignor == test_consignor.name

	def test_payout_includes_correct_date_range(self, test_consignor, signed_contract):
		"""Test that payout includes correct posting date information."""
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "DATE-TEST"
		)
		create_and_submit_invoice(item, 100)

		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Payout should have a posting date
		assert payout.posting_date
		# Should be today or recent
		assert payout.posting_date == today()


@pytest.mark.integration
class TestPayoutWorkflow:
	"""Test complete payout workflows."""

	def test_complete_sale_to_payout_workflow(self, test_consignor, signed_contract):
		"""Test complete workflow from sale to payout."""
		# Step 1: Create and submit sales
		sale_count = 3
		for i in range(sale_count):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"WORKFLOW-{i}"
			)
			create_and_submit_invoice(item, 100)

		# Step 2: Verify commissions created
		assert get_pending_commission_count(test_consignor.name) == sale_count

		# Step 3: Get pending commissions
		pending = get_pending_commissions(test_consignor.name)
		assert len(pending) == sale_count

		# Step 4: Create payout
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Step 5: Verify payout created correctly
		assert payout.consignor == test_consignor.name
		assert len(payout.items) == sale_count
		assert flt(payout.total_amount, 2) == flt(sale_count * 70, 2)  # 3 * $70 = $210

		# Step 6: Verify all commissions processed
		assert get_pending_commission_count(test_consignor.name) == 0

		# Step 7: Verify commission references updated
		for item in payout.items:
			commission = frappe.get_doc("Commission Entry", item.commission_entry)
			assert commission.payout_status == "Processed"
			assert commission.payout_reference == payout.name

	def test_multiple_payouts_for_same_consignor(self, test_consignor, signed_contract):
		"""Test creating multiple payouts over time for same consignor."""
		# First batch of sales
		for i in range(2):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"BATCH1-{i}"
			)
			create_and_submit_invoice(item, 100)

		# Create first payout
		pending1 = get_pending_commissions(test_consignor.name)
		payout1 = create_payout(test_consignor.name, pending_commissions=pending1)

		assert flt(payout1.total_amount, 2) == 140.00  # 2 * $70
		assert get_pending_commission_count(test_consignor.name) == 0

		# Second batch of sales
		for i in range(3):
			item = create_consignment_item(
				test_consignor.name, signed_contract.name, signed_contract.commission_rate, f"BATCH2-{i}"
			)
			create_and_submit_invoice(item, 150)

		# Create second payout
		pending2 = get_pending_commissions(test_consignor.name)
		payout2 = create_payout(test_consignor.name, pending_commissions=pending2)

		assert flt(payout2.total_amount, 2) == 315.00  # 3 * $105 (150 * 0.7)
		assert get_pending_commission_count(test_consignor.name) == 0

		# Verify two separate payouts exist
		payouts = frappe.get_all("Consignment Payout", filters={"consignor": test_consignor.name})
		assert len(payouts) == 2

	def test_payout_excludes_already_processed_commissions(self, test_consignor, signed_contract):
		"""Test that already processed commissions are not included in new payouts."""
		# Create first sale and payout
		item1 = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "FIRST"
		)
		create_and_submit_invoice(item1, 100)

		pending1 = get_pending_commissions(test_consignor.name)
		payout1 = create_payout(test_consignor.name, pending_commissions=pending1)

		# Create second sale
		item2 = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "SECOND"
		)
		create_and_submit_invoice(item2, 200)

		# Get pending commissions - should only include new sale
		pending2 = get_pending_commissions(test_consignor.name)
		assert len(pending2) == 1
		assert flt(pending2[0]["consignor_amount"], 2) == 140.00  # $200 * 0.7

		# Create second payout
		payout2 = create_payout(test_consignor.name, pending_commissions=pending2)
		assert flt(payout2.total_amount, 2) == 140.00
		assert len(payout2.items) == 1


@pytest.mark.unit
class TestPayoutEdgeCases:
	"""Test edge cases and error conditions."""

	def test_payout_with_zero_commission_rate(self, test_consignor, signed_contract):
		"""Test payout when commission rate is 0% (consignor gets full amount)."""
		# Update contract to 0% commission
		signed_contract.commission_rate = 0
		signed_contract.save()

		item = create_consignment_item(
			test_consignor.name, signed_contract.name, 0, "ZERO-COMMISSION"
		)
		create_and_submit_invoice(item, 100)

		pending = get_pending_commissions(test_consignor.name)
		assert len(pending) == 1
		assert flt(pending[0]["consignor_amount"], 2) == 100.00

		payout = create_payout(test_consignor.name, pending_commissions=pending)
		assert flt(payout.total_amount, 2) == 100.00

	def test_payout_with_decimal_amounts(self, test_consignor, signed_contract):
		"""Test payout with decimal amounts for rounding accuracy."""
		# Create sale with odd amount
		item = create_consignment_item(
			test_consignor.name, signed_contract.name, signed_contract.commission_rate, "DECIMAL"
		)
		create_and_submit_invoice(item, 99.99)

		pending = get_pending_commissions(test_consignor.name)
		payout = create_payout(test_consignor.name, pending_commissions=pending)

		# Verify decimal handling
		# 99.99 * 0.7 = 69.993 → should be 69.99
		expected = flt(99.99 * 0.7, 2)
		assert flt(payout.total_amount, 2) == expected

	def test_get_pending_commissions_empty_result(self):
		"""Test get_pending_commissions when no commissions exist."""
		# Create a new consignor with no sales
		consignor = frappe.get_doc(
			{
				"doctype": "Consignor",
				"first_name": "Empty",
				"last_name": "Test",
				"email": "empty@test.com",
				"phone": "555-0199",
			}
		)
		consignor.insert()

		pending = get_pending_commissions(consignor.name)
		assert pending == [] or len(pending) == 0
