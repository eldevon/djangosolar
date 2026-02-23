from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Wishlist

@receiver(post_save, sender=User)
def create_user_wishlist(sender, instance, created, **kwargs):
    """Create a wishlist for new users"""
    if created:
        Wishlist.objects.create(user=instance)

        