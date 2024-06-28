from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from .models import *
from .forms import *
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
from django.template.loader import render_to_string
from django.db.models import Q, Count
from decimal import Decimal
from datetime import datetime
from django.core.paginator import Paginator
from .utils import send_custom_email, generate_invoice_pdf, get_site_settings
from django.utils.functional import SimpleLazyObject
import json
import stripe
import random

stripe.api_key = settings.STRIPE_SECRET_KEY

class CustomPasswordResetView(PasswordResetView):
    form_class = PasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = form.cleaned_data['email']
        if not User.objects.filter(email=email).exists():
            if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'error': 'No user found with this email address.'}, status=400)
            messages.error(self.request, 'No user found with this email address.')
            return self.form_invalid(form)
        
        form.save(
            request=self.request,
            use_https=self.request.is_secure(),
            email_template_name=self.email_template_name,
            subject_template_name=self.subject_template_name,
            from_email=None,
        )
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"message": "Password reset email sent successfully."})
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({"error": form.errors}, status=400)
        return super().form_invalid(form)
    
class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'registration/password_reset_done.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = AuthenticationForm()
        context['register_form'] = UserCreationForm()
        return context
    
def home(request):
    login_form = LoginForm()
    register_form = SellerRegistrationForm()
    categories = Category.objects.all()
    
    # Fetch listings
    featured_listings = Listing.objects.filter(is_featured=True).order_by('-created_at')
    normal_listings = Listing.objects.filter(is_featured=False).order_by('-created_at')
    
    # Debug information
    print("Featured Listings Count:", featured_listings.count())
    print("Normal Listings Count:", normal_listings.count())

    # Check if there are any listings in the database at all
    all_listings = Listing.objects.all()
    print("Total Listings Count:", all_listings.count())

    return render(request, 'home.html', {
        'login_form': login_form,
        'register_form': register_form,
        'categories': categories,
        'featured_listings': featured_listings,
        'normal_listings': normal_listings
    })

@login_required
def dashboard(request):
    seller = Seller.objects.get(user=request.user)
    messages_count = Message.objects.filter(seller=seller).count()
    package_renew_date = seller.membership_expiry

    # Check if the seller has an active package
    if not package_renew_date:
        package_status = "You have zero active packages"
    else:
        package_status = package_renew_date

    # Get views analytics for the seller's listings
    listings = seller.listing_set.all()
    views_data = {
        'dates': [listing.created_at.strftime('%Y-%m-%d') for listing in listings],
        'views': [listing.views for listing in listings],
    }

    context = {
        'messages_count': messages_count,
        'package_status': package_status,
        'views_data': views_data,
        'has_payment_method': bool(seller.stripe_payment_method_id),
    }
    return render(request, 'dashboard.html', context)

@login_required
def remove_payment_method(request):
    if request.method == 'POST':
        seller = Seller.objects.get(user=request.user)
        seller.stripe_payment_method_id = ''
        seller.is_auto_renew = False
        # Only update the fields related to payment method and auto renew
        seller.save(update_fields=['stripe_payment_method_id', 'is_auto_renew'])
        return JsonResponse({'status': 'success', 'message': 'Your saved payment method has been removed.'})
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'})


