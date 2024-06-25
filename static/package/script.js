document.addEventListener('DOMContentLoaded', function() {
    var stripe = Stripe('{{ stripe_key }}');
    var elements = stripe.elements();
    var card = elements.create('card');
    card.mount('#unique-card-element');

    var paymentModal = document.getElementById('unique-payment-modal');
    var messageModal = document.getElementById('unique-message-modal');
    var closePaymentModal = document.getElementsByClassName('closex')[0];
    var closeMessageModal = document.getElementsByClassName('close-message')[0];
    var stripeButton = document.getElementById('unique-stripe-button');

    var form; // Declare a variable to hold the form element
    var packageId; // Declare a variable to hold the package ID

    function openModal(modal, title, description) {
        if (modal === 'unique-payment-modal') {
            document.getElementById('unique-modal-title').textContent = title;
            document.getElementById('unique-modal-description').textContent = description;
            paymentModal.style.display = 'block';
        } else {
            document.getElementById('unique-message-title').textContent = title;
            document.getElementById('unique-message-content').textContent = description;
            messageModal.style.display = 'block';
        }
    }

    function closeModal(modal) {
        if (modal === 'unique-payment-modal') {
            paymentModal.style.display = 'none';
        } else {
            messageModal.style.display = 'none';
        }
    }

    closePaymentModal.onclick = function() {
        closeModal('unique-payment-modal');
    }

    closeMessageModal.onclick = function() {
        closeModal('unique-message-modal');
    }

    window.onclick = function(event) {
        if (event.target == paymentModal) {
            closeModal('unique-payment-modal');
        }
        if (event.target == messageModal) {
            closeModal('unique-message-modal');
        }
    }

    function handlePayment(event, amount, description) {
        event.preventDefault();

        stripe.createToken(card).then(function(result) {
            if (result.error) {
                var errorElement = document.getElementById('unique-card-errors');
                errorElement.textContent = result.error.message;
            } else {
                if (!form) {
                    openModal('unique-message-modal', 'Error', 'Form not found.');
                    return;
                }
                var hiddenInput = document.createElement('input');
                hiddenInput.setAttribute('type', 'hidden');
                hiddenInput.setAttribute('name', 'stripeToken');
                hiddenInput.setAttribute('value', result.token.id);
                form.appendChild(hiddenInput);

                var amountInput = document.createElement('input');
                amountInput.setAttribute('type', 'hidden');
                amountInput.setAttribute('name', 'amount');
                amountInput.setAttribute('value', amount);
                form.appendChild(amountInput);

                var descriptionInput = document.createElement('input');
                descriptionInput.setAttribute('type', 'hidden');
                descriptionInput.setAttribute('name', 'description');
                descriptionInput.setAttribute('value', description);
                form.appendChild(descriptionInput);

                if (form.id === 'unique-package-form') {
                    var packageIdInput = document.createElement('input');
                    packageIdInput.setAttribute('type', 'hidden');
                    packageIdInput.setAttribute('name', 'package_id');
                    packageIdInput.setAttribute('value', packageId);
                    form.appendChild(packageIdInput);
                }

                form.submit();
            }
        });
    }

    document.querySelectorAll('.unique-package-button').forEach(button => {
        button.addEventListener('click', function(event) {
            packageId = event.target.getAttribute('data-package-id');
            var packagePrice = parseFloat(event.target.getAttribute('data-package-price'));
            if (isNaN(packagePrice) || packagePrice <= 0) {
                openModal('unique-message-modal', 'Error', 'Invalid package price.');
                return;
            }
            form = document.getElementById('unique-package-form'); // Set the form variable to the package form
            openModal('unique-payment-modal', 'Buy Package', 'You are about to purchase a package for $' + packagePrice);
            stripeButton.onclick = function(e) {
                handlePayment(e, packagePrice, 'Purchase Package ID: ' + packageId);
            };
        });
    });

    var normalPostsSlider = document.getElementById('unique-individual-normal-posts');
    var normalPostsCount = document.getElementById('unique-normal-listings-count');
    normalPostsSlider.addEventListener('input', function() {
        normalPostsCount.textContent = normalPostsSlider.value;
    });

    var featuredPostsSlider = document.getElementById('unique-individual-featured-posts');
    var featuredPostsCount = document.getElementById('unique-featured-listings-count');
    featuredPostsSlider.addEventListener('input', function() {
        featuredPostsCount.textContent = featuredPostsSlider.value;
    });

    document.getElementById('unique-buy-listings-button').addEventListener('click', function(event) {
        var normalListings = parseInt(normalPostsSlider.value, 10);
        var featuredListings = parseInt(featuredPostsSlider.value, 10);
        if (isNaN(normalListings) || isNaN(featuredListings) || normalListings < 0 || featuredListings < 0) {
            openModal('unique-message-modal', 'Error', 'Please enter a valid number of listings.');
            return;
        }
        var normalListingPrice = parseFloat(document.getElementById('unique-normal-listing-price').textContent);
        var featuredListingPrice = parseFloat(document.getElementById('unique-featured-listing-price').textContent);
        if (isNaN(normalListingPrice) || isNaN(featuredListingPrice)) {
            openModal('unique-message-modal', 'Error', 'Invalid listing price.');
            return;
        }
        var totalAmount = (normalListings * normalListingPrice) + (featuredListings * featuredListingPrice);
        if (totalAmount <= 0) {
            openModal('unique-message-modal', 'Error', 'Total amount must be greater than zero.');
            return;
        }
        form = document.getElementById('unique-individual-listing-form'); // Set the form variable to the individual listing form
        openModal('unique-payment-modal', 'Buy Individual Listings', 'You are about to purchase individual listings for $' + totalAmount.toFixed(2));
        stripeButton.onclick = function(e) {
            handlePayment(e, totalAmount, 'Purchase Individual Listings');
        };
    });
});