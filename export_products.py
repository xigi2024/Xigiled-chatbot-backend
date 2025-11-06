import os
import django
import openpyxl

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myassistant.settings')
django.setup()

from Alexa.models import Product

def export_products_to_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Products"

    # Headers
    headers = ['Name', 'Description', 'Price', 'Category', 'Guide Steps']
    ws.append(headers)

    # Query all products
    products = Product.objects.all()

    for product in products:
        # Combine guide_steps into a single string with line breaks
        guide_steps_str = '\n'.join(product.guide_steps) if product.guide_steps else ''

        row = [
            product.name,
            product.description,
            product.price,
            product.category or '',
            guide_steps_str
        ]
        ws.append(row)

    wb.save('products.xlsx')
    print("Products exported to products.xlsx")

if __name__ == '__main__':
    export_products_to_excel()
