# urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('register/', register_seller, name='register_seller'),
    path('validate_step/', validate_step, name='validate_step'),
    path('activate/<uidb64>/<token>/', activate, name='activate'),
    path('api/countries/', load_countries, name='load_countries'),
    path('api/get_states/<int:country_id>/', load_states, name='load_states'),
    path('api/get_citiess/<int:state_id>/', load_citiess, name='load_citiess'),
    path('api/get_country_code/<int:country_id>/', get_country_code, name='get_country_code'),
    path('listing/create/', create_listing, name='create_listing'),
    path('ajax/load-states/', listing_load_states, name='listing_load_states'),
    path('ajax/load-cities/', listing_load_cities, name='listing_load_cities'),
    path('listing/<slug:slug>/edit/', edit_listing, name='edit_listing'),
    path('listing/<slug:slug>/', listing_detail, name='listing_detail'),
    path('seller/listings/', seller_listings, name='seller_listings'),
    path('listings/', all_listings, name='all_listings'),
    path('country-autocomplete/', country_autocomplete, name='country_autocomplete'),
    path('state-autocomplete/', state_autocomplete, name='state_autocomplete'),
    path('city-autocomplete/', city_autocomplete, name='city_autocomplete'),
    path('buy-membership-listing/', buy_package_listing, name='buy_package_listing'),
    path('memberships/', public_packages, name='public_packages'),
    path('transactions/', transaction_history, name='transaction_history'),
    path('listing/<slug:slug>/submit_message/', submit_message, name='submit_message_with_slug'),
    path('seller/submit_message/', submit_message, name='submit_message_without_slug'),
    path('login/', login_user, name='login_user'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('update-profile/', update_profile, name='update_profile'),
    path('change-password/', change_password, name='change_password'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('cancel-auto-renew/', cancel_auto_renew, name='cancel_auto_renew'),
    path('seller/messages/', seller_messages, name='seller_messages'),
    path('seller/messages/<int:message_id>/', message_detail, name='message_detail'),
    path('seller/<int:seller_id>/', seller_profile, name='seller_profile'),
    path('remove_payment_method/', remove_payment_method, name='remove_payment_method'),
    path('add-payment-method/', AddPaymentMethodView.as_view(), name='add_payment_method'),
    #new
    path('contact-us/', ContactUsView.as_view(), name='contact_us'),
    path('faqs/', faq_list, name='faq_list'),
    path('page/<slug:slug>/', page_detail, name='page_detail'),
    
    # Password reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),

    #admin
    path('admin/formfieldsetting/', FormFieldSettingAdmin.changelist_view),
]