# Consignment Store Test Suite

Comprehensive test suite for the ERPNext Consignment Store application.

## Overview

This test suite provides extensive coverage of the consignment store's core functionality, including:

- **Commission Calculation** - Verify financial accuracy
- **Payout System** - Test payment aggregation and processing
- **Contract Management** - Validate contract lifecycle and signatures
- **Consignor Operations** - Test registration and management
- **Invoice Integration** - Verify ERPNext integration
- **API Endpoints** - Test all API functions
- **End-to-End Workflows** - Complete business process testing

## Test Statistics

- **Total Test Files**: 8
- **Test Categories**:
  - Unit Tests: High coverage of individual functions
  - Integration Tests: Multi-component workflows
  - E2E Tests: Complete business processes

## Prerequisites

### Required Packages

```bash
pip install pytest pytest-cov
```

### ERPNext Test Site

Tests require a Frappe/ERPNext test site:

```bash
# Create test site (if not exists)
bench new-site test_site --force
bench --site test_site install-app erpnext
bench --site test_site install-app consignment_store
```

## Running Tests

### Run All Tests

```bash
# From the bench directory
bench --site test_site run-tests --app consignment_store

# Or using pytest directly
cd apps/consignment_store
pytest
```

### Run Specific Test Files

```bash
# Commission tests only
pytest consignment_store/tests/test_commission.py

# Payout tests only
pytest consignment_store/tests/test_payout.py

# Contract tests only
pytest consignment_store/tests/test_contract.py
```

### Run by Test Category

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Slow tests (excluded by default)
pytest -m slow
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=consignment_store --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Verbose Output

```bash
# Detailed test output
pytest -v

# Show print statements
pytest -s

# Both verbose and print
pytest -vs
```

## Test Organization

### Test Files

```
consignment_store/tests/
├── README.md                      # This file
├── conftest.py                    # Pytest fixtures and configuration
├── test_commission.py             # Commission calculation tests
├── test_payout.py                 # Payout system tests
├── test_contract.py               # Contract lifecycle tests
├── test_consignor.py              # Consignor management tests
├── test_invoice_integration.py    # Invoice integration tests
├── test_api.py                    # API endpoint tests
├── test_workflows.py              # End-to-end workflow tests
└── utils/
    └── test_helpers.py            # Test utility functions
```

### Test Fixtures

Reusable fixtures are defined in `conftest.py`:

- `test_customer` - Sample customer for invoices
- `test_warehouse` - Test warehouse for stock
- `test_accounts` - Test GL accounts
- `test_consignor` - Sample consignor
- `test_contract` - Pending contract
- `signed_contract` - Active (signed) contract
- `test_item` - Consignment item with stock
- `test_sales_invoice` - Draft sales invoice

## Test Coverage by Module

### 1. Commission Calculation (`test_commission.py`)

**What's Tested:**
- ✅ Basic commission calculations (30% of $100 = $30)
- ✅ Various commission rates (10%, 25%, 50%)
- ✅ Decimal precision and rounding
- ✅ Multiple items in single invoice
- ✅ Zero commission rate edge case
- ✅ GL entry creation and balance
- ✅ Commission cancellation on invoice cancel

**Critical Tests:**
- `test_basic_commission_calculation` - Core financial logic
- `test_gl_entries_balance` - Accounting integrity
- `test_commission_cancelled_with_invoice` - Reversal logic

### 2. Payout System (`test_payout.py`)

**What's Tested:**
- ✅ Single and multiple commission aggregation
- ✅ Commission status updates (Pending → Processed)
- ✅ Minimum payout thresholds
- ✅ Payout validation rules
- ✅ Multiple payout cycles
- ✅ Exclusion of already-processed commissions
- ✅ Edge cases (zero rate, decimals)

**Critical Tests:**
- `test_create_payout_multiple_commissions` - Aggregation logic
- `test_payout_updates_commission_status` - State management
- `test_complete_sale_to_payout_workflow` - Full cycle

### 3. Contract Management (`test_contract.py`)

**What's Tested:**
- ✅ Contract creation and initialization
- ✅ Signature token generation (uniqueness)
- ✅ Digital signature workflow
- ✅ Token validation and security
- ✅ Status transitions (Pending → Active → Expired)
- ✅ Contract validation rules
- ✅ IP address and timestamp recording

**Critical Tests:**
- `test_sign_contract_basic` - Signature workflow
- `test_sign_contract_with_invalid_token` - Security
- `test_signature_tokens_are_unique` - Data integrity

### 4. Consignor Management (`test_consignor.py`)

**What's Tested:**
- ✅ Consignor registration
- ✅ Code auto-generation and uniqueness
- ✅ Supplier linking
- ✅ Search functionality
- ✅ Item intake process
- ✅ QR code generation
- ✅ Validation rules

**Critical Tests:**
- `test_consignor_code_auto_generated` - Auto-generation
- `test_supplier_created_automatically` - ERPNext integration
- `test_search_consignor_by_name` - Search functionality