@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.seller)
        if form.is_valid():
            if form.has_changed():
                form.save()
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})
                else:
                    messages.success(request, 'Profile updated successfully')
                    return render(request, 'update_profile.html', {'form': form, 'show_modal': True})
            else:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'message': 'No changes detected.'})
                else:
                    messages.info(request, 'No changes detected.')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
    else:
        form = UserProfileForm(instance=request.user.seller)
    
    return render(request, 'update_profile.html', {'form': form})

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important to keep the user logged in after password change
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Password changed successfully.'})
            else:
                messages.success(request, 'Your password was successfully updated!')
                return redirect('dashboard')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
            else:
                messages.error(request, 'Please correct the error below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'change_password.html', {'form': form})

def register_seller(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            seller = Seller.objects.create(
                user=user,
                company_name=form.cleaned_data.get('company_name'),
                company_address=form.cleaned_data.get('company_address'),
                company_phone_number=form.cleaned_data.get('company_phone_number'),
                first_name=form.cleaned_data.get('first_name'),
                last_name=form.cleaned_data.get('last_name'),
                is_approved=False
            )
            # Create Stripe customer
            stripe_customer = stripe.Customer.create(
                email=user.email
            )
            seller.stripe_customer_id = stripe_customer.id
            seller.save()
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': f'Account created for {user.username}, awaiting admin approval.'})
            else:
                messages.success(request, f'Account created for {user.username}, awaiting admin approval.')
                return redirect('home')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
    else:
        form = SellerRegistrationForm()
    return render(request, 'register_seller.html', {'form': form})

def login_user(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.seller.is_approved:
                    login(request, user)
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({'success': True, 'message': 'Logged in successfully.'})
                    return redirect('dashboard')
                else:
                    error_message = 'Your account is awaiting admin approval.'
            else:
                error_message = 'Invalid username or password'
        else:
            error_message = 'Invalid form submission'
        
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': {'form': error_message}})
        else:
            messages.error(request, error_message)
    
    return redirect('home')

@login_required
def create_listing(request):
    seller = request.user.seller
    if not (seller.package or seller.individual_normal_posts > 0 or seller.individual_featured_posts > 0):
        messages.error(request, 'You must buy packages or listings to post a listing.')
        return redirect('buy_package_listing')

    field_order = [
        'project_name', 'project_description', 'categories', 'status', 'project_state', 
        'project_city', 'project_ntp_date', 'project_cod_date', 'project_pto_date',
        'contractor_name', 'project_size', 'battery_storage', 
        'projected_annual_income', 'epc_name', 'current_annual_om_cost', 
        'om_escalation_rate', 'sales_price', 'project_address', 'lot_size', 
        'property_type', 'lease_term', 'current_lease_rate_per_acre', 'lease_escalation_rate',
        'project_status', 'tax_credit_type', 'total_tax_credit_percentage', 'remarks',
        'buyer_protections', 'latitude', 'longitude', 'thumbnail_image'
    ]

    has_featured_posts = seller.featured_post_count > 0 or seller.individual_featured_posts > 0

    if has_featured_posts:
        field_order.insert(0, 'is_featured')

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user.seller

            if listing.is_featured:
                if seller.package and seller.featured_post_count > 0:
                    seller.featured_post_count -= 1
                elif seller.individual_featured_posts > 0:
                    seller.individual_featured_posts -= 1
                else:
                    messages.error(request, 'You do not have enough featured posts available.')
                    return render(request, 'create_listing.html', {'form': form, 'field_order': field_order})
            else:
                if seller.package and seller.normal_post_count > 0:
                    seller.normal_post_count -= 1
                elif seller.individual_normal_posts > 0:
                    seller.individual_normal_posts -= 1
                else:
                    messages.error(request, 'You do not have enough normal posts available.')
                    return render(request, 'create_listing.html', {'form': form, 'field_order': field_order})

            seller.save()

            if not listing.slug:
                listing.slug = slugify(listing.project_name)
            
            listing.save()

            # Save the categories to the listing
            form.save_m2m()

            images = request.FILES.getlist('images')
            for image in images:
                photo = ListingImage(listing=listing, image=image)
                photo.save()

            '''send_mail(
                'Listing Created',
                f'Your listing "{listing.project_name}" has been created successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )'''

            # Send email notification
            try:
                send_custom_email(
                    subject='Listing Created',
                    template_name='emails/listing_created_email.html',
                    context={'user': {
                                'first_name': seller.first_name,
                                },
                            'listing': listing},
                    recipient_list=[request.user.email]
                )
            except:
                pass
            messages.success(request, 'Listing created successfully')
            return redirect('dashboard')
        else:
            print("Form is not valid.")
            print(form.errors)
    else:
        form = ListingForm(user=request.user)

    return render(request, 'create_listing.html', {'form': form, 'field_order': field_order})

def load_cities(request):
    state_id = request.GET.get('state')
    if state_id:
        cities = City.objects.filter(state_id=state_id).order_by('name')
        cities_list = list(cities.values('id', 'name'))
    else:
        cities_list = []
    return JsonResponse(cities_list, safe=False)

@login_required
def edit_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    seller = request.user.seller

    field_order = [
        'project_name', 'project_description', 'categories', 'status', 'project_state', 
        'project_city', 'project_ntp_date', 'project_cod_date', 'project_pto_date',
        'contractor_name', 'project_size', 'battery_storage', 
        'projected_annual_income', 'epc_name', 'current_annual_om_cost', 
        'om_escalation_rate', 'sales_price', 'project_address', 'lot_size', 
        'property_type', 'lease_term', 'current_lease_rate_per_acre', 'lease_escalation_rate',
        'project_status', 'tax_credit_type', 'total_tax_credit_percentage', 'remarks',
        'buyer_protections', 'latitude', 'longitude', 'thumbnail_image'
    ]

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing, user=request.user)

        if form.is_valid():
            updated_listing = form.save(commit=False)
            updated_listing.seller = request.user.seller

            # Save the updated listing without modifying post counts or checking is_featured
            if not updated_listing.slug:
                updated_listing.slug = slugify(updated_listing.project_name)

            updated_listing.save()

            # Save the categories to the listing
            form.save_m2m()

            # Handle image deletions
            images_to_delete = request.POST.getlist('delete_images')
            for image_id in images_to_delete:
                image = ListingImage.objects.get(id=image_id)
                image.delete()

            # Handle new images
            images = request.FILES.getlist('images')
            for image in images:
                photo = ListingImage(listing=updated_listing, image=image)
                photo.save()

            '''send_mail(
                'Listing Updated',
                f'Your listing "{updated_listing.project_name}" has been updated successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )'''

            # Send email notification
            try:
                send_custom_email(
                    subject='Listing Updated',
                    template_name='emails/listing_updated_email.html',
                    context={'user': {
                                'first_name': seller.first_name,
                                },
                            'listing': updated_listing},
                    recipient_list=[request.user.email]
                )
            except:
                pass

            messages.success(request, 'Listing updated successfully')
            return redirect('listing_detail', updated_listing.slug)
        else:
            print("Form is not valid.")
            print(form.errors)
    else:
        form = ListingForm(instance=listing, user=request.user)
        existing_images = ListingImage.objects.filter(listing=listing)

    return render(request, 'edit_listing.html', {'form': form, 'field_order': field_order, 'existing_images': existing_images})


def listing_detail(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    listing.views += 1
    listing.save()

    seller = listing.seller
    form = MessageForm()
    login_form = LoginForm()
    register_form = SellerRegistrationForm()

    return render(request, 'listing_detail.html', {
        'listing': listing,
        'seller': seller,
        'form': form,
        'login_form': login_form,
        'register_form': register_form,
    })

@login_required
def seller_listings(request):
    listings = Listing.objects.filter(seller=request.user.seller)
    return render(request, 'seller_listings.html', {'listings': listings})


@login_required
def buy_package_listing(request):
    seller = request.user.seller
    packages = Package.objects.all()
    listing_price = ListingPrice.objects.first()

    if request.method == 'POST':
        try:
            stripe_token = request.POST.get('stripeToken', None)
            amount = float(request.POST.get('amount'))
            description = request.POST.get('description')
            package_id = request.POST.get('package_id', None)
            normal_listings = int(request.POST.get('normal_listings', 0))
            featured_listings = int(request.POST.get('featured_listings', 0))
        except (TypeError, ValueError, KeyError):
            messages.error(request, 'Invalid input. Please try again.')
            return redirect('buy_package_listing')

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('buy_package_listing')

        amount_in_cents = int(amount * 100)

        try:
            if stripe_token:
                customer = stripe.Customer.retrieve(seller.stripe_customer_id)
                payment_method = stripe.PaymentMethod.create(
                    type="card",
                    card={"token": stripe_token},
                )
                stripe.PaymentMethod.attach(payment_method.id, customer=customer.id)
                seller.stripe_payment_method_id = payment_method.id
                seller.save()

            payment_intent = stripe.PaymentIntent.create(
                customer=seller.stripe_customer_id,
                amount=amount_in_cents,
                currency='usd',
                payment_method=seller.stripe_payment_method_id,
                off_session=True,
                confirm=True,
                description=description,
            )
        except stripe.error.StripeError as e:
            print(f"Stripe Error: {e}")
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('buy_package_listing')

        if package_id:
            package = get_object_or_404(Package, id=package_id)
            if seller.package and seller.new_package:
                messages.error(request, 'You cannot purchase another package while you have an upcoming package.')
                return redirect('buy_package_listing')

            if seller.package:
                seller.new_package = package
                seller.membership_expiry = seller.membership_expiry  # Future package starts from the current package expiry date
            else:
                seller.package = package
                seller.normal_post_count = package.normal_post_limit
                seller.featured_post_count = package.featured_post_limit
                seller.membership_expiry = timezone.now() + timedelta(minutes=package.get_duration_in_minutes())
                seller.is_auto_renew = True

            seller.save()
            print(f"Package {package.name} assigned to seller {seller.user.username}")

            Transaction.objects.create(
                seller=seller,
                amount=amount,
                description=f'Purchase of package {package.name}',
                transaction_type='Package'
            )
            '''send_mail(
                'Package Purchased',
                f'You have successfully purchased the {package.name} package. It will be active from {seller.membership_expiry}.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )'''

            # Generate invoice PDF
            site_settings = get_site_settings()
            invoice_context = {
                'invoice_id': random.randint(12345, 99999),
                'invoice_date': timezone.now(),
                'package': package,
                'amount': amount,
                'user': request.user,
                'site_title': site_settings.site_title if site_settings else '',
                'site_logo_url': request.build_absolute_uri(site_settings.site_logo.url) if site_settings and site_settings.site_logo else '',
                'site_address': site_settings.site_description if site_settings else '',
            }
            invoice_pdf = generate_invoice_pdf(invoice_context)

            # Send email notification with invoice attachment
            try:
                send_custom_email(
                    subject='Package Purchased',
                    template_name='emails/package_purchase_email.html',
                    context={
                        'user': {
                                'first_name': seller.first_name,
                            },
                        'package': package,
                        'membership_expiry': seller.membership_expiry,
                        'auto_renew': 'Yes' if seller.is_auto_renew else 'No'
                    },
                    recipient_list=[request.user.email],
                    attachment=invoice_pdf
                )
            except:
                pass

        elif normal_listings > 0 or featured_listings > 0:
            if normal_listings > 0:
                seller.individual_normal_posts += normal_listings
            if featured_listings > 0:
                seller.individual_featured_posts += featured_listings
            seller.save()
            print(f"Listings updated for seller {seller.user.username}")

            Transaction.objects.create(
                seller=seller,
                amount=amount,
                description=f'Purchase of {description}',
                transaction_type='Individual Listing'
            )
            '''send_mail(
                'Listings Purchased',
                f'You have successfully purchased {description}.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )'''

            # Convert SimpleLazyObject to User
            # Convert SimpleLazyObject to User
            user = request.user
            if isinstance(user, SimpleLazyObject):
                user = user._wrapped

            # Print context to debug
            context = {
                'user': {
                    'first_name': seller.first_name,
                },
                'description': description
            }
            print(context)
    
            # Send email notification without attachment
            try:
                send_custom_email(
                    subject='Listings Purchased',
                    template_name='emails/listings_purchase_email.html',
                    context=context,
                    recipient_list=[request.user.email]
                )
            except:
                pass

        messages.success(request, 'Purchase successful')
        return redirect('dashboard')
    current_normal_posts_used = seller.package.normal_post_limit - seller.normal_post_count if seller.package else 0
    current_featured_posts_used = seller.package.featured_post_limit - seller.featured_post_count if seller.package else 0

    context = {
        'packages': packages,
        'listing_price': listing_price,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
        'current_normal_posts_used': current_normal_posts_used,
        'current_featured_posts_used': current_featured_posts_used,
    }
    return render(request, 'buy_package_listing.html', context)


@login_required
def cancel_auto_renew(request):
    seller = request.user.seller
    seller.cancel_auto_renew()
    messages.success(request, 'Auto-renewal for your current package has been canceled. It will remain active until the expiry date.')
    return redirect('dashboard')

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(seller=request.user.seller).select_related('seller')
    
    # Add pagination
    paginator = Paginator(transactions, 5)  # Show 5 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    for transaction in page_obj:
        transaction.auto_renew = transaction.seller.is_auto_renew
        transaction.payment_method_saved = bool(transaction.seller.stripe_payment_method_id)
    
    return render(request, 'transaction_history.html', {'page_obj': page_obj})

def submit_message(request):
    if request.method == 'POST':
        slug = request.POST.get('slug')
        if slug:
            listing = get_object_or_404(Listing, slug=slug)
            seller = listing.seller
        else:
            seller_id = request.POST.get('seller_id')
            seller = get_object_or_404(Seller, id=seller_id)
            listing = None
        
        form = MessageForm(request.POST)
        if form.is_valid():
            message = form.save(commit=False)
            message.listing = listing
            message.seller = seller
            message.save()

            # Send email notification
            try:
                send_custom_email(
                    subject='New Message Received',
                    template_name='emails/new_message_email.html',
                    context={'seller': seller.user, 'message': message},
                    recipient_list=[seller.user.email]
                )
            except:
                pass
            return JsonResponse({'success': True, 'message': 'Your message has been sent successfully!'})
        else:
            errors = form.errors.as_json()
            return JsonResponse({'success': False, 'errors': errors})
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    listings = Listing.objects.filter(category=category)
    return render(request, 'category_detail.html', {'category': category, 'listings': listings})


@login_required
def seller_messages(request):
    seller = get_object_or_404(Seller, user=request.user)
    message_list = Message.objects.filter(seller=seller).order_by('-sent_at')
    paginator = Paginator(message_list, 3)  # Show 4 messages per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj
    }
    return render(request, 'seller_messages.html', context)

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id, seller__user=request.user)
    listing_url = reverse('listing_detail', args=[message.listing.slug]) if message.listing else None
    context = {
        'message': message,
        'listing_url': listing_url
    }
    return render(request, 'message_detail.html', context)

# Search Feature
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def state_autocomplete(request):
    if 'term' in request.GET:
        qs = State.objects.filter(name__icontains=request.GET.get('term'))
        states = list(qs.values_list('name', flat=True))
        return JsonResponse(states, safe=False)
    else:
        states = list(State.objects.values_list('name', flat=True))
        return JsonResponse(states, safe=False)
    
def all_listings(request):
    listings = Listing.objects.all().order_by('-is_featured', '-created_at')
    states = State.objects.all()
    categories = Category.objects.all()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        location = request.GET.get('location')
        category_names = request.GET.getlist('categories[]')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort_by')

        print("Filters received: ")
        print(f"Location: {location}")
        print(f"Categories: {category_names}")
        print(f"Min Price: {min_price}")
        print(f"Max Price: {max_price}")
        print(f"Sort By: {sort_by}")

        filters = Q()

        if location:
            filters &= Q(project_state__name__icontains=location)
            print(f"Location filter applied: {location}")

        if min_price:
            filters &= Q(sales_price__gte=min_price)
            print(f"Min Price filter applied: {min_price}")

        if max_price:
            filters &= Q(sales_price__lte=max_price)
            print(f"Max Price filter applied: {max_price}")

        if category_names and category_names != ['']:
            category_ids = Category.objects.filter(name__in=category_names).values_list('id', flat=True)
            filters &= Q(categories__id__in=category_ids)
            print(f"Category filter applied: {category_names} -> {list(category_ids)}")
        else:
            print("No valid categories selected, skipping category filter")

        listings = listings.filter(filters).distinct()
        print(f"Filtered Listings Count: {listings.count()}")

        if sort_by:
            if sort_by == 'date_newest':
                listings = listings.order_by('-created_at')
            elif sort_by == 'date_oldest':
                listings = listings.order_by('created_at')
            elif sort_by == 'price_low_to_high':
                listings = listings.order_by('sales_price')
            elif sort_by == 'price_high_to_low':
                listings = listings.order_by('-sales_price')
            elif sort_by == 'update_time':
                listings = listings.order_by('-updated_at')

            print(f"Sort applied: {sort_by}")

        # Ensure featured listings come first
        listings = listings.order_by('-is_featured', *listings.query.order_by)
        print("Listings ordered with featured first.")

        html = render_to_string('partials/listings.html', {'listings': listings})
        listings_data = list(listings.values('latitude', 'longitude', 'id', 'project_name'))
        return JsonResponse({'html': html, 'listings': listings_data})

    listings_data = list(listings.values('latitude', 'longitude', 'id', 'project_name'))
    #Login form for normal user
    login_form = LoginForm()
    register_form = SellerRegistrationForm()

    context = {
        'login_form': login_form,
        'register_form': register_form,
        'listings': listings,
        'states': states,
        'categories': categories,
        'listings_data': json.dumps(listings_data, default=decimal_default),
    }
    return render(request, 'all_listings.html', context)


def seller_profile(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    listings = seller.listing_set.all()
    paginator = Paginator(listings, 3)  # 3 listings per page
    form = MessageForm()

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'seller_profile.html', {'seller': seller, 'listings': page_obj, 'form': form})