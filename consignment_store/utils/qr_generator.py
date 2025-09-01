# consignment_store/utils/qr_generator.py
import frappe
import qrcode
import io
import base64
from PIL import Image

class QRGenerator:
    def generate_qr_for_item(self, doc, method=None):
        """Generate QR code when item is created"""
        if not doc.is_consignment:
            return

        # Generate QR data
        qr_data = doc.consignment_code

        # Create QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")

        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()

        # Save to item
        doc.db_set('qr_code_data', img_str, update_modified=False)

    def generate_batch_labels(self, items):
        """Generate HTML for printing labels"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                @page { size: letter; margin: 0.5in; }
                body { margin: 0; padding: 0; }
                .labels-grid {
                    display: grid;
                    grid-template-columns: repeat(4, 2in);
                    gap: 0.125in;
                }
                .label {
                    width: 2in;
                    height: 2in;
                    border: 1px dashed #ccc;
                    padding: 0.1in;
                    box-sizing: border-box;
                    text-align: center;
                    font-family: Arial, sans-serif;
                }
                .qr { margin: 5px auto; }
                .item-name {
                    font-size: 9pt;
                    font-weight: bold;
                    height: 2em;
                    overflow: hidden;
                    margin: 5px 0;
                }
                .price {
                    font-size: 16pt;
                    font-weight: bold;
                    margin: 5px 0;
                }
                .code {
                    font-size: 8pt;
                    color: #666;
                    margin-top: 5px;
                }
                @media print {
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <button class="no-print" onclick="window.print()"
                style="position:fixed;top:10px;right:10px;padding:10px;">
                Print Labels
            </button>
            <div class="labels-grid">
        """

        for item in items:
            # Get or generate QR
            qr_data = item.qr_code_data
            if not qr_data:
                self.generate_qr_for_item(item)
                qr_data = item.qr_code_data

            html += f"""
                <div class="label">
                    <img class="qr" src="data:image/png;base64,{qr_data}"
                        width="80" height="80">
                    <div class="item-name">{item.item_name[:40]}</div>
                    <div class="price">${item.standard_rate:.2f}</div>
                    <div class="code">{item.consignment_code}</div>
                </div>
            """

        html += """
            </div>
        </body>
        </html>
        """

        return html

# Module function for hooks
def generate_qr_for_item(doc, method=None):
    """Hook function to generate QR for items"""
    generator = QRGenerator()
    generator.generate_qr_for_item(doc, method)
