from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.utils import timezone
from django.urls import reverse
from .models import *
from .forms import SellerRegistrationForm, LoginForm, ListingForm, ContactForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.contrib.auth.views import PasswordResetView, PasswordResetDoneView
from django.contrib.auth.forms import PasswordResetForm, AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.urls import reverse_lazy
from django.contrib.auth import update_session_auth_hash
import stripe

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
    return render(request, 'home.html', {'login_form': login_form, 'register_form': register_form, 'categories': categories})

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def update_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user.seller)
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

    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            listing = form.save(commit=False)
            listing.seller = request.user.seller
            listing_type = form.cleaned_data.get('listing_type')

            if listing.is_featured:
                if listing_type == 'individual':
                    if seller.individual_featured_posts > 0:
                        seller.individual_featured_posts -= 1
                    else:
                        messages.error(request, 'You do not have enough individual featured posts available.')
                        return render(request, 'create_listing.html', {'form': form})
                else:
                    if seller.featured_post_count > 0:
                        seller.featured_post_count -= 1
                    else:
                        messages.error(request, 'You do not have enough featured posts available in your package.')
                        return render(request, 'create_listing.html', {'form': form})
            else:
                if listing_type == 'individual':
                    if seller.individual_normal_posts > 0:
                        seller.individual_normal_posts -= 1
                    else:
                        messages.error(request, 'You do not have enough individual normal posts available.')
                        return render(request, 'create_listing.html', {'form': form})
                else:
                    if seller.normal_post_count > 0:
                        seller.normal_post_count -= 1
                    else:
                        messages.error(request, 'You do not have enough normal posts available in your package.')
                        return render(request, 'create_listing.html', {'form': form})

            seller.save()
            listing.save()
            send_mail(
                'Listing Created',
                f'Your listing "{listing.title}" has been created successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )
            messages.success(request, 'Listing created successfully')
            return redirect('dashboard')
    else:
        form = ListingForm(user=request.user)
    return render(request, 'create_listing.html', {'form': form})

@login_required
def edit_listing(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    if request.method == 'POST':
        form = ListingForm(request.POST, request.FILES, instance=listing, user=request.user)
        if form.is_valid():
            form.save()
            send_mail(
                'Listing Updated',
                f'Your listing "{listing.title}" has been updated successfully.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )
            messages.success(request, 'Listing updated successfully')
            return redirect('listing_detail', listing.slug)
    else:
        form = ListingForm(instance=listing, user=request.user)
    return render(request, 'edit_listing.html', {'form': form})

def listing_detail(request, slug):
    listing = get_object_or_404(Listing, slug=slug)
    listing.views += 1
    listing.save()
    return render(request, 'listing_detail.html', {'listing': listing})

@login_required
def seller_listings(request):
    listings = Listing.objects.filter(seller=request.user.seller)
    return render(request, 'seller_listings.html', {'listings': listings})

def all_listings(request):
    listings = Listing.objects.all()
    return render(request, 'all_listings.html', {'listings': listings})

@login_required
def buy_package_listing(request):
    seller = request.user.seller
    packages = Package.objects.all()
    listing_price = ListingPrice.objects.first()

    if request.method == 'POST':
        try:
            stripe_token = request.POST['stripeToken']
            print(f"Stripe Token: {stripe_token}")
        except KeyError:
            messages.error(request, 'Payment token was not provided. Please try again.')
            return redirect('buy_package_listing')

        try:
            amount = float(request.POST.get('amount'))
            print(f"Amount: {amount}")
        except (TypeError, ValueError):
            messages.error(request, 'Invalid amount. Please enter a valid number.')
            return redirect('buy_package_listing')

        if amount <= 0:
            messages.error(request, 'Amount must be greater than zero.')
            return redirect('buy_package_listing')

        description = request.POST.get('description')
        package_id = request.POST.get('package_id', None)
        print(f"Description: {description}, Package ID: {package_id}")

        try:
            normal_listings = int(request.POST.get('normal_listings', 0))
            print(f"Normal Listings: {normal_listings}")
        except (TypeError, ValueError):
            messages.error(request, 'Invalid number of normal listings.')
            return redirect('buy_package_listing')

        try:
            featured_listings = int(request.POST.get('featured_listings', 0))
            print(f"Featured Listings: {featured_listings}")
        except (TypeError, ValueError):
            messages.error(request, 'Invalid number of featured listings.')
            return redirect('buy_package_listing')

        amount_in_cents = int(amount * 100)
        try:
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
            print("Payment processed successfully")
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
            send_mail(
                'Package Purchased',
                f'You have successfully purchased the {package.name} package. It will be active from {seller.membership_expiry}.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )
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
            send_mail(
                'Listings Purchased',
                f'You have successfully purchased {description}.',
                settings.DEFAULT_FROM_EMAIL,
                [request.user.email],
            )

        messages.success(request, 'Purchase successful')
        return redirect('dashboard')

    context = {
        'packages': packages,
        'listing_price': listing_price,
        'stripe_key': settings.STRIPE_PUBLISHABLE_KEY,
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
    transactions = Transaction.objects.filter(seller=request.user.seller)
    return render(request, 'transaction_history.html', {'transactions': transactions})

def contact_seller(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_name = form.cleaned_data['name']
            contact_email = form.cleaned_data['email']
            contact_message = form.cleaned_data['message']
            send_mail(
                subject=f'New contact for {listing.title}',
                message=f'Name: {contact_name}\nEmail: {contact_email}\n\nMessage:\n{contact_message}',
                from_email=contact_email,
                recipient_list=[listing.contact_email],
            )
            messages.success(request, 'Your message has been sent to the seller.')
            return redirect('listing_detail', listing.slug)
    else:
        form = ContactForm()
    return render(request, 'contact_seller.html', {'form': form, 'listing': listing})

def search(request):
    query = Listing.objects.all()
    
    location = request.GET.get('location')
    property_type = request.GET.get('property_type')
    price_min = request.GET.get('price_min')
    price_max = request.GET.get('price_max')

    if location:
        query = query.filter(location__icontains=location)
    
    if property_type:
        query = query.filter(property_type=property_type)
    
    if price_min:
        query = query.filter(price__gte=price_min)
    
    if price_max:
        query = query.filter(price__lte=price_max)

    return render(request, 'search_results.html', {'listings': query})

def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    listings = Listing.objects.filter(category=category)
    return render(request, 'category_detail.html', {'category': category, 'listings': listings})
