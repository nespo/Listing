# management/commands/send_reminders.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from myapp.models import Reminder, Seller

class Command(BaseCommand):
    help = 'Send reminder emails to sellers and auto renew packages'

    def handle(self, *args, **kwargs):
        today = timezone.now().date()
        reminders = Reminder.objects.filter(reminder_date=today, email_sent=False)
        for reminder in reminders:
            seller = reminder.seller
            if seller.new_package:
                subject = 'Your new package will start soon'
                message = f'Your current package will expire in 7 days, and your new package "{seller.new_package.name}" will start.'
            else:
                subject = 'Your package will expire soon'
                message = f'Your current package will expire in 7 days. Please renew your package to continue using our services.'
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [seller.user.email],
            )
            reminder.email_sent = True
            reminder.save()

        # Auto renew packages if the expiry date is today
        sellers_to_renew = Seller.objects.filter(membership_expiry=today, is_auto_renew=True)
        for seller in sellers_to_renew:
            seller.renew_package()

        self.stdout.write(self.style.SUCCESS('Successfully sent reminders and renewed packages'))
