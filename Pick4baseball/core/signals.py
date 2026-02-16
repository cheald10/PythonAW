# core/signals.py
"""
Signals for Baseball Pick 4 application.
Automatically creates UserProfile when a new User is created.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Automatically create a UserProfile when a new User is created.
    This ensures every user always has a profile, preventing errors.
    """
    if created:
        UserProfile.objects.create(user=instance)
        print(f"✓ Created profile for new user: {instance.username}")


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """
    Save the UserProfile whenever the User is saved.
    Creates profile if it doesn't exist (safety net).
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        # Safety net: create profile if it somehow doesn't exist
        UserProfile.objects.get_or_create(user=instance)