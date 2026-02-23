from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, TemplateView
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.db.models import Q, Sum, Count, Avg
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
import json
from decimal import Decimal

from .models import Product, Category, Cart, CartItem, Order, OrderItem, ShippingAddress, Review, Wishlist
from .forms import ContactForm, ReviewForm, ShippingAddressForm

# ============ HOME & STATIC PAGES ============

def index(request):
    """Home page view"""
    featured = Product.objects.filter(featured=True, stock__gt=0)[:8]
    new_arrivals = Product.objects.filter(stock__gt=0).order_by('-created_at')[:6]
    categories = Category.objects.all()[:6]
    
    # Get best sellers (products with most orders)
    best_sellers = Product.objects.annotate(
        order_count=Count('orderitem')
    ).filter(stock__gt=0).order_by('-order_count')[:4]
    
    context = {
        'featured_products': featured,
        'new_arrivals': new_arrivals,
        'categories': categories,
        'best_sellers': best_sellers,
    }
    return render(request, 'store/index.html', context)


class AboutView(TemplateView):
    """About page"""
    template_name = 'store/about.html'


def contact_view(request):
    """Contact page with form submission"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Save contact message (you'd need a ContactMessage model)
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            message = form.cleaned_data['message']
            
            # Send email notification
            subject = f'New Contact Message from {name}'
            email_message = f"""
            Name: {name}
            Email: {email}
            Message: {message}
            """
            
            send_mail(
                subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.CONTACT_EMAIL],
                fail_silently=False,
            )
            
            messages.success(request, 'Thank you for your message! We will get back to you soon.')
            return redirect('contact')
    else:
        form = ContactForm()
    
    return render(request, 'store/contact.html', {'form': form})


# ============ PRODUCT VIEWS ============

class ProductListView(ListView):
    """Product listing with filtering and sorting"""
    model = Product
    template_name = 'store/product_list.html'
    context_object_name = 'products'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = Product.objects.filter(stock__gt=0).select_related('category')
        
        # Filter by category
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Filter by panel type
        panel_type = self.request.GET.get('type')
        if panel_type:
            queryset = queryset.filter(panel_type=panel_type)
        
        # Filter by price range
        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price:
            queryset = queryset.filter(price__gte=Decimal(min_price))
        if max_price:
            queryset = queryset.filter(price__lte=Decimal(max_price))
        
        # Filter by wattage
        min_wattage = self.request.GET.get('min_wattage')
        max_wattage = self.request.GET.get('max_wattage')
        if min_wattage:
            queryset = queryset.filter(wattage__gte=int(min_wattage))
        if max_wattage:
            queryset = queryset.filter(wattage__lte=int(max_wattage))
        
        # Search
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        # Sort
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'price_low':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high':
            queryset = queryset.order_by('-price')
        elif sort_by == 'wattage_high':
            queryset = queryset.order_by('-wattage')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'popular':
            queryset = queryset.annotate(
                order_count=Count('orderitem')
            ).order_by('-order_count')
        else:
            queryset = queryset.order_by('name')
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['panel_types'] = Product.TYPE_CHOICES
        
        # Get filter values for template
        context['current_category'] = self.request.GET.get('category', '')
        context['current_type'] = self.request.GET.get('type', '')
        context['current_sort'] = self.request.GET.get('sort', 'name')
        context['search_query'] = self.request.GET.get('q', '')
        
        # Price ranges for filter
        price_stats = Product.objects.aggregate(
            min_price=Min('price'),
            max_price=Max('price')
        )
        context['min_price_range'] = price_stats['min_price'] or 0
        context['max_price_range'] = price_stats['max_price'] or 10000
        
        return context


class ProductDetailView(DetailView):
    """Product detail page with reviews"""
    model = Product
    template_name = 'store/product_detail.html'
    context_object_name = 'product'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.object
        
        # Related products
        context['related_products'] = Product.objects.filter(
            category=product.category
        ).exclude(id=product.id)[:4]
        
        # Reviews
        context['reviews'] = Review.objects.filter(product=product).order_by('-created_at')
        context['review_count'] = context['reviews'].count()
        context['average_rating'] = context['reviews'].aggregate(
            avg=Avg('rating')
        )['avg'] or 0
        
        # Review form (if user is authenticated)
        if self.request.user.is_authenticated:
            context['review_form'] = ReviewForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle review submission"""
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to submit a review.')
            return redirect('login')
        
        self.object = self.get_object()
        form = ReviewForm(request.POST)
        
        if form.is_valid():
            review = form.save(commit=False)
            review.product = self.object
            review.user = request.user
            review.save()
            messages.success(request, 'Thank you for your review!')
        
        return redirect('product_detail', slug=self.object.slug)


def category_view(request, slug):
    """Category-specific product listing"""
    category = get_object_or_404(Category, slug=slug)
    products = Product.objects.filter(category=category, stock__gt=0)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'store/category.html', {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
    })


# ============ CART VIEWS ============

