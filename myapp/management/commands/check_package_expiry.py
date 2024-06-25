from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import Seller
import time

class Command(BaseCommand):
    help = 'Continuously check for expired packages and handle auto-renewals.'

    def handle(self, *args, **kwargs):
        while True:
            now = timezone.now()  # Use datetime
            sellers_to_renew = Seller.objects.filter(membership_expiry__lte=now, is_auto_renew=True)
            for seller in sellers_to_renew:
                try:
                    print(f"Renewing package for seller: {seller.user.username} with expiry: {seller.membership_expiry}")
                    seller.renew_package()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error renewing package for {seller.user.username}: {e}"))

            # Check for new package activation
            sellers_to_activate = Seller.objects.filter(new_package__isnull=False, membership_expiry__lte=now)
            for seller in sellers_to_activate:
                try:
                    print(f"Applying new package for seller: {seller.user.username} with expiry: {seller.membership_expiry}")
                    seller.apply_new_package()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error applying new package for {seller.user.username}: {e}"))

            self.stdout.write(self.style.SUCCESS('Checked package expirations and handled auto-renewals.'))

            # Wait for 60 seconds before checking again
            time.sleep(60)
