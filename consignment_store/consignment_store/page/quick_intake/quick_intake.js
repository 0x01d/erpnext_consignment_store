// consignment_store/consignment_store/page/quick_intake/quick_intake.js
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
                <div class="seller-section card">
                    <div class="card-header">
                        <h4>Seller Information</h4>
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
                                    <div class="alert alert-info">
                                        <strong class="seller-display-name"></strong>
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

                <div class="items-section card mt-3">
                    <div class="card-header">
                        <h4>Add Items</h4>
                    </div>
                    <div class="card-body">
                        <div class="quick-buttons mb-3">
                            <button class="btn btn-default quick-add" data-category="Shirt">👔 Shirt</button>
                            <button class="btn btn-default quick-add" data-category="Pants">👖 Pants</button>
                            <button class="btn btn-default quick-add" data-category="Dress">👗 Dress</button>
                            <button class="btn btn-default quick-add" data-category="Jacket">🧥 Jacket</button>
                            <button class="btn btn-default quick-add" data-category="Shoes">👟 Shoes</button>
                            <button class="btn btn-default quick-add" data-category="Bag">👜 Bag</button>
                            <button class="btn btn-default quick-add" data-category="Accessory">💍 Accessory</button>
                        </div>

                        <table class="table table-bordered items-table">
                            <thead>
                                <tr>
                                    <th width="25%">Description</th>
                                    <th width="15%">Brand</th>
                                    <th width="10%">Size</th>
                                    <th width="10%">Color</th>
                                    <th width="10%">Condition</th>
                                    <th width="10%">Price</th>
                                    <th width="10%">Comm %</th>
                                    <th width="10%">Actions</th>
                                </tr>
                            </thead>
                            <tbody class="items-tbody"></tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="5"><strong>Total</strong></td>
                                    <td><strong class="total-value">$0.00</strong></td>
                                    <td colspan="2">
                                        <strong class="total-items">0 items</strong>
                                    </td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>

                <div class="actions-section mt-3">
                    <button class="btn btn-lg btn-success process-intake">
                        <i class="fa fa-check"></i> Process & Print Labels
                    </button>
                    <button class="btn btn-lg btn-default clear-all">
                        <i class="fa fa-times"></i> Clear All
                    </button>
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
            this.clear_all();
        });

        // Remove item
        this.page.wrapper.on('click', '.remove-item', (e) => {
            $(e.currentTarget).closest('tr').remove();
            this.update_totals();
        });

        // Update totals on value change
        this.page.wrapper.on('change', '.item-price', () => {
            this.update_totals();
        });

        // Tab navigation
        this.page.wrapper.on('keydown', 'input', (e) => {
            if (e.key === 'Tab' && !e.shiftKey) {
                const $input = $(e.currentTarget);
                const $tr = $input.closest('tr');
                const $lastInput = $tr.find('input:last');

                if ($input.is($lastInput)) {
                    e.preventDefault();
                    this.add_item('');
                }
            }
        });
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
            $results.html('<div class="no-results">No sellers found</div>');
            return;
        }

        const html = sellers.map(s => `
            <div class="seller-result" data-name="${s.name}">
                <div class="seller-name">${s.consignor_name}</div>
                <div class="seller-info">${s.consignor_code} | ${s.email} | ${s.phone}</div>
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
        });
    }

    change_seller() {
        this.current_seller = null;
        this.page.wrapper.find('.seller-search').val('').show();
        this.page.wrapper.find('.selected-seller').hide();
    }

    create_new_seller() {
        const dialog = new frappe.ui.Dialog({
            title: 'New Seller Registration',
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
                    label: 'ID Number',
                    fieldname: 'id_number',
                    fieldtype: 'Data'
                },
                {
                    label: 'City',
                    fieldname: 'city',
                    fieldtype: 'Data'
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
                                message: 'Seller created successfully',
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
            <tr data-id="${id}">
                <td>
                    <input type="text" class="form-control input-sm item-desc"
                        placeholder="Description..." value="${category}">
                </td>
                <td>
                    <input type="text" class="form-control input-sm item-brand"
                        placeholder="Brand">
                </td>
                <td>
                    <select class="form-control input-sm item-size">
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
                    <input type="text" class="form-control input-sm item-color"
                        placeholder="Color">
                </td>
                <td>
                    <select class="form-control input-sm item-condition">
                        <option>New</option>
                        <option>Excellent</option>
                        <option selected>Good</option>
                        <option>Fair</option>
                    </select>
                </td>
                <td>
                    <input type="number" class="form-control input-sm item-price"
                        placeholder="0.00" step="0.01" min="0">
                </td>
                <td>
                    <input type="number" class="form-control input-sm item-commission"
                        value="${commission}" min="0" max="100">
                </td>
                <td>
                    <button class="btn btn-xs btn-danger remove-item">
                        <i class="fa fa-times"></i>
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
        let count = 0;

        this.page.wrapper.find('.items-tbody tr').each((i, row) => {
            const price = parseFloat($(row).find('.item-price').val()) || 0;
            total += price;
            count++;
        });

        this.page.wrapper.find('.total-value').text(`$${total.toFixed(2)}`);
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
            frappe.msgprint('Please select a seller first');
            return;
        }

        const items = this.get_items_data();

        if (!items.length) {
            frappe.msgprint('Please add at least one item with description and price');
            return;
        }

        frappe.call({
            method: 'consignment_store.api.intake.process_intake',
            args: {
                consignor: this.current_seller.name,
                items: items
            },
            freeze: true,
            freeze_message: 'Processing intake...',
            callback: (r) => {
                if (r.message && r.message.success) {
                    this.print_labels_and_receipt(r.message);
                    this.clear_all();
                    frappe.show_alert({
                        message: `Successfully processed ${r.message.items_count} items`,
                        indicator: 'green'
                    });
                }
            }
        });
    }

    print_labels_and_receipt(result) {
        // Open print window
        const print_window = window.open('', '_blank');
        print_window.document.write(result.labels_html);
        print_window.document.close();

        // Auto print
        setTimeout(() => {
            print_window.print();
        }, 500);
    }

    clear_all() {
        this.change_seller();
        this.page.wrapper.find('.items-tbody').empty();
        this.update_totals();
    }
}
