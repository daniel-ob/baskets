import time
from decimal import Decimal

from django.urls import reverse
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait


class BasePage(object):
    """Base page object"""

    TITLE = (By.TAG_NAME, "h1")
    USERNAME = (By.ID, "username")
    HISTORY_LINK = (By.ID, "nav-history")

    url = None

    def __init__(self, driver, live_server_url):
        self.driver = driver
        self.live_server_url = live_server_url

    def load(self):
        self.driver.get(self.live_server_url + self.url)

    @property
    def title(self):
        return self.driver.find_element(*self.TITLE).text

    @property
    def username(self):
        return self.driver.find_element(*self.USERNAME).text

    def fill_form_by_name(self, name, value):
        field = self.driver.find_element(By.NAME, name)
        field.send_keys(value)

    def load_history_page(self):
        history_link = self.driver.find_element(*self.HISTORY_LINK)
        history_link.click()
        return OrdersPage(
            self.driver, self.live_server_url
        )  # history page is also an IndexPage


class LoginPage(BasePage):
    """Abstracts interactions with login.html template"""

    LOGIN_BUTTON = (By.CLASS_NAME, "btn")

    url = reverse("account_login")

    def set_login(self, email):
        self.fill_form_by_name("login", email)

    def set_password(self, password):
        self.fill_form_by_name("password", password)

    def submit(self):
        login_button = self.driver.find_element(*self.LOGIN_BUTTON)
        login_button.click()
        return OrdersPage(self.driver, self.live_server_url)


class OrdersPage(BasePage):
    """Abstracts interactions with orders.html template"""

    # page locators
    DELIVERIES = (By.CLASS_NAME, "delivery")
    ORDERS = (By.CLASS_NAME, "order")
    SELECTED_ORDER = (By.CLASS_NAME, "table-active")
    ORDER_VIEW = (By.ID, "order-view")
    ORDER_VIEW_TITLE = (By.ID, "order-view-title")
    PRODUCERS = (By.CLASS_NAME, "producer")
    PRODUCER_NAMES = (By.CLASS_NAME, "producer-name")
    PRODUCER_BADGES = (By.CLASS_NAME, "badge")
    ITEMS = (By.CLASS_NAME, "order-view-item")
    ITEM_NAMES = (By.CLASS_NAME, "product-name")
    ITEM_UNIT_PRICES = (By.CLASS_NAME, "unit-price")
    ITEM_QUANTITIES = (By.CLASS_NAME, "quantity")
    ITEM_AMOUNTS = (By.CLASS_NAME, "amount")
    ORDER_AMOUNT = (By.ID, "order-amount")
    SAVE_BUTTON = (By.ID, "save")
    DELETE_BUTTON = (By.ID, "delete")

    MAX_WAIT_SECONDS = 2

    url = reverse("index")

    def get_deliveries_count(self):
        return len(self.driver.find_elements(*self.DELIVERIES))

    def get_order_url(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        url = order.get_attribute("data-url")
        return url or None

    def get_order_amount(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        return (
            Decimal(order.text.split()[0].replace(",", "."))
            if order.text.count("€")
            else None
        )

    def get_delivery_date(self, index):
        delivery = self.driver.find_elements(*self.DELIVERIES)[index]
        return delivery.text

    def get_delivery_id(self, index):
        delivery = self.driver.find_elements(*self.DELIVERIES)[index]
        url = delivery.get_attribute("data-url")
        # urls are like "/api/v1/deliveries/1/"
        return int(url.split("/")[-2])

    def open_order(self, index):
        order = self.driver.find_elements(*self.ORDERS)[index]
        order.click()
        # wait until order view is displayed
        wait = WebDriverWait(self.driver, self.MAX_WAIT_SECONDS)
        order_view = self.driver.find_element(*self.ORDER_VIEW)
        wait.until(ec.visibility_of(order_view))

    def get_order_view_title(self):
        return self.driver.find_element(*self.ORDER_VIEW_TITLE).text

    def get_producers_count(self):
        return len(self.driver.find_elements(*self.PRODUCERS))

    def open_all_producers(self):
        producers = self.driver.find_elements(*self.PRODUCERS)
        for producer in producers:
            producer.click()

    def get_producer_name(self, producer_index):
        return self.driver.find_elements(*self.PRODUCER_NAMES)[producer_index].text

    def get_producer_items_count(self, producer_index):
        producer = self.driver.find_elements(*self.PRODUCERS)[producer_index]
        producer_items = producer.find_elements(*self.ITEMS)
        return len(producer_items)

    def get_producer_badge_value(self, producer_index):
        producer = self.driver.find_elements(*self.PRODUCERS)[producer_index]
        badge = producer.find_element(*self.PRODUCER_BADGES)
        return int(badge.text) if badge.text else None

    def get_items_count(self):
        items = self.driver.find_elements(*self.ITEMS)
        return len(items)

    def _get_container(self, producer_index):
        container = self.driver
        if producer_index is not None:
            container = self.driver.find_elements(*self.PRODUCERS)[producer_index]
        return container

    def get_item_id(self, index, producer_index=None):
        container = self._get_container(producer_index)
        item = container.find_elements(*self.ITEMS)[index]
        return int(item.get_attribute("data-productid"))

    def get_item_name(self, index, producer_index=None):
        container = self._get_container(producer_index)
        return container.find_elements(*self.ITEM_NAMES)[index].text

    def get_item_unit_price(self, index, producer_index=None):
        container = self._get_container(producer_index)
        return Decimal(container.find_elements(*self.ITEM_UNIT_PRICES)[index].text)

    def get_item_quantity(self, index, producer_index=None):
        container = self._get_container(producer_index)
        quantity_elem = container.find_elements(*self.ITEM_QUANTITIES)[index]
        if self.item_quantity_is_writable(index, producer_index):
            return int(quantity_elem.get_attribute("value"))
        else:
            return int(quantity_elem.text.replace("x", ""))

    def get_item_amount(self, item_index, producer_index=None):
        container = self._get_container(producer_index)
        return Decimal(container.find_elements(*self.ITEM_AMOUNTS)[item_index].text)

    def item_quantity_is_writable(self, index, producer_index=None):
        container = self._get_container(producer_index)
        item_quantity = container.find_elements(*self.ITEM_QUANTITIES)[index]
        # Quantity is an <input> on 'Next Orders' page and a <td> on 'Order History' page
        return item_quantity.tag_name == "input"

    def set_item_quantity(self, index, quantity):
        quantity_input = self.driver.find_elements(*self.ITEM_QUANTITIES)[index]
        quantity_input.clear()
        quantity_input.send_keys(quantity)

    def get_order_view_amount(self):
        return Decimal(self.driver.find_element(*self.ORDER_AMOUNT).text)

    def save_order(self):
        save_button = self.driver.find_element(*self.SAVE_BUTTON)
        # scroll to bottom and wait for the button to be visible
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        save_button.click()
        self.wait_until_order_view_closed()

    def delete_order(self):
        delete_button = self.driver.find_element(*self.DELETE_BUTTON)
        delete_button.click()
        self.wait_until_order_view_closed()

    def wait_until_order_view_closed(self):
        wait = WebDriverWait(self.driver, self.MAX_WAIT_SECONDS)
        order_view = self.driver.find_element(*self.ORDER_VIEW)
        wait.until(ec.invisibility_of_element(order_view))
