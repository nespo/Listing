from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from django.forms import modelformset_factory
from tinymce.widgets import TinyMCE
import re
from .models import *

class LoginForm(forms.Form):
    username = forms.CharField(max_length=255)
    password = forms.CharField(widget=forms.PasswordInput())

class SellerRegistrationForm(forms.ModelForm):
    username = forms.CharField(max_length=255)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput())
    confirm_password = forms.CharField(widget=forms.PasswordInput())
    company_name = forms.CharField(max_length=255)
    country = forms.ModelChoiceField(queryset=Country.objects.all(), required=True)
    state = forms.ModelChoiceField(queryset=Region.objects.none(), required=False)
    city = forms.CharField(max_length=255, required=True)
    mobile_number = forms.CharField(max_length=20, required=False)
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

    class Meta:
        model = Seller
        fields = [
            'username', 'email', 'password', 'confirm_password', 'company_name', 'company_address',
            'country', 'state', 'city', 'company_phone_number', 'mobile_number',
            'first_name', 'last_name'
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                if country_id in [Country.objects.get(code='US').id, Country.objects.get(code='CA').id]:
                    self.fields['state'].required = True
                    self.fields['state'].queryset = Region.objects.filter(country_id=country_id).order_by('name')
                else:
                    self.fields['state'].required = False
                    self.fields['state'].queryset = Region.objects.none()
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.country:
            if self.instance.country.code in ['US', 'CA']:
                self.fields['state'].required = True
                self.fields['state'].queryset = Region.objects.filter(country=self.instance.country).order_by('name')
            else:
                self.fields['state'].required = False
                self.fields['state'].queryset = Region.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        country = cleaned_data.get("country")
        state = cleaned_data.get("state")

        if password != confirm_password:
            self.add_error('confirm_password', "Password and Confirm Password do not match")

        if country and country.code in ['US', 'CA'] and not state:
            self.add_error('state', "This field is required for US and Canada.")

        return cleaned_data
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_company_phone_number(self):
        phone_number = self.cleaned_data.get('company_phone_number')
        if Seller.objects.filter(company_phone_number=phone_number).exists():
            raise forms.ValidationError("This phone number is already in use.")
        return phone_number

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

class ListingForm(forms.ModelForm):
    thumbnail_image = forms.ImageField(required=False)
    project_country = forms.ModelChoiceField(queryset=Country.objects.all(), required=True)
    project_state = forms.ModelChoiceField(queryset=Region.objects.none(), required=False)
    project_city = forms.CharField(max_length=255, required=False)
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    project_description = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
    lease_term = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    remarks = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)
    buyer_protections = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}), required=False)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        is_creation = kwargs.pop('is_creation', False)
        super(ListingForm, self).__init__(*args, **kwargs)

        if self.user:
            seller = self.user.seller
            if seller.featured_post_count == 0:
                self.fields['is_featured'].disabled = True

        if 'project_country' in self.data:
            try:
                country_id = int(self.data.get('project_country'))
                if country_id in [Country.objects.get(code='US').id, Country.objects.get(code='CA').id]:
                    self.fields['project_state'].queryset = Region.objects.filter(country_id=country_id).order_by('name')
                else:
                    self.fields['project_state'].queryset = Region.objects.none()
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.project_country:
            if self.instance.project_country.code in ['US', 'CA']:
                self.fields['project_state'].queryset = Region.objects.filter(country=self.instance.project_country).order_by('name')
            else:
                self.fields['project_state'].queryset = Region.objects.none()

        if is_creation:
            self.fields['status'].required = False
            self.fields['status'].initial = 'inactive'
            self.fields['status'].widget = forms.HiddenInput()
        else:
            self.fields['status'].widget = forms.Select(choices=Listing.STATUS_CHOICES)

        form_name = self.__class__.__name__
        field_settings = FormFieldSetting.objects.filter(form_name=form_name).order_by('order')

        for setting in field_settings:
            if setting.field_name in self.fields:
                self.fields[setting.field_name].label = setting.label

        ordered_fields = [setting.field_name for setting in field_settings]

        if is_creation and seller.featured_post_count > 0:
            ordered_fields.insert(0, 'is_featured')
        elif not is_creation and self.instance.is_featured:
            ordered_fields.insert(0, 'is_featured')

        self.order_fields(ordered_fields)

    def clean_sales_price(self):
        sales_price = self.cleaned_data.get('sales_price')
        if sales_price <= 0:
            raise forms.ValidationError("Sales price must be greater than zero.")
        return sales_price

    class Meta:
        model = Listing
        fields = [
            'categories', 'project_ntp_date', 'project_cod_date', 'project_pto_date',
            'is_featured', 'project_name', 'project_description', 'contractor_name',
            'project_size', 'battery_storage', 'projected_annual_income', 'epc_name', 'current_annual_om_cost',
            'om_escalation_rate', 'sales_price', 'project_address', 'project_country', 'project_state', 'project_city',
            'lot_size', 'property_type', 'lease_term', 'current_lease_rate_per_acre', 'lease_escalation_rate',
            'project_status', 'tax_credit_type', 'total_tax_credit_percentage', 'remarks', 'buyer_protections',
            'latitude', 'longitude', 'thumbnail_image', 'status'
        ]
        labels = {
            'categories': 'Project Technology*',
            'project_ntp_date': 'Project NTP Date',
            'project_cod_date': 'Project COD Date',
            'project_pto_date': 'Project PTO Date',
            'is_featured': 'Featured',
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
            'project_country': 'Project Country',
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
        }
        widgets = {
            'project_ntp_date': forms.DateInput(attrs={'type': 'date'}),
            'project_cod_date': forms.DateInput(attrs={'type': 'date'}),
            'project_pto_date': forms.DateInput(attrs={'type': 'date'}),
            'status': forms.HiddenInput(),
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
            'project_country': forms.Select(attrs={'placeholder': 'Project Country'}),
            'project_state': forms.Select(attrs={'placeholder': 'Project State'}),
            'project_city': forms.TextInput(attrs={'placeholder': 'Project City'}),
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
        fields = [
            'company_name', 'company_address', 'company_phone_number', 'mobile_number', 
            'country', 'state', 'city', 'first_name', 'last_name', 'bio', 'about', 'profile_image'
        ]
        widgets = {
            'company_phone_number': forms.TextInput(attrs={'placeholder': 'Phone number in format +9999999999'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        country = None
        if 'country' in self.data:
            try:
                country_id = int(self.data.get('country'))
                country = Country.objects.get(id=country_id)
            except (ValueError, TypeError, Country.DoesNotExist):
                pass
        elif self.instance.pk:
            country = self.instance.country

        if country and country.code in ['US', 'CA']:
            self.fields['state'].required = True
            self.fields['state'].queryset = Region.objects.filter(country=country).order_by('name')
        else:
            self.fields['state'].required = False
            self.fields['state'].queryset = Region.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        country = cleaned_data.get("country")
        state = cleaned_data.get("state")

        if country and country.code in ['US', 'CA'] and not state:
            self.add_error('state', "This field is required for US and Canada.")
        elif country and country.code not in ['US', 'CA']:
            cleaned_data['state'] = None  # Clear state if not required

        return cleaned_data

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
            'message': TinyMCE(attrs={'cols': 10, 'rows': 5}),
        }

class ContactUsForm(forms.ModelForm):
    class Meta:
        model = ContactUs
        fields = ['name', 'email', 'phone_number', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Your name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Your email'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'Your phone number', 'id': 'id_phone_number'}),
            'message': forms.Textarea(attrs={'placeholder': 'Your message', 'rows': 4}),
        }

class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['question', 'answer']
        widgets = {
            'answer': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }

class PageForm(forms.ModelForm):
    class Meta:
        model = Page
        fields = ['title', 'content']
        widgets = {
            'content': TinyMCE(attrs={'cols': 80, 'rows': 30}),
        }

class PackageForm(forms.ModelForm):
    class Meta:
        model = Package
        fields = ['name', 'normal_post_limit', 'featured_post_limit', 'price', 'duration', 'duration_unit', 'description', 'inclusions']
