const headers = {
  'X-CSRFToken': getCookie('csrftoken'),
  'Content-Type': 'application/json; charset=UTF-8',
};

document.addEventListener('DOMContentLoaded', function() {

  // Manage clicks on order list items
  document.querySelectorAll('.order-list-item').forEach(orderListItem => {
    orderListItem.addEventListener('click', () => {
      highlightOrderListItem(orderListItem);
      clearAlert();
      updateOrderView(orderListItem);
    })
  })

  // Manage clicks on 'Save' and 'Delete' order buttons
  document.querySelector('#save').addEventListener('click', () => saveOrder());
  document.querySelector('#delete').addEventListener('click', () => deleteOrder());

})

async function updateOrderView(selectedOrderListItem) {
  // Load selected order-list-item in order-view. If item has no order, display an empty order form.
  const deliveryDate = selectedOrderListItem.querySelector('.delivery').innerText;
  const deliveryUrl = selectedOrderListItem.querySelector('.delivery').dataset.url;
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const spinner = document.querySelector('#spinner');
  const orderView = document.querySelector('#order-view');
  const orderViewTitle = document.querySelector('#order-view-title');
  const orderViewSubtitle = document.querySelector('#order-view-subtitle');
  const orderViewMessage = document.querySelector('#order-view-message');
  const orderViewItemsContainer = document.querySelector('#order-view-items');
  const producerList = document.querySelector('#producer-list');
  const orderAmountSpan = document.querySelector('#order-amount');
  const saveIcon = document.querySelector('#save');
  const deleteIcon = document.querySelector('#delete');

  // hide order-view while updating
  hide(orderView);
  show(spinner);

  let delivery = null;
  const order = (orderUrl !== '') ? await requestGetOrder(orderUrl) : null;

  orderViewItemsContainer.innerHTML = '';
  producerList.innerHTML = '';
  if (order) {
      orderView.classList.add('border-success');
      orderView.classList.add('shadow');
      orderViewTitle.innerText = `Commande pour le ${deliveryDate}`;
      if (order.is_open) {
        // order can be updated and deleted
        delivery = await requestGetDelivery(deliveryUrl);
        orderViewSubtitle.innerText = `Peut être modifiée jusqu'au ${formatDate(delivery.order_deadline)}`;
        orderViewMessage.innerText = delivery.message;
        delivery.message ? show(orderViewMessage) : hide(orderViewMessage);
        addProducersAndItems(delivery);
        updateItemsFromOrder(order);
        show(deleteIcon);
        saveIcon.innerText = 'Mettre à jour'
        show(saveIcon);
      } else {
        // order in view-only mode (history page)
        orderViewSubtitle.innerText = '';
        hide(orderViewMessage);
        addOrderViewItemsViewOnlyMode(order);
        hide(deleteIcon);
        hide(saveIcon);
      }
      orderAmountSpan.innerText = parseFloat(order.amount).toFixed(2);
  } else {
    // new order
    orderView.classList.remove('border-success');
    orderView.classList.remove('shadow');
    orderViewTitle.innerText = `Nouvelle commande pour le ${deliveryDate}`;
    delivery = await requestGetDelivery(deliveryUrl);
    orderViewSubtitle.innerText = `Dernier jour pour commander: ${formatDate(delivery.order_deadline)}`;
    orderViewMessage.innerText = delivery.message;
    delivery.message ? show(orderViewMessage) : hide(orderViewMessage);
    addProducersAndItems(delivery);
    hide(deleteIcon);
    saveIcon.innerText = 'Créer'
    show(saveIcon);
    let orderAmount = 0;
    orderAmountSpan.innerText = orderAmount.toFixed(2);
  }

  // Finally, show order-view
  hide(spinner);
  show(orderView);

  function addProducersAndItems(delivery) {
    delivery.products_by_producer.forEach((producer, index) => {
      const producerDiv = createProducerDiv(producer, index);
      producerList.append(producerDiv);
      const productList = producerDiv.querySelector('.product-list');
      // add new .order-view-item for each product
      producer.products.forEach(product => {
        const orderViewItemDiv = createOrderViewItemDiv(product);
        productList.append(orderViewItemDiv);
      })
    })

    function createProducerDiv(producer, index) {
      const producerDiv = document.createElement('div');
      producerDiv.className = 'producer accordion block';
      producerDiv.innerHTML = `
        <div class="accordion-item">
          <h3 class="accordion-header" id="panelsStayOpen-heading${index}">
            <button class="accordion-button collapsed p-2" type="button" data-bs-toggle="collapse"
                    data-bs-target="#collapse${index}" aria-expanded="false"
                    aria-controls="collapse${index}">
              <span class="producer-name">${producer.name}</span>
              <span class="badge bg-secondary ms-1 d-none"></span>
            </button>
          </h3>
          <div id="collapse${index}" class="accordion-collapse collapse"
               aria-labelledby="panelsStayOpen-heading${index}">
            <div class="accordion-body">
              <div class="product-list">
                <!-- .order-view-items are appended here on 'next orders' page -->
              </div>
            </div>
          </div>
        </div>`
        return producerDiv;
    }

    function createOrderViewItemDiv(product) {
      const orderViewItemDiv = document.createElement('div');
      orderViewItemDiv.className = 'order-view-item container p-0';
      orderViewItemDiv.dataset.productid = product.id;
      orderViewItemDiv.innerHTML = `
        <div class="row align-items-center border">
          <div class="product-name col-sm-6 p-2">${product.name}</div>
          <div class="col-sm-6">
            <div class="row align-items-center">
              <div class="col text-end"><span class="unit-price">${product.unit_price}</span> €/U</div>
              <div class="col"><input type="number" class="quantity form-control form-control-sm text-end" value="0" min="0"></div>
              <div class="col text-end"><span class="amount">0.00</span> €</div>
            </div>
          </div>
        </div>`
      // set action on quantity input change
      orderViewItemDiv.querySelector('.quantity').addEventListener('input', () => {
        clearAlert();
        updateOrderViewAmounts();
        updateBadges();
      })
      return orderViewItemDiv;
    }

    function updateOrderViewAmounts() {
      // Re-calculate order-view amounts (items and total) according to items quantities
      const orderViewItems = document.querySelectorAll('.order-view-item');
      let orderAmount = 0;
      orderViewItems.forEach(orderViewItem => {
        const unitPrice = orderViewItem.querySelector('.unit-price').innerText;
        const quantity = orderViewItem.querySelector('.quantity').value;
        const itemAmount = unitPrice * quantity;
        orderViewItem.querySelector('.amount').innerText = itemAmount.toFixed(2);
        orderAmount += itemAmount;
      })
      orderAmountSpan.innerText = orderAmount.toFixed(2);
    }
  }

  function updateItemsFromOrder(order) {
    // update existing order-view-items with quantities and amounts from order
    const orderViewItems = document.querySelectorAll('.order-view-item');
    orderViewItems.forEach(orderViewItem => {
      let productId = parseInt(orderViewItem.dataset.productid);
      let orderItem = order.items.find(item => item.product === productId)
      if (orderItem) {
        const orderViewItemQuantity = orderViewItem.querySelector('.quantity');
        const orderViewItemAmount = orderViewItem.querySelector('.amount');
        orderViewItemQuantity.value = orderItem.quantity;
        orderViewItemAmount.innerText = parseFloat(orderItem.amount).toFixed(2);
      }
    })
    updateBadges();
  }

  function addOrderViewItemsViewOnlyMode(order) {
    // add order-view-items for order. 'View-only' mode
    const orderViewItemsContainer = document.querySelector('#order-view-items');
    order.items.forEach(item => {
      const orderViewItem = document.createElement('tr');
      orderViewItem.className = "order-view-item";
      orderViewItem.dataset.productid = item.product.id;
      orderViewItem.innerHTML = `
        <td class="product-name">${item.product_name}</td>
        <td class="col-2 text-end"><span class="unit-price">${item.product_unit_price}</span> €/U</td>
        <td class="col-1 text-end quantity">x${item.quantity}</td>
        <td class="col-2 text-end"><span class="amount">${item.amount}</span> €</td>`;
      orderViewItemsContainer.append(orderViewItem);
    })
  }

  function updateBadges() {
    const producers = document.querySelectorAll('.producer');
    producers.forEach(producer => {
      const producerBadge = producer.querySelector('.badge');
      let producerItemsQuantity = 0;
      producer.querySelectorAll('.quantity').forEach(producerQuantityInput => {
        producerItemsQuantity += parseInt(producerQuantityInput.value);
      })
      producerBadge.innerText = producerItemsQuantity;
      producerItemsQuantity ? show(producerBadge) : hide(producerBadge);
    })
  }
}

