from io import BytesIO

import openpyxl
from django.urls import reverse

from baskets.tests.common import BasketsTestCase


class TestExports(BasketsTestCase):
    def test_delivery_export_success(self):
        d = self.d2
        # staff member required for export
        self.u1.is_staff = True
        self.u1.save()
        self.client.force_login(self.u1)
        response = self.client.get(reverse("delivery_export", args=[d.id]))
        self.assertEqual(response.status_code, 200)

        self.assertIn(
            f"filename={str(d.date)}", response.headers["Content-Disposition"]
        )
        wb = openpyxl.load_workbook(BytesIO(response.content))
        self.assertEqual(len(wb.worksheets), d.orders.count())
        sheets = {sheet.title: sheet for sheet in wb.worksheets}
        for order in d.orders.all():
            self.assertIn(order.user.username, sheets.keys())
            sheet = sheets[order.user.username]
            rows = list(sheet.iter_rows(values_only=True))
            order_amount = rows[-1][-1]
            self.assertEqual(f"{order_amount:.2f}", f"{order.amount:.2f}")

    def test_delivery_export_not_staff(self):
        url = reverse("delivery_export", args=[self.d2.id])
        response = self.client.get(url)
        self.assertRedirects(response, f"{reverse('admin:login')}?next={url}")
