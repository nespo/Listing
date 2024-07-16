from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.urls import reverse
from django.contrib import admin
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
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from django.core.paginator import Paginator
from .utils import send_custom_email, generate_invoice_pdf
from django.views.decorators.csrf import csrf_exempt
from django.utils.functional import SimpleLazyObject
from django.template import RequestContext
from django.views.generic import FormView
from django.contrib.auth.tokens import default_token_generator as account_activation_token
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_str, force_bytes
from django.contrib.sites.shortcuts import get_current_site
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.humanize.templatetags.humanize import intcomma
import json
import stripe
import traceback

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
    messages_count = Message.objects.filter(seller=seller, is_read=False).count()
    package_renew_date = seller.membership_expiry

    if not package_renew_date:
        package_status = "You have no active Membership"
        package_name = "You don't have Any Membership"
    else:
        package_status = package_renew_date
        if seller.package:
            package_name = seller.package.name
        else:
            package_name = "You don't Have Any package"

    listings = seller.listing_set.all()
    views_data = {
        'dates': [listing.created_at.strftime('%Y-%m-%d') for listing in listings],
        'views': [listing.views for listing in listings],
    }

    context = {
        'messages_count': messages_count,
        'package_status': package_status,
        'package_name': package_name,
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
        print("Received POST data:", request.POST)
        
        if form.is_valid():
            form.save()
            print("Form data saved")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Profile updated successfully.'})
            else:
                messages.success(request, 'Profile updated successfully')
                return redirect('update_profile')
        else:
            print("Form is not valid:", form.errors)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: form.errors[field][0] for field in form.errors}
                return JsonResponse({'success': False, 'errors': errors})
            else:
                messages.error(request, 'Please correct the errors below.')
    else:
        form = UserProfileForm(instance=request.user.seller)
        print("Initial form data:", form.initial)
    
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

'''def register_seller(request):
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
'''

def register_seller(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = SellerRegistrationForm(request.POST)
        if form.is_valid():
            current_site = get_current_site(request)
            mail_subject = 'Activate your account.'
            email = form.cleaned_data.get('email')
            user_data = {
                'username': form.cleaned_data.get('username'),
                'email': email,
                'password': form.cleaned_data.get('password'),
            }
            seller_data = {
                'company_name': form.cleaned_data.get('company_name'),
                'company_address': form.cleaned_data.get('company_address'),
                'company_phone_number': form.cleaned_data.get('company_phone_number'),
                'first_name': form.cleaned_data.get('first_name'),
                'last_name': form.cleaned_data.get('last_name'),
                'country': form.cleaned_data.get('country').id,
                'state': form.cleaned_data.get('state').id if form.cleaned_data.get('state') else None,
                'city': form.cleaned_data.get('city'),
                'mobile_number': form.cleaned_data.get('mobile_number'),
            }
            uid = urlsafe_base64_encode(force_bytes(email))
            token = account_activation_token.make_token(User(username=user_data['username']))

            # Store user_data and seller_data in the session
            request.session['user_data'] = user_data
            request.session['seller_data'] = seller_data

            message = render_to_string('emails/acc_active_email.html', {
                'domain': current_site.domain,
                'uid': uid,
                'token': token,
                'first_name': seller_data['first_name'],
            })

            try:
                send_mail(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [email])
            except Exception as e:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Error sending email. Please try again later.'})
                else:
                    messages.error(request, 'Error sending email. Please try again later.')
                    return redirect('home')

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'success': True, 'message': 'Please confirm your email address to complete the registration.'})
            else:
                messages.success(request, 'Please confirm your email address to complete the registration.')
                return redirect('home')
        else:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                errors = {field: error[0] for field, error in form.errors.items()}
                return JsonResponse({'success': False, 'errors': errors})
            else:
                return render(request, 'register_seller.html', {'form': form})
    else:
        form = SellerRegistrationForm()
    return render(request, 'register_seller.html', {'form': form})

