# Testing Guide for ERPNext Consignment Store

This document provides comprehensive instructions for running the test suite in a Frappe/ERPNext environment.

## Prerequisites

### 1. Frappe Bench Environment

The tests require a working Frappe bench with ERPNext installed. If you don't have one:

```bash
# Install bench
pip install frappe-bench

# Create a new bench
bench init frappe-bench --frappe-branch version-15
cd frappe-bench

# Create a new site
bench new-site mysite.local
bench --site mysite.local add-to-hosts

# Get and install ERPNext
bench get-app erpnext --branch version-15
bench --site mysite.local install-app erpnext
```

### 2. Install Consignment Store App

```bash
# If this repo is cloned locally
bench get-app /path/to/erpnext_consignment_store

# Or from GitHub
bench get-app https://github.com/0x01d/erpnext_consignment_store

# Install on site
bench --site mysite.local install-app consignment_store
```

### 3. Install Test Dependencies

```bash
# Activate bench virtual environment
source env/bin/activate

# Install pytest and coverage
pip install pytest pytest-cov
```

## Running Tests

### Method 1: Using Bench (Recommended)

```bash
# Run all tests for the app
bench --site mysite.local run-tests --app consignment_store

# Run with coverage
bench --site mysite.local run-tests --app consignment_store --coverage

# Run specific test module
bench --site mysite.local run-tests --app consignment_store --module test_commission

# Run specific test class
bench --site mysite.local run-tests --app consignment_store --module test_commission --test TestCommissionCalculation

# Run specific test function
bench --site mysite.local run-tests --app consignment_store --module test_commission --test test_basic_commission_calculation
```

### Method 2: Using Pytest Directly

```bash
# Navigate to bench directory
cd ~/frappe-bench

# Activate virtual environment
source env/bin/activate

# Set Frappe site
export FRAPPE_SITE=mysite.local

# Run tests
cd apps/consignment_store
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest consignment_store/tests/test_commission.py

# Run with coverage
pytest --cov=consignment_store --cov-report=html
```

### Method 3: Run Tests by Category

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Exclude slow tests
pytest -m "not slow"

# Run slow tests
pytest -m slow
```

## Test Organization

### Test Files

| File | Tests | Description |
|------|-------|-------------|
| `test_commission.py` | 34 | Commission calculations, GL entries, rounding |
| `test_payout.py` | 18 | Payout aggregation, status updates, cycles |
| `test_contract.py` | 28 | Contract lifecycle, digital signatures, tokens |
| `test_consignor.py` | 17 | Registration, code generation, supplier linking |
| `test_invoice_integration.py` | 14 | Invoice hooks, mixed items, cancellations |
| `test_api.py` | 20 | API validation, security, error handling |
| `test_workflows.py` | 12 | End-to-end business processes |
| **Total** | **143** | **Complete test coverage** |

### Test Fixtures

Available fixtures (defined in `conftest.py`):

- `test_customer` - Sample customer for invoices
- `test_warehouse` - Test warehouse for stock
- `test_accounts` - GL accounts (commission income, payable, debtors)
- `test_consignor` - Sample consignor with auto-generated code
- `test_contract` - Pending contract
- `signed_contract` - Active (signed) contract
- `test_item` - Consignment item with stock
- `test_sales_invoice` - Draft sales invoice

## Test Database Setup

### Using Test Site

For consistent testing, create a dedicated test site:

```bash
# Create test site
bench new-site test.local --force

# Install apps
bench --site test.local install-app erpnext
bench --site test.local install-app consignment_store

# Set up Chart of Accounts
bench --site test.local execute frappe.utils.install.complete_setup_wizard

# Run tests
bench --site test.local run-tests --app consignment_store
```

### Database Cleanup

Tests use automatic rollback, but you can manually reset:

```bash
# Drop and recreate test site
bench drop-site test.local --force
bench new-site test.local
bench --site test.local install-app erpnext
bench --site test.local install-app consignment_store
```

## Understanding Test Results

### Successful Run

```
===================== test session starts ======================
platform linux -- Python 3.11.14, pytest-9.0.1
collected 143 items

test_commission.py::TestCommissionCalculation::test_basic_commission_calculation PASSED [ 1%]
test_commission.py::TestCommissionCalculation::test_commission_calculation_different_rates PASSED [ 2%]
...
===================== 143 passed in 45.23s ====================
```

### Failed Test Example

```
FAILED test_commission.py::test_basic_commission_calculation - AssertionError: expected 30.0, got 29.99

=========================== FAILURES ===========================
_______________ test_basic_commission_calculation ______________

    def test_basic_commission_calculation(test_sales_invoice):
        test_sales_invoice.submit()
        commissions = get_commission_entries(test_sales_invoice.name)
>       assert commission.commission_amount == 30.00
E       AssertionError: expected 30.0, got 29.99

test_commission.py:42: AssertionError
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=consignment_store --cov-report=html

