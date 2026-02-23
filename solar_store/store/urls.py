# from django.urls import path
# from . import views

# urlpatterns = [
#     path('', views.index, name='index'),
#     path('products/', views.ProductListView.as_view(), name='product_list'),
#     path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
#     path('cart/', views.cart_view, name='cart'),
#     path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
#     path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
#     path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
# ]


from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Home & Static Pages
    path('', views.index, name='index'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.contact_view, name='contact'),
    
    # Products
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('products/search/', views.search_view, name='search'),
    path('products/category/<slug:slug>/', views.category_view, name='category'),
    path('products/<slug:slug>/', views.ProductDetailView.as_view(), name='product_detail'),
    
    # Cart
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('cart/remove/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/count/', views.cart_count, name='cart_count'),
    
    # Checkout & Orders
    path('checkout/', views.checkout_view, name='checkout'),
    path('orders/', views.order_list_view, name='order_list'),
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset (using Django's built-in views)
    path('password-reset/', 
         auth_views.PasswordResetView.as_view(
             template_name='store/auth/password_reset.html'
         ), 
         name='password_reset'),
    path('password-reset/done/', 
         auth_views.PasswordResetDoneView.as_view(
             template_name='store/auth/password_reset_done.html'
         ), 
         name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', 
         auth_views.PasswordResetConfirmView.as_view(
             template_name='store/auth/password_reset_confirm.html'
         ), 
         name='password_reset_confirm'),
    path('password-reset-complete/', 
         auth_views.PasswordResetCompleteView.as_view(
             template_name='store/auth/password_reset_complete.html'
         ), 
         name='password_reset_complete'),
    
    # Wishlist
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),
    
    # API Endpoints
    path('api/products/filter/', views.product_filter_api, name='product_filter_api'),
]