def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        email = uid
        user_data = request.session.get('user_data')
        seller_data = request.session.get('seller_data')

        if user_data and seller_data and user_data['email'] == email:
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                is_active=True  # Activate user upon creation
            )

            # Check if state is present
            state = Region.objects.get(id=seller_data['state']) if seller_data['state'] else None

            seller = Seller.objects.create(
                user=user,
                company_name=seller_data['company_name'],
                company_address=seller_data['company_address'],
                company_phone_number=seller_data['company_phone_number'],
                first_name=seller_data['first_name'],
                last_name=seller_data['last_name'],
                country=Country.objects.get(id=seller_data['country']),
                state=state,
                city=seller_data['city'],
                mobile_number=seller_data['mobile_number'],
                is_approved=False
            )
            # Create Stripe customer
            stripe_customer = stripe.Customer.create(email=user.email)
            seller.stripe_customer_id = stripe_customer.id
            seller.save()

            try:
                # Get admin user emails
                admin_emails = User.objects.filter(is_superuser=True).values_list('email', flat=True)
                # Send email to admin about new user registration
                send_mail(
                    'New Seller Registration',
                    f'A new seller has registered:\n\n'
                    f'Username: {user.username}\n'
                    f'Email: {user.email}\n'
                    f'Company Name: {seller.company_name}',
                    settings.DEFAULT_FROM_EMAIL,
                    admin_emails,
                )
            except:
                pass

            messages.success(request, 'Thank you for confirming your email address. Your account will be reviewed by our admin team. You will receive an email once your account is approved, after which you will be able to log in.')
            del request.session['user_data']
            del request.session['seller_data']
            return redirect('home')
        else:
            messages.warning(request, 'Activation link is invalid!')
            return redirect('home')
    except (TypeError, ValueError, OverflowError, User.DoesNotExist) as e:
        messages.warning(request, 'Activation link is invalid!')
        return redirect('home')
    
@csrf_exempt
def validate_step(request):
    if request.method == 'POST':
        step = int(request.POST.get('step', 0))
        print(f"Received POST data: {request.POST}")
        form = SellerRegistrationForm(request.POST)

        # Define the fields required for each step
        step_fields = [
            ['username', 'email'],
            ['email', 'mobile_number', 'first_name', 'last_name', 'password', 'confirm_password'],
            ['company_name', 'company_address', 'company_phone_number'],
            ['country', 'state', 'city']
        ]

        fields = step_fields[step] if step < len(step_fields) else []

        # Remove fields not related to the current step
        fields_to_remove = [field for field in form.fields if field not in fields]
        for field in fields_to_remove:
            form.fields.pop(field)
            
        # Validate form
        if form.is_valid():
            print("Form is valid.")
            return JsonResponse({'success': True})
        else:
            errors = {field: error[0] for field, error in form.errors.items()}
            print(f"Form errors: {errors}")
            return JsonResponse({'success': False, 'errors': errors})

    print("Invalid request.")
    return JsonResponse({'success': False, 'error': 'Invalid request'})

def load_countries(request):
    countries = Country.objects.all().order_by('name')
    return JsonResponse(list(countries.values('id', 'name')), safe=False)

def load_states(request, country_id):
    print(country_id)
    states = Region.objects.filter(country_id=country_id).order_by('name')
    return JsonResponse(list(states.values('id', 'name')), safe=False)

def get_country_code(request, country_id):
    country = Country.objects.get(id=country_id)
    return JsonResponse({'country_code': country.code2})  # Using the correct field name

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
def listing_load_states(request):
    country_id = request.GET.get('country_id')
    states = Region.objects.filter(country_id=country_id).order_by('name')
    return JsonResponse(list(states.values('id', 'name')), safe=False)


