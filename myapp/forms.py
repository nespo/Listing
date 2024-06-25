from django import forms
from django.contrib.auth.models import User
from .models import Listing, Seller, Package
from django.core.validators import RegexValidator
import re

class SellerRegistrationForm(forms.ModelForm):
    company_name = forms.CharField(max_length=255)
    company_address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Company Address'}))
    company_phone_number = forms.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{10}$',
            message="Phone number must be a valid US number in the format: '+9999999999'."
        )]
    )
    first_name = forms.CharField(max_length=255)
    last_name = forms.CharField(max_length=255)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ['username', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_company_name(self):
        company_name = self.cleaned_data.get('company_name')
        if Seller.objects.filter(company_name=company_name).exists():
            raise forms.ValidationError("This company name is already registered.")
        return company_name

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError("Password must be at least 8 characters long.")
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError("Password must contain at least one uppercase letter.")
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError("Password must contain at least one lowercase letter.")
        if not re.search(r'\d', password):
            raise forms.ValidationError("Password must contain at least one digit.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise forms.ValidationError("Password must contain at least one special character.")
        return password

class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())

class ListingForm(forms.ModelForm):
    image = forms.ImageField(required=False)
    thumbnail_image = forms.ImageField(required=False)
    listing_type = forms.ChoiceField(choices=[('package', 'Package'), ('individual', 'Individual')], widget=forms.RadioSelect, required=False)
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ListingForm, self).__init__(*args, **kwargs)
        
        if self.user:
            seller = self.user.seller
            listing_choices = []
            
            if seller.package and (seller.normal_post_count > 0 or seller.featured_post_count > 0):
                listing_choices.append(('package', 'Package'))
                
            if seller.individual_normal_posts > 0 or seller.individual_featured_posts > 0:
                listing_choices.append(('individual', 'Individual'))
            
            if len(listing_choices) == 1:
                self.fields['listing_type'].initial = listing_choices[0][0]
                self.fields['listing_type'].widget = forms.HiddenInput()
            else:
                self.fields['listing_type'].choices = listing_choices
                
            if seller.featured_post_count == 0 and seller.individual_featured_posts == 0:
                self.fields['is_featured'].disabled = True
    
    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price

    class Meta:
        model = Listing
        fields = [
            'category', 'title', 'description', 'project_ntp_date', 
            'project_cod_date', 'price', 'location', 'is_featured', 'status',
            'project_name', 'project_description', 'developer_name', 
            'contractor_name', 'project_size', 'completion_percentage',
            'contact_email', 'contact_phone', 'additional_info', 
            'latitude', 'longitude', 'image', 'thumbnail_image', 'listing_type'
        ]


class PackageChangeForm(forms.ModelForm):
    class Meta:
        model = Seller
        fields = ['new_package']

class IndividualListingForm(forms.Form):
    LISTING_TYPE_CHOICES = [
        ('normal', 'Normal Listing'),
        ('featured', 'Featured Listing')
    ]
    listing_type = forms.ChoiceField(choices=LISTING_TYPE_CHOICES)

class ContactForm(forms.Form):
    name = forms.CharField(max_length=255)
    email = forms.EmailField()
    message = forms.CharField(widget=forms.Textarea)

class UserProfileForm(forms.ModelForm):
    company_address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Company Address'}))

    class Meta:
        model = Seller
        fields = ['company_name', 'company_address', 'company_phone_number', 'first_name', 'last_name']
        widgets = {
            'company_phone_number': forms.TextInput(attrs={
                'placeholder': 'Phone number in format +9999999999'
            })
        }