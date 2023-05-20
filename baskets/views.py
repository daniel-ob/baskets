from datetime import date
import json

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, HttpResponse, HttpResponseNotAllowed, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from .email import email_staff_ask_account_activation, email_staff_contact
from .export import get_order_forms_xlsx, get_orders_export_xlsx, get_producer_export_xlsx
from .forms import BasketsSetPasswordForm, ContactForm, UserForm
from .models import Delivery, Order, OrderItem, Producer, Product, User


@login_required
def index(request):
    """Render 'Next Orders' page: a list of opened deliveries and its related orders in chronological order"""

    opened_deliveries = Delivery.objects.filter(order_deadline__gte=date.today()).order_by("date")

    deliveries_orders = [
        {
            "delivery": d,
            "order": Order.objects.filter(user=request.user, delivery=d).first()
        }
        for d in opened_deliveries
    ]

    return render(request, "baskets/index.html", {
        "title": "Commandes à venir",
        "deliveries_orders": deliveries_orders,
        "producers": Producer.objects.all()
    })


@login_required
def order_history(request):
    """Render 'Order history' page: a list of closed user orders in reverse chronological order"""

    closed_user_orders = Order.objects.filter(
        user=request.user,
        delivery__order_deadline__lt=date.today()
    ).order_by("-delivery__date")

    deliveries_orders = [
        {
            "delivery": o.delivery,
            "order": o
        }
        for o in closed_user_orders
    ]

    return render(request, "baskets/index.html", {
        "title": "Historique",
        "deliveries_orders": deliveries_orders
    })


def login_view(request):
    if request.method != "POST":
        if request.user.is_authenticated:
            return HttpResponseRedirect(reverse("index"))
        else:
            return render(request, "baskets/login.html")

    # Attempt to sign user in
    username = request.POST["username"]
    password = request.POST["password"]
    user = authenticate(request, username=username, password=password)

    if user is None:
        return render(request, "baskets/login.html", {
            "message": "Nom d'utilisateur ou mot de passe invalides."
        })
    login(request, user)
    return HttpResponseRedirect(reverse("index"))


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method != "POST":
        # render empty forms
        return render(request, "baskets/register.html", {
            "user_form": UserForm(),
            "password_form": BasketsSetPasswordForm(user=request.user)
        })

    user_form = UserForm(request.POST)
    password_form = BasketsSetPasswordForm(user=request.user, data=request.POST)
    if not (user_form.is_valid() and password_form.is_valid()):
        # render the same page adding existing forms data, so users can see the errors they made
        return render(request, "baskets/register.html", {
            "user_form": user_form,
            "password_form": password_form
        })

    # Create new user
    user = user_form.save(commit=False)
    # check that passwords matches and save hashed password
    password = password_form.clean_new_password2()
    user.set_password(password)
    # user account will be activated by admin
    user.is_active = False
    user.save()
    email_staff_ask_account_activation(user)
    return render(request, "baskets/register.html", {
        "message": "Votre demande d'inscription a été envoyée aux administrateurs pour validation. "
                   "Vous recevrez un email dès que votre compte sera activé.",
        "user_form": user_form,
        "password_form": password_form
    })


@login_required
def profile(request):
    """User profile:
    - GET: render 'User profile' page
    - POST: update user profile
    """

    user = User.objects.get(username=request.user)
    message = ""

    if request.method == "POST":
        form = UserForm(instance=user, data=request.POST)
        if not form.is_valid():
            # render the same page adding existing form data, so users can see the errors they made
            return render(request, "baskets/profile.html", {
                "form": form
            })
        user.save()
        message = "Vos coordonnées ont été mises à jour avec succès."

    # render user information
    return render(request, "baskets/profile.html", {
        "message": message,
        "form": UserForm(instance=user)
    })


def contact(request):
    """Contact admins:
    - GET: render 'Contact' page
    - POST: submit contact form to admins by email
    """

    message = ""

    if request.method == "POST":
        form = ContactForm(request.POST)
        if not form.is_valid():
            return render(request, "baskets/contact.html", {
                "form": form
            })

        email_staff_contact(
            from_email=form.cleaned_data["from_email"],
            subject=form.cleaned_data["subject"],
            message=form.cleaned_data["message"]
        )
        message = "Votre message a été envoyé."

    default_data = {"from_email": request.user.email if request.user.is_authenticated else None}
    return render(request, "baskets/contact.html", {
        "message": message,
        "form": ContactForm(initial=default_data)
    })