@login_required
def create_listing(request):
    seller = request.user.seller

    # Check if the seller has no package and no individual listings left
    if not seller.package and not (seller.normal_post_count > 0 or seller.featured_post_count > 0):
        messages.error(request, 'You must buy packages or listings to post a listing.')
        return redirect('buy_package_listing')

    # Check if the seller has used all their allowed listings
    if seller.normal_post_used >= seller.normal_post_count and seller.featured_post_used >= seller.featured_post_count:
        messages.error(request, 'You have used all your allowed listings. Please buy more packages or individual listings.')
        return redirect('buy_package_listing')

    form_name = 'ListingForm'
    field_settings = FormFieldSetting.objects.filter(form_name=form_name).order_by('order')
    field_order = [setting.field_name for setting in field_settings]

    if seller.featured_post_count > 0:
        field_order.insert(0, 'is_featured')

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, user=request.user, is_creation=True)
        
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user.seller
            listing.status = 'active'
            listing.expires_on = seller.membership_expiry

            if listing.is_featured:
                if seller.featured_post_count > 0:
                    seller.featured_post_count -= 1
                    seller.featured_post_used += 1
                else:
                    return JsonResponse({'errors': {'__all__': ['You do not have enough featured posts available.']}}, status=400)
            else:
                if seller.normal_post_count > 0:
                    seller.normal_post_count -= 1
                    seller.normal_post_used += 1
                else:
                    return JsonResponse({'errors': {'__all__': ['You do not have enough normal posts available.']}}, status=400)

            if not listing.slug:
                listing.slug = slugify(listing.project_name)
                original_slug = listing.slug
                counter = 1
                while Listing.objects.filter(slug=listing.slug).exists():
                    listing.slug = f"{original_slug}-{counter}"
                    counter += 1
            
            listing.save()
            form.save_m2m()

            images = request.FILES.getlist('images')
            for image in images:
                photo = ListingImage(listing=listing, image=image)
                photo.save()

            seller.save()

            try:
                send_custom_email(
                    subject='Your listing has been successfully created.',
                    template_name='emails/listing_created_email.html',
                    context={'user': {'first_name': seller.first_name}, 'listing': listing},
                    recipient_list=[request.user.email]
                )
            except:
                pass
            messages.success(request, 'Listing created successfully')
            return JsonResponse({'success': True, 'redirect_url': redirect('seller_listings').url})
        else:
            form_html = render_to_string('create_listing_form.html', {'form': form, 'field_order': field_order})
            return JsonResponse({'errors': form.errors, 'form_html': form_html}, status=400)
    else:
        form = ListingForm(user=request.user, is_creation=True)

    return render(request, 'create_listing.html', {'form': form, 'field_order': field_order})

@login_required
def edit_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    seller = request.user.seller
    original_status = listing.status

    if seller.membership_expiry <= timezone.now():
        messages.error(request, 'Your package has expired. Please renew your package to edit listings.')
        return redirect(reverse('dashboard'))

    form_name = 'ListingForm'
    field_settings = FormFieldSetting.objects.filter(form_name=form_name).order_by('order')
    field_order = [setting.field_name for setting in field_settings]

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing, user=request.user)
        existing_images = ListingImage.objects.filter(listing=listing)

        if form.is_valid():
            updated_listing = form.save(commit=False)
            updated_listing.seller = seller
            new_status = request.POST.getlist('status')[0]

            if original_status == 'inactive' and new_status in ['contingent', 'pending']:
                message = "You can't change the status from inactive to any other thing except Active"
                messages.success(request, "You can't change the status from inactive to any other thing except Active")
                return JsonResponse({'success': False, 'message': message, 'message_type': 'error'})

            try:
                with transaction.atomic():
                    updated_listing.previous_status = original_status
                    
                    if seller.membership_expiry > timezone.now():
                        updated_listing.expires_on = seller.membership_expiry

                    if updated_listing.expires_on and updated_listing.expires_on <= timezone.now():
                        updated_listing.status = 'inactive'
                    elif new_status == 'sold':
                        updated_listing.status = 'inactive'
                    else:
                        if new_status == 'active':
                            if original_status != 'active':
                                if updated_listing.is_featured:
                                    if seller.featured_post_count > 0:
                                        seller.featured_post_count -= 1
                                        seller.featured_post_used += 1
                                        seller.save()
                                    else:
                                        updated_listing.status = 'inactive'
                                        send_mail(
                                        'Your Listing has been Deactivated',
                                        f'Hello {seller.user.first_name},\n\n'
                                        f'Your listing {listing.name} has been Deactivated. You current status of the listing: Inactive.\n\n'
                                        'Thank you!\n\n'
                                        'Green Energy Connection Team',
                                        settings.DEFAULT_FROM_EMAIL,
                                        [seller.user.email],
                                        )
                                else:
                                    if seller.normal_post_count > 0:
                                        seller.normal_post_count -= 1
                                        seller.normal_post_used += 1
                                        seller.save()
                                    else:
                                        updated_listing.status = 'inactive'
                                        send_mail(
                                        'Your Listing has been Deactivated',
                                        f'Hello {seller.user.first_name},\n\n'
                                        f'Your listing {listing.name} has been Deactivated. You don\'t have enough Listing.\n\n'
                                        'Thank you!\n\n'
                                        'Green Energy Connection Team',
                                        settings.DEFAULT_FROM_EMAIL,
                                        [seller.user.email],
                                        )

                        else:
                            updated_listing.status = new_status

                    updated_listing.save()
                    form.save_m2m()

                    images_to_delete = request.POST.getlist('delete_images')
                    for image_id in images_to_delete:
                        image = ListingImage.objects.get(id=image_id)
                        image.delete()

                    images = request.FILES.getlist('images')
                    for image in images:
                        photo = ListingImage(listing=updated_listing, image=image)
                        photo.save()

                    try:
                        send_custom_email(
                            subject='Your Listing has been Updated',
                            template_name='emails/listing_updated_email.html',
                            context={'user': {'first_name': seller.first_name},
                                     'listing': updated_listing},
                            recipient_list=[request.user.email]
                        )
                    except:
                        pass

                messages.success(request, 'Listing updated successfully')
                return JsonResponse({'success': True, 'message': 'Listing updated successfully', 'message_type': 'success'})
            except Exception as e:
                error_details = traceback.format_exc()
                print("Error occurred:", error_details)  # This will print the error details to the console
                return JsonResponse({'errors': {'__all__': ['An error occurred while updating the listing. Please try again.']}, 'message': 'An error occurred while updating the listing. Please try again.', 'message_type': 'error'}, status=500)

        else:
            form_html = render_to_string('edit_listing_form.html', {'form': form, 'field_order': field_order, 'existing_images': existing_images}, request=request)
            return JsonResponse({'errors': form.errors, 'form_html': form_html}, status=400)

    else:
        form = ListingForm(instance=listing, user=request.user)
        existing_images = ListingImage.objects.filter(listing=listing)

    context = {'form': form, 'field_order': field_order, 'existing_images': existing_images}
    return render(request, 'edit_listing.html', context)

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
    listings = Listing.objects.filter(seller=request.user.seller).order_by('-id')  # Ensure queryset is ordered
    paginator = Paginator(listings, 4)  # Show 4 listings per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    has_listings = listings.exists()
    return render(request, 'seller_listings.html', {'page_obj': page_obj, 'has_listings': has_listings})