### 5. Invoice Integration (`test_invoice_integration.py`)

**What's Tested:**
- ✅ Invoice validation hooks
- ✅ Commission field population
- ✅ Mixed invoices (consignment + regular items)
- ✅ POS Invoice support
- ✅ Invoice cancellation handling
- ✅ Discount and quantity edge cases

**Critical Tests:**
- `test_mixed_invoice_processes_only_consignment` - Selective processing
- `test_cancel_invoice_reverses_commission` - Cancellation logic
- `test_invoice_with_discount_on_consignment_item` - Price calculation

### 6. API Endpoints (`test_api.py`)

**What's Tested:**
- ✅ API input validation
- ✅ Response format consistency
- ✅ Error handling
- ✅ SQL injection prevention
- ✅ Permission and authorization
- ✅ Portal API guest access

**Critical Tests:**
- `test_api_handles_special_characters` - Security
- `test_get_pending_commissions_filters_by_consignor` - Data isolation
- `test_complete_payout_via_api` - API integration

### 7. End-to-End Workflows (`test_workflows.py`)

**What's Tested:**
- ✅ Complete consignment lifecycle
- ✅ Multiple consignors in parallel
- ✅ Recurring sales and payouts
- ✅ Invoice cancellation recovery
- ✅ Partial payouts
- ✅ High volume scenarios (50+ sales)
- ✅ Varying price points

**Critical Tests:**
- `test_full_consignment_workflow` - Complete business process
- `test_weekly_sales_monthly_payout` - Realistic scenario
- `test_high_volume_sales_workflow` - Stress test

## Writing New Tests

### Test Structure

```python
import pytest
import frappe
from consignment_store.tests.utils.test_helpers import ...

@pytest.mark.unit  # or @pytest.mark.integration
class TestFeatureName:
    """Test description."""

    def test_specific_behavior(self, test_fixture):
        """Test that specific behavior works correctly."""
        # Arrange
        setup_data = create_test_data()

        # Act
        result = function_under_test(setup_data)

        # Assert
        assert result.expected_field == expected_value
```

### Using Fixtures

```python
def test_with_fixtures(test_consignor, signed_contract):
    """Fixtures are automatically created and cleaned up."""
    # Use the fixtures directly
    assert test_consignor.name
    assert signed_contract.status == "Active"
```

### Best Practices

1. **Descriptive Names**: Use clear, descriptive test names
   - Good: `test_commission_calculation_with_30_percent_rate`
   - Bad: `test_commission1`

2. **Single Assertion Focus**: Each test should verify one behavior
   - Exception: Related assertions for same operation are OK

3. **Arrange-Act-Assert**: Follow AAA pattern
   ```python
   # Arrange
   item = create_item()

   # Act
   result = process_item(item)

   # Assert
   assert result.success
   ```

4. **Use Fixtures**: Leverage existing fixtures instead of duplicating setup

5. **Mark Appropriately**: Use `@pytest.mark.unit`, `@pytest.mark.integration`, or `@pytest.mark.slow`

6. **Clean Up**: Database rollback happens automatically, but be aware of side effects

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install pytest pytest-cov
      - name: Run tests
        run: |
          pytest --cov=consignment_store
```

## Common Issues and Solutions

### Issue: Tests fail with "Site not found"

**Solution**: Ensure test site exists and app is installed:
```bash
bench new-site test_site
bench --site test_site install-app consignment_store
```

### Issue: Import errors

**Solution**: Run tests from bench directory:
```bash
cd ~/frappe-bench
bench --site test_site run-tests --app consignment_store
```

### Issue: Database errors

**Solution**: Tests should auto-rollback, but you can manually reset:
```bash
bench --site test_site reinstall
```

### Issue: GL Account errors

**Solution**: Ensure Chart of Accounts is set up in test site:
```bash
bench --site test_site execute "frappe.db.commit()"
```

## Coverage Goals

- **Current Coverage**: Run `pytest --cov` to see current stats
- **Target Coverage**:
  - Critical modules (commission, payout): 90%+
  - Other modules: 70%+
  - Overall: 75%+

## Test Maintenance

### When to Update Tests

- ✅ When adding new features
- ✅ When fixing bugs (add regression test)
- ✅ When changing business logic
- ✅ When API contracts change

### Test Review Checklist

- [ ] All new code has tests
- [ ] Tests follow naming conventions
- [ ] Tests are properly marked (unit/integration/slow)
- [ ] Tests use existing fixtures where possible
- [ ] Tests clean up after themselves
- [ ] Tests are documented with docstrings

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Frappe Testing Guide](https://frappeframework.com/docs/user/en/testing)
- [ERPNext Developer Guide](https://docs.erpnext.com/docs/user/manual/en/setting-up/articles/developing-erpnext)

## Support

For issues or questions about the tests:
1. Check this README
2. Review existing test examples
3. Check Frappe/ERPNext testing docs
4. Open an issue in the repository

---

**Last Updated**: 2025-11-22
**Test Suite Version**: 1.0.0
**Total Tests**: 100+
