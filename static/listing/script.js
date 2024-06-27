document.addEventListener('DOMContentLoaded', function() {
    // Function to toggle lease fields
    function toggleLeaseFields() {
        var leaseFields = ['lease_term', 'current_lease_rate_per_acre', 'lease_escalation_rate'];
        var propertyType = document.getElementById('id_property_type').value;
        leaseFields.forEach(function (field) {
            var fieldElement = document.querySelector('.' + field);
            if (fieldElement) {
                if (propertyType === 'lease') {
                    fieldElement.style.display = 'block';
                } else {
                    fieldElement.style.display = 'none';
                }
            }
        });
    }

    // Attach change event listener to property type field
    document.getElementById('id_property_type').addEventListener('change', toggleLeaseFields);

    // Initial call to toggle fields based on the initial value
    toggleLeaseFields();

    // Fetch cities based on selected state
    document.getElementById('id_project_state').addEventListener('change', function () {
        var url = "{% url 'load_cities' %}";
        var stateId = this.value;
        fetch(url + '?state=' + stateId)
            .then(response => response.json())
            .then(data => {
                var citySelect = document.getElementById('id_project_city');
                citySelect.innerHTML = '<option value="">Select a city</option>';
                data.forEach(function (city) {
                    var option = document.createElement('option');
                    option.value = city.id;
                    option.textContent = city.name;
                    citySelect.appendChild(option);
                });
            })
            .catch(error => console.error('Error fetching cities:', error));
    });

    // Show or hide battery storage field based on selected categories
    document.getElementById('id_categories').addEventListener('change', function () {
        var batteryField = document.querySelector('.battery_storage');
        if (batteryField) {
            if (Array.from(this.selectedOptions).map(option => option.value).includes('BESS')) {
                batteryField.style.display = 'block';
            } else {
                batteryField.style.display = 'none';
            }
        }
    });

    // Initialize cities if a state is already selected
    var stateSelect = document.getElementById('id_project_state');
    var citySelect = document.getElementById('id_project_city');
    var selectedState = stateSelect.value;
    if (selectedState) {
        var url = "{% url 'load_cities' %}";
        fetch(url + '?state=' + selectedState)
            .then(response => response.json())
            .then(data => {
                citySelect.innerHTML = '<option value="">Select a city</option>';
                data.forEach(function (city) {
                    var option = document.createElement('option');
                    option.value = city.id;
                    option.textContent = city.name;
                    citySelect.appendChild(option);
                });

                var selectedCity = "{{ form.instance.project_city.id }}";
                if (selectedCity) {
                    citySelect.value = selectedCity;
                }
            })
            .catch(error => console.error('Error fetching initial cities:', error));
    }
});