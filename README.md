# Baskets

A website to manage orders for local food baskets.

Project built using Django, Bootstrap and JavaScript.

![Baskets screenshot](screenshot.png)

Please note that, for the moment, this website is in French. English translation should be added soon.

## Table of contents

1. [Background and goal](#background)
2. [Features](#features)
3. [Dependencies](#dependencies)
4. [Run using Docker](#run)
5. [Tests run](#tests-run)
6. [API Reference](#api-ref)

## Background and goal <a name="background"></a> 

This project has been developed to meet a real need for a local association.

The aforementioned association centralises orders for several local food producers.
Thus, food baskets are delivered regularly to users.

Before the deployment of this application, administrators got orders from users via SMS or email.

`Baskets` app aims to save them time by gathering user orders in one unique tool.

Payments are managed outside this application.

## Features <a name="features"></a> 

### User interface

- **Login** page: Not logged users will be redirected to "Login" page. Where they can log in using their email and password.
- **Register** page: Users can create an account by entering their personal information and setting a password.
  - Passwords are validated to prevent weak passwords.
  - A verification email is sent to user. Users can't log in until email is verified.
- **Next Orders** page: shows the list of deliveries for which we can still order, in chronological order.
  - Clicking on each delivery opens a frame below showing delivery details: date when baskets will be delivered, last day to order and available products arranged by producer.
  - User can create one order per delivery.
  - Orders can be updated or deleted until deadline.
- **Order history** page: shows a list of user's closed orders in reverse chronological order. Clicking on each order will open its details below.
- **Password reset**:
  - In "Login" page, a link allows users to request password reset entering their email address. 
  - If an account exists for that email address, an email is sent with a link to a page allowing to set a new password.
- **Profile** page: clicking on username loads a page where user can view and update its profile information.
- **Contact us** page: a link on page footer loads a page with a contact form. The message will be sent to all staff members.

All functionalities except "contact" requires authentication.

### Admin interface

- **Users** page allows activating/deactivating user accounts and setting user groups.
- **Groups** page allows sending an email to all users in each group via a link.
- **Producers** page allows to: 
  - Manage producers and its products (name and unit price).
  - Export .xlsx file containing recap of monthly quantities ordered for each product (one sheet per producer)
- **Deliveries** page allows to:
  - Set each delivery date, order deadline and available products.
    - If "order deadline" is left blank, it will be set to `ORDER_DEADLINE_DAYS_BEFORE` before delivery date.
  - View **total ordered quantity** for each product to notify producers. A link allows to see all related Order Items.
  - In "Deliveries list" page:
    - View "orders count", which links to related orders.
    - **Export related order forms**: Once a delivery deadline is passed, a link will be shown to download delivery order forms in *xlsx* format. The file will contain one sheet per order including user information and order items.
    - Email users having ordered for selected deliveries.
- **Orders** page allows to:
  - View and update user orders.
  - Export .xlsx file containing recap of monthly order amounts per user.

### Other

- **Soft-delete** has been implemented for `Producer` and `Product` models. When deleting them, by default they are just deactivated. They won't be anymore shown on User or Admin interfaces but we keep them on database.
- **Mobile-responsiveness**: This has been achieved using Bootstrap framework in user interface. Moreover, Django admin interface is also mobile responsive.
- **API**: User orders can be managed using an API. See [API reference](#api-ref) for further details.

## Dependencies <a name="dependencies"></a>

In addition to **Django**, the following libraries has been used:

- **Django-allauth**: to manage user login, register and password reset
- **XlsxWriter**: to create xlsx files in `baskets/export.py`
- **Selenium**: to do browser end-to-end testing in `baskets/tests/test_functional.py`

See required versions in `requirements` folder (pip) or Pipfile (pipenv).

## Run using Docker <a name="run"></a>
 
    $ git clone https://github.com/daniel-ob/baskets.git
    $ cd baskets

Create following env files:

- `.envs/.local/.db`: 

```
POSTGRES_DB=baskets
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password
```

- `.envs/.local/.web`:

```
SECRET_KEY= # set to a unique, unpredictable value
DEBUG=True  # set to False in PROD
ALLOWED_HOSTS=127.0.0.1
DATABASE_URL=postgres://postgres:postgres_password@baskets-db:5432/baskets
SECURE_SSL_REDIRECT=False  # Set to True in PROD
# Email sending
EMAIL_HOST=
EMAIL_HOST_PASSWORD=
EMAIL_HOST_USER=
EMAIL_PORT=
EMAIL_USE_TLS=
DEFAULT_FROM_EMAIL=
```

Then run:

    $ docker-compose up -d

And finally, create a superuser:

    $ docker-compose exec web python manage.py createsuperuser

- User interface: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- Admin interface: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

## Tests run <a name="tests-run"></a>

First launch and apply migrations to `db`:
    
    $ docker-compose up -d
    
Create virtual environment and install dependencies:

    $ pipenv shell
    $ pipenv install --dev

Launch all tests:

    $ python manage.py test

Launch only functional tests:

    $ python manage.py test baskets.tests.test_functional


## API Reference <a name="api-ref"></a>

### List open deliveries

List deliveries for which we can still order.

```
GET /deliveries
```

**Response**

```
 Status: 200 OK
```
```
[
    {
        "id": 5,
        "date": "2021-11-30"
    },
    {
        "id": 6,
        "date": "2021-12-07"
    }
]
```

### Get delivery details

```
GET /deliveries/{delivery_id}
```

**Response**

```
 Status: 200 OK
```
```
{
    "date": "2023-05-30",
    "order_deadline": "2023-05-25",
    "products_by_producer": [
        {
            "id": 1,
            "name": "producer1",
            "products": [
                {
                    "id": 1,
                    "name": "Eggs (6 units)",
                    "unit_price": "2.00"
                },
            ]
        },
        {
            "id": 2,
            "name": "producer2",
            "products": [
                {
                    "id": 2,
                    "name": "Big vegetables basket",
                    "unit_price": "1.15"
                }
            ]
        }
    ],
    "message": "This week meat producer is on vacation",
    "is_open": true
}
```

### List user orders

Requires authentication

```
GET /orders
```

**Response**

```
 Status: 200 OK
```
```
[
    {
        "id": 2,
        "delivery_id": 1
    },
    {
        "id": 38,
        "delivery_id": 3
    }
]
```

### Get order details

Requires authentication

```
GET /orders/{order_id}
```

**Response**

```
 Status: 200 OK
```
```
{
    "delivery_id": 3,
    "items": [
        {
            "product": {
                "id": 2,
                "name": "Big vegetables basket",
                "unit_price": "17.00"
            },
            "quantity": 2,
            "amount": "34.00"
        }
    ],
    "amount": "34.00",
    "message": "API test order"
}
```

### Create an order

Requires authentication

**X-CSRFToken** header must be set to the value of **csrftoken** cookie

```
POST /orders
```
```
{
    "delivery_id": 5,
    "items": [
        {
            "product_id": 1,
            "quantity": 1
        },
        {
            "product_id": 2,
            "quantity": 2
        }
    ],
    "message": "is it possible to come and pick it up the next day?"
}
```

Request must follow this rules:

- delivery must be opened for orders (delivery.is_open == true)
- a user can only post an order per delivery
- order must contain at least one item
- all item products must be available in delivery.products
- all item quantities must be greater than zero

**Response**
```
Status: 201 Created
```
```
{
    "message": "Order has been successfully created",
    "url": "/orders/48",
    "amount": "36.00"
}
```

### Update an order

Requires authentication.

Orders can be updated while related delivery.order_deadline is not passed.

**X-CSRFToken** header must be set to the value of **csrftoken** cookie.

```
PUT /orders/{order_id}
```
```
{
    "items": [
        {
            "product_id": 1,
            "quantity": 2
        },
        {
            "product_id": 3,
            "quantity": 1
        }
    ],
    "message": ""
}
```

Updated items must follow this rules:

- all item products must be available in delivery.products
- all item quantities must be greater than zero

**Response**

```
 Status: 200 OK
```
```
{
    "message": "Order has been successfully updated",
    "amount": "7.00"
}
```

### Delete an order

Requires authentication

**X-CSRFToken** header must be set to the value of **csrftoken** cookie.

```
DELETE /orders/{order_id}
```

**Response**

```
 Status: 200 OK
```
```
{
    "message": "Order has been successfully deleted"
}
```