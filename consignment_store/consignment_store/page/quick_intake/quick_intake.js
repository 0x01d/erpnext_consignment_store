// consignment_store/consignment_store/page/quick_intake/quick_intake.js
// Enhanced with smart search and tab navigation

frappe.pages['quick-intake'].on_page_show = function(wrapper) {
    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Quick Consignment Intake',
        single_column: true
    });

    frappe.quick_intake = new QuickIntake(page);
}

class QuickIntake {
    constructor(page) {
        this.page = page;
        this.current_seller = null;
        this.items = [];
        this.brands_cache = null;
        this.make_page();
        this.bind_events();
        this.load_brands();
    }

    make_page() {
        this.page.wrapper.html(`
            <div class="quick-intake-container">
                <div class="alert alert-info">
                    <strong>📋 Contract System Active</strong> - Items will have NO warehouse value until ownership transfers after contract expiry.
                </div>

                <div class="seller-section card">
                    <div class="card-header bg-primary text-white">
                        <h4><i class="fa fa-user"></i> Seller Information</h4>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-8">
                                <div class="seller-search-container">
                                    <input type="text" class="form-control seller-search"
                                        placeholder="Search by name, phone, email, or code... (Tab to select)">
                                    <div class="seller-results dropdown-results"></div>
                                </div>
                                <div class="selected-seller" style="display:none;">
                                    <div class="alert alert-success">
                                        <strong class="seller-display-name"></strong>
                                        <span class="seller-commission-info"></span>
                                        <button class="btn btn-xs btn-default float-right change-seller">Change</button>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <button class="btn btn-primary new-seller">
                                    <i class="fa fa-plus"></i> New Seller
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <div class="contract-terms-section card mt-3">
                    <div class="card-header bg-info text-white">
                        <h4><i class="fa fa-file-contract"></i> Contract Terms</h4>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            <div class="col-md-4">
                                <label>Contract Duration (Days)</label>
                                <input type="number" class="form-control contract-duration" value="60" min="30" max="180">
                            </div>
                            <div class="col-md-4">
                                <label>Grace Period (Days)</label>
                                <input type="number" class="form-control grace-period" value="14" min="7" max="30">
                            </div>
                            <div class="col-md-4">
                                <label>Ownership Transfer After</label>
                                <div class="form-control-static text-info">
                                    <strong class="ownership-days">74</strong> days
                                </div>
                            </div>
                        </div>
                        <div class="alert alert-warning mt-2">
                            <small>
                                <i class="fa fa-info-circle"></i>
                                Items not collected after grace period become store property at 30% markdown value
                            </small>
                        </div>
                    </div>
                </div>

                <div class="items-section card mt-3">
                    <div class="card-header bg-success text-white">
                        <h4><i class="fa fa-tags"></i> Add Items</h4>
                    </div>
                    <div class="card-body">
                        <div class="quick-buttons mb-3">
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Shirt">👔 Shirt</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Pants">👖 Pants</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Dress">👗 Dress</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Jacket">🧥 Jacket</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Shoes">👟 Shoes</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Bag">👜 Bag</button>
                            <button class="btn btn-sm btn-outline-primary quick-add" data-category="Accessory">💍 Accessory</button>
                            <button class="btn btn-sm btn-outline-secondary quick-add" data-category="">➕ Other</button>
                        </div>

                        <table class="table table-bordered table-hover items-table">
                            <thead class="thead-light">
                                <tr>
                                    <th width="25%">Description</th>
                                    <th width="15%">Brand</th>
                                    <th width="10%">Size</th>
                                    <th width="10%">Color</th>
                                    <th width="10%">Condition</th>
                                    <th width="10%">Price €</th>
                                    <th width="10%">Comm %</th>
                                    <th width="10%">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="items-tbody"></tbody>
                            <tfoot class="table-info">
                                <tr>
                                    <td colspan="5"><strong>Total</strong></td>
                                    <td><strong class="total-value">€0.00</strong></td>
                                    <td>
                                        <small class="expected-commission text-muted">€0.00</small>
                                    </td>
                                    <td>
                                        <strong class="total-items">0 items</strong>
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>

                <div class="actions-section mt-3 text-center">
                    <button class="btn btn-lg btn-success process-intake">
                        <i class="fa fa-check"></i> Create Contract & Print
                    </button>
                    <button class="btn btn-lg btn-warning print-labels-only" style="display:none;">
                        <i class="fa fa-print"></i> Print Labels Only
                    </button>
                    <button class="btn btn-lg btn-danger clear-all">
                        <i class="fa fa-times"></i> Clear All
                    </button>
                </div>

                <div class="info-section mt-4">
                    <div class="alert alert-info">
                        <h5>📊 How This Works:</h5>
                        <ol class="mb-0">
                            <li>Items are consigned for agreed duration (default 60 days)</li>
                            <li><strong>NO warehouse value recorded</strong> - items remain consignor\'s property</li>
                            <li>When sold: Only commission (%) is recognized as income</li>
                            <li>After contract expires: Grace period for pickup</li>
                            <li>Uncollected items: Become store property at 30% markdown</li>
                        </ol>
                    </div>
                </div>
            </div>

            <style>
                .dropdown-results {
                    position: absolute;
                    top: 100%;
                    left: 0;
                    right: 0;
                    max-height: 300px;
                    overflow-y: auto;
                    background: white;
                    border: 1px solid #ddd;
                    border-top: 0;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    z-index: 1000;
                    display: none;
                }
                .dropdown-results.show {
                    display: block;
                }
                .dropdown-result {
                    padding: 8px 12px;
                    cursor: pointer;
                    border-bottom: 1px solid #f0f0f0;
                }
                .dropdown-result:hover,
                .dropdown-result.highlighted {
                    background: #f8f9fa;
                }
                .dropdown-result.create-new {
                    background: #e8f5e9;
                    color: #2e7d32;
                    font-weight: 500;
                }
                .dropdown-result.create-new:hover {
                    background: #c8e6c9;
                }
                .brand-search-wrapper {
                    position: relative;
                }
                .brand-results {
                    margin-top: -1px;
                }
                .no-results {
                    padding: 8px 12px;
                    color: #666;
                    font-style: italic;
                }
            </style>
        `);
    }

