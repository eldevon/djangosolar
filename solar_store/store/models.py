# # from django.db import models
# # from django.contrib.auth.models import User
# # from django.core.validators import MinValueValidator

# # class Category(models.Model):
# #     name = models.CharField(max_length=100)
# #     slug = models.SlugField(unique=True)
# #     description = models.TextField(blank=True)
    
# #     class Meta:
# #         verbose_name_plural = "Categories"
    
# #     def __str__(self):
# #         return self.name

# # class Product(models.Model):
# #     TYPE_CHOICES = [
# #         ('mono', 'Monocrystalline'),
# #         ('poly', 'Polycrystalline'),
# #         ('thin', 'Thin-Film'),
# #     ]
    
# #     name = models.CharField(max_length=200)
# #     slug = models.SlugField(unique=True)
# #     description = models.TextField()
# #     price = models.DecimalField(max_digits=10, decimal_places=2)
# #     category = models.ForeignKey(Category, on_delete=models.CASCADE)
# #     panel_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
# #     wattage = models.IntegerField(help_text="Wattage in watts")
# #     efficiency = models.DecimalField(max_digits=4, decimal_places=2, help_text="Efficiency percentage")
# #     dimensions = models.CharField(max_length=100, help_text="Dimensions in mm")
# #     weight = models.DecimalField(max_digits=6, decimal_places=2, help_text="Weight in kg")
# #     warranty_years = models.IntegerField()
# #     image = models.ImageField(upload_to='products/', blank=True)
# #     stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)
    
# #     def __str__(self):
# #         return self.name

# # class Cart(models.Model):
# #     user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
# #     session_key = models.CharField(max_length=100, null=True, blank=True)
# #     created_at = models.DateTimeField(auto_now_add=True)
# #     updated_at = models.DateTimeField(auto_now=True)
    
# #     @property
# #     def total_price(self):
# #         return sum(item.total_price for item in self.items.all())
    
# #     @property
# #     def total_items(self):
# #         return sum(item.quantity for item in self.items.all())

# # class CartItem(models.Model):
# #     cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
# #     product = models.ForeignKey(Product, on_delete=models.CASCADE)
# #     quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    
# #     @property
# #     def total_price(self):
# #         return self.product.price * self.quantity
    
# #     def __str__(self):
# #         return f"{self.quantity} x {self.product.name}"


from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.text import slugify
from django.urls import reverse
import uuid

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='solar-panel', 
                           help_text="Font Awesome icon class")
    
    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Product(models.Model):
    TYPE_CHOICES = [
        ('mono', 'Monocrystalline'),
        ('poly', 'Polycrystalline'),
        ('thin', 'Thin-Film'),
        ('bifacial', 'Bifacial'),
    ]
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    description = models.TextField()
    detailed_description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    panel_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    wattage = models.IntegerField(help_text="Wattage in watts")
    efficiency = models.DecimalField(max_digits=4, decimal_places=2, 
                                    help_text="Efficiency percentage")
    dimensions = models.CharField(max_length=100, help_text="Dimensions in mm (L x W x H)")
    weight = models.DecimalField(max_digits=6, decimal_places=2, help_text="Weight in kg")
    warranty_years = models.IntegerField(default=25)
    temperature_coefficient = models.CharField(max_length=50, blank=True)
    max_system_voltage = models.IntegerField(default=1000, help_text="Maximum system voltage in volts")
    image = models.ImageField(upload_to='products/', blank=True)
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True)
    stock = models.IntegerField(default=0, validators=[MinValueValidator(0)])
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self):
        return reverse('product_detail', kwargs={'slug': self.slug})
    
    @property
    def price_per_watt(self):
        return round(self.price / self.wattage, 4)
    
    def get_related_products(self):
        return Product.objects.filter(
            category=self.category
        ).exclude(id=self.id)[:4]

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/gallery/')
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']

class ProductReview(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['product', 'user']

# class Cart(models.Model):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
#     session_key = models.CharField(max_length=100, null=True, blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
    
#     class Meta:
#         ordering = ['-created_at']
    
#     @property
#     def total_price(self):
#         return sum(item.total_price for item in self.items.all())
    
#     @property
#     def total_items(self):
#         return sum(item.quantity for item in self.items.all())
    
#     def get_or_create_cart(request):
#         if request.user.is_authenticated:
#             cart, created = Cart.objects.get_or_create(user=request.user)
#         else:
#             if not request.session.session_key:
#                 request.session.create()
#             session_key = request.session.session_key
#             cart, created = Cart.objects.get_or_create(session_key=session_key)
#         return cart

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-added_at']
        unique_together = ['cart', 'product']
    
    @property
    def total_price(self):
        return self.product.price * self.quantity
    
    def __str__(self):
#         return f"{self.quantity} x {self.product.name}"

class Wishlist(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    added_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'product']
        ordering = ['-added_at']

