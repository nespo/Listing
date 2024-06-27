from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Seller, Package, Reminder

@receiver(post_save, sender=Seller)
def handle_package_change(sender, instance, created, **kwargs):
    if not created:
        current_datetime = timezone.now()
        expiry_datetime = instance.get_aware_datetime(instance.membership_expiry)
        if expiry_datetime and expiry_datetime <= current_datetime:
            if instance.new_package:
                instance.apply_new_package()
            elif not instance.is_auto_renew:
                instance.package = None
                instance.normal_post_count = 0
                instance.featured_post_count = 0
                instance.membership_expiry = None
                instance.is_auto_renew = False
                instance.canceled_at = current_datetime
                instance.save()

@receiver(post_save, sender=Package)
def create_reminder(sender, instance, **kwargs):
    sellers_with_package = Seller.objects.filter(package=instance)
    for seller in sellers_with_package:
        expiry_date = seller.membership_expiry
        if expiry_date:
            reminder_date = expiry_date - timezone.timedelta(days=1)
            Reminder.objects.get_or_create(seller=seller, reminder_date=reminder_date)
