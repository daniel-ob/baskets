import io

from django.contrib.auth import get_user_model
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from xlsxwriter.workbook import Workbook

from baskets.models import Delivery, Producer


def get_order_forms_xlsx(delivery):
    """Generate an 'in memory' Excel workbook containing order forms for given delivery, one sheet per user order"""

    # Create a file-like buffer
    buffer = io.BytesIO()

    # Create the Workbook object, using the buffer as its "file"
    workbook = Workbook(buffer, {'in_memory': True})

    # Add formats
    bold = workbook.add_format({'bold': True})
    bold_right = workbook.add_format({'bold': True, 'align': 'right'})
    shrink = workbook.add_format({'shrink': True})  # shrink text so that it fits in a cell
    money = workbook.add_format({'num_format': '0.00 €'})

    for order in delivery.orders.all():
        worksheet = workbook.add_worksheet(order.user.username)

        # order header
        row = 0
        col = 0
        worksheet.write(row, col, "Commande de paniers", bold)
        worksheet.write(row + 1, col, "Livraison du")
        worksheet.write(row + 1, col + 1, str(delivery.date.strftime("%d/%m/%Y")))

        # user info
        row = 3
        worksheet.write(row, col, "Utilisateur")
        worksheet.write(row, col + 1, f"{order.user.first_name} {order.user.last_name}", bold)
        worksheet.write(row + 1, col, "Groupe")
        worksheet.write(row + 1, col + 1, order.user.groups.first().name if order.user.groups.first() else "")
        worksheet.write(row + 2, col, "Téléphone")
        worksheet.write(row + 2, col + 1, order.user.phone)

        # order items headers
        row = 7
        worksheet.write(row, col, "Produit", bold)
        worksheet.write(row, col + 1, "Prix unitaire", bold_right)
        worksheet.write(row, col + 2, "Quantité", bold_right)
        worksheet.write(row, col + 3, "Montant", bold_right)
        row += 1

        # order items
        for item in order.items.all():
            worksheet.write_string(row, col, item.product.name, shrink)
            worksheet.write_number(row, col + 1, item.product.unit_price, money)
            worksheet.write_number(row, col + 2, item.quantity)
            worksheet.write_number(row, col + 3, item.amount, money)
            row += 1

        # set columns width
        worksheet.set_column('A:A', 35)
        worksheet.set_column('B:D', 13)

        # order total
        row += 1  # one empty row
        worksheet.write(row, col + 2, "Total", bold_right)
        worksheet.write_number(row, col + 3, order.amount, money)

    workbook.close()

    buffer.seek(0)  # set pointer to beginning
    return buffer


def get_all_delivery_dates():
    return Delivery.objects.all().values_list(
        "date__year", "date__month"
    ).order_by(
        "date__year", "date__month"
    ).distinct()


def get_amounts_per_user_and_month():
    amounts_per_user_and_month = {}
    for month in get_all_delivery_dates():
        amounts_per_user = get_user_model().objects.annotate(
            total_amount=Coalesce(
                Sum(
                    "orders__amount",
                    filter=Q(orders__delivery__date__year=month[0], orders__delivery__date__month=month[1])
                ),
                0,
                output_field=DecimalField()
            )
        ).values(
            "username", "total_amount"
        ).order_by("username")

        amounts_per_user_and_month[month] = {
            item["username"]: item["total_amount"]
            for item in amounts_per_user
        }

    return amounts_per_user_and_month


def get_orders_export_xlsx():
    """Generate an 'in memory' Excel workbook containing total order amount per user and month"""

    # Create Workbook, using file-like buffer
    buffer = io.BytesIO()
    workbook = Workbook(buffer, {'in_memory': True})
    worksheet = workbook.add_worksheet("commandes")

    # Add formats
    bold = workbook.add_format({'bold': True})
    money = workbook.add_format({'num_format': '0.00 €'})

    # Write headers
    row_num = 0
    col_num = 0
    worksheet.write(row_num, col_num, "Année_Mois", bold)
    for username in list(get_amounts_per_user_and_month().values())[0]:
        col_num += 1
        worksheet.write(row_num, col_num, username, bold)

    # Write data
    row_num += 1
    for (year, month), amounts_per_user in get_amounts_per_user_and_month().items():
        col_num = 0
        worksheet.write(row_num, col_num, f"{year}_{month}", bold)
        for username, total_order_amount in amounts_per_user.items():
            col_num += 1
            worksheet.write(row_num, col_num, total_order_amount, money)
        row_num += 1

    workbook.close()
    buffer.seek(0)  # set pointer to the beginning
    return buffer


def get_producer_export_xlsx():
    """Generate an 'in memory' Excel workbook containing summary of one sheet per producer with
    total ordered quantity per product and month"""

    buffer = io.BytesIO()
    workbook = Workbook(buffer, {'in_memory': True})

    for producer in Producer.objects.all():
        worksheet = workbook.add_worksheet(producer.name)

        # Prepare data
        quantity_per_product_and_month = {
            product: {
                month: product.order_items.aggregate(
                    total_quantity=Coalesce(
                        Sum(
                            "quantity",
                            filter=Q(order__delivery__date__year=month[0], order__delivery__date__month=month[1])
                        ),
                        0,
                        output_field=DecimalField()
                    )
                )
                for month in get_all_delivery_dates()
            }
            for product in producer.products.all()
        }

        # Add formats
        bold = workbook.add_format({'bold': True})

        # Write header
        worksheet.write(0, 0, "Produit", bold)
        # Write data
        for row_num, (product, value) in enumerate(quantity_per_product_and_month.items(), start=1):
            col_num = 0
            worksheet.write(row_num, col_num, product.name)
            for (year, month), quantity in value.items():
                col_num += 1
                worksheet.write(0, col_num, f"{year}_{month}", bold)
                worksheet.write(row_num, col_num, quantity["total_quantity"])

        # force 1st column width
        worksheet.set_column('A:A', 35)

    workbook.close()
    buffer.seek(0)
    return buffer
