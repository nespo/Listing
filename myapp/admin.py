from django.contrib import admin
from django.urls import reverse
from django.utils import timezone
from datetime import datetime, timedelta, time, date
from django.utils.html import format_html
from django.core.mail import send_mail
from django.conf import settings
from django import forms
from .forms import FAQForm, PageForm
from .models import *

class FooterWidgetLinkInline(admin.TabularInline):
    model = FooterWidgetLink
    extra = 1
    fields = ('text', 'url')
    can_delete = True
    verbose_name = "Link"
    verbose_name_plural = "Links"

class FooterWidgetForm(forms.ModelForm):
    class Meta:
        model = FooterWidget
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['text'].widget.attrs['style'] = 'display:none'
        self.fields['custom_html'].widget.attrs['style'] = 'display:none'

        if self.instance and self.instance.widget_type == 'logo_text':
            self.fields['text'].widget.attrs['style'] = ''
        elif self.instance and (self.instance.widget_type == 'link1' or self.instance.widget_type == 'link2'):
            pass
        elif self.instance and self.instance.widget_type == 'html':
            self.fields['custom_html'].widget.attrs['style'] = ''

    class Media:
        js = ('admin/js/footer_widget.js',)

@admin.register(FooterWidget)
class FooterWidgetAdmin(admin.ModelAdmin):
    form = FooterWidgetForm
    list_display = ('widget_type', 'text', 'custom_html')
    list_filter = ('widget_type',)
    search_fields = ('text', 'custom_html')
    inlines = [FooterWidgetLinkInline]

@admin.register(FooterMenuItem)
class FooterMenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'url')

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('site_title',)
    fieldsets = (
        (None, {
            'fields': ('site_title', 'site_description', 'site_logo', 'site_favicon', 'meta_data')
        }),
        ('Footer Menu', {
            'fields': ('footer_menu_items', 'footer_widgets')
        }),
    )
    filter_horizontal = ('footer_menu_items', 'footer_widgets')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name', 'description')

class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = '__all__'

@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    form = PackageForm
    list_display = ('name', 'normal_post_limit', 'featured_post_limit', 'price', 'duration', 'duration_unit')
    list_filter = ('duration_unit',)
    search_fields = ('name', 'description')

@admin.register(ListingPrice)
class ListingPriceAdmin(admin.ModelAdmin):
    list_display = ('normal_listing_price', 'featured_listing_price')

@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ('user', 'company_name', 'is_approved', 'normal_post_count', 'featured_post_count', 'individual_normal_posts', 'individual_featured_posts', 'membership_expiry', 'is_auto_renew', 'send_reset_password_link')
    actions = ['approve_seller', 'disapprove_seller']

    def approve_seller(self, request, queryset):
        queryset.update(is_approved=True)
        for seller in queryset:
            try:
                send_mail(
                    'Account Approved',
                    'Your account has been approved by admin.',
                    settings.DEFAULT_FROM_EMAIL,
                    [seller.user.email],
                )
            except:
                continue
    approve_seller.short_description = "Approve selected sellers"

    def disapprove_seller(self, request, queryset):
        queryset.update(is_approved=False)
        for seller in queryset:
            try:
                send_mail(
                    'Account Disapproved',
                    'Your account has been disapproved by admin.',
                    settings.DEFAULT_FROM_EMAIL,
                    [seller.user.email],
                )
            except:
                continue
    disapprove_seller.short_description = "Disapprove selected sellers"

    def send_reset_password_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">Send Reset Password Link</a>', url)
    send_reset_password_link.short_description = "Send Reset Password Link"

    def save_model(self, request, obj, form, change):
        if 'send_reset_password_link' in request.POST:
            user = obj.user
            try:
                send_mail(
                    subject="Password Reset Request",
                    message="You can reset your password by clicking the link below:",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email]
                )
            except:
                pass

        # Check if the package was changed
        if change and 'package' in form.changed_data:
            # Apply new package details
            if obj.package:
                obj.normal_post_count = obj.package.normal_post_limit
                obj.featured_post_count = obj.package.featured_post_limit
                obj.membership_expiry = timezone.now() + timedelta(minutes=obj.package.get_duration_in_minutes())
            else:
                obj.normal_post_count = 0
                obj.featured_post_count = 0
                obj.membership_expiry = None

        super().save_model(request, obj, form, change)

class ListingImageInline(admin.TabularInline):
    model = ListingImage
    extra = 1

@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'seller', 'get_categories', 'sales_price', 'status', 'views', 'created_at')
    list_filter = ('status', 'categories')
    search_fields = ('project_name', 'project_description', 'project_address')
    inlines = [ListingImageInline]

    def get_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])
    get_categories.short_description = 'Categories'

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('seller', 'amount', 'transaction_date', 'description', 'transaction_type', 'transaction_id')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    form = FAQForm
    list_display = ('question',)

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    form = PageForm
    list_display = ('title', 'slug')

@admin.register(ContactUs)
class ContactUsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'sent_at')