def get_or_create_cart(request):
    """Helper function to get or create cart for user/session"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


@require_POST
def add_to_cart(request, product_id):
    """Add product to cart (HTMX compatible)"""
    product = get_object_or_404(Product, id=product_id)
    
    # Check stock
    if product.stock < 1:
        if request.htmx:
            return HttpResponse('<div class="text-red-600">Out of stock</div>')
        messages.error(request, 'This product is out of stock.')
        return redirect('product_detail', slug=product.slug)
    
    cart = get_or_create_cart(request)
    
    # Add or update cart item
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        # Check if adding more than available stock
        if cart_item.quantity + 1 > product.stock:
            if request.htmx:
                return HttpResponse('<div class="text-red-600">Not enough stock available</div>')
            messages.error(request, 'Not enough stock available.')
        else:
            cart_item.quantity += 1
            cart_item.save()
    
    messages.success(request, f'Added {product.name} to cart')
    
    if request.htmx:
        return render(request, 'store/partials/_cart_items.html', {
            'cart': cart
        })
    
    return redirect('cart_view')


@require_POST
def update_cart_item(request, item_id):
    """Update cart item quantity"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    # Verify cart belongs to user
    if request.user.is_authenticated:
        if cart_item.cart.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    else:
        if cart_item.cart.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    quantity = int(request.POST.get('quantity', 1))
    
    # Check stock
    if quantity > cart_item.product.stock:
        return JsonResponse({
            'error': f'Only {cart_item.product.stock} items available'
        }, status=400)
    
    if quantity < 1:
        cart_item.delete()
    else:
        cart_item.quantity = quantity
        cart_item.save()
    
    cart = cart_item.cart
    
    if request.htmx:
        return render(request, 'store/partials/_cart_items.html', {
            'cart': cart
        })
    
    return JsonResponse({
        'success': True,
        'total': str(cart.total_price()),
        'item_total': str(cart_item.total_price())
    })


@require_POST
def remove_from_cart(request, item_id):
    """Remove item from cart"""
    cart_item = get_object_or_404(CartItem, id=item_id)
    
    # Verify cart belongs to user
    if request.user.is_authenticated:
        if cart_item.cart.user != request.user:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    else:
        if cart_item.cart.session_key != request.session.session_key:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    cart = cart_item.cart
    product_name = cart_item.product.name
    cart_item.delete()
    
    messages.success(request, f'Removed {product_name} from cart')
    
    if request.htmx:
        return render(request, 'store/partials/_cart_items.html', {
            'cart': cart
        })
    
    return redirect('cart_view')


def cart_view(request):
    """Cart page"""
    cart = get_or_create_cart(request)
    
    # Check stock for all items
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.warning(
                request, 
                f'Only {item.product.stock} of {item.product.name} available'
            )
    
    return render(request, 'store/cart.html', {'cart': cart})


@require_GET
def cart_count(request):
    """API endpoint for cart count (for AJAX updates)"""
    cart = get_or_create_cart(request)
    count = cart.items.count()
    total = cart.total_price()
    
    return JsonResponse({
        'count': count,
        'total': str(total),
        'formatted_total': f'${total:.2f}'
    })


# ============ CHECKOUT & ORDERS ============

@login_required
def checkout_view(request):
    """Checkout process"""
    cart = get_or_create_cart(request)
    
    if cart.items.count() == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('cart_view')
    
    # Check stock before checkout
    for item in cart.items.all():
        if item.quantity > item.product.stock:
            messages.error(
                request, 
                f'Only {item.product.stock} of {item.product.name} available. Please update your cart.'
            )
            return redirect('cart_view')
    
    if request.method == 'POST':
        form = ShippingAddressForm(request.POST)
        if form.is_valid():
            # Create shipping address
            shipping_address = form.save(commit=False)
            shipping_address.user = request.user
            shipping_address.save()
            
            # Create order
            order = Order.objects.create(
                user=request.user,
                shipping_address=shipping_address,
                total=cart.total_price(),
                status='pending'
            )
            
            # Create order items and update stock
            for cart_item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=cart_item.product,
                    quantity=cart_item.quantity,
                    price=cart_item.product.price
                )
                
                # Update product stock
                cart_item.product.stock -= cart_item.quantity
                cart_item.product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            # Send order confirmation email
            send_order_confirmation_email(request.user, order)
            
            messages.success(request, 'Order placed successfully!')
            return redirect('order_detail', order_id=order.id)
    else:
        # Try to get user's default shipping address
        try:
            default_address = ShippingAddress.objects.filter(
                user=request.user, is_default=True
            ).first()
            form = ShippingAddressForm(instance=default_address)
        except ShippingAddress.DoesNotExist:
            form = ShippingAddressForm()
    
    return render(request, 'store/checkout.html', {
        'cart': cart,
        'form': form
    })


def send_order_confirmation_email(user, order):
    """Send order confirmation email"""
    subject = f'Order Confirmation #{order.id}'
    html_message = render_to_string('store/emails/order_confirmation.html', {
        'order': order,
        'user': user
    })
    
    send_mail(
        subject,
        '',  # Plain text version (empty for HTML-only)
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=True,
    )


