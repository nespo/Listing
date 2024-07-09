from django.core.management.base import BaseCommand
from django.utils import timezone
from myapp.models import Seller
import time

class Command(BaseCommand):
    help = 'Continuously check for expired packages and handle auto-renewals.'

    def handle(self, *args, **kwargs):
        while True:
            now = timezone.now()
            sellers_to_check = Seller.objects.filter(membership_expiry__lte=now)
            for seller in sellers_to_check:
                try:
                    if seller.is_auto_renew:
                        seller.renew_package()
                    elif seller.new_package:
                        seller.apply_new_package()
                    else:
                        seller.deactivate_listings()
                        seller.package = None
                        seller.normal_post_count = 0
                        seller.featured_post_count = 0
                        seller.membership_expiry = None
                        seller.is_auto_renew = False
                        seller.canceled_at = now
                        seller.save()
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error handling package for {seller.user.username}: {e}"))

            self.stdout.write(self.style.SUCCESS('Checked package expirations and handled auto-renewals.'))
            time.sleep(60)
