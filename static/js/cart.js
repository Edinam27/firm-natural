// static/js/cart.js
document.addEventListener('DOMContentLoaded', function() {
    // Function to Get CSRF Token from Cookie
    function getCsrfToken() {
        return document.cookie.split('; ')
            .find(row => row.startsWith('csrf_token='))
            ?.split('=')[1];
    }

    // Function to Get Fetch Options with CSRF Token
    function getFetchOptions(method, body) {
        return {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            },
            body: JSON.stringify(body)
        };
    }

    // Update Cart Quantity
    async function updateCartQuantity(productId, size, quantity) {
        try {
            const response = await fetch('/api/update-cart', getFetchOptions('POST', {
                product_id: productId,
                size: size,
                quantity: quantity
            }));
            
            const data = await response.json();
            if (data.success) {
                updateCartDisplay(data.cart_count, data.cart_total);
            } else {
                alert('Error updating cart: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to update cart');
        }
    }
    // Remove Item from Cart
    async function removeFromCart(productId, size) {
        try {
            const response = await fetch('/api/remove-from-cart', getFetchOptions('POST', {
                product_id: productId,
                size: size
            }));
            
            const data = await response.json();
            if (data.success) {
                updateCartDisplay(data.cart_count, data.cart_total);
                const cartItem = document.querySelector(`[data-product-id="${productId}"][data-size="${size}"]`);
                if (cartItem) {
                    cartItem.remove();
                }
            } else {
                alert('Error removing item: ' + data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to remove item');
        }
    }

    // Update Cart Display
    function updateCartDisplay(count, total) {
        const cartCount = document.getElementById('cart-count');
        const cartTotal = document.getElementById('cart-total');
        
        if (cartCount) cartCount.textContent = count;
        if (cartTotal) cartTotal.textContent = `$${total.toFixed(2)}`;
        
        const emptyCartMessage = document.getElementById('empty-cart-message');
        if (emptyCartMessage) {
            emptyCartMessage.style.display = count === 0 ? 'block' : 'none';
        }
    }

    // Event Listeners for Quantity Changes and Remove Buttons
    document.querySelectorAll('.quantity-input').forEach(input => {
        input.addEventListener('change', function() {
            const productId = this.closest('.cart-item').dataset.productId;
            const size = this.closest('.cart-item').dataset.size;
            updateCartQuantity(productId, size, this.value);
        });
    });

    document.querySelectorAll('.remove-item').forEach(button => {
        button.addEventListener('click', function() {
            const productId = this.closest('.cart-item').dataset.productId;
            const size = this.closest('.cart-item').dataset.size;
            removeFromCart(productId, size);
        });
    });
});