@login_required
def buy_package_listing(request):
    seller = request.user.seller
    packages = Package.objects.all()
    listing_price = ListingPrice.objects.first()

    if request.method == 'POST':
        try:
            stripe_token = request.POST.get('stripeToken', None)
            amount = Decimal(request.POST.get('amount'))
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

            if package_id:
                package = get_object_or_404(Package, id=package_id)
                if seller.package and seller.new_package:
                    messages.error(request, 'You cannot purchase another package while you have an upcoming package.')
                    return redirect('buy_package_listing')

                if seller.package:
                    current_package = seller.package
                    current_package_price = current_package.price
                    current_package_duration = current_package.get_duration_in_days()
                    current_package_per_day_cost = current_package_price / Decimal(current_package_duration)

                    # Calculate days left until package expiry
                    current_time = timezone.now()
                    expiry_time = seller.membership_expiry
                    days_left = (expiry_time - current_time).days

                    # Ensure days_left is a positive integer or zero
                    days_left = max(days_left, 0)

                    # Calculate the new chargeable amount based on remaining days
                    adjusted_amount = amount - (current_package_per_day_cost * Decimal(days_left))
                    print(f"Adjusted amount: {adjusted_amount}")
                    amount_in_cents = int(adjusted_amount * 100)

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

        transaction = None
        if package_id:
            package = get_object_or_404(Package, id=package_id)
            if seller.package:
                seller.new_package = package
                seller.save()
                seller.apply_new_package()
            else:
                seller.package = package
                seller.normal_post_count = package.normal_post_limit
                seller.featured_post_count = package.featured_post_limit
                seller.membership_expiry = timezone.now() + timedelta(minutes=package.get_duration_in_minutes())
                seller.is_auto_renew = True
                seller.save()

            transaction = Transaction.objects.create(
                seller=seller,
                amount=amount,
                description=f'{package.name}',
                transaction_type='Membership',
                transaction_id=payment_intent.id
            )

            try:
                site_settings = get_site_settings()
                invoice_pdf = generate_invoice_pdf({
                    'invoice_id': transaction.transaction_id,
                    'invoice_date': timezone.now(),
                    'package': package,
                    'amount': amount,
                    'user': request.user,
                    'first_name': seller.first_name,
                    'last_name': seller.last_name,
                    'address': seller.company_address,
                    'site_title': 'Green Energy Connection',
                    'site_logo_url': request.build_absolute_uri(site_settings.site_logo.url) if site_settings and site_settings.site_logo else '',
                    'site_phone': '+1 214 699 7895',
                    'site_email': 'info@greenenergyconnection.com',
                })
                send_custom_email(
                    subject='Membership Purchase Confirmation',
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
                    attachment={
                        'filename': invoice_pdf['filename'],
                        'content': invoice_pdf['content'],
                        'mimetype': invoice_pdf['mimetype']
                    }
                )
            except Exception as e:
                print(f"Email sending error: {e}")

        elif normal_listings > 0 or featured_listings > 0:
            if normal_listings > 0:
                seller.normal_post_count += normal_listings
            if featured_listings > 0:
                seller.featured_post_count += featured_listings
            seller.save()

            transaction = Transaction.objects.create(
                seller=seller,
                amount=amount,
                description=f'{description}',
                transaction_type='Individual Listing',
                transaction_id=payment_intent.id
            )

            user = request.user
            if isinstance(user, SimpleLazyObject):
                user = user._wrapped

            context = {
                'user': {
                    'first_name': seller.first_name,
                },
                'description': description
            }

            try:
                send_custom_email(
                    subject='Listings Purchased',
                    template_name='emails/listings_purchase_email.html',
                    context=context,
                    recipient_list=[request.user.email]
                )
            except Exception as e:
                print(f"Email sending error: {e}")

        messages.success(request, 'Purchase successful')
        return redirect('dashboard')

    total_normal_posts = seller.normal_post_count + seller.normal_post_used
    total_featured_posts = seller.featured_post_count + seller.featured_post_used
    normal_posts_used = seller.normal_post_used
    featured_posts_used = seller.featured_post_used

    all_listings_used = normal_posts_used >= total_normal_posts and featured_posts_used >= total_featured_posts

    context = {
        'packages': packages,
        'listing_price': listing_price,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
        'total_normal_posts': total_normal_posts,
        'total_featured_posts': total_featured_posts,
        'normal_posts_used': normal_posts_used,
        'featured_posts_used': featured_posts_used,
        'show_package_container': seller.package or seller.new_package,
        'show_available_packages': True,#not seller.is_auto_renew and (not seller.package or not seller.new_package),
        'show_individual_listings': False,
        'all_listings_used': all_listings_used
    }
    return render(request, 'buy_package_listing.html', context)



