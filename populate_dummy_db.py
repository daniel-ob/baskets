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
for producer, product_name, product_unit_price in [
    (bourginon, "Package of meat (5kg)", 110),
    (garden, "Little vegetables basket", 11),
    (garden, "Big vegetables basket", 17),
    (moulin, "Semi-whole wheat flour 1kg", 3),
    (moulin, "Chickpea flour 1kg", 5),
    (moulin, "Semi-whole wheat flour 20kg", 46),
    (moulin, "Barley flour 1kg", 3),
    (moulin, "Whole wheat flour 1kg", 3),
    (moulin, "Whole wheat flour 20kg", 46),
    (hens, "Organic Eggs (x6)", 2),
]:
    Product.objects.create(
        producer=producer, name=product_name, unit_price=product_unit_price
    )


# Delivery for next 10 Tuesdays
today = date.today()
for week_i in range(1, 11):
    tuesday_i = today + timedelta(days=-today.weekday() + 1, weeks=week_i)
    d = Delivery.objects.create(date=tuesday_i)
    d.products.set(Product.objects.exclude(name__contains="meat"))
    # meat available every 2 weeks
    meat = Product.objects.filter(name__contains="meat").first()
    if week_i % 2:
        d.products.add(meat)