    bind_events() {
        const me = this;

        // Seller search with enhanced keyboard navigation
        this.page.wrapper.on('input', '.seller-search', frappe.utils.debounce((e) => {
            this.search_seller(e.target.value);
        }, 300));

        // Tab key handling for seller search
        this.page.wrapper.on('keydown', '.seller-search', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                const $results = this.page.wrapper.find('.seller-results');
                const $firstResult = $results.find('.seller-result:first');

                if ($firstResult.length) {
                    e.preventDefault();
                    const name = $firstResult.data('name');
                    this.select_seller(name);

                    // Focus on first item description field or contract duration
                    setTimeout(() => {
                        const $firstItem = this.page.wrapper.find('.items-tbody .item-desc:first');
                        if ($firstItem.length) {
                            $firstItem.focus();
                        } else {
                            this.page.wrapper.find('.contract-duration').focus();
                        }
                    }, 100);
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateResults('.seller-results', 'down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateResults('.seller-results', 'up');
            } else if (e.key === 'Enter') {
                const $highlighted = this.page.wrapper.find('.seller-results .highlighted');
                if ($highlighted.length) {
                    e.preventDefault();
                    const name = $highlighted.data('name');
                    this.select_seller(name);
                }
            }
        });

        // Click outside to close dropdowns
        $(document).on('click', (e) => {
            if (!$(e.target).closest('.seller-search-container, .brand-search-wrapper').length) {
                this.page.wrapper.find('.dropdown-results').removeClass('show');
            }
        });

        // New seller
        this.page.wrapper.on('click', '.new-seller', () => {
            this.create_new_seller();
        });

        // Change seller
        this.page.wrapper.on('click', '.change-seller', () => {
            this.change_seller();
        });

        // Contract duration change
        this.page.wrapper.on('change', '.contract-duration, .grace-period', () => {
            this.update_ownership_days();
        });

        // Quick add buttons
        this.page.wrapper.on('click', '.quick-add', (e) => {
            const category = $(e.currentTarget).data('category');
            this.add_item(category);
        });

        // Process intake
        this.page.wrapper.on('click', '.process-intake', () => {
            this.process_intake();
        });

        // Clear all
        this.page.wrapper.on('click', '.clear-all', () => {
            if (confirm('Clear all items and start over?')) {
                this.clear_all();
            }
        });

        // Remove item
        this.page.wrapper.on('click', '.remove-item', (e) => {
            $(e.currentTarget).closest('tr').fadeOut(200, function() {
                $(this).remove();
                me.update_totals();
            });
        });

        // Update totals on value change
        this.page.wrapper.on('change', '.item-price, .item-commission', () => {
            this.update_totals();
        });

        // Tab navigation in item rows
        this.page.wrapper.on('keydown', 'input, select', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                const $input = $(e.currentTarget);
                const $tr = $input.closest('tr');
                const $lastInput = $tr.find('input:last, select:last').filter(':visible');

                if ($input.is($lastInput)) {
                    e.preventDefault();
                    this.add_item('');
                }
            }
        });
    }

    load_brands() {
        // Load all unique brands from Items
        frappe.call({
            method: 'frappe.client.get_list',
            args: {
                doctype: 'Brand',
                fields: ['name'],
                limit_page_length: 0
            },
            callback: (r) => {
                this.brands_cache = r.message || [];
            }
        });
    }

    navigateResults(container, direction) {
        const $results = this.page.wrapper.find(container);
        const $items = $results.find('.dropdown-result');
        const $highlighted = $results.find('.highlighted');

        if (!$items.length) return;

        let index = $highlighted.length ? $items.index($highlighted) : -1;

        if (direction === 'down') {
            index = (index + 1) % $items.length;
        } else {
            index = index <= 0 ? $items.length - 1 : index - 1;
        }

        $items.removeClass('highlighted');
        $items.eq(index).addClass('highlighted');
    }

    update_ownership_days() {
        const duration = parseInt(this.page.wrapper.find('.contract-duration').val()) || 60;
        const grace = parseInt(this.page.wrapper.find('.grace-period').val()) || 14;
        this.page.wrapper.find('.ownership-days').text(duration + grace);
    }

    search_seller(query) {
        const $results = this.page.wrapper.find('.seller-results');

        if (!query) {
            $results.removeClass('show').empty();
            return;
        }

        frappe.call({
            method: 'consignment_store.api.intake.search_consignor',
            args: { query: query },
            callback: (r) => {
                this.show_seller_results(r.message || []);
            }
        });
    }

    show_seller_results(sellers) {
        const $results = this.page.wrapper.find('.seller-results');

        if (!sellers.length) {
            $results.html('<div class="no-results">No sellers found - click "New Seller" to register</div>');
            $results.addClass('show');
            return;
        }

        const html = sellers.map((s, index) => `
            <div class="dropdown-result seller-result ${index === 0 ? 'highlighted' : ''}"
                 data-name="${s.name}">
                <div class="seller-name font-weight-bold">${s.consignor_name}</div>
                <div class="seller-info text-muted small">${s.consignor_code} | ${s.email} | ${s.phone}</div>
            </div>
        `).join('');

        $results.html(html).addClass('show');

        // Bind click
        $results.find('.seller-result').on('click', (e) => {
            const name = $(e.currentTarget).data('name');
            this.select_seller(name);
        });
    }

    select_seller(name) {
        frappe.db.get_doc('Consignor', name).then(doc => {
            this.current_seller = doc;
            this.page.wrapper.find('.seller-search').hide();
            this.page.wrapper.find('.seller-results').removeClass('show').empty();
            this.page.wrapper.find('.selected-seller').show();
            this.page.wrapper.find('.seller-display-name').text(
                `${doc.consignor_name} (${doc.consignor_code})`
            );
            this.page.wrapper.find('.seller-commission-info').html(
                `<br><small>Default Commission: ${doc.default_commission_rate || 50}%</small>`
            );

            // Update commission rates for existing items
            this.page.wrapper.find('.item-commission').each(function() {
                if (!$(this).val()) {
                    $(this).val(doc.default_commission_rate || 50);
                }
            });
        });
    }

    change_seller() {
        this.current_seller = null;
        this.page.wrapper.find('.seller-search').val('').show();
        this.page.wrapper.find('.selected-seller').hide();
    }

    create_new_seller() {
        const dialog = new frappe.ui.Dialog({
            title: '👤 New Seller Registration',
            fields: [
                {
                    label: 'Full Name',
                    fieldname: 'consignor_name',
                    fieldtype: 'Data',
                    reqd: 1
                },
                {
                    label: 'Email',
                    fieldname: 'email',
                    fieldtype: 'Data',
                    options: 'Email',
                    reqd: 1
                },
                {
                    label: 'Phone',
                    fieldname: 'phone',
                    fieldtype: 'Data',
                    reqd: 1
                },
                {
                    fieldtype: 'Column Break'
                },
                {
                    label: 'ID/Passport Number',
                    fieldname: 'id_number',
                    fieldtype: 'Data'
                },
                {
                    label: 'City',
                    fieldname: 'city',
                    fieldtype: 'Data'
                },
                {
                    label: 'Default Commission %',
                    fieldname: 'default_commission_rate',
                    fieldtype: 'Int',
                    default: 50
                },
                {
                    fieldtype: 'Section Break'
                },
                {
                    label: 'Payment Method',
                    fieldname: 'payment_method',
                    fieldtype: 'Select',
                    options: 'Bank Transfer\nPayPal\nCash\nStore Credit',
                    default: 'Bank Transfer'
                }
            ],
            primary_action_label: 'Create',
            primary_action: (values) => {
                frappe.call({
                    method: 'consignment_store.api.intake.create_consignor',
                    args: values,
                    callback: (r) => {
                        if (r.message) {
                            this.select_seller(r.message.name);
                            dialog.hide();
                            frappe.show_alert({
                                message: '✅ Seller registered successfully',
                                indicator: 'green'
                            });
                        }
                    }
                });
            }
        });
        dialog.show();
    }

    add_item(category = '') {
        const id = frappe.utils.get_random(10);
        const commission = this.current_seller?.default_commission_rate || 50;

        const row = `
            <tr data-id="${id}" class="item-row">
                <td>
                    <input type="text" class="form-control form-control-sm item-desc"
                        placeholder="Description..." value="${category}">
                </td>
                <td>
                    <div class="brand-search-wrapper">
                        <input type="text" class="form-control form-control-sm item-brand"
                            placeholder="Brand... (Tab to select)" autocomplete="off">
                        <div class="brand-results dropdown-results"></div>
                    </div>
                </td>
                <td>
                    <select class="form-control form-control-sm item-size">
                        <option value="">-</option>
                        <option>XS</option>
                        <option>S</option>
                        <option>M</option>
                        <option>L</option>
                        <option>XL</option>
                        <option>XXL</option>
                        <option>One Size</option>
                    </select>
                </td>
                <td>
                    <input type="text" class="form-control form-control-sm item-color"
                        placeholder="Color">
                </td>
                <td>
                    <select class="form-control form-control-sm item-condition">
                        <option>New</option>
                        <option>Excellent</option>
                        <option selected>Good</option>
                        <option>Fair</option>
                    </select>
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm item-price"
                        placeholder="0.00" step="0.01" min="0">
                </td>
                <td>
                    <input type="number" class="form-control form-control-sm item-commission"
                        value="${commission}" min="0" max="100">
                </td>
                <td>
                    <button class="btn btn-sm btn-danger remove-item" title="Remove">
                        <i class="fa fa-trash"></i>
                    </button>
                </td>
            </tr>
        `;

        this.page.wrapper.find('.items-tbody').append(row);

        const $newRow = this.page.wrapper.find(`tr[data-id="${id}"]`);
        $newRow.find('.item-desc').focus();

        // Bind brand search events for this row
        this.bindBrandSearch($newRow);

        this.update_totals();
    }

    bindBrandSearch($row) {
        const me = this;
        const $brandInput = $row.find('.item-brand');
        const $brandResults = $row.find('.brand-results');

        // Brand search input
        $brandInput.on('input', frappe.utils.debounce((e) => {
            const query = e.target.value;
            this.searchBrands(query, $brandResults, $brandInput);
        }, 300));

        // Brand keyboard navigation
        $brandInput.on('keydown', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                const $firstResult = $brandResults.find('.dropdown-result:first');

                if ($firstResult.length && $brandResults.hasClass('show')) {
                    e.preventDefault();

                    if ($firstResult.hasClass('create-new')) {
                        const brandName = $brandInput.val();
                        this.createBrand(brandName, $brandInput, $brandResults);
                    } else {
                        const brand = $firstResult.data('brand');
                        this.selectBrand(brand, $brandInput, $brandResults);
                    }

                    // Move to next field
                    setTimeout(() => {
                        $row.find('.item-size').focus();
                    }, 100);
                }
            } else if (e.key === 'ArrowDown') {
                e.preventDefault();
                this.navigateBrandResults($brandResults, 'down');
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                this.navigateBrandResults($brandResults, 'up');
            } else if (e.key === 'Enter') {
                const $highlighted = $brandResults.find('.highlighted');
                if ($highlighted.length) {
                    e.preventDefault();

                    if ($highlighted.hasClass('create-new')) {
                        const brandName = $brandInput.val();
                        this.createBrand(brandName, $brandInput, $brandResults);
                    } else {
                        const brand = $highlighted.data('brand');
                        this.selectBrand(brand, $brandInput, $brandResults);
                    }
                }
            } else if (e.key === 'Escape') {
                $brandResults.removeClass('show').empty();
            }
        });

        // Click outside to close
        $brandInput.on('blur', () => {
            setTimeout(() => {
                if (!$brandResults.is(':hover')) {
                    $brandResults.removeClass('show');
                }
            }, 200);
        });
    }

    searchBrands(query, $results, $input) {
        if (!query) {
            $results.removeClass('show').empty();
            return;
        }

        // Search in cached brands
        const matches = this.brands_cache.filter(b =>
            b.name.toLowerCase().includes(query.toLowerCase())
        ).slice(0, 10);

        this.showBrandResults(matches, query, $results, $input);
    }

    showBrandResults(brands, query, $results, $input) {
        let html = '';

        if (brands.length === 0) {
            html = `
                <div class="dropdown-result create-new highlighted" data-brand="${query}">
                    <i class="fa fa-plus"></i> Create new brand: "<strong>${query}</strong>"
                </div>
            `;
        } else {
            html = brands.map((b, index) => `
                <div class="dropdown-result ${index === 0 ? 'highlighted' : ''}"
                     data-brand="${b.name}">
                    ${b.name}
                </div>
            `).join('');

            // Add create option if exact match not found
            const exactMatch = brands.find(b => b.name.toLowerCase() === query.toLowerCase());
            if (!exactMatch) {
                html += `
                    <div class="dropdown-result create-new" data-brand="${query}">
                        <i class="fa fa-plus"></i> Create new brand: "<strong>${query}</strong>"
                    </div>
                `;
            }
        }

        $results.html(html).addClass('show');

        // Bind click events
        $results.find('.dropdown-result').on('click', (e) => {
            const $item = $(e.currentTarget);
            const brand = $item.data('brand');

            if ($item.hasClass('create-new')) {
                this.createBrand(brand, $input, $results);
            } else {
                this.selectBrand(brand, $input, $results);
            }
        });
    }

    navigateBrandResults($results, direction) {
        const $items = $results.find('.dropdown-result');
        const $highlighted = $results.find('.highlighted');

        if (!$items.length) return;

        let index = $highlighted.length ? $items.index($highlighted) : -1;

        if (direction === 'down') {
            index = (index + 1) % $items.length;
        } else {
            index = index <= 0 ? $items.length - 1 : index - 1;
        }

        $items.removeClass('highlighted');
        $items.eq(index).addClass('highlighted');
    }

    selectBrand(brand, $input, $results) {
        $input.val(brand);
        $results.removeClass('show').empty();
    }

    createBrand(brandName, $input, $results) {
        if (!brandName) return;

        frappe.call({
            method: 'frappe.client.insert',
            args: {
                doc: {
                    doctype: 'Brand',
                    brand: brandName
                }
            },
            callback: (r) => {
                if (r.message) {
                    // Add to cache
                    this.brands_cache.push({name: brandName});

                    // Set the value
                    $input.val(brandName);
                    $results.removeClass('show').empty();

                    frappe.show_alert({
                        message: `Brand "${brandName}" created`,
                        indicator: 'green'
                    }, 3);
                }
            },
            error: (r) => {
                // If brand already exists or other error
                $input.val(brandName);
                $results.removeClass('show').empty();
            }
        });
    }

    update_totals() {
        let total = 0;
        let commission = 0;
        let count = 0;

        this.page.wrapper.find('.items-tbody tr').each((i, row) => {
            const price = parseFloat($(row).find('.item-price').val()) || 0;
            const comm_rate = parseFloat($(row).find('.item-commission').val()) || 0;
            total += price;
            commission += (price * comm_rate / 100);
            count++;
        });

        this.page.wrapper.find('.total-value').text(`€${total.toFixed(2)}`);
        this.page.wrapper.find('.expected-commission').text(`€${commission.toFixed(2)}`);
        this.page.wrapper.find('.total-items').text(`${count} items`);
    }

    get_items_data() {
        const items = [];

        this.page.wrapper.find('.items-tbody tr').each((i, row) => {
            const $row = $(row);
            const item = {
                description: $row.find('.item-desc').val(),
                brand: $row.find('.item-brand').val(),
                size: $row.find('.item-size').val(),
                color: $row.find('.item-color').val(),
                condition: $row.find('.item-condition').val(),
                price: parseFloat($row.find('.item-price').val()) || 0,
                commission_rate: parseFloat($row.find('.item-commission').val()) || 50
            };

            if (item.description && item.price > 0) {
                items.push(item);
            }
        });

        return items;
    }

    process_intake() {
        if (!this.current_seller) {
            frappe.msgprint('⚠️ Please select a seller first');
            return;
        }

        const items = this.get_items_data();

        if (!items.length) {
            frappe.msgprint('⚠️ Please add at least one item with description and price');
            return;
        }

        const duration = parseInt(this.page.wrapper.find('.contract-duration').val()) || 60;
        const grace = parseInt(this.page.wrapper.find('.grace-period').val()) || 14;

        frappe.call({
            method: 'consignment_store.api.intake.process_intake',
            args: {
                consignor: this.current_seller.name,
                items: items,
                contract_duration: duration,
                grace_period: grace
            },
            freeze: true,
            freeze_message: '📝 Creating contract and items...',
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.handle_success(r.message);
                }
            }
        });
    }

    handle_success(result) {
        // Show success message
        frappe.show_alert({
            message: `✅ Contract ${result.contract_id} created with ${result.items_count} items`,
            indicator: 'green'
        }, 5);

        // Open print dialogs
        this.print_documents(result);

        // Store for reprint
        this.last_result = result;
        this.page.wrapper.find('.print-labels-only').show();

        // Clear form for next intake
        this.clear_items();
    }

    print_documents(result) {
        // Print contract
        const contract_window = window.open('', 'contract', 'width=800,height=600');
        contract_window.document.write(result.contract_html);
        contract_window.document.close();

        // Print labels
        setTimeout(() => {
            const labels_window = window.open('', 'labels', 'width=800,height=600');
            labels_window.document.write(result.labels_html);
            labels_window.document.close();

            // Auto print after load
            setTimeout(() => {
                contract_window.print();
                labels_window.print();
            }, 500);
        }, 100);
    }

    clear_items() {
        this.page.wrapper.find('.items-tbody').empty();
        this.update_totals();
    }

    clear_all() {
        this.change_seller();
        this.clear_items();
        this.page.wrapper.find('.contract-duration').val(60);
        this.page.wrapper.find('.grace-period').val(14);
        this.update_ownership_days();
        this.page.wrapper.find('.print-labels-only').hide();
    }
}
