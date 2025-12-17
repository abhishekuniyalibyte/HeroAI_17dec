// static/chat-widget.js
(function () {
  'use strict';

  console.log(
    '[ChatWidget] v6.6 loaded with Category Quick Add + Razorpay + Qty selector + Cart +/- + Payment Cancel Fix'
  );

  // Find the current <script> tag and read data attributes
  const currentScript =
    document.currentScript ||
    (function () {
      const scripts = document.getElementsByTagName('script');
      return scripts[scripts.length - 1];
    })();

  const restaurantId = currentScript.getAttribute('data-restaurant-id');
  const apiBaseUrl = currentScript.getAttribute('data-api-base-url') || '';

  if (!restaurantId) {
    console.error('[ChatWidget] data-restaurant-id is required.');
    return;
  }

  const baseApiUrl = apiBaseUrl.replace(/\/$/, '');
  const apiUrl = baseApiUrl + '/api/chatbot/simple/';
  const categoriesUrl = baseApiUrl + '/api/chatbot/categories/';
  const SESSION_KEY = 'rb_chat_session_id';

  // Simple session id stored in localStorage
  let sessionId = localStorage.getItem(SESSION_KEY);
  if (!sessionId) {
    sessionId =
      'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem(SESSION_KEY, sessionId);
  }

  // 🔹 Keep track of last non-empty order so we can restore cart on payment cancel
  let lastOrder = null;

  // Inject improved styles (bigger panel, larger fonts, quick-add buttons, menu qty)
  const style = document.createElement('style');
  style.textContent = `
    #chat-launcher {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 64px;
      height: 64px;
      border-radius: 999px;
      background: #111827;
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 14px;
      cursor: pointer;
      box-shadow: 0 10px 25px rgba(15,23,42,0.35);
      z-index: 1000;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      border: 1px solid rgba(148,163,184,0.4);
    }

    #chat-launcher:hover {
      transform: translateY(-1px);
      box-shadow: 0 14px 30px rgba(15,23,42,0.45);
    }

    /* Bigger side panel instead of tiny popup */
    #chat-widget {
      position: fixed;
      top: 20px;
      right: 20px;
      bottom: 20px;
      width: 420px;
      max-width: 95vw;
      background: #ffffff;
      border-radius: 18px;
      box-shadow: 0 18px 45px rgba(15,23,42,0.45);
      display: none;
      flex-direction: column;
      overflow: hidden;
      z-index: 1001;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      font-size: 16px;
    }

    @media (max-width: 768px) {
      #chat-widget {
        top: 0;
        right: 0;
        bottom: 0;
        left: 0;
        width: 100vw;
        max-width: 100vw;
        border-radius: 0;
      }
    }

    #chat-header {
      background: #111827;
      color: #f9fafb;
      padding: 12px 16px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 16px;
      font-weight: 600;
    }

    #chat-header span {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }

    #chat-header .chat-subtitle {
      font-size: 12px;
      font-weight: 400;
      color: #e5e7eb;
    }

    #chat-close-btn {
      border: none;
      background: transparent;
      color: #e5e7eb;
      font-size: 20px;
      cursor: pointer;
      padding: 0 4px;
    }

    #chat-cart {
      padding: 10px 14px;
      border-bottom: 1px solid #e5e7eb;
      background: #f9fafb;
    }

    .cart-title {
      font-weight: 600;
      margin-bottom: 4px;
      font-size: 14px;
      color: #111827;
    }

    .cart-body {
      max-height: 110px;
      overflow-y: auto;
      font-size: 14px;
      color: #111827;
    }

    .cart-empty {
      color: #6b7280;
      font-style: italic;
      font-size: 13px;
    }

    .cart-item {
      font-size: 14px;
      margin-bottom: 4px;
      padding: 4px 0;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .cart-item-main {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .cart-item-name {
      font-weight: 500;
    }

    .cart-item-line-total {
      font-size: 13px;
      color: #111827;
    }

    .cart-item-qty {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }

    .cart-total {
      margin-top: 6px;
      font-weight: 600;
      font-size: 14px;
      color: #111827;
    }

    .cart-actions {
      margin-top: 8px;
      display: flex;
      gap: 8px;
    }

    .cart-btn {
      flex: 1;
      border-radius: 999px;
      border: 1px solid #d1d5db;
      background: #f3f4f6;
      font-size: 13px;
      padding: 6px 8px;
      cursor: pointer;
      font-weight: 500;
    }

    .cart-btn.primary {
      border-color: #111827;
      background: #111827;
      color: #ffffff;
    }

    .cart-btn:disabled {
      opacity: 0.5;
      cursor: default;
    }

    /* 🔹 Quick-add section just below cart */
    #chat-quick {
      padding: 6px 14px 4px;
      border-bottom: 1px solid #e5e7eb;
      background: #fdfdfd;
    }

    .quick-title {
      font-size: 12px;
      color: #6b7280;
      margin-bottom: 4px;
    }

    .quick-buttons {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
    }

    .quick-item-btn {
      border-radius: 999px;
      border: 1px solid #d1d5db;
      background: #eef2ff;
      font-size: 12px;
      padding: 5px 10px;
      cursor: pointer;
      font-weight: 500;
      color: #1f2937;
      transition: background 0.15s ease, transform 0.1s ease, box-shadow 0.15s ease;
    }

    .quick-item-btn:hover {
      background: #e0e7ff;
      transform: translateY(-1px);
      box-shadow: 0 4px 10px rgba(15,23,42,0.16);
    }

    #chat-messages {
      flex: 1;
      padding: 16px;
      background: #f4f4f5;
      overflow-y: auto;
    }

    .rb-msg {
      margin: 6px 0;
      padding: 10px 12px;
      border-radius: 12px;
      max-width: 85%;
      line-height: 1.5;
      font-size: 16px;
      word-wrap: break-word;
      white-space: pre-wrap;
    }

    .rb-msg.user {
      background: #dbeafe;
      margin-left: auto;
      border-bottom-right-radius: 4px;
    }

    .rb-msg.bot {
      background: #e5e7eb;
      margin-right: auto;
      border-bottom-left-radius: 4px;
    }

    #chat-form {
      display: flex;
      border-top: 1px solid #e5e7eb;
      background: #ffffff;
      padding: 8px 10px;
      gap: 8px;
    }

    #chat-input {
      flex: 1;
      border-radius: 999px;
      border: 1px solid #d1d5db;
      padding: 10px 14px;
      font-size: 15px;
      outline: none;
    }

    #chat-input:focus {
      border-color: #111827;
      box-shadow: 0 0 0 1px #11182711;
    }

    #chat-send-btn {
      border-radius: 999px;
      border: none;
      padding: 0 18px;
      background: #111827;
      color: #ffffff;
      font-size: 14px;
      cursor: pointer;
      font-weight: 500;
      white-space: nowrap;
    }

    #chat-send-btn:disabled {
      opacity: 0.65;
      cursor: default;
    }

    /* 🔹 Menu suggestion cards with quantity controls */
    .menu-suggestions {
      margin-top: 8px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .menu-item-row {
      border-radius: 12px;
      border: 1px solid #d1d5db;
      background: #ffffff;
      padding: 8px 10px;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .menu-item-main {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 14px;
      font-weight: 500;
      color: #111827;
    }

    .menu-item-price {
      font-weight: 600;
    }

    .menu-item-qty {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 13px;
    }

    .qty-btn,
    .qty-add {
      border-radius: 999px;
      border: 1px solid #d1d5db;
      background: #f3f4f6;
      padding: 3px 8px;
      font-size: 13px;
      cursor: pointer;
    }

    .qty-add {
      background: #111827;
      border-color: #111827;
      color: #ffffff;
      font-weight: 500;
      margin-left: 4px;
    }

    .qty-value {
      min-width: 18px;
      text-align: center;
    }
  `;
  document.head.appendChild(style);

  // Launcher button
  const launcher = document.createElement('div');
  launcher.id = 'chat-launcher';
  launcher.textContent = 'Chat';
  document.body.appendChild(launcher);

  // Chat widget container
  const widget = document.createElement('div');
  widget.id = 'chat-widget';
  widget.innerHTML = `
    <div id="chat-header">
      <span>
        <span>Restaurant Chatbot</span>
        <span class="chat-subtitle">Ask about menu, add items, confirm order</span>
      </span>
      <button id="chat-close-btn" aria-label="Close chat">&times;</button>
    </div>
    <div id="chat-cart">
      <div class="cart-title">Your Cart</div>
      <div class="cart-body">
        <div class="cart-empty">Cart is empty</div>
      </div>
      <div class="cart-total">Total: ₹0.00</div>
      <div class="cart-actions">
        <button type="button" class="cart-btn cart-clear-btn">Clear</button>
        <button type="button" class="cart-btn primary cart-confirm-btn">Confirm</button>
      </div>
    </div>
    <!-- Quick-add section will be injected here via JS -->
    <div id="chat-messages"></div>
    <form id="chat-form">
      <input
        id="chat-input"
        type="text"
        placeholder="Type a message, e.g. 'show menu'..."
      />
      <button id="chat-send-btn" type="submit">Send</button>
    </form>
  `;
  document.body.appendChild(widget);

  // Element references
  const closeBtn = widget.querySelector('#chat-close-btn');
  const cartBodyEl = widget.querySelector('.cart-body');
  const cartTotalEl = widget.querySelector('.cart-total');
  const clearBtn = widget.querySelector('.cart-clear-btn');
  const confirmBtn = widget.querySelector('.cart-confirm-btn');
  const messagesEl = widget.querySelector('#chat-messages');
  const form = widget.querySelector('#chat-form');
  const input = widget.querySelector('#chat-input');
  const sendBtn = widget.querySelector('#chat-send-btn');

  // 🔹 Build the Quick Category section and insert it just after the cart
  (function setupQuickAdd() {
    const quickDiv = document.createElement('div');
    quickDiv.id = 'chat-quick';
    quickDiv.innerHTML = `
      <div class="quick-title">Browse by category</div>
      <div class="quick-buttons"></div>
    `;

    const quickButtonsContainer = quickDiv.querySelector('.quick-buttons');
    const cartEl = widget.querySelector('#chat-cart');
    cartEl.insertAdjacentElement('afterend', quickDiv);

    async function loadCategories() {
      try {
        const res = await fetch(
          categoriesUrl + '?restaurant_id=' + encodeURIComponent(restaurantId)
        );
        if (!res.ok) {
          throw new Error('HTTP ' + res.status);
        }

        const data = await res.json();
        const categories = data.categories || [];

        if (!categories.length) {
          // No categories → hide quick section
          quickDiv.style.display = 'none';
          return;
        }

        quickButtonsContainer.innerHTML = '';

        categories.forEach((cat) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'quick-item-btn';
          btn.setAttribute('data-category', cat);
          btn.textContent = cat;
          quickButtonsContainer.appendChild(btn);
        });
      } catch (err) {
        console.error('[ChatWidget] Failed to load categories', err);
        quickDiv.style.display = 'none';
      }
    }

    // Load categories on widget init
    loadCategories();

    // Clicking a category asks the bot "what do you have in <category>?"
    quickButtonsContainer.addEventListener('click', function (e) {
      const target = e.target;
      if (target && target.classList.contains('quick-item-btn')) {
        const category = target.getAttribute('data-category');
        if (category) {
          sendMessage('what do you have in ' + category + '?');
        }
      }
    });
  })();

  function toggleWidget(show) {
    widget.style.display = show ? 'flex' : 'none';
    if (show) {
      input.focus();
    }
  }

  function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = 'rb-msg ' + sender;
    div.textContent = text;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // 🔹 Render clickable menu items from backend "menu_items" with + / – / Add
  function addMenuItems(items) {
    if (!items || !items.length) return;

    const wrapper = document.createElement('div');
    wrapper.className = 'rb-msg bot';

    const title = document.createElement('div');
    title.textContent = 'Tap + / - to choose quantity, then "Add":';
    wrapper.appendChild(title);

    const list = document.createElement('div');
    list.className = 'menu-suggestions';

    items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'menu-item-row';

      // Top line: name + price
      const main = document.createElement('div');
      main.className = 'menu-item-main';

      const nameSpan = document.createElement('span');
      nameSpan.className = 'menu-item-name';
      nameSpan.textContent = item.name;

      const priceSpan = document.createElement('span');
      priceSpan.className = 'menu-item-price';
      if (item.price) {
        priceSpan.textContent = '₹' + item.price;
      }

      main.appendChild(nameSpan);
      main.appendChild(priceSpan);
      row.appendChild(main);

      // Quantity controls
      const qtyDiv = document.createElement('div');
      qtyDiv.className = 'menu-item-qty';

      const minusBtn = document.createElement('button');
      minusBtn.type = 'button';
      minusBtn.className = 'qty-btn qty-minus';
      minusBtn.textContent = '-';

      const qtyValue = document.createElement('span');
      qtyValue.className = 'qty-value';
      qtyValue.textContent = '1';

      const plusBtn = document.createElement('button');
      plusBtn.type = 'button';
      plusBtn.className = 'qty-btn qty-plus';
      plusBtn.textContent = '+';

      const addBtn = document.createElement('button');
      addBtn.type = 'button';
      addBtn.className = 'qty-add';
      addBtn.textContent = 'Add';

      // Handlers for + / -
      minusBtn.addEventListener('click', function () {
        let current = parseInt(qtyValue.textContent, 10) || 1;
        if (current > 1) {
          qtyValue.textContent = String(current - 1);
        }
      });

      plusBtn.addEventListener('click', function () {
        let current = parseInt(qtyValue.textContent, 10) || 1;
        if (current < 10) {
          qtyValue.textContent = String(current + 1);
        }
      });

      // Handler for Add → send "add <qty> <name>"
      addBtn.addEventListener('click', function () {
        const qty = parseInt(qtyValue.textContent, 10) || 1;
        const name = item.name;
        // This follows our LLM examples: "add 2 butter naan"
        sendMessage('add ' + qty + ' ' + name);
      });

      qtyDiv.appendChild(minusBtn);
      qtyDiv.appendChild(qtyValue);
      qtyDiv.appendChild(plusBtn);
      qtyDiv.appendChild(addBtn);

      row.appendChild(qtyDiv);
      list.appendChild(row);
    });

    wrapper.appendChild(list);
    messagesEl.appendChild(wrapper);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  // 🔹 Render cart with + / – inside cart itself
  function renderCart(order) {
    if (!order || !order.items || order.items.length === 0) {
      cartBodyEl.innerHTML = '<div class="cart-empty">Cart is empty</div>';
      cartTotalEl.textContent = 'Total: ₹0.00';
      clearBtn.disabled = true;
      confirmBtn.disabled = true;
      lastOrder = null; // cart really empty now
      return;
    }

    cartBodyEl.innerHTML = '';
    order.items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'cart-item';

      row.innerHTML = `
        <div class="cart-item-main">
          <span class="cart-item-name">${item.name}</span>
          <span class="cart-item-line-total">₹${item.total_price}</span>
        </div>
        <div class="cart-item-qty">
          <button type="button" class="qty-btn cart-minus" data-name="${item.name}">-</button>
          <span class="qty-value">${item.quantity}</span>
          <button type="button" class="qty-btn cart-plus" data-name="${item.name}">+</button>
        </div>
      `;

      cartBodyEl.appendChild(row);
    });

    cartTotalEl.textContent = `Total: ₹${order.total}`;
    clearBtn.disabled = false;
    confirmBtn.disabled = false;

    // 🔹 Remember last non-empty order
    lastOrder = order;

    // Attach +/- handlers for cart
    cartBodyEl.querySelectorAll('.cart-plus').forEach((btn) => {
      btn.addEventListener('click', () => {
        const name = btn.getAttribute('data-name');
        if (name) {
          // Use same intent flow: "add 1 <name>"
          sendMessage('add 1 ' + name);
        }
      });
    });

    cartBodyEl.querySelectorAll('.cart-minus').forEach((btn) => {
      btn.addEventListener('click', () => {
        const name = btn.getAttribute('data-name');
        if (name) {
          // Use same intent flow: "remove 1 <name>"
          sendMessage('remove 1 ' + name);
        }
      });
    });
  }

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed) {
      return;
    }

    addMessage(trimmed, 'user');
    input.value = '';
    sendBtn.disabled = true;

    try {
      const res = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          restaurant_id: parseInt(restaurantId, 10),
          session_id: sessionId,
          message: trimmed,
        }),
      });

      const data = await res.json();
      console.log('[ChatWidget] response:', data);

      if (data.session_id && data.session_id !== sessionId) {
        sessionId = data.session_id;
        localStorage.setItem(SESSION_KEY, sessionId);
      }

      // Show reply
      addMessage(data.reply ?? 'No reply received from server.', 'bot');

      // If backend sent structured menu items, show them as clickable cards with qty
      if (Array.isArray(data.menu_items) && data.menu_items.length > 0) {
        addMenuItems(data.menu_items);
      }

      // Razorpay Payment trigger
      if (data.payment) {
        const payment = data.payment;
        console.log('[ChatWidget] Payment info:', payment);

        const options = {
          key: payment.key,
          amount: payment.amount,
          currency: payment.currency,
          name: 'Restaurant Order',
          description: 'Order Payment',
          order_id: payment.order_id,
          handler: async function (response) {
            addMessage('Verifying your payment, please wait...', 'bot');
            try {
              const verifyRes = await fetch(
                baseApiUrl + '/api/payments/verify/',
                {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({
                    razorpay_payment_id: response.razorpay_payment_id,
                    razorpay_order_id: response.razorpay_order_id,
                    razorpay_signature: response.razorpay_signature,
                  }),
                }
              );

              const verifyData = await verifyRes.json();
              if (verifyData.status === 'success') {
                addMessage(
                  'Payment successful. Your order is confirmed.',
                  'bot'
                );
                renderCart(null); // clear cart on success
              } else {
                addMessage('Payment failed. Please try again.', 'bot');
              }
            } catch (err) {
              console.error('Verify error', err);
              addMessage(
                'Could not verify payment. Please contact staff.',
                'bot'
              );
            }
          },
          theme: { color: '#3399cc' },
          // 🔹 Handle user closing Razorpay without paying
          modal: {
            ondismiss: function () {
              console.log('[ChatWidget] Payment popup closed by user');
              addMessage(
                'Payment cancelled. Your cart is still active.',
                'bot'
              );
              if (lastOrder) {
                // restore the same cart + keep Confirm button enabled
                renderCart(lastOrder);
              }
            },
          },
        };

        // Load Razorpay script if needed
        if (typeof Razorpay !== 'undefined') {
          const rzp = new Razorpay(options);
          rzp.open();
        } else {
          const razorpayScript = document.createElement('script');
          razorpayScript.src = 'https://checkout.razorpay.com/v1/checkout.js';
          razorpayScript.onload = () => {
            const rzp = new Razorpay(options);
            rzp.open();
          };
          document.body.appendChild(razorpayScript);
        }
      }

      // Cart rendering
      // ⚠️ IMPORTANT: don't clear cart when we're just opening a payment popup
      if (data.order) {
        renderCart(data.order);
      } else if (!data.payment) {
        // Only treat "no order" as empty when there's no payment step
        renderCart(null);
      }
    } catch (err) {
      console.error('[ChatWidget] Error calling API:', err);
      addMessage(
        'Error talking to server. Please try again in a moment.',
        'bot'
      );
      renderCart(null);
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  // Event handlers
  launcher.addEventListener('click', function () {
    toggleWidget(true);
  });

  closeBtn.addEventListener('click', function () {
    toggleWidget(false);
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage(input.value);
  });

  clearBtn.addEventListener('click', function () {
    sendMessage('clear');
  });

  confirmBtn.addEventListener('click', function () {
    sendMessage('confirm');
  });

  // Initialize cart state so buttons start disabled on fresh load
  renderCart(null);

  // Initial greeting + open the bigger panel on page load
  addMessage(
    'Hi! I am your restaurant assistant. You can ask for the menu, browse by category, tap items, adjust quantity (both from menu cards and inside cart), view cart, and confirm your order here.',
    'bot'
  );
  toggleWidget(true);
})();


