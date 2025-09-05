# consignment_store/consignment_store/doctype/consignment_contract/consignment_contract.py
import frappe
from frappe.model.document import Document
from frappe.utils import nowdate, add_days, flt, now_datetime
from frappe import _
import hashlib
import base64

class ConsignmentContract(Document):
    def validate(self):
        self.set_dates()
        self.calculate_totals()
        self.generate_signature_token()

    def set_dates(self):
        """Set contract end and ownership transfer dates"""
        if self.contract_date and self.contract_duration_days:
            self.contract_end_date = add_days(self.contract_date, self.contract_duration_days)
            self.ownership_transfer_date = add_days(
                self.contract_end_date,
                self.grace_period_days or 14
            )

    def calculate_totals(self):
        """Calculate contract totals"""
        self.total_items = len(self.items)
        self.total_retail_value = sum(flt(item.retail_price) for item in self.items)
        self.expected_commission = sum(
            flt(item.retail_price) * flt(item.commission_rate) / 100
            for item in self.items
        )

        # Calculate expected commission for each item
        for item in self.items:
            item.expected_commission = flt(item.retail_price) * flt(item.commission_rate) / 100

    def generate_signature_token(self):
        """Generate unique token for digital signature URL"""
        if not self.signature_token:
            # Create unique hash for this contract
            data = f"{self.consignor}{self.name}{nowdate()}"
            self.signature_token = hashlib.sha256(data.encode()).hexdigest()[:32]

    def on_submit(self):
        """Link items to this contract and send signature request"""
        for item in self.items:
            frappe.db.set_value('Item', item.item_code, {
                'consignment_contract': self.name,
                'consignment_expiry_date': self.contract_end_date,
                'ownership_transfer_date': self.ownership_transfer_date,
                'consignment_status': 'Pending Signature'
            })

        # Send email with signature link
        self.send_signature_request()

    def send_signature_request(self):
        """Send email to consignor with link to digitally sign"""
        consignor = frappe.get_doc('Consignor', self.consignor)

        if not consignor.email:
            return

        signature_url = frappe.utils.get_url(
            f"/seller-portal/sign-contract?token={self.signature_token}"
        )

        message = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #FFB6C1 0%, #E6E6FA 100%); padding: 30px; border-radius: 15px 15px 0 0;">
                <h2 style="color: white; margin: 0; text-align: center;">📝 Contract Ready for Signature</h2>
            </div>

            <div style="padding: 30px; background: #FAFAFA;">
                <p style="font-size: 16px;">Dear <strong>{consignor.consignor_name}</strong>,</p>

                <p>Your consignment contract <strong>{self.name}</strong> is ready for your digital signature.</p>

                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #7B68EE; margin-top: 0;">Contract Details:</h3>
                    <ul style="list-style: none; padding: 0;">
                        <li>📦 <strong>Items:</strong> {self.total_items}</li>
                        <li>💰 <strong>Total Value:</strong> €{self.total_retail_value:.2f}</li>
                        <li>📅 <strong>Duration:</strong> {self.contract_duration_days} days</li>
                        <li>💵 <strong>Expected Commission:</strong> €{self.expected_commission:.2f}</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{signature_url}"
                       style="display: inline-block;
                              background: linear-gradient(135deg, #98FB98 0%, #87CEEB 100%);
                              color: white;
                              padding: 15px 40px;
                              text-decoration: none;
                              border-radius: 25px;
                              font-size: 18px;
                              font-weight: bold;
                              box-shadow: 0 5px 15px rgba(0,0,0,0.1);">
                        ✍️ Sign Contract Now
                    </a>
                </div>

                <p style="color: #999; font-size: 14px; text-align: center;">
                    This link is unique to you. Please do not share it with others.
                </p>
            </div>

            <div style="background: #F0E6FA; padding: 20px; border-radius: 0 0 15px 15px; text-align: center;">
                <p style="margin: 0; color: #666;">Thank you for consigning with us!</p>
            </div>
        </div>
        """

        frappe.sendmail(
            recipients=[consignor.email],
            subject=f"✍️ Sign Your Consignment Contract - {self.name}",
            message=message
        )

    @frappe.whitelist()
    def sign_contract(self, signature_data, signer_name, signer_ip=None):
        """Process digital signature"""
        if self.docstatus != 1:
            frappe.throw(_("Contract must be submitted before signing"))

        if self.consignor_signed:
            frappe.throw(_("Contract has already been signed"))

        # Save signature data
        self.db_set('consignor_signature_data', signature_data)
        self.db_set('consignor_signed', 1)
        self.db_set('consignor_signed_date', now_datetime())
        self.db_set('consignor_signer_name', signer_name)
        self.db_set('consignor_signer_ip', signer_ip)
        self.db_set('contract_status', 'Active')

        # Update all items to Active status
        for item in self.items:
            frappe.db.set_value('Item', item.item_code, 'consignment_status', 'Active')
            item.db_set('status', 'Active')

        # Send confirmation
        self.send_signature_confirmation()

        return {
            'success': True,
            'message': 'Contract signed successfully'
        }

    def send_signature_confirmation(self):
        """Send confirmation email after signing"""
        consignor = frappe.get_doc('Consignor', self.consignor)

        if not consignor.email:
            return

        portal_url = frappe.utils.get_url("/seller-portal")

        message = f"""
        <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background: linear-gradient(135deg, #98FB98 0%, #87CEEB 100%); padding: 30px; border-radius: 15px 15px 0 0;">
                <h2 style="color: white; margin: 0; text-align: center;">✅ Contract Signed Successfully!</h2>
            </div>

            <div style="padding: 30px; background: #FAFAFA;">
                <p style="font-size: 16px;">Dear <strong>{consignor.consignor_name}</strong>,</p>

                <p>Thank you for signing your consignment contract. Your items are now active for sale!</p>

                <div style="background: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <h3 style="color: #7B68EE; margin-top: 0;">What's Next?</h3>
                    <ul style="line-height: 1.8;">
                        <li>Your items will be displayed for {self.contract_duration_days} days</li>
                        <li>You'll receive notifications when items are sold</li>
                        <li>Track your items and earnings in the seller portal</li>
                        <li>Collect unsold items before {self.contract_end_date}</li>
                    </ul>
                </div>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{portal_url}"
                       style="display: inline-block;
                              background: linear-gradient(135deg, #DDA0DD 0%, #87CEEB 100%);
                              color: white;
                              padding: 12px 30px;
                              text-decoration: none;
                              border-radius: 25px;
                              font-size: 16px;
                              font-weight: bold;">
                        📊 View Your Dashboard
                    </a>
                </div>
            </div>
        </div>
        """

        frappe.sendmail(
            recipients=[consignor.email],
            subject=f"✅ Contract {self.name} Signed - Your Items Are Now Active!",
            message=message
        )

    @frappe.whitelist()
    def get_contract_for_signing(token):
        """Get contract details for signing page"""
        contract = frappe.db.get_value('Consignment Contract',
            {'signature_token': token, 'docstatus': 1},
            ['name', 'consignor', 'contract_date', 'contract_end_date',
             'total_items', 'total_retail_value', 'expected_commission',
             'contract_duration_days', 'grace_period_days', 'ownership_transfer_date',
             'consignor_signed', 'consignor_signed_date', 'contract_terms'],
            as_dict=True
        )

        if not contract:
            return None

        # Get consignor details
        consignor = frappe.get_doc('Consignor', contract.consignor)

        # Get items
        items = frappe.db.get_all('Consignment Contract Item',
            filters={'parent': contract.name},
            fields=['item_code', 'item_name', 'retail_price', 'commission_rate',
                   'expected_commission']
        )

        contract['consignor_details'] = consignor
        contract['items'] = items

        return contract

    def on_cancel(self):
        """Unlink items from contract"""
        for item in self.items:
            frappe.db.set_value('Item', item.item_code, {
                'consignment_contract': None,
                'consignment_status': 'Cancelled'
            })

    @frappe.whitelist()
    def process_ownership_transfer(self):
        """Transfer ownership of all unsold items to store"""
        if self.contract_status != 'Awaiting Pickup':
            frappe.throw(_("Can only transfer ownership for contracts awaiting pickup"))

        company = frappe.db.get_single_value('Global Defaults', 'default_company')
        abbr = frappe.db.get_value('Company', company, 'abbr')
        warehouse = f'Stores - {abbr}'

        # Create stock entry for ownership transfer
        stock_entry = frappe.new_doc('Stock Entry')
        stock_entry.stock_entry_type = 'Material Receipt'
        stock_entry.purpose = 'Material Receipt'
        stock_entry.remarks = f"Ownership transfer from contract {self.name}"

        items_transferred = []

        for item in self.items:
            if item.status == 'Active':  # Only transfer unsold items
                # Update item to become stock item at markdown price
                markdown_price = flt(item.retail_price) * 0.3  # 30% of original

                frappe.db.set_value('Item', item.item_code, {
                    'is_stock_item': 1,  # NOW it becomes stock item
                    'is_consignment': 0,  # No longer consignment
                    'consignment_status': 'Ownership Transferred',
                    'standard_rate': markdown_price,
                    'item_group': 'Clearance'
                })

                # Add to stock entry at markdown value
                stock_entry.append('items', {
                    'item_code': item.item_code,
                    't_warehouse': warehouse,
                    'qty': 1,
                    'basic_rate': markdown_price,
                    'valuation_rate': markdown_price
                })

                # Update contract item status
                item.db_set('status', 'Ownership Transferred')
                items_transferred.append(item.item_code)

        if items_transferred:
            stock_entry.insert()
            stock_entry.submit()

            # Update contract status
            self.db_set('contract_status', 'Ownership Transferred')

            # Notify consignor
            self.notify_ownership_transfer(items_transferred)

            frappe.msgprint(f"Transferred ownership of {len(items_transferred)} items")
        else:
            frappe.msgprint("No items to transfer")

    def notify_ownership_transfer(self, items):
        """Send notification to consignor"""
        consignor = frappe.get_doc('Consignor', self.consignor)

        if consignor.email:
            items_list = '<ul>'
            for item_code in items:
                item_name = frappe.db.get_value('Item', item_code, 'item_name')
                items_list += f'<li>{item_name} ({item_code})</li>'
            items_list += '</ul>'

            frappe.sendmail(
                recipients=[consignor.email],
                subject=f"Ownership Transfer - Contract {self.name}",
                message=f"""
                <p>Dear {consignor.consignor_name},</p>

                <p>As per our consignment agreement, ownership of the following
                uncollected items has been transferred to the store:</p>

                {items_list}

                <p>Contract: {self.name}<br>
                Transfer Date: {nowdate()}</p>

                <p>Thank you for consigning with us.</p>
                """
            )