def get_site_settings():
    try:
        return SiteSettings.objects.first()
    except SiteSettings.DoesNotExist:
        return None
    
@method_decorator(login_required, name='dispatch')
class AddPaymentMethodView(View):
    template_name = 'add_payment_method.html'

    def get(self, request, *args, **kwargs):
        seller = request.user.seller
        existing_payment_method = None
        
        if seller.stripe_payment_method_id:
            existing_payment_method = stripe.PaymentMethod.retrieve(seller.stripe_payment_method_id)
        
        intent = stripe.SetupIntent.create(
            customer=seller.stripe_customer_id
        )
        return render(request, self.template_name, {
            'client_secret': intent.client_secret, 
            'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
            'existing_payment_method': existing_payment_method
        })

    def post(self, request, *args, **kwargs):
        seller = request.user.seller
        if 'remove_payment_method' in request.POST:
            try:
                # Detach the payment method
                stripe.PaymentMethod.detach(seller.stripe_payment_method_id)
                
                # Update seller model
                seller.stripe_payment_method_id = None
                seller.is_auto_renew = False
                seller.save()

                messages.success(request, 'Your payment method has been removed successfully.')
                return redirect('add_payment_method')
            except stripe.error.StripeError as e:
                messages.error(request, f"Error removing payment method: {str(e)}")
                return redirect('add_payment_method')
        
        payment_method_id = request.POST.get('payment_method_id')
        try:
            # Attach the payment method to the customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=seller.stripe_customer_id,
            )
            
            # Set the payment method as the default payment method
            stripe.Customer.modify(
                seller.stripe_customer_id,
                invoice_settings={
                    'default_payment_method': payment_method_id,
                },
            )

            # Update the seller with the new payment method
            seller.stripe_payment_method_id = payment_method_id
            seller.save()

            messages.success(request, 'Your payment method has been added successfully.')
            return redirect('add_payment_method')

        except stripe.error.StripeError as e:
            messages.error(request, f"Error adding payment method: {str(e)}")
            return redirect('add_payment_method')

