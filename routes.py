# routes.py
from flask import Blueprint, jsonify, request, redirect, url_for, render_template, session, flash
from models import (
    User, 
    Order, 
    ShippingAddress, 
    OrderItem, 
    Product, 
    IndividualProfile, 
    CompanyProfile, 
    CharityProfile, 
    GroupProfile, 
    Subscription, 
    SubscriptionPlan
)
from extensions import db
import uuid
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
import stripe
import logging

from flask_wtf.csrf import generate_csrf

logging.basicConfig(level=logging.DEBUG) 
logger = logging.getLogger(__name__)

bp = Blueprint('main', __name__)

@bp.after_request 
def add_csrf_token(response): 
    if 'text/html' in response.headers.get('Content-Type', ''): 
        response.set_cookie('csrf_token', generate_csrf()) 
        return response

@bp.route('/api/place-order', methods=['POST'])
def place_order():
    if 'cart' not in session:
        return jsonify({'success': False, 'error': 'Empty cart'})

    try:
        order = Order(
            user_id=session['user_id'],
            order_number=str(uuid.uuid4().hex[:8]),
            subtotal=calculate_subtotal(session['cart']),
            shipping=2.00,
            tax=calculate_tax(session['cart']),
            expected_delivery_date=datetime.utcnow() + timedelta(days=3)
        )
        order.total = order.subtotal + order.shipping + order.tax

        shipping_address = ShippingAddress(
            full_name=f"{request.form['firstName']} {request.form['lastName']}",
            street=request.form['address'],
            city=request.form['city'],
            postal_code=request.form['postalCode']
        )
        
        order.shipping_address = shipping_address

        for item in session['cart']:
            order_item = OrderItem(
                product_id=item['product_id'],
                quantity=item['quantity'],
                size=item['size']
            )
            order.items.append(order_item)

        db.session.add(order)
        db.session.commit()

        session.pop('cart', None)
        return jsonify({
            'success': True,
            'order_id': order.id
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/order-confirmation/<order_id>')
def order_confirmation(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != session.get('user_id'):
        return redirect(url_for('login'))
        
    return render_template('order-confirmation.html', order=order)

def calculate_subtotal(cart):
    total = 0
    for item in cart:
        product = Product.query.get(item['product_id'])
        total += product.price * item['quantity']
    return total

def calculate_tax(cart):
    return calculate_subtotal(cart) * 0.08

@bp.route('/')
def index():
    products = Product.query.limit(3).all()
    return render_template('index.html', products=products)


@bp.route('/products')
def products():
    products = Product.query.all()
    return render_template('products.html', products=products)

@bp.route('/api/cart-count')
def cart_count():
    count = 0
    if isinstance(session.get('cart'), dict):
        for item in session['cart'].values():
            count += item['quantity']
    return jsonify({'count': count})

@bp.route('/cart')
def cart():
    cart_items = []
    subtotal = 0.0
    
    try:
        if isinstance(session.get('cart'), dict):
            for cart_key, item_data in session['cart'].items():
                product_id = cart_key.split('_')[0]
                product = Product.query.get(int(product_id))
                
                if product:
                    quantity = item_data['quantity']
                    size = item_data['size']
                    
                    # Calculate price based on size
                    base_price = product.price
                    if size == '1L':
                        base_price *= 1.8
                    elif size == '2L':
                        base_price *= 3.2
                    
                    item_total = base_price * quantity
                    
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'size': size,
                        'price': base_price,
                        'total': item_total
                    })
                    
                    subtotal += item_total
        
        shipping = 5.00 if subtotal > 0 else 0.00
        tax = subtotal * 0.08
        total = subtotal + shipping + tax
        
        print("Cart items:", cart_items)  # Debug line
        
        return render_template('cart.html',
                             cart_items=cart_items,
                             subtotal=subtotal,
                             shipping=shipping,
                             tax=tax,
                             total=total)
                             
    except Exception as e:
        print(f"Cart error: {str(e)}")
        session['cart'] = {}
        session.modified = True
        return render_template('cart.html', cart_items=[])

@bp.route('/checkout')
def checkout():
    if not current_user.is_authenticated:
        # Redirect to login with the correct blueprint prefix
        return redirect(url_for('main.login'))
    
    cart_items = []
    subtotal = 0.0
    
    try:
        if isinstance(session.get('cart'), dict):
            for cart_key, item_data in session['cart'].items():
                product_id = cart_key.split('_')[0]
                product = Product.query.get(int(product_id))
                
                if product:
                    quantity = item_data['quantity']
                    size = item_data['size']
                    base_price = product.price
                    
                    # Apply size multipliers
                    if size == '1L':
                        base_price *= 1.8
                    elif size == '2L':
                        base_price *= 3.2
                    
                    item_total = base_price * quantity
                    cart_items.append({
                        'product': product,
                        'quantity': quantity,
                        'size': size,
                        'price': base_price,
                        'total': item_total
                    })
                    subtotal += item_total
        
        shipping = 5.00 if subtotal > 0 else 0.00
        tax = subtotal * 0.08
        total = subtotal + shipping + tax
        
        return render_template('checkout.html',
                             cart_items=cart_items,
                             subtotal=subtotal,
                             shipping=shipping,
                             tax=tax,
                             total=total)
                             
    except Exception as e:
        flash('An error occurred during checkout', 'danger')
        return redirect(url_for('main.cart'))

from logging import getLogger

@bp.route('/api/add-to-cart', methods=['POST'])
def add_to_cart():
    try:
        logger.debug(f"Received add-to-cart request: {request.json}")

        if not request.json:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        product_id = request.json.get('product_id')
        size = request.json.get('size')

        if not product_id or not size:
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        # Initialize cart if needed
        if 'cart' not in session:
            session['cart'] = {}

        cart_key = f"{product_id}_{size}"

        # Update cart
        if cart_key in session['cart']:
            session['cart'][cart_key]['quantity'] += 1
        else:
            product = Product.query.get(int(product_id))
            if not product:
                return jsonify({'success': False, 'error': 'Product not found'}), 404

            session['cart'][cart_key] = {
                'quantity': 1,
                'size': size,
                'price': float(product.price),
                'total': float(product.price),
                'product_name': product.name
            }

        session.modified = True

        # Calculate cart totals
        cart_count = sum(item['quantity'] for item in session['cart'].values())
        cart_total = sum(item['total'] for item in session['cart'].values())

        return jsonify({
            'success': True,
            'cart_count': cart_count,
            'cart_total': round(cart_total, 2)
        })

    except Exception as e:
        logger.exception("Error in add_to_cart:")
        return jsonify({'success': False, 'error': str(e)}), 500


class LoginForm(FlaskForm):
    email = StringField('Email')
    password = PasswordField('Password')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.account'))
    
    form = LoginForm()
    if request.method == 'POST':
        user = User.query.filter_by(email=request.form['email']).first()
        
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.account'))
        else:
            flash('Invalid email or password', 'danger')
            
    return render_template('login.html', form=form)

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

@bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user_type = request.form.get('user_type')

        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('register'))

        # Create new user
        user = User(
            email=email,
            password=generate_password_hash(password),
            user_type=user_type
        )
        db.session.add(user)
        db.session.flush()  # Get user ID before committing

        # Create profile based on user type
        if user_type == 'individual':
            profile = IndividualProfile(
                user_id=user.id,
                first_name=request.form.get('first_name'),
                last_name=request.form.get('last_name'),
                phone=request.form.get('phone'),
                address=request.form.get('address'),
                date_of_birth=request.form.get('date_of_birth')
            )
        elif user_type == 'company':
            profile = CompanyProfile(
                user_id=user.id,
                company_name=request.form.get('company_name'),
                registration_number=request.form.get('registration_number'),
                contact_person=request.form.get('contact_person'),
                business_phone=request.form.get('business_phone'),
                business_address=request.form.get('business_address'),
                industry=request.form.get('industry')
            )
        elif user_type == 'charity':
            profile = CharityProfile(
                user_id=user.id,
                charity_name=request.form.get('charity_name'),
                charity_number=request.form.get('charity_number'),
                contact_person=request.form.get('contact_person'),
                charity_phone=request.form.get('charity_phone'),
                charity_address=request.form.get('charity_address'),
                mission_statement=request.form.get('mission_statement')
            )
        elif user_type == 'group':
            profile = GroupProfile(
                user_id=user.id,
                group_name=request.form.get('group_name'),
                group_type=request.form.get('group_type'),
                contact_person=request.form.get('contact_person'),
                group_phone=request.form.get('group_phone'),
                group_address=request.form.get('group_address'),
                member_count=request.form.get('member_count')
            )

        db.session.add(profile)
        db.session.commit()

        login_user(user)
        flash('Registration successful!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('register.html')
@bp.route('/account')
@login_required
def account():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('account.html', orders=orders)

@bp.route('/api/update-cart', methods=['POST'])
def update_cart():
    try:
        # Validate Request Data
        if not request.json:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        product_id = request.json.get('product_id')
        size = request.json.get('size')
        quantity = request.json.get('quantity', 1)
        
        if not all([product_id, size, quantity]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        cart_key = f"{product_id}_{size}"
        
        # Update Cart
        if cart_key in session.get('cart', {}):
            if quantity <= 0:
                del session['cart'][cart_key]
            else:
                session['cart'][cart_key]['quantity'] = quantity
                session['cart'][cart_key]['total'] = round(
                    session['cart'][cart_key]['price'] * quantity, 2
                )
            session.modified = True
        
        # Calculate Cart Totals
        cart_count = sum(item['quantity'] for item in session.get('cart', {}).values())
        cart_total = sum(item['total'] for item in session.get('cart', {}).values())
        
        return jsonify({
            'success': True,
            'cart_count': cart_count,
            'cart_total': round(cart_total, 2)
        })
    except Exception as e:
        logger.exception("Error updating cart:")
        return jsonify({'success': False, 'error': str(e)}), 500
    
# Remove from Cart Endpoint
@bp.route('/api/remove-from-cart', methods=['POST'])
def remove_from_cart():
    try:
        if not request.json:
            return jsonify({'success': False, 'error': 'No data provided'}), 400

        product_id = request.json.get('product_id')
        size = request.json.get('size')

        if not all([product_id, size]):
            return jsonify({'success': False, 'error': 'Missing required fields'}), 400

        cart_key = f"{product_id}_{size}"

        if cart_key in session.get('cart', {}):
            del session['cart'][cart_key]
            session.modified = True

        # Calculate cart totals
        cart_count = sum(item['quantity'] for item in session.get('cart', {}).values())
        cart_total = sum(item['total'] for item in session.get('cart', {}).values())

        return jsonify({
            'success': True,
            'cart_count': cart_count,
            'cart_total': round(cart_total, 2)
        })

    except Exception as e:
        logger.exception("Error removing from cart:")
        return jsonify({'success': False, 'error': str(e)}), 500

def calculate_cart_total(cart):
    total = 0
    for item in cart:
        product = Product.query.get(item['product_id'])
        total += product.price * item['quantity']
    return total

@bp.route('/api/newsletter-signup', methods=['POST'])
def newsletter_signup():
    email = request.json.get('email')
    if not email:
        return jsonify({'success': False, 'error': 'Email required'})
    
    # Add newsletter signup logic here
    return jsonify({'success': True})

@bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@bp.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

@bp.route('/about')
def about():
    return render_template('about.html')



stripe.api_key = 'your_stripe_secret_key'

@bp.route("/subscribe")
@login_required
def subscribe():
    subscription_plans = SubscriptionPlan.query.filter_by(is_active=True).all()
    return render_template('subscribe.html', subscription_plans=subscription_plans)

@bp.route("/api/create-subscription", methods=['POST'])
@login_required
def create_subscription():
    try:
        data = request.json
        plan = SubscriptionPlan.query.get(data['planId'])
        
        if not plan:
            return jsonify({'success': False, 'error': 'Invalid plan'})

        # Create or get Stripe customer
        if not current_user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                payment_method=data['paymentMethodId'],
                invoice_settings={
                    'default_payment_method': data['paymentMethodId'],
                },
            )
            current_user.stripe_customer_id = customer.id
            db.session.commit()
        else:
            # Update payment method
            stripe.PaymentMethod.attach(
                data['paymentMethodId'],
                customer=current_user.stripe_customer_id,
            )

        # Create Stripe subscription
        stripe_subscription = stripe.Subscription.create(
            customer=current_user.stripe_customer_id,
            items=[{'price': plan.stripe_price_id}],
            payment_behavior='default_incomplete',
            expand=['latest_invoice.payment_intent'],
        )

        # Create local subscription record
        subscription = Subscription(
            user_id=current_user.id,
            plan_id=plan.id,
            start_date=datetime.utcnow(),
            next_billing_date=datetime.utcnow() + timedelta(days=30)
        )
        db.session.add(subscription)
        db.session.commit()

        return jsonify({
            'success': True,
            'subscription': stripe_subscription.id
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route("/subscription/success")
@login_required
def subscription_success():
    return render_template('subscription_success.html')



# Add this to your initialization script or create a new management command
def initialize_subscription_plans():
    plans = [
        {
            'name': 'Basic Hydration',
            'price': 29.00,
            'description': '4 x 5-gallon bottles monthly',
            'stripe_price_id': 'price_basic_xxxx',
            'is_active': True
        },
        {
            'name': 'Premium Hydration',
            'price': 49.00,
            'description': '8 x 5-gallon bottles monthly',
            'stripe_price_id': 'price_premium_xxxx',
            'is_active': True
        },
        {
            'name': 'Business Hydration',
            'price': 89.00,
            'description': '16 x 5-gallon bottles monthly',
            'stripe_price_id': 'price_business_xxxx',
            'is_active': True
        }
    ]

    for plan in plans:
        existing_plan = SubscriptionPlan.query.filter_by(name=plan['name']).first()
        if not existing_plan:
            new_plan = SubscriptionPlan(**plan)
            db.session.add(new_plan)
    
    db.session.commit()