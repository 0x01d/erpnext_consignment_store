// consignment_store/consignment_store/page/quick_intake/quick_intake.js
// Updated to work with contracts instead of batches

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
        this.make_page();
        this.bind_events();
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
                                        placeholder="Search by name, phone, email, or code...">
                                    <div class="seller-results"></div>
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
                            <li><strong>NO warehouse value recorded</strong> - items remain consignor's property</li>
                            <li>When sold: Only commission (%) is recognized as income</li>
                            <li>After contract expires: Grace period for pickup</li>
                            <li>Uncollected items: Become store property at 30% markdown</li>
                        </ol>
                    </div>
                </div>
            </div>
        `);
    }

    bind_events() {
        const me = this;

        // Seller search
        this.page.wrapper.on('input', '.seller-search', frappe.utils.debounce((e) => {
            this.search_seller(e.target.value);
        }, 300));

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

        // Tab navigation
        this.page.wrapper.on('keydown', 'input', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                const $input = $(e.currentTarget);
                const $tr = $input.closest('tr');
                const $lastInput = $tr.find('input:last, select:last');

                if ($input.is($lastInput)) {
                    e.preventDefault();
                    this.add_item('');
                }
            }
        });
    }

    update_ownership_days() {
        const duration = parseInt(this.page.wrapper.find('.contract-duration').val()) || 60;
        const grace = parseInt(this.page.wrapper.find('.grace-period').val()) || 14;
        this.page.wrapper.find('.ownership-days').text(duration + grace);
    }

    search_seller(query) {
        if (!query) {
            this.page.wrapper.find('.seller-results').empty();
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
            $results.html('<div class="no-results p-2 text-muted">No sellers found - click "New Seller" to register</div>');
            return;
        }

        const html = sellers.map(s => `
            <div class="seller-result p-2 border-bottom" data-name="${s.name}" style="cursor: pointer;">
                <div class="seller-name font-weight-bold">${s.consignor_name}</div>
                <div class="seller-info text-muted small">${s.consignor_code} | ${s.email} | ${s.phone}</div>
            </div>
        `).join('');

        $results.html(html);

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
            this.page.wrapper.find('.seller-results').empty();
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
                    <input type="text" class="form-control form-control-sm item-brand"
                        placeholder="Brand">
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
        this.page.wrapper.find(`tr[data-id="${id}"] .item-desc`).focus();
        this.update_totals();
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