async function saveOrder() {
  // Create or Update order
  const selectedOrderListItem = document.querySelector('.table-active');
  const deliveryId = selectedOrderListItem.querySelector('.delivery').dataset.url.split('/').at(-2);
  const orderView = document.querySelector('#order-view');
  const orderAmount = document.querySelector('#order-amount').innerText;
  let orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;

  let orderItems = getOrderItems()
  let result;
  if (orderItems.length > 0) {
    if (orderUrl === '') {
      result = await requestCreateOrder(deliveryId, orderItems);
    } else {
      result = await requestUpdateOrder(orderUrl, deliveryId, orderItems);
    }
    orderUrl = result.url; // new or updated order url

    // if order amount sent by back-end matches front-end one, order has been successfully created/updated
    if (result.amount === orderAmount) {
      updateSelectedOrderListItem(orderAmount, orderUrl);
      highlightOrderListItem(null);
      restartAnimation(selectedOrderListItem.querySelector('.order'));
      showAlert('successSave');
      hide(orderView);
    } else {
      showAlert('errorSave');
    }
  } else {
    showAlert('errorItems');
  }

  function getOrderItems() {
    // Get order items from order-view
    let orderItems = []
    let orderViewItems = document.querySelectorAll('.order-view-item')
    orderViewItems.forEach(orderViewItem => {
      let quantity = orderViewItem.querySelector('.quantity').value;
      // valid order items have quantity greater than 0
      if (quantity > 0) {
        orderItems.push({
          'product': orderViewItem.dataset.productid,
          'quantity': quantity,
        });
      }
    })
    return orderItems;
  }
}

