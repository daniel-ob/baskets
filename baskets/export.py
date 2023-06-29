from io import BytesIO

from django.contrib.auth import get_user_model
from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from xlsxwriter.workbook import Workbook

from baskets.models import Delivery, Producer


class InMemoryWorkbook:
    """Context manager encapsulating xlsxwriter's Workbook and BytesIO buffer"""

    def __init__(self):
        # Create a file-like buffer
        self.buffer = BytesIO()
        # Create the Workbook object, using the buffer as its "file"
        self.workbook = Workbook(self.buffer, {"in_memory": True})

        # Formats
        self.bold = self.workbook.add_format({"bold": True})
        self.bold_right = self.workbook.add_format({"bold": True, "align": "right"})
        self.money = self.workbook.add_format({"num_format": "0.00 €"})
        self.shrink = self.workbook.add_format(
            {"shrink": True}
        )  # shrink text so that it fits in a cell

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.workbook.close()
        # Set pointer to beginning
        self.buffer.seek(0)


def get_order_forms_xlsx(delivery):
    """Generate an 'in memory' Excel workbook containing order forms for given delivery, one sheet per user order"""

    with InMemoryWorkbook() as wb:
        for order in delivery.orders.all():
            worksheet = wb.workbook.add_worksheet(order.user.username)

            # order header
            row = 0
            col = 0
            worksheet.write(row, col, "Commande de paniers", wb.bold)
            worksheet.write(row + 1, col, "Livraison du")
            worksheet.write(row + 1, col + 1, str(delivery.date.strftime("%d/%m/%Y")))

            # user info
            row = 3
            worksheet.write(row, col, "Utilisateur")
            worksheet.write(
                row, col + 1, f"{order.user.first_name} {order.user.last_name}", wb.bold
            )
            worksheet.write(row + 1, col, "Groupe")
            worksheet.write(
                row + 1,
                col + 1,
                order.user.groups.first().name if order.user.groups.first() else "",
            )
            worksheet.write(row + 2, col, "Téléphone")
            worksheet.write(row + 2, col + 1, order.user.phone)

            # order items headers
            row = 7
            worksheet.write(row, col, "Produit", wb.bold)
            worksheet.write(row, col + 1, "Prix unitaire", wb.bold_right)
            worksheet.write(row, col + 2, "Quantité", wb.bold_right)
            worksheet.write(row, col + 3, "Montant", wb.bold_right)
            row += 1

            # order items
            for item in order.items.all():
                worksheet.write_string(row, col, item.product.name, wb.shrink)
                worksheet.write_number(row, col + 1, item.product.unit_price, wb.money)
                worksheet.write_number(row, col + 2, item.quantity)
                worksheet.write_number(row, col + 3, item.amount, wb.money)
                row += 1

            # set columns width
            worksheet.set_column("A:A", 35)
            worksheet.set_column("B:D", 13)

            # order total
            row += 1  # one empty row
            worksheet.write(row, col + 2, "Total", wb.bold_right)
            worksheet.write_number(row, col + 3, order.amount, wb.money)

        return wb.buffer


def get_all_delivery_dates():
    return (
        Delivery.objects.all()
        .values_list("date__year", "date__month")
        .order_by("date__year", "date__month")
        .distinct()
    )


def get_amount_per_user_and_month():
    return {
        user: {
            month: user.orders.aggregate(
                total_amount=Coalesce(
                    Sum(
                        "amount",
                        filter=Q(
                            delivery__date__year=month[0],
                            delivery__date__month=month[1],
                        ),
                    ),
                    0,
                    output_field=DecimalField(),
                )
            )
            for month in get_all_delivery_dates()
        }
        for user in get_user_model().objects.all()
    }


def get_orders_export_xlsx():
    """Generate an 'in memory' Excel workbook containing total order amount per user and month"""

    with InMemoryWorkbook() as wb:
        worksheet = wb.workbook.add_worksheet("commandes")
        for row_num, (user, value) in enumerate(
            get_amount_per_user_and_month().items(), start=1
        ):
            col_num = 0
            worksheet.write(row_num, col_num, user.username, wb.bold)
            for (year, month), amount in value.items():
                col_num += 1
                worksheet.write(0, col_num, f"{year}_{month}", wb.bold)
                worksheet.write(row_num, col_num, amount["total_amount"], wb.money)
        worksheet.set_column("A:A", 20)
        return wb.buffer


def get_quantity_per_producer_and_month(producer):
    return {
        product: {
            month: product.order_items.aggregate(
                total_quantity=Coalesce(
                    Sum(
                        "quantity",
                        filter=Q(
                            order__delivery__date__year=month[0],
                            order__delivery__date__month=month[1],
                        ),
                    ),
                    0,
                    output_field=DecimalField(),
                )
            )
            for month in get_all_delivery_dates()
        }
        for product in producer.products.all()
    }


def get_producer_export_xlsx():
    """Generate an 'in memory' Excel workbook containing summary of one sheet per producer with
    total ordered quantity per product and month"""

    with InMemoryWorkbook() as wb:
        for producer in Producer.objects.all():
            worksheet = wb.workbook.add_worksheet(producer.name)
            # Write data
            for row_num, (product, value) in enumerate(
                get_quantity_per_producer_and_month(producer).items(), start=1
            ):
                col_num = 0
                worksheet.write(row_num, col_num, product.name, wb.bold)
                for (year, month), quantity in value.items():
                    col_num += 1
                    worksheet.write(0, col_num, f"{year}_{month}", wb.bold)
                    worksheet.write(row_num, col_num, quantity["total_quantity"])
            # Force 1st column width
            worksheet.set_column("A:A", 35)
        return wb.buffer
