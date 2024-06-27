from django import forms
from django.contrib.auth.models import User
from .models import Listing, Seller, Package, City, State, ListingImage, Category, Message
from django.core.validators import RegexValidator
from localflavor.us.us_states import STATE_CHOICES
from django.forms import modelformset_factory
from tinymce.widgets import TinyMCE
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
    thumbnail_image = forms.ImageField(required=False)
    listing_type = forms.ChoiceField(choices=[('package', 'Package'), ('individual', 'Individual')], widget=forms.RadioSelect, required=False)
    project_state = forms.ModelChoiceField(queryset=State.objects.all(), required=False)
    project_city = forms.ModelChoiceField(queryset=City.objects.none(), required=False)
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.all(), required=True)
    project_description = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    lease_term = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    remarks = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    buyer_protections = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)

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

        if 'project_state' in self.data:
            try:
                state_id = int(self.data.get('project_state'))
                self.fields['project_city'].queryset = City.objects.filter(state_id=state_id).order_by('name')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.project_state:
            self.fields['project_city'].queryset = City.objects.filter(state=self.instance.project_state).order_by('name')

    def clean_sales_price(self):
        sales_price = self.cleaned_data.get('sales_price')
        if sales_price <= 0:
            raise forms.ValidationError("Sales price must be greater than zero.")
        return sales_price

    class Meta:
        model = Listing
        fields = [
            'categories', 'project_ntp_date', 'project_cod_date', 'project_pto_date',
            'is_featured', 'status', 'project_name', 'project_description', 'contractor_name',
            'project_size', 'battery_storage', 'projected_annual_income', 'epc_name', 'current_annual_om_cost',
            'om_escalation_rate', 'sales_price', 'project_address', 'project_state', 'project_city',
            'lot_size', 'property_type', 'lease_term', 'current_lease_rate_per_acre', 'lease_escalation_rate',
            'project_status', 'tax_credit_type', 'total_tax_credit_percentage', 'remarks', 'buyer_protections',
            'latitude', 'longitude', 'thumbnail_image', 'listing_type'
        ]
        labels = {
            'categories': 'Project Technology*',
            'project_ntp_date': 'Project NTP Date',
            'project_cod_date': 'Project COD Date',
            'project_pto_date': 'Project PTO Date',
            'is_featured': 'Featured',
            'status': 'Listing Status*',
            'project_name': 'Project Name*',
            'project_description': 'Project Description',
            'contractor_name': 'Contractor Name',
            'project_size': 'Project Size',
            'battery_storage': 'Battery Storage',
            'projected_annual_income': 'Projected Annual Income',
            'epc_name': 'EPC Name',
            'current_annual_om_cost': 'Current Annual O&M Cost',
            'om_escalation_rate': 'O&M Escalation Rate',
            'sales_price': 'Sales Price',
            'project_address': 'Project Address',
            'project_state': 'Project State',
            'project_city': 'Project City',
            'lot_size': 'Lot Size',
            'property_type': 'Property Type',
            'lease_term': 'Lease Term',
            'current_lease_rate_per_acre': 'Current Lease Rate per Acre',
            'lease_escalation_rate': 'Lease Escalation Rate',
            'project_status': 'Project Status',
            'tax_credit_type': 'Tax Credit Type',
            'total_tax_credit_percentage': 'Total Tax Credit Percentage',
            'remarks': 'Remarks',
            'buyer_protections': 'Buyer Protections',
            'latitude': 'Latitude',
            'longitude': 'Longitude',
            'thumbnail_image': 'Thumbnail Image',
            'listing_type': 'Listing Type',
        }
        widgets = {
            'project_ntp_date': forms.DateInput(attrs={'type': 'date'}),
            'project_cod_date': forms.DateInput(attrs={'type': 'date'}),
            'project_pto_date': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.Select(attrs={'placeholder': 'Status'}),
            'project_name': forms.TextInput(attrs={'placeholder': 'Project Name'}),
            'project_description': forms.Textarea(attrs={'placeholder': 'Project Description'}),
            'contractor_name': forms.TextInput(attrs={'placeholder': 'Contractor Name'}),
            'project_size': forms.NumberInput(attrs={'placeholder': 'Project Size'}),
            'battery_storage': forms.NumberInput(attrs={'placeholder': 'Battery Storage'}),
            'projected_annual_income': forms.NumberInput(attrs={'placeholder': 'Projected Annual Income'}),
            'epc_name': forms.TextInput(attrs={'placeholder': 'EPC Name'}),
            'current_annual_om_cost': forms.NumberInput(attrs={'placeholder': 'Current Annual O&M Cost'}),
            'om_escalation_rate': forms.NumberInput(attrs={'placeholder': 'O&M Escalation Rate'}),
            'sales_price': forms.NumberInput(attrs={'placeholder': 'Sales Price'}),
            'project_address': forms.TextInput(attrs={'placeholder': 'Project Address'}),
            'project_state': forms.Select(attrs={'placeholder': 'Project State'}),
            'project_city': forms.Select(attrs={'placeholder': 'Project City'}),
            'lot_size': forms.NumberInput(attrs={'placeholder': 'Lot Size'}),
            'property_type': forms.Select(attrs={'placeholder': 'Property Type'}),
            'lease_term': forms.TextInput(attrs={'placeholder': 'Lease Term'}),
            'current_lease_rate_per_acre': forms.NumberInput(attrs={'placeholder': 'Current Lease Rate per Acre'}),
            'lease_escalation_rate': forms.NumberInput(attrs={'placeholder': 'Lease Escalation Rate'}),
            'project_status': forms.Select(attrs={'placeholder': 'Project Status'}),
            'tax_credit_type': forms.Select(attrs={'placeholder': 'Tax Credit Type'}),
            'total_tax_credit_percentage': forms.NumberInput(attrs={'placeholder': 'Total Tax Credit Percentage'}),
            'remarks': forms.Textarea(attrs={'placeholder': 'Remarks'}),
            'buyer_protections': forms.Textarea(attrs={'placeholder': 'Buyer Protections'}),
            'latitude': forms.NumberInput(attrs={'placeholder': 'Latitude'}),
            'longitude': forms.NumberInput(attrs={'placeholder': 'Longitude'}),
            'thumbnail_image': forms.ClearableFileInput(attrs={'placeholder': 'Thumbnail Image'}),
            'listing_type': forms.RadioSelect(attrs={'placeholder': 'Listing Type'}),
        }

class ListingImageForm(forms.ModelForm):
    class Meta:
        model = ListingImage
        fields = ['image']

ListingImageFormSet = modelformset_factory(ListingImage, form=ListingImageForm, extra=10)

class UserProfileForm(forms.ModelForm):
    company_address = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Company Address'}))
    bio = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    about = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    profile_image = forms.ImageField(required=False)

    class Meta:
        model = Seller
        fields = ['company_name', 'company_address', 'company_phone_number', 'first_name', 'last_name', 'bio', 'about', 'profile_image']
        widgets = {
            'company_phone_number': forms.TextInput(attrs={'placeholder': 'Phone number in format +9999999999'})
        }

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['first_name', 'last_name', 'email', 'phone', 'company', 'message']
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone'}),
            'company': forms.TextInput(attrs={'placeholder': 'Company (optional)'}),
            'message': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }