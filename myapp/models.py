from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from datetime import datetime, timedelta, date, time
from django.core.validators import MaxValueValidator
from tinymce.models import HTMLField
from decimal import Decimal
import stripe

stripe.api_key = settings.STRIPE_SECRET_KEY


class Country(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=3, unique=True)

    def __str__(self):
        return self.name

class Region(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=3)
    country = models.ForeignKey(Country, related_name='regions', on_delete=models.CASCADE)

    def __str__(self):
        return self.name
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
        super().save(*args, **kwargs)

class Package(models.Model):
    PACKAGE_TYPE_CHOICES = [
        ('minutes', 'Minutes'),
        ('hours', 'Hourly'),
        ('days', 'Daily'),
        ('weeks', 'Weekly'),
        ('months', 'Monthly'),
        ('years', 'Yearly')
    ]
    name = models.CharField(max_length=255)
    normal_post_limit = models.IntegerField()
    featured_post_limit = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration = models.IntegerField(default=30)
    duration_unit = models.CharField(max_length=10, choices=PACKAGE_TYPE_CHOICES, default='days')
    description = models.TextField(null=True, blank=True)
    inclusions = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Membership"
        verbose_name_plural = "Memberships"

    def __str__(self):
        return self.name

    def get_duration_in_minutes(self):
        duration_mapping = {
            'minutes': 1,
            'hours': 60,
            'days': 1440,
            'weeks': 10080,
            'months': 43200,
            'years': 525600
        }
        return self.duration * duration_mapping.get(self.duration_unit, 1440)
    
    
class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=255, unique=True)
    company_address = models.TextField()
    company_phone_number = models.CharField(max_length=20)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True)
    state = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    new_package = models.ForeignKey(Package, related_name='new_package_set', null=True, blank=True, on_delete=models.SET_NULL)
    normal_post_count = models.IntegerField(default=0)  # Total normal posts allowed (package + individual)
    featured_post_count = models.IntegerField(default=0)  # Total featured posts allowed (package + individual)
    individual_normal_post_count = models.IntegerField(default=0)  # Tracking individual normal post
    individual_featured_post_count = models.IntegerField(default=0)  # Tracking individual featured post
    normal_post_used = models.IntegerField(default=0)  # Normal posts used
    featured_post_used = models.IntegerField(default=0)  # Featured posts used
    membership_expiry = models.DateTimeField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    is_auto_renew = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=255, null=True, blank=True)
    stripe_payment_method_id = models.CharField(max_length=255, null=True, blank=True)
    bio = HTMLField(null=True, blank=True)
    about = HTMLField(null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)

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
                    expiry_datetime = self.get_aware_datetime(seller.membership_expiry)
                    if expiry_datetime and timezone.now() >= expiry_datetime:
                        payment_intent = stripe.PaymentIntent.create(
                            customer=seller.stripe_customer_id,
                            amount=amount_in_cents,
                            currency='usd',
                            payment_method=seller.stripe_payment_method_id,
                            off_session=True,
                            confirm=True,
                            description=f'Renewal of Membership {seller.package.name}',
                        )
                        new_expiry = timezone.now() + timedelta(minutes=seller.package.get_duration_in_minutes())
                        seller.membership_expiry = new_expiry
                        seller.save()
            except stripe.error.StripeError as e:
                send_mail(
                    'Auto-renewal Failed',
                    'We were unable to renew your Memership. We will try again two more times. If it continues to fail, your package will be deactivated.',
                    settings.DEFAULT_FROM_EMAIL,
                    [self.user.email],
                )
                raise
            except Exception as e:
                raise

    def apply_new_package(self):
        if self.new_package:
            try:
                with transaction.atomic():
                    seller = Seller.objects.select_for_update().get(pk=self.pk)
                    
                    total_normal_posts = seller.individual_normal_post_count + seller.new_package.normal_post_limit
                    total_featured_posts = seller.individual_featured_post_count + seller.new_package.featured_post_limit
                    
                    seller.normal_post_count = total_normal_posts
                    seller.featured_post_count = total_featured_posts
                    
                    seller.package = seller.new_package
                    seller.new_package = None
                    new_expiry = timezone.now() + timedelta(minutes=seller.package.get_duration_in_minutes())
                    seller.membership_expiry = new_expiry
                    seller.is_auto_renew = True
                    seller.canceled_at = None
                    seller.save()
                    send_mail(
                        'Package Updated',
                        f'Your new Membership {seller.package.name} is now active.',
                        settings.DEFAULT_FROM_EMAIL,
                        [seller.user.email],
                    )
            except Exception as e:
                raise

    def save(self, *args, **kwargs):
        expiry_datetime = self.get_aware_datetime(self.membership_expiry)
        current_time = timezone.now()

        if self.package and self.membership_expiry and expiry_datetime:
            if expiry_datetime <= current_time:
                if self.new_package:
                    self.apply_new_package()
                elif not self.is_auto_renew and not self.stripe_payment_method_id:
                    self.deactivate_listings()
                    self.package = None
                    self.normal_post_count = 0
                    self.featured_post_count = 0
                    self.membership_expiry = None
                    self.is_auto_renew = False
                    self.canceled_at = current_time

        super().save(*args, **kwargs)

    def cancel_auto_renew(self):
        self.is_auto_renew = False
        self.canceled_at = timezone.now()
        self.save()

    def deactivate_listings(self):
        self.listing_set.update(status='inactive')

    def reactivate_listings(self):
        self.listing_set.update(status='active', expires_on=self.membership_expiry)

    def can_downgrade(self, new_package):
        total_normal_posts = self.normal_post_count + new_package.normal_post_limit
        total_featured_posts = self.featured_post_count + new_package.featured_post_limit
        
        if self.normal_post_used > total_normal_posts or self.featured_post_used > total_featured_posts:
            return False
        return True


