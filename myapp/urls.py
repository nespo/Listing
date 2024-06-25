# urls.py
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('register/', register_seller, name='register_seller'),
    path('listing/create/', create_listing, name='create_listing'),
    path('listing/<slug:slug>/edit/', edit_listing, name='edit_listing'),
    path('listing/<slug:slug>/', listing_detail, name='listing_detail'),
    path('seller/listings/', seller_listings, name='seller_listings'),
    path('all/listings/', all_listings, name='all_listings'),
    path('buy-package-listing/', buy_package_listing, name='buy_package_listing'),
    path('transactions/', transaction_history, name='transaction_history'),
    path('contact-seller/<int:listing_id>/', contact_seller, name='contact_seller'),
    path('login/', login_user, name='login_user'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('update-profile/', update_profile, name='update_profile'),
    path('change-password/', change_password, name='change_password'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('search/', search, name='search'),
    path('category/<slug:slug>/', category_detail, name='category_detail'),
    path('cancel-auto-renew/', cancel_auto_renew, name='cancel_auto_renew'),
    
    # Password reset URLs
    path('password-reset/', CustomPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
]