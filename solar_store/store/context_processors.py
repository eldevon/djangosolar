# def cart_count(request):
#     from .models import Cart, CartItem
    
#     cart_count = 0
#     if request.user.is_authenticated:
#         cart, created = Cart.objects.get_or_create(user=request.user)
#         cart_count = cart.total_items
#     else:
#         session_key = request.session.session_key
#         if session_key:
#             cart, created = Cart.objects.get_or_create(session_key=session_key)
#             cart_count = cart.total_items
    
#     return {'cart_count': cart_count}


# from .models import Cart, Wishlist

# def cart_context(request):
#     """Add cart information to all templates"""
#     context = {}
    
#     # Get or create cart
#     if request.user.is_authenticated:
#         cart, created = Cart.objects.get_or_create(user=request.user)
#         wishlist_count = Wishlist.objects.filter(user=request.user).count()
#     else:
#         if request.session.session_key:
#             cart, created = Cart.objects.get_or_create(session_key=request.session.session_key)
#         else:
#             cart = None
#         wishlist_count = 0
    
#     context['cart'] = cart
#     context['cart_count'] = cart.total_items if cart else 0
#     context['cart_total'] = cart.total_price if cart else 0
#     context['wishlist_count'] = wishlist_count
    
#     return context


from .models import Cart, Category

def cart_context(request):
    """Add cart information to all templates"""
    cart_count = 0
    cart_total = 0
    
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
        else:
            cart = None
    
    if cart:
        cart_count = cart.items.count()
        cart_total = cart.total_price()
    
    return {
        'cart_count': cart_count,
        'cart_total': cart_total,
        'cart': cart,
    }

def categories_context(request):
    """Add categories to all templates"""
    categories = Category.objects.all()[:8]  # Limit to 8 for menu
    return {
        'categories': categories,
    }
    