class Reminder(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    email_sent = models.BooleanField(default=False)
    reminder_date = models.DateField()

    def __str__(self):
        return f"Reminder for {self.seller.user.username} on {self.reminder_date}"

class ListingPrice(models.Model):
    normal_listing_price = models.PositiveIntegerField(default=1250)
    featured_listing_price = models.PositiveIntegerField(default=1650)

    def __str__(self):
        return f"Normal: {self.normal_listing_price}, Featured: {self.featured_listing_price}"

class Listing(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('contingent', 'Contingent'),
        ('pending', 'Pending'),
        ('sold', 'Sold'),
        ('inactive', 'Inactive'),
    ]
    PROJECT_STATUS_CHOICES = [
        ('ntp', 'NTP'),
        ('in_construction', 'In-Construction'),
        ('in_operation', 'In-Operation'),
    ]
    TAX_CREDIT_TYPE_CHOICES = [
        ('itc', 'ITC'),
        ('ptc', 'PTC'),
        ('other', 'Other'),
    ]
    PROPERTY_TYPE_CHOICES = [
        ('own', 'Own'),
        ('lease', 'Lease'),
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    categories = models.ManyToManyField(Category, blank=True)
    
    project_name = models.CharField(max_length=255)
    project_description = HTMLField(null=True, blank=True)
    
    project_ntp_date = models.DateField(null=True, blank=True)
    project_cod_date = models.DateField(null=True, blank=True)
    project_pto_date = models.DateField(null=True, blank=True)
    
    is_featured = models.BooleanField(default=False)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='active')
    previous_status = models.CharField(max_length=50, choices=STATUS_CHOICES, null=True, blank=True)
    
    views = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    contractor_name = models.CharField(max_length=255)
    project_size = models.DecimalField(max_digits=17, decimal_places=2, validators=[MaxValueValidator(Decimal('10000000000000000'))], null=True, blank=True)
    battery_storage = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    projected_annual_income = models.PositiveIntegerField(
        validators=[MaxValueValidator(100000000000000000000000)], null=True, blank=True)
    epc_name = models.CharField(max_length=255, null=True, blank=True)
    current_annual_om_cost = models.PositiveIntegerField(
        validators=[MaxValueValidator(1000000000000000000000)], null=True, blank=True)
    om_escalation_rate = models.PositiveIntegerField(
        validators=[MaxValueValidator(100)], null=True, blank=True)
    sales_price = models.PositiveIntegerField(
        validators=[MaxValueValidator(10000000000000000000000)])
    
    project_address = models.CharField(max_length=255, null=True, blank=True)
    project_country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True)
    project_state = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True)
    project_city = models.CharField(max_length=255, null=True, blank=True)
    
    lot_size = models.DecimalField(max_digits=30, decimal_places=2, validators=[MaxValueValidator(Decimal('10000000000000000000000'))], null=True, blank=True)
    property_type = models.CharField(max_length=50, choices=PROPERTY_TYPE_CHOICES, null=True, blank=True)
    lease_term = models.PositiveIntegerField(validators=[MaxValueValidator(500)], null=True, blank=True)
    current_lease_rate_per_acre = models.PositiveIntegerField(
        validators=[MaxValueValidator(1000000000000000000000)], null=True, blank=True)
    lease_escalation_rate = models.PositiveIntegerField(
        validators=[MaxValueValidator(100)], null=True, blank=True)
    
    project_status = models.CharField(max_length=50, choices=PROJECT_STATUS_CHOICES, null=True, blank=True)
    tax_credit_type = models.CharField(max_length=50, choices=TAX_CREDIT_TYPE_CHOICES, null=True, blank=True)
    total_tax_credit_percentage = models.PositiveIntegerField(
        validators=[MaxValueValidator(100)], null=True, blank=True)
    remarks = HTMLField(null=True, blank=True)
    buyer_protections = HTMLField(null=True, blank=True)
    
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    sold_date = models.DateField(null=True, blank=True)
    thumbnail_image = models.ImageField(upload_to='listing_thumbnails/', null=True, blank=True)
    slug = models.SlugField(unique=True, blank=True, null=True)
    expires_on = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.project_name)

        super().save(*args, **kwargs)

        



