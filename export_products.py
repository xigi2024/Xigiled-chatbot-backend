import os
import django
from openpyxl import Workbook

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myassistant.settings')
django.setup()

from Alexa.models import Product

def export_products_to_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Products"

    # Headers
    headers = ['Name', 'Description', 'Price', 'Category', 'Guide Steps']
    ws.append(headers)

    # Fetch all products
    products = Product.objects.all()
    for product in products:
        guide_steps_text = '\n'.join(product.guide_steps) if product.guide_steps else ''
        row = [
            product.name,
            product.description,
            product.price,
            product.category or '',
            guide_steps_text
        ]
        ws.append(row)

    # Save the file
    wb.save('products.xlsx')
    print("Exported products to products.xlsx")

if __name__ == '__main__':
    export_products_to_excel()
