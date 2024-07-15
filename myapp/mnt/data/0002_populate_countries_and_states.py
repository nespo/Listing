import json
from django.db import migrations
def load_countries_and_states(apps, schema_editor):
    Country = apps.get_model('myapp', 'Country')
    Region = apps.get_model('myapp', 'Region')
    
    # Load countries data
    with open('myapp/mnt/data/countries.json', 'r') as file:
        countries = json.load(file)
        for country in countries:
            Country.objects.create(name=country['name'], code=country['code'])
    
    # Load states data for the USA
    with open('myapp/mnt/data/states_hash.json', 'r') as file:
        states = json.load(file)
        usa = Country.objects.get(code='US')
        for state_code, state_name in states.items():
            Region.objects.create(name=state_name, code=state_code, country=usa)
    
    # Load provinces data for Canada
    with open('myapp/mnt/data/canadian-provinces.json', 'r') as file:
        provinces = json.load(file)
        canada = Country.objects.get(code='CA')
        for province_code, province_name in provinces.items():
            Region.objects.create(name=province_name, code=province_code, country=canada)
class Migration(migrations.Migration):
    dependencies = [
        ('myapp', '0001_initial'),  # Ensure this matches the initial migration file
    ]
    operations = [
        # Remove the AddField operations if the columns already exist
        # migrations.AddField(
        #     model_name='seller',
        #     name='city',
        #     field=models.CharField(max_length=255, null=True, blank=True),
        # ),
        # migrations.AddField(
        #     model_name='listing',
        #     name='project_city',
        #     field=models.CharField(max_length=255, null=True, blank=True),
        # ),
        migrations.RunPython(load_countries_and_states),
    ]