class ListingImage(models.Model):
    listing = models.ForeignKey(Listing, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='listing_images/')

    def __str__(self):
        return f"Image for {self.listing.project_name}"

class Message(models.Model):
    listing = models.ForeignKey(Listing, null=True, blank=True, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False) 

    def __str__(self):
        return f"Message from {self.first_name} {self.last_name} to {self.seller.user.username} about {self.listing.project_name if self.listing else 'No Listing'}"

class Transaction(models.Model):
    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_date = models.DateTimeField(default=timezone.now)
    description = models.TextField(null=True, blank=True)
    transaction_type = models.CharField(max_length=50)
    transaction_id = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Transaction by {self.seller.user.username} on {self.transaction_date}"

    @property
    def is_auto_renew_transaction(self):
        return self.transaction_type == 'Package' and self.seller.is_auto_renew
    
class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = HTMLField()

    def __str__(self):
        return self.question

class Page(models.Model):
    title = models.CharField(max_length=255)
    content = HTMLField()
    slug = models.SlugField(unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class ContactUs(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)  # New field for phone number
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            send_mail(
                subject='New Contact Us Message',
                message=self.message,
                from_email=self.email,
                recipient_list=[settings.ADMIN_EMAIL],
            )
        except:
            pass


class FormFieldSetting(models.Model):
    form_name = models.CharField(max_length=100)
    field_name = models.CharField(max_length=100)
    label = models.CharField(max_length=255)
    order = models.IntegerField()

    class Meta:
        unique_together = ('form_name', 'field_name')
        ordering = ['order']

    def __str__(self):
        return f"{self.form_name} - {self.field_name}"