def public_packages(request):
    packages = Package.objects.all()
    listing_price = ListingPrice.objects.first()
    login_form = LoginForm()
    register_form = SellerRegistrationForm()
    faqs = FAQ.objects.all()
    
    context = {
        'packages': packages,
        'listing_price': listing_price,
        'login_form': login_form,
        'register_form': register_form,
        'faqs' : faqs,
    }
    return render(request, 'public_packages.html', context)

@login_required
def cancel_auto_renew(request):
    seller = request.user.seller
    seller.cancel_auto_renew()
    messages.success(request, 'Auto-renewal for your current package has been canceled. It will remain active until the expiry date.')
    return redirect('dashboard')

@login_required
def transaction_history(request):
    transactions = Transaction.objects.filter(seller=request.user.seller).select_related('seller').order_by('-id')
    
    paginator = Paginator(transactions, 5)  # Show 5 transactions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    for transaction in page_obj:
        if transaction.transaction_type == 'Package':
            transaction.auto_renew_display = 'Yes' if transaction.seller.is_auto_renew else 'No'
        else:
            transaction.auto_renew_display = 'No'
    
    has_transactions = transactions.exists()
    
    return render(request, 'transaction_history.html', {'page_obj': page_obj, 'has_transactions': has_transactions})

def submit_message(request, slug=None):
    if request.method == 'POST':
        seller_id = request.POST.get('seller_id')
        slug = request.POST.get('slug')
        print(f"Seller ID: {seller_id}, Slug: {slug}")

        if slug:
            listing = get_object_or_404(Listing, slug=slug)
            seller = listing.seller
        else:
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
            except Exception as e:
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
    paginator = Paginator(message_list, 3)  # Show 3 messages per page

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unread_messages_count = message_list.filter(is_read=False).count()

    context = {
        'page_obj': page_obj,
        'unread_messages_count': unread_messages_count
    }
    return render(request, 'seller_messages.html', context)

@login_required
def message_detail(request, message_id):
    message = get_object_or_404(Message, id=message_id, seller__user=request.user)
    
    if not message.is_read:
        message.is_read = True
        message.save()

    unread_messages_count = Message.objects.filter(seller__user=request.user, is_read=False).count()

    listing_url = reverse('listing_detail', args=[message.listing.slug]) if message.listing else None
    context = {
        'message': message,
        'listing_url': listing_url,
        'unread_messages_count': unread_messages_count
    }
    return render(request, 'message_detail.html', context)

# Search Feature
def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError

def country_autocomplete(request):
    if 'term' in request.GET:
        qs = Country.objects.filter(name__icontains=request.GET.get('term'))
        countries = list(qs.values_list('name', flat=True))
        return JsonResponse(countries, safe=False)
    else:
        countries = list(Country.objects.values_list('name', flat=True))
        return JsonResponse(countries, safe=False)


def state_autocomplete(request):
    if 'term' in request.GET:
        qs = Region.objects.filter(name__icontains=request.GET.get('term'))
        states = list(qs.values_list('name', flat=True))
        return JsonResponse(states, safe=False)
    else:
        states = list(Region.objects.values_list('name', flat=True))
        return JsonResponse(states, safe=False)


# Custom JSON Encoder to handle Decimal serialization
class DecimalEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)
    