@login_required
def order_list_view(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'store/order_list.html', {'orders': orders})


@login_required
def order_detail_view(request, order_id):
    """Order detail page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'store/order_detail.html', {'order': order})


# ============ USER AUTHENTICATION ============

def register_view(request):
    """User registration"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Log the user in
            login(request, user)
            
            # Migrate session cart to user cart
            if request.session.session_key:
                try:
                    session_cart = Cart.objects.get(session_key=request.session.session_key)
                    user_cart, created = Cart.objects.get_or_create(user=user)
                    
                    # Merge cart items
                    for item in session_cart.items.all():
                        user_item, created = CartItem.objects.get_or_create(
                            cart=user_cart,
                            product=item.product,
                            defaults={'quantity': item.quantity}
                        )
                        if not created:
                            user_item.quantity += item.quantity
                            user_item.save()
                    
                    session_cart.delete()
                except Cart.DoesNotExist:
                    pass
            
            messages.success(request, 'Registration successful! Welcome to SolarStore.')
            return redirect('index')
    else:
        form = UserCreationForm()
    
    return render(request, 'store/auth/register.html', {'form': form})


def login_view(request):
    """User login"""
    if request.user.is_authenticated:
        return redirect('index')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                
                # Migrate session cart to user cart
                if request.session.session_key:
                    try:
                        session_cart = Cart.objects.get(session_key=request.session.session_key)
                        user_cart, created = Cart.objects.get_or_create(user=user)
                        
                        # Merge cart items
                        for item in session_cart.items.all():
                            user_item, created = CartItem.objects.get_or_create(
                                cart=user_cart,
                                product=item.product,
                                defaults={'quantity': item.quantity}
                            )
                            if not created:
                                user_item.quantity += item.quantity
                                user_item.save()
                        
                        session_cart.delete()
                    except Cart.DoesNotExist:
                        pass
                
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect to next page if specified
                next_page = request.GET.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect('index')
    else:
        form = AuthenticationForm()
    
    return render(request, 'store/auth/login.html', {'form': form})


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('index')


# ============ WISHLIST ============

@login_required
def wishlist_view(request):
    """User's wishlist"""
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist': wishlist})


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    """Add/remove product from wishlist"""
    product = get_object_or_404(Product, id=product_id)
    wishlist, created = Wishlist.objects.get_or_create(user=request.user)
    
    if product in wishlist.products.all():
        wishlist.products.remove(product)
        added = False
        message = 'Removed from wishlist'
    else:
        wishlist.products.add(product)
        added = True
        message = 'Added to wishlist'
    
    if request.htmx:
        return HttpResponse(f'''
            <div class="text-green-600">{message}</div>
            <button hx-post="/wishlist/toggle/{product_id}/"
                    hx-target="this"
                    hx-swap="outerHTML"
                    class="text-solar-yellow hover:text-solar-yellow/80">
                <i class="fas fa-heart {'text-solar-yellow' if added else 'text-gray-300'}"></i>
            </button>
        ''')
    
    return JsonResponse({'added': added, 'message': message})


# ============ SEARCH ============

def search_view(request):
    """Search results page"""
    query = request.GET.get('q', '')
    
    if not query:
        return redirect('product_list')
    
    products = Product.objects.filter(
        Q(name__icontains=query) |
        Q(description__icontains=query) |
        Q(category__name__icontains=query) |
        Q(panel_type__icontains=query)
    ).filter(stock__gt=0)
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'store/search_results.html', {
        'products': page_obj,
        'query': query,
        'count': products.count(),
        'page_obj': page_obj,
    })


# ============ API ENDPOINTS ============

@require_GET
def product_filter_api(request):
    """API endpoint for filtering products (AJAX)"""
    category = request.GET.get('category')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    panel_type = request.GET.get('panel_type')
    
    products = Product.objects.filter(stock__gt=0)
    
    if category:
        products = products.filter(category__slug=category)
    if min_price:
        products = products.filter(price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(price__lte=Decimal(max_price))
    if panel_type:
        products = products.filter(panel_type=panel_type)
    
    # Return as JSON
    data = [{
        'id': p.id,
        'name': p.name,
        'slug': p.slug,
        'price': str(p.price),
        'image': p.image.url if p.image else '/static/images/default-product.jpg',
        'url': p.get_absolute_url(),
        'wattage': p.wattage,
        'efficiency': p.efficiency,
        'stock': p.stock,
    } for p in products[:50]]  # Limit to 50 results
    
    return JsonResponse({'products': data})


# ============ ERROR HANDLERS ============

def handler404(request, exception):
    """Custom 404 page"""
    return render(request, 'store/errors/404.html', status=404)


def handler500(request):
    """Custom 500 page"""
    return render(request, 'store/errors/500.html', status=500)


def handler403(request, exception):
    """Custom 403 page"""
    return render(request, 'store/errors/403.html', status=403)


def handler400(request, exception):
    """Custom 400 page"""
    return render(request, 'store/errors/400.html', status=400)