# View report
open htmlcov/index.html
```

Example output:
```
Name                                   Stmts   Miss  Cover
----------------------------------------------------------
consignment_store/__init__.py             5      0   100%
consignment_store/api/commission.py      45      3    93%
consignment_store/api/intake.py          78      8    90%
consignment_store/utils/commission.py   125     12    90%
----------------------------------------------------------
TOTAL                                    853     45    95%
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'frappe'"

**Solution**: Tests must run in Frappe bench environment

```bash
cd ~/frappe-bench
source env/bin/activate
bench --site mysite.local run-tests --app consignment_store
```

### Issue: "Site not found"

**Solution**: Create or specify the site

```bash
bench new-site mysite.local
bench --site mysite.local install-app consignment_store
```

### Issue: "Account not found" errors

**Solution**: Ensure Chart of Accounts is set up

```bash
# Complete ERPNext setup wizard
bench --site mysite.local execute frappe.utils.install.complete_setup_wizard

# Or create required accounts manually via UI
```

### Issue: Test database contamination

**Solution**: Use test site with automatic cleanup

```bash
# Always use a dedicated test site
bench --site test.local run-tests --app consignment_store

# Tests auto-rollback, but you can force clean:
bench drop-site test.local --force
bench new-site test.local
bench --site test.local install-app erpnext
bench --site test.local install-app consignment_store
```

### Issue: ImportError in tests

**Solution**: Ensure all dependencies installed

```bash
cd ~/frappe-bench/apps/consignment_store
pip install -e .
pip install pytest pytest-cov
```

### Issue: Slow test execution

**Solution**: Exclude slow tests or run in parallel

```bash
# Skip slow tests
pytest -m "not slow"

# Run tests in parallel (requires pytest-xdist)
pip install pytest-xdist
pytest -n auto
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/tests.yml`:

```yaml
name: Run Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      mariadb:
        image: mariadb:10.6
        env:
          MYSQL_ROOT_PASSWORD: root
        ports:
          - 3306:3306
        options: --health-cmd="mysqladmin ping" --health-interval=10s --health-timeout=5s --health-retries=3

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install frappe-bench
          bench init frappe-bench --skip-redis-config-generation --frappe-branch version-15
          cd frappe-bench

      - name: Install ERPNext
        run: |
          cd frappe-bench
          bench get-app erpnext --branch version-15
          bench new-site test.local --admin-password admin --mariadb-root-password root
          bench --site test.local install-app erpnext

      - name: Install Consignment Store
        run: |
          cd frappe-bench
          bench get-app $GITHUB_WORKSPACE
          bench --site test.local install-app consignment_store

      - name: Run Tests
        run: |
          cd frappe-bench
          bench --site test.local run-tests --app consignment_store --coverage

      - name: Upload Coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frappe-bench/apps/consignment_store/coverage.xml
```

## Test Development Guidelines

### Writing New Tests

1. **Use descriptive names**
   ```python
   def test_commission_calculation_with_30_percent_rate():
       """Test commission calculation with 30% rate on $100 sale."""
   ```

2. **Follow AAA pattern**
   ```python
   def test_payout_creation():
       # Arrange
       consignor = create_test_consignor()
       create_sales(consignor, count=3)

       # Act
       payout = create_payout(consignor.name)

       # Assert
       assert payout.total_amount == expected_amount
   ```

3. **Use fixtures**
   ```python
   def test_with_fixtures(test_consignor, signed_contract):
       # Fixtures automatically created and cleaned up
       assert test_consignor.consignor_code
       assert signed_contract.status == "Active"
   ```

4. **Mark appropriately**
   ```python
   @pytest.mark.unit
   def test_calculation():
       pass

   @pytest.mark.integration
   def test_workflow():
       pass

   @pytest.mark.slow
   def test_high_volume():
       pass
   ```

### Running Tests During Development

```bash
# Run tests on file save (requires pytest-watch)
pip install pytest-watch
ptw consignment_store/tests/

# Run only failed tests
pytest --lf

# Run tests in pdb on failure
pytest --pdb

# See print statements
pytest -s
```

## Performance Benchmarking

```bash
# Time individual tests
pytest --durations=10

# Profile tests
pip install pytest-profiling
pytest --profile
```

## Additional Resources

- [Frappe Testing Documentation](https://frappeframework.com/docs/user/en/testing)
- [ERPNext Developer Guide](https://docs.erpnext.com/docs/user/en/developing-erpnext)
- [Pytest Documentation](https://docs.pytest.org/)
- [consignment_store/tests/README.md](consignment_store/tests/README.md) - Detailed test documentation

## Summary Commands

```bash
# Quick start
cd ~/frappe-bench
bench --site mysite.local run-tests --app consignment_store

# With coverage
bench --site mysite.local run-tests --app consignment_store --coverage

# Specific module
bench --site mysite.local run-tests --app consignment_store --module test_commission

# Using pytest directly
cd ~/frappe-bench/apps/consignment_store
pytest -v --cov=consignment_store --cov-report=html
```

---

**Questions?** Open an issue in the repository or consult the Frappe testing documentation.