async function deleteOrder() {
  // delete selected order
  const selectedOrderListItem = document.querySelector('.table-active');
  const orderUrl = selectedOrderListItem.querySelector('.order').dataset.url;
  const orderView = document.querySelector('#order-view');

  const response = await requestDeleteOrder(orderUrl);

  if (response.status == 204) {
    updateSelectedOrderListItem(null, '');
    highlightOrderListItem(null);
    showAlert('successRemove');
    hide(orderView);
  }
}

async function requestGetDelivery(deliveryUrl) {
  // Send 'GET' request to get delivery details
  const response = await fetch(deliveryUrl)
  .catch(error => showAlert(error.message));
  return await response.json();
}

async function requestGetOrder(orderUrl) {
  // Send 'GET' request to get order details
  const response = await fetch(orderUrl)
  .catch(error => showAlert(error.message));
  return response.json();
}

async function requestCreateOrder(deliveryId, orderItems) {
  // Send 'POST' request to create order in back-end
  const createOrderUrl = document.querySelector('#create-order').dataset.url;
  const response = await fetch(createOrderUrl, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify({
      'delivery': deliveryId,
      'items': orderItems,
    })
  })
  .catch(error => showAlert(error.message));
  return response.json();
}

async function requestUpdateOrder(orderUrl, deliveryId, orderItems) {
  // Send 'PUT' request to update order in back-end
  const response = await fetch(orderUrl, {
    method: 'PUT',
    headers: headers,
    body: JSON.stringify({
      'delivery': deliveryId,
      'items': orderItems,
    })
  })
  .catch(error => showAlert(error.message));
  return await response.json();
}

async function requestDeleteOrder(orderUrl) {
  // Send 'DELETE' order request to back-end
  const response = await fetch(orderUrl, {
    method: 'DELETE',
    headers: headers,
  })
  .catch(error => showAlert(error.message));
  return response;
}

function updateSelectedOrderListItem(orderAmount, orderUrl) {
  const selectedOrderListItem = document.querySelector('.table-active');
  const selectedOrder = selectedOrderListItem.querySelector('.order');

  selectedOrder.innerText = orderAmount ? orderAmount + ' €' : 'Commander';
  selectedOrder.dataset.url = orderUrl;
}

function highlightOrderListItem(orderListItem) {
  // highlight given orderListItem or none (null given)
  document.querySelectorAll('.order-list-item')
      .forEach(order => order.classList.remove('table-active'));
  if (orderListItem) {
    orderListItem.classList.add('table-active');
  }
}

function showAlert(alertType) {
  alert = document.querySelector('#alert');
  clearAlert();
  switch(alertType) {
    case 'successSave':
      alert.classList.add('text-success');
      alert.innerText = "La commande a été enregistrée avec succès";
      break;
    case 'successRemove':
      alert.classList.add('text-success');
      alert.innerText = "La commande a été supprimée avec succès";
      break;
    case 'errorSave':
      alert.classList.add('text-danger');
      alert.innerText = "Une erreur est survenue lors de l'enregistrement de la commande. Veuillez recharger la page et réesayer";
      break;
    case 'errorItems':
      alert.classList.add('text-danger');
      alert.innerText = "Au moins un produit doit avoir une quantité supérieure à 0";
      break;
    default:
      alert.classList.add('text-danger');
      alert.innerText = alertType;
  }
  show(alert);
  window.scrollTo(0, 0);
}

function clearAlert() {
  alert = document.querySelector('#alert');
  hide(alert);
  alert.classList.remove('text-success');
  alert.classList.remove('text-danger');
  alert.innerText = '';
}

function show(element) {
  element.classList.replace('d-none', 'block');
}

function hide(element) {
  element.classList.replace('block', 'd-none');
}

function restartAnimation(element) {
  element.classList.remove('run-animation');
  element.offsetWidth;  // trigger reflow
  element.classList.add('run-animation');
}

function formatDate(date) {
  // format date to DD/MM/YYYY (Note that ISOString format is YYYY-MM-DDTHH:mm:ss.sssZ)
  // TODO: do this on back-end?
  const dateISO = new Date(date).toISOString();
  return dateISO.slice(0, 10).split('-').reverse().join('/');
}

// from https://docs.djangoproject.com/en/3.2/ref/csrf/
function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}