def all_listings(request):
    listings = Listing.objects.all().order_by('-is_featured', '-created_at')
    states = Region.objects.all()
    countries = Country.objects.all()
    categories = Category.objects.all()
    login_form = LoginForm()
    register_form = SellerRegistrationForm()
    

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        country = request.GET.get('country')
        category_names = request.GET.getlist('categories[]')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        sort_by = request.GET.get('sort_by')

        filters = Q()

        if country:
            filters &= Q(project_country__name__icontains=country)

        if min_price:
            filters &= Q(sales_price__gte=min_price)

        if max_price:
            filters &= Q(sales_price__lte=max_price)

        if category_names and category_names != ['']:
            category_ids = Category.objects.filter(name__in=category_names).values_list('id', flat=True)
            filters &= Q(categories__id__in=category_ids)

        listings = listings.filter(filters).distinct()

        # Apply user-defined sorting while keeping featured posts first
        if sort_by:
            if sort_by == 'date_newest':
                listings = listings.order_by('-is_featured', '-created_at')
            elif sort_by == 'date_oldest':
                listings = listings.order_by('-is_featured', 'created_at')
            elif sort_by == 'price_low_to_high':
                listings = listings.order_by('-is_featured', 'sales_price')
            elif sort_by == 'price_high_to_low':
                listings = listings.order_by('-is_featured', '-sales_price')
            elif sort_by == 'update_time':
                listings = listings.order_by('-is_featured', '-updated_at')
        else:
            listings = listings.order_by('-is_featured', '-created_at')

        html = render_to_string('partials/listings.html', {'listings': listings, 'login_form': login_form, 'register_form': register_form,})
        listings_data = json.dumps([{
            'id': listing.id,
            'project_name': listing.project_name,
            'latitude': listing.latitude,
            'longitude': listing.longitude,
            'project_city' : listing.project_city,
        } for listing in listings], cls=DecimalEncoder)

        return JsonResponse({
            'html': html,
            'listings': listings_data,
            'total_results': listings.count()
        })

    return render(request, 'all_listings.html', {
        'listings': listings,
        'states': states,
        'categories': categories,
        'countries': countries,
        'login_form': login_form,
        'register_form': register_form,
        'listings_data': json.dumps([{
            'id': listing.id,
            'project_name': listing.project_name,
            'latitude': listing.latitude,
            'longitude': listing.longitude,
            'project_city' : listing.project_city,
        } for listing in listings], cls=DecimalEncoder)
    })


def seller_profile(request, seller_id):
    seller = get_object_or_404(Seller, id=seller_id)
    listings = seller.listing_set.all()
    paginator = Paginator(listings, 3)  # 3 listings per page
    form = MessageForm()

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'seller_profile.html', {'seller': seller, 'listings': page_obj, 'form': form})


class ContactUsView(FormView):
    template_name = 'contact_us.html'
    form_class = ContactUsForm
    success_url = reverse_lazy('contact_us')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['login_form'] = LoginForm()
        context['register_form'] = SellerRegistrationForm()
        return context

    def form_valid(self, form):
        form.save()
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'message': 'Success'})
        return super().form_valid(form)

def faq_list(request):
    faqs = FAQ.objects.all()
    login_form = LoginForm()
    register_form = SellerRegistrationForm()
    return render(request, 'faq_list.html', {'faqs': faqs, 'login_form': login_form, 'register_form': register_form,})

def page_detail(request, slug):
    page = Page.objects.get(slug=slug)
    login_form = LoginForm()
    register_form = SellerRegistrationForm()
    return render(request, 'page_detail.html', {'page': page,'login_form': login_form, 'register_form': register_form,})

#Custom admin code
@staff_member_required
def form_field_setting_changelist(request):
    # Get fields from ListingForm
    form_fields = ListingForm().fields

    # Create or update FormFieldSetting entries based on ListingForm fields
    for field_name, field in form_fields.items():
        FormFieldSetting.objects.get_or_create(
            form_name='ListingForm',
            field_name=field_name,
            defaults={'label': field.label, 'order': 0}  # Defaults, can be updated later
        )

    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('label_'):
                _, form_name, field_name = key.split('_')
                label = value
                order = request.POST.get(f'order_{form_name}_{field_name}', 0)
                setting, created = FormFieldSetting.objects.get_or_create(form_name=form_name, field_name=field_name)
                setting.label = label
                setting.order = int(order)
                setting.save()
        return redirect(request.path)

    settings = FormFieldSetting.objects.filter(form_name='ListingForm').order_by('order')
    context = {
        'settings': settings,
    }
    return render(request, 'admin/formfieldsetting_changelist.html', context)