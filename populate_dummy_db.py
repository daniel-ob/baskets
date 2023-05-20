from datetime import timedelta, date

from baskets.models import Producer, Product, Delivery
from django.contrib.auth.models import Group

# Groups
Group.objects.create(name="Members")
Group.objects.create(name="Guests")

# Producers
bourginon = Producer.objects.create(name="Beef Bourginon")
garden = Producer.objects.create(name="The Edible Garden")
moulin = Producer.objects.create(name="The Moulin")
hens = Producer.objects.create(name="Plein'Air Hens")

# Products
meat = Product.objects.create(producer=bourginon, name="Package of meat (5kg)", unit_price=110)
little_veg = Product.objects.create(producer=garden, name="Little vegetables basket", unit_price=11)
big_veg = Product.objects.create(producer=garden, name="Big vegetables basket", unit_price=17)
flour1 = Product.objects.create(producer=moulin, name="Semi-whole wheat flour 1kg", unit_price=3)
flour2 = Product.objects.create(producer=moulin, name="Chickpea flour 1kg", unit_price=5)
flour3 = Product.objects.create(producer=moulin, name="Semi-whole wheat flour 20kg", unit_price=46)
flour4 = Product.objects.create(producer=moulin, name="Barley flour 1kg", unit_price=3)
flour5 = Product.objects.create(producer=moulin, name="Whole wheat flour 1kg", unit_price=3)
flour6 = Product.objects.create(producer=moulin, name="Whole wheat flour 20kg", unit_price=46)
eggs = Product.objects.create(producer=hens, name="Organic Eggs (x6)", unit_price=2)

# Delivery for next 10 Tuesdays
today = date.today()
for week_i in range(1, 11):
    tuesday_i = today + timedelta(days=-today.weekday()+1, weeks=week_i)
    d = Delivery.objects.create(date=tuesday_i)
    d.products.set([little_veg, big_veg, flour1, flour2, flour3, flour4, flour5, flour6, eggs])
    # meet available every 2 weeks
    if week_i % 2:
        d.products.add(meat)
