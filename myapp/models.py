from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.db.models import F
from datetime import datetime, timedelta, time, date
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY

class FooterMenuItem(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return self.name

class FooterWidget(models.Model):
    WIDGET_TYPES = [
        ('logo_text', 'Logo and Text'),
        ('link1', 'Link Section 1'),
        ('link2', 'Link Section 2'),
        ('html', 'Custom HTML')
    ]
    
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPES)
    text = models.CharField(max_length=255, null=True, blank=True)
    custom_html = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.get_widget_type_display()} - {self.text or self.custom_html[:30]}"

class FooterWidgetLink(models.Model):
    widget = models.ForeignKey(FooterWidget, related_name='links', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    url = models.URLField()

    def __str__(self):
        return self.text

class SiteSettings(models.Model):
    site_title = models.CharField(max_length=255)
    site_description = models.TextField()
    site_logo = models.ImageField(upload_to='site_logo/', null=True, blank=True)
    site_favicon = models.ImageField(upload_to='site_favicon/', null=True, blank=True)
    meta_data = models.JSONField(default=dict)
    footer_menu_items = models.ManyToManyField(FooterMenuItem, blank=True)
    footer_widgets = models.ManyToManyField(FooterWidget, blank=True)

    def __str__(self):
        return self.site_title

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(default='No description available')
    icon = models.ImageField(upload_to='category_icons/', null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', args=[str(self.slug)])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        else:
            new_slug = slugify(self.name)
            if self.slug != new_slug:
                self.slug = new_slug
        super().save(*args, **kwargs)

class Package(models.Model):
    PACKAGE_TYPE_CHOICES = [
        ('minutes', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')
    ]
    name = models.CharField(max_length=255)
    normal_post_limit = models.IntegerField()
    featured_post_limit = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(default=30)
    duration_unit = models.CharField(max_length=10, choices=PACKAGE_TYPE_CHOICES, default='days')
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def get_duration_in_minutes(self):
        if self.duration_unit == 'minutes':
            return self.duration
        elif self.duration_unit == 'hours':
            return self.duration * 60
        elif self.duration_unit == 'days':
            return self.duration * 1440  # 24 * 60
        elif self.duration_unit == 'weeks':
            return self.duration * 10080  # 7 * 24 * 60
        elif self.duration_unit == 'months':
            return self.duration * 43200  # 30 * 24 * 60
        elif self.duration_unit == 'years':
            return self.duration * 525600  # 365 * 24 * 60
        return self.duration * 1440  # Default to days

class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, unique=True)
    company_address = models.TextField()
    company_phone_number = models.CharField(max_length=20)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    normal_post_count = models.IntegerField(default=0)
    featured_post_count = models.IntegerField(default=0)
    membership_expiry = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    individual_normal_posts = models.IntegerField(default=0)
    individual_featured_posts = models.IntegerField(default=0)
    new_package = models.ForeignKey(Package, related_name='new_package_set', null=True, blank=True, on_delete=models.SET_NULL)
    is_auto_renew = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_method_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return self.user.username

    def get_aware_datetime(self, date_time):
        """Ensure datetime is timezone-aware."""
        if isinstance(date_time, datetime):
            if timezone.is_naive(date_time):
                return timezone.make_aware(date_time)
            return date_time
        elif isinstance(date_time, date):
            return timezone.make_aware(datetime.combine(date_time, time.min))
        return None

    def renew_package(self):
        if self.package and self.is_auto_renew:
            amount_in_cents = int(self.package.price * 100)
            try:
                with transaction.atomic():
                    seller = Seller.objects.select_for_update().get(pk=self.pk)
                    print(f"Attempting to renew package for seller {seller.user.username}, current expiry: {seller.membership_expiry}")
                    expiry_datetime = self.get_aware_datetime(seller.membership_expiry)
                    if expiry_datetime and timezone.now() >= expiry_datetime:
                        print(f"Membership expired, processing payment for seller {seller.user.username}")
                        payment_intent = stripe.PaymentIntent.create(
                            customer=seller.stripe_customer_id,
                            amount=amount_in_cents,
                            currency='usd',
                            payment_method=seller.stripe_payment_method_id,
                            off_session=True,
                            confirm=True,
                            description=f'Renewal of package {seller.package.name}',
                        )
                        print(f"Payment processed successfully for seller {seller.user.username}")
                        # Update the membership expiry to extend by the package duration
                        seller.membership_expiry = timezone.now() + timedelta(minutes=seller.package.get_duration_in_minutes())
                        seller.save()
                        print(f"Package {seller.package.name} renewed for seller {seller.user.username}, new expiry: {seller.membership_expiry}")
                    else:
                        print(f"Membership has not yet expired for seller {seller.user.username}, no action taken. Expiry time {seller.membership_expiry}, Current time {timezone.now()}")
            except stripe.error.StripeError as e:
                print(f"Stripe Error while renewing package for seller {seller.user.username}: {e}")
                raise
            except Exception as e:
                print(f"Unexpected error while renewing package for seller {seller.user.username}: {e}")
                raise

    def apply_new_package(self):
        if self.new_package:
            try:
                with transaction.atomic():
                    seller = Seller.objects.select_for_update().get(pk=self.pk)
                    print(f"Applying new package for seller {seller.user.username}")
                    seller.package = seller.new_package
                    seller.new_package = None
                    seller.normal_post_count = seller.package.normal_post_limit
                    seller.featured_post_count = seller.package.featured_post_limit
                    seller.membership_expiry = timezone.now() + timedelta(minutes=seller.package.get_duration_in_minutes())
                    seller.is_auto_renew = True
                    seller.canceled_at = None
                    seller.save()
                    send_mail(
                        'Package Updated',
                        f'Your new package {seller.package.name} is now active.',
                        settings.DEFAULT_FROM_EMAIL,
                        [seller.user.email],
                    )
                    print(f"Applied new package {seller.package.name} for seller {seller.user.username}")
            except Exception as e:
                print(f"Unexpected error while applying new package for seller {seller.user.username}: {e}")
                raise

    def save(self, *args, **kwargs):
        print(f"Saving seller {self.user.username}, current expiry: {self.membership_expiry}")
        expiry_datetime = self.get_aware_datetime(self.membership_expiry)
        if self.package and self.membership_expiry and expiry_datetime and timezone.now() >= expiry_datetime:
            self.apply_new_package()
        super().save(*args, **kwargs)
        print(f"Saved seller {self.user.username}, new expiry: {self.membership_expiry}")

    def cancel_auto_renew(self):
        self.is_auto_renew = False
        self.canceled_at = timezone.now()
        self.save()

class Reminder(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    email_sent = models.BooleanField(default=False)
    reminder_date = models.DateField()

    def __str__(self):
        return f"Reminder for {self.seller.user.username} on {self.reminder_date}"

class ListingPrice(models.Model):
    normal_listing_price = models.DecimalField(max_digits=10, decimal_places=2, default=2.00)
    featured_listing_price = models.DecimalField(max_digits=10, decimal_places=2, default=3.00)

    def __str__(self):
        return f"Normal: {self.normal_listing_price}, Featured: {self.featured_listing_price}"

class Listing(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('sold', 'Sold'),
        ('archived', 'Archived')
    ]
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    project_ntp_date = models.DateField(null=True, blank=True)
    project_cod_date = models.DateField(null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    location = models.CharField(max_length=255)
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    project_name = models.CharField(max_length=255)
    project_description = models.TextField(null=True, blank=True)
    developer_name = models.CharField(max_length=255)
    contractor_name = models.CharField(max_length=255)
    project_size = models.DecimalField(max_digits=10, decimal_places=2)
    completion_percentage = models.IntegerField(default=0)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    additional_info = models.TextField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    sold_date = models.DateField(null=True, blank=True)
    image = models.ImageField(upload_to='listing_images/', null=True, blank=True)
    thumbnail_image = models.ImageField(upload_to='listing_thumbnails/', null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.status == 'sold' and not self.sold_date:
            self.sold_date = timezone.now()
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    @property
    def is_recently_sold(self):
        if self.sold_date:
            return timezone.now() - self.sold_date <= timezone.timedelta(days=7)
        return False

    def __str__(self):
        return self.title

class Transaction(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(default=timezone.now)
    description = models.TextField(null=True, blank=True)
    transaction_type = models.CharField(max_length=50)

    def __str__(self):
        return f"Transaction by {self.seller.user.username} on {self.transaction_date}"
