from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Seller, Package, Reminder

@receiver(post_save, sender=Seller)
def handle_package_change(sender, instance, created, **kwargs):
    if not created and instance.package:
        current_datetime = timezone.now()
        # Apply new package if the current package has expired
        if instance.new_package and instance.membership_expiry and current_datetime >= instance.membership_expiry:
            instance.apply_new_package()
        # Renew package if auto-renew is enabled and the package has expired
        elif instance.is_auto_renew and instance.package and instance.membership_expiry and current_datetime >= instance.membership_expiry:
            try:
                instance.renew_package()
            except Exception as e:
                print(f"Error in renewing package: {e}")

@receiver(post_save, sender=Package)
def create_reminder(sender, instance, **kwargs):
    sellers_with_package = Seller.objects.filter(package=instance)
    for seller in sellers_with_package:
        expiry_date = seller.membership_expiry
        if expiry_date:
            reminder_date = expiry_date - timezone.timedelta(days=1)
            Reminder.objects.get_or_create(seller=seller, reminder_date=reminder_date)