def orders(request):
    """Orders API:
    - GET: Get the list of user orders
    - POST: Create order for given delivery
    """

    # User must be authenticated to create/retrieve orders
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    if request.method == "GET":
        order_list = [
            {
                "id": o.id,
                "delivery_id": o.delivery.id,
            }
            for o in request.user.orders.all().order_by("-delivery__date")
        ]
        return JsonResponse(order_list, safe=False)

    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])

    data = json.loads(request.body)

    # Attempt to retrieve delivery
    d_id = data["delivery_id"]
    d = get_object_or_404(Delivery, pk=d_id)

    # Delivery must be opened (still accepting orders)
    if not d.is_open:
        return JsonResponse({"error": "The order deadline for this delivery has passed"}, status=400)

    # User can only have one order per delivery
    if d.orders.filter(user=request.user):
        return JsonResponse({"error": "User already has an order for this delivery"}, status=400)

    o = Order.objects.create(
        user=request.user,
        delivery=d,
        message=data.get("message", "")
    )

    # Add order items
    if data.get("items") is None:
        o.delete()
        return JsonResponse({"error": "Order must contain at least one item"}, status=400)
    else:
        for item in data["items"]:
            # Attempt to retrieve product
            try:
                product = Product.objects.get(id=item["product_id"])
            except Product.DoesNotExist:
                o.delete()
                return JsonResponse({"error": f"Product with id {item['product_id']} does not exist"}, status=404)
            order_item = OrderItem.objects.create(
                order=o,
                product=product,
                quantity=int(item["quantity"])
            )
            if not order_item.is_valid():
                # Delete order with related items
                o.delete()
                return JsonResponse({"error": "Invalid order. All products must be available in the delivery and "
                                              "quantities must be greater than zero"}, status=400)
        o.save()

    return JsonResponse({
        "message": "Order has been successfully created",
        "url": reverse("order", args=[o.id]),
        "amount": o.amount
    }, status=201)


def order(request, order_id):
    """Order API:
    - GET: Get Order details
    - PUT: Update existing Order (items, message)
    - DELETE: Delete Order
    """

    # User must be authenticated to access orders
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    # Attempt to retrieve order
    o = get_object_or_404(Order, id=order_id)

    # User can only access its own orders
    if o.user != request.user:
        raise PermissionDenied

    if request.method == "GET":
        return JsonResponse(o.serialize())

    elif request.method == "PUT":
        # Orders can only be updated if their related delivery is open
        if not o.delivery.is_open:
            return JsonResponse({"error": "Related delivery is closed. Order can no longer be updated"}, status=400)

        data = json.loads(request.body)

        if data.get("items") is not None:
            # Update order items (add new, remove old)
            old_order_items_ids = [oi.id for oi in o.items.all()]

            for item in data["items"]:
                # Attempt to retrieve product
                try:
                    product = Product.objects.get(id=item["product_id"])
                except Product.DoesNotExist:
                    return JsonResponse({"error": f"Product with id {item['product_id']} does not exist"}, status=404)
                new_order_item = OrderItem(
                    order=o,
                    product=product,
                    quantity=int(item["quantity"])
                )
                if not new_order_item.is_valid():
                    return JsonResponse({"error": "All products must be available in the delivery and "
                                                  "quantities must be greater than zero"}, status=400)
                new_order_item.save()

            OrderItem.objects.filter(id__in=old_order_items_ids).delete()

        if data.get("message") is not None:
            o.message = data["message"]

        o.save()

        return JsonResponse({
            "message": "Order has been successfully updated",
            "amount": "{:.2f}".format(o.amount)
        }, status=200)

    elif request.method == "DELETE":
        o.delete()
        return JsonResponse({
            "message": "Order has been successfully deleted",
        }, status=200)

    else:
        return HttpResponseNotAllowed(["GET", "PUT", "DELETE"])


def deliveries(request):
    """Deliveries API: GET the list of opened deliveries"""

    opened_deliveries = Delivery.objects.filter(order_deadline__gte=date.today()).order_by("date")
    d_list = [
        {
            "id": d.id,
            "date": d.date
        }
        for d in opened_deliveries
    ]
    return JsonResponse(d_list, safe=False)


def delivery(request, delivery_id):
    """Delivery API: GET Delivery details"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    if request.method == "GET":
        return JsonResponse(d.serialize())


@staff_member_required
def delivery_export(request, delivery_id):
    """Download delivery related orders forms"""

    # Attempt to retrieve delivery
    d = get_object_or_404(Delivery, id=delivery_id)

    buffer = get_order_forms_xlsx(d)
    return FileResponse(buffer, as_attachment=True, filename=f"{d.date}_bons_commande.xlsx")


@staff_member_required
def order_export(request):
    """Download orders summary for accounting"""

    buffer = get_orders_export_xlsx()
    return FileResponse(buffer, as_attachment=True, filename="export_commandes.xlsx")


@staff_member_required
def producer_export(request):
    """Download summary of ordered products, one sheet per producer"""

    buffer = get_producer_export_xlsx()
    return FileResponse(buffer, as_attachment=True, filename="export_producteurs.xlsx")
