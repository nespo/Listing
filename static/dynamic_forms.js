document.addEventListener("DOMContentLoaded", function () {
    const signupForm = document.getElementById("signup-form");
    const steps = document.querySelectorAll(".step-content");
    const stepIndicators = document.querySelectorAll("#step-indicator .step");
    const nextButtons = document.querySelectorAll(".next-step");
    const prevButtons = document.querySelectorAll(".prev-step");

    let currentStep = 0;

    function showStep(step) {
        steps.forEach((stepContent, index) => {
            stepContent.classList.toggle("active", index === step);
            stepIndicators[index].classList.toggle("active", index <= step);
        });
    }

    function validateStep(step, callback) {
        const inputs = steps[step].querySelectorAll("input, select");
        const formData = new FormData(signupForm);
        formData.append('step', step);

        fetch("{% url 'validate_step' %}", {
            method: "POST",
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            let valid = true;
            if (data.errors) {
                valid = false;
                displayErrors(data.errors);
            }
            callback(valid);
        })
        .catch(error => {
            console.error('An error occurred:', error);
            callback(false);
        });
    }

    function displayErrors(errors) {
        document.querySelectorAll('.error').forEach(el => el.textContent = '');
        for (let field in errors) {
            const errorElement = document.getElementById(`error-${field}`);
            if (errorElement) {
                errorElement.textContent = errors[field];
            }
        }
    }

    nextButtons.forEach((button, index) => {
        button.addEventListener("click", function () {
            validateStep(currentStep, function(valid) {
                if (valid) {
                    currentStep++;
                    showStep(currentStep);
                }
            });
        });
    });

    prevButtons.forEach(button => {
        button.addEventListener("click", function () {
            currentStep--;
            showStep(currentStep);
        });
    });

    signupForm.addEventListener("submit", function (event) {
        validateStep(currentStep, function(valid) {
            if (!valid) {
                event.preventDefault();
            }
        });
    });

    showStep(currentStep);

    // Format and validate phone number
    const companyPhoneNumberField = document.getElementById('id_company_phone_number');
    const companyMobileNumberField = document.getElementById('id_mobile_number');

    if (companyPhoneNumberField) {
        const phoneInput = window.intlTelInput(companyPhoneNumberField, {
            utilsScript:
              "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js",
        });
    } 
    
    if (companyMobileNumberField){
        const phoneInput = window.intlTelInput(companyMobileNumberField, {
            utilsScript:
              "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js",
          });

        // Automatically set country code when the country is selected
        companyMobileNumberField.addEventListener("countrychange", function () {
            const countryData = phoneInput.getSelectedCountryData();
            companyMobileNumberField.value = "+" + countryData.dialCode;
        });
    }

    // Handle country, state, and city fields
    const countryField = document.getElementById('id_country');
    const stateField = document.getElementById('id_state');
    const cityField = document.getElementById('id_city');

    if (countryField) {
        countryField.addEventListener('change', function() {
            const countryId = this.value;
            if (countryId) {
                fetch(`/api/get_states/${countryId}/`)
                    .then(response => response.json())
                    .then(data => {
                        stateField.innerHTML = '';
                        const defaultOption = document.createElement('option');
                        defaultOption.textContent = 'Select State';
                        defaultOption.value = '';
                        stateField.appendChild(defaultOption);

                        data.forEach(state => {
                            const option = document.createElement('option');
                            option.value = state.id;
                            option.textContent = state.name;
                            stateField.appendChild(option);
                        });
                    });
            }
        });
    }

    if (stateField) {
        stateField.addEventListener('change', function() {
            const stateId = this.value;
            if (stateId) {
                fetch(`/api/get_cities/${stateId}/`)
                    .then(response => response.json())
                    .then(data => {
                        cityField.innerHTML = '';
                        const defaultOption = document.createElement('option');
                        defaultOption.textContent = 'Select City';
                        defaultOption.value = '';
                        cityField.appendChild(defaultOption);

                        data.forEach(city => {
                            const option = document.createElement('option');
                            option.value = city.id;
                            option.textContent = city.name;
                            cityField.appendChild(option);
                        });
                    });
            }
        });
    }
});



// dfiuhfhdjkhf

document.addEventListener("DOMContentLoaded", function () {
    console.log("DOM fully loaded and parsed");
    
    const signupForm = document.getElementById("signup-form");
    const steps = document.querySelectorAll(".step-content");
    const stepIndicators = document.querySelectorAll("#step-indicator .step");
    const nextButtons = document.querySelectorAll(".next-step");
    const prevButtons = document.querySelectorAll(".prev-step");
    const submitButton = signupForm.querySelector("button[type='submit']");
    const loginPasswordField = document.getElementById("login_password");
    const signupPasswordField = document.getElementById("id_signup_password");
    const signupConfirmPasswordField = document.getElementById("id_signup_confirm_password");
    const passwordStrength = document.getElementById("password-strength");
    const toggleLoginPassword = document.getElementById("toggle-login-password");
    const toggleSignupPassword = document.getElementById("toggle-signup-password");
    const toggleSignupConfirmPassword = document.getElementById("toggle-signup-confirm-password");

    let currentStep = 0;
    let isSubmitting = false; // Flag to prevent multiple submissions

    function showStep(step, direction = 'next') {
        steps.forEach((stepContent, index) => {
            stepContent.classList.remove('slide-in-left', 'slide-in-right', 'slide-out-left', 'slide-out-right');
            if (index === step) {
                stepContent.style.display = 'block';
                stepContent.classList.add(direction === 'next' ? 'slide-in-right' : 'slide-in-left');
            } else {
                stepContent.style.display = 'none';
            }
            stepIndicators[index].classList.toggle("active", index <= step);
        });
    }

    function validateStep(step, callback) {
        const formData = new FormData();

        steps.forEach((stepContent, index) => {
            if (index <= step) {
                const inputs = stepContent.querySelectorAll("input, select");
                inputs.forEach(input => {
                    formData.append(input.name, input.value);
                });
            }
        });
        
        formData.append('step', step);
        formData.append('csrfmiddlewaretoken', document.querySelector('input[name="csrfmiddlewaretoken"]').value);

        fetch("{% url 'validate_step' %}", {
            method: "POST",
            headers: {
                'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            let valid = true;
            if (data.errors) {
                valid = false;
                displayErrors(data.errors);
            }
            callback(valid);
        })
        .catch(error => {
            console.error('An error occurred:', error);
            callback(false);
        });
    }

    function displayErrors(errors) {
        document.querySelectorAll('.error').forEach(el => el.textContent = '');
        for (let field in errors) {
            const errorElement = document.getElementById(`error-${field}`);
            if (errorElement) {
                errorElement.textContent = errors[field];
            }
        }
    }

    nextButtons.forEach((button, index) => {
        button.addEventListener("click", function () {
            validateStep(currentStep, function(valid) {
                if (valid) {
                    currentStep++;
                    showStep(currentStep, 'next');
                }
            });
        });
    });

    prevButtons.forEach(button => {
        button.addEventListener("click", function () {
            currentStep--;
            showStep(currentStep, 'prev');
        });
    });

    signupForm.addEventListener("submit", function (event) {
        event.preventDefault();
        if (isSubmitting) return; // Prevent multiple submissions
        isSubmitting = true;
        submitButton.innerHTML = '<i class="fa fa-spinner fa-spin"></i> Submitting...';

        validateStep(currentStep, function(valid) {
            if (valid) {
                const formData = new FormData(signupForm);
                fetch(signupForm.action, {
                    method: signupForm.method,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: formData
                })
                .then(response => response.json())
                .then(data => {
                    isSubmitting = false; // Reset flag
                    if (data.success) {
                        signupPopup.style.display = "none";
                        signupForm.reset(); // Reset the form data
                        let messagesPopupContent = document.querySelector("#messages-popup .messages-container");
                        if (!messagesPopupContent) {
                            messagesPopup.innerHTML = `
                            <div class="popup-content" style="
                            background: linear-gradient(135deg, #ffffff 0%, #f0f0f0 100%);
                            border-radius: 15px;
                            padding: 20px;
                            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                            border: 1px solid #ccc;
                            backdrop-filter: blur(10px);
                            ">
                            <span class="close" id="close-messages" style="
                                color: #aaa;
                                float: right;
                                font-size: 20px;
                                font-weight: bold;
                                cursor: pointer;
                                ">&times;</span>
                            <div class="messages-container" style="
                                padding: 10px;
                                background: #ffffff;
                                border-radius: 10px;
                                box-shadow: inset 0 1px 3px rgba(0, 0, 0, 0.1);
                                ">
                                <!-- Messages will be dynamically inserted here -->
                            </div>
                        </div>
                            `;
                            messagesPopupContent = document.querySelector("#messages-popup .messages-container");
                        }
                        messagesPopupContent.innerHTML = `<div class="message success">We have sent you an Email. Please Verify Your Email.</div>`;
                        messagesPopup.style.display = "block";
                    } else {
                        displayErrors(data.errors);
                        submitButton.innerHTML = 'Submit'; // Reset button text
                    }
                })
                .catch(error => {
                    console.error('An error occurred:', error);
                    isSubmitting = false; // Reset flag
                    submitButton.innerHTML = 'Submit'; // Reset button text
                });
            } else {
                isSubmitting = false; // Reset flag
                submitButton.innerHTML = 'Submit'; // Reset button text
            }
        });
    });

    showStep(currentStep);

    function togglePasswordVisibility(field, icon) {
        console.log("Toggling password visibility");
        icon.addEventListener("click", function () {
            if (field.type === "password") {
                field.type = "text";
                icon.classList.remove("fa-eye");
                icon.classList.add("fa-eye-slash");
            } else {
                field.type = "password";
                icon.classList.remove("fa-eye-slash");
                icon.classList.add("fa-eye");
            }
        });
    }

    function updatePasswordStrength(password) {
        console.log("Updating password strength");
        const regexes = [
            { regex: /.{8,}/, message: "At least 8 characters" },
            { regex: /[A-Z]/, message: "At least one uppercase letter" },
            { regex: /[a-z]/, message: "At least one lowercase letter" },
            { regex: /\d/, message: "At least one digit" },
            { regex: /[!@#$%^&*(),.?":{}|<>]/, message: "At least one special character" }
        ];

        const passedChecks = regexes.filter(rule => rule.regex.test(password)).length;
        const strength = Math.min(passedChecks / regexes.length * 100, 100);

        passwordStrength.style.width = `${strength}%`;
        passwordStrength.className = `password-strength strength-${passedChecks}`;
    }

    if (loginPasswordField) {
        togglePasswordVisibility(loginPasswordField, toggleLoginPassword);
    }

    if (signupPasswordField) {
        togglePasswordVisibility(signupPasswordField, toggleSignupPassword);
        signupPasswordField.addEventListener("input", function () {
            updatePasswordStrength(signupPasswordField.value);
        });
    }

    if (signupConfirmPasswordField) {
        togglePasswordVisibility(signupConfirmPasswordField, toggleSignupConfirmPassword);
    }

    // Format and validate phone number
    const phoneNumberFields = ['id_company_phone_number', 'id_mobile_number'];
    phoneNumberFields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            const phoneInput = window.intlTelInput(field, {
                initialCountry: "auto",
                geoIpLookup: function(callback) {
                    fetch('https://ipinfo.io/json')
                        .then(response => response.json())
                        .then(data => callback(data.country))
                        .catch(() => callback('us'));
                },
                utilsScript: "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/17.0.8/js/utils.js",
            });

            field.addEventListener("countrychange", function () {
                const countryData = phoneInput.getSelectedCountryData();
                field.value = "+" + countryData.dialCode;
            });
        }
    });

    // Handle country, state, and city fields
    const countryField = document.getElementById('id_country');
    const stateField = document.getElementById('id_state');
    const cityField = document.getElementById('id_city');

    if (countryField) {
        countryField.addEventListener('change', function() {
            const countryId = this.value;
            if (countryId) {
                fetch(`/api/get_states/${countryId}/`)
                    .then(response => response.json())
                    .then(data => {
                        stateField.innerHTML = '';
                        const defaultOption = document.createElement('option');
                        defaultOption.textContent = 'Select State';
                        defaultOption.value = '';
                        stateField.appendChild(defaultOption);

                        data.forEach(state => {
                            const option = document.createElement('option');
                            option.value = state.id;
                            option.textContent = state.name;
                            stateField.appendChild(option);
                        });
                    });
            }
        });
    }

    if (stateField) {
        stateField.addEventListener('change', function() {
            const stateId = this.value;
            if (stateId) {
                fetch(`/api/get_cities/${stateId}/`)
                    .then(response => response.json())
                    .then(data => {
                        cityField.innerHTML = '';
                        const defaultOption = document.createElement('option');
                        defaultOption.textContent = 'Select City';
                        defaultOption.value = '';
                        cityField.appendChild(defaultOption);

                        data.forEach(city => {
                            const option = document.createElement('option');
                            option.value = city.id;
                            option.textContent = city.name;
                            cityField.appendChild(option);
                        });
                    });
            }
        });
    }

    // Toggle dropdown content visibility
    const accountIcon = document.getElementById("account-icon");
    const dropdownContent = document.getElementById("dropdown-content");
    const loginPopup = document.getElementById("login-popup");
    const signupPopup = document.getElementById("signup-popup");
    const resetPopup = document.getElementById("reset-popup");
    const messagesPopup = document.getElementById("messages-popup");
    const closeLogin = document.getElementById("close-login");
    const closeSignup = document.getElementById("close-signup");
    const closeReset = document.getElementById("close-reset");
    const closeMessages = document.getElementById("close-messages");
    const loginLink = document.getElementById("login");
    const signupLink = document.getElementById("signup");
    const showSignup = document.getElementById("show-signup");
    const showLogin = document.getElementById("show-login");
    const showReset = document.getElementById("show-reset");
    const showLoginFromReset = document.getElementById("show-login-from-reset");
    const hamburgerIcon = document.getElementById("hamburger-icon");
    const closeIcon = document.getElementById("close-icon");
    const mobileMenu = document.getElementById("mobile-menu");
    const mobileLoginLink = document.getElementById("mobile-login");
    const mobileSignupLink = document.getElementById("mobile-signup");
    const loginForm = document.getElementById("login-popup")?.querySelector("form");
    const resetForm = document.getElementById("reset-form");

    accountIcon.addEventListener("click", function (event) {
        dropdownContent.style.display = dropdownContent.style.display === "block" ? "none" : "block";
        event.stopPropagation();
    });

    window.addEventListener("click", function (event) {
        if (!event.target.closest("#account-icon") && !event.target.closest("#dropdown-content")) {
            dropdownContent.style.display = "none";
        }
    });

    if (loginLink) {
        loginLink.addEventListener("click", function () {
            loginPopup.style.display = "block";
            dropdownContent.style.display = "none";
        });
    }

    if (signupLink) {
        signupLink.addEventListener("click", function () {
            signupPopup.style.display = "block";
            dropdownContent.style.display = "none";
        });
    }

    if (showSignup) {
        showSignup.addEventListener("click", function () {
            signupPopup.style.display = "block";
            loginPopup.style.display = "none";
        });
    }

    if (showLogin) {
        showLogin.addEventListener("click", function () {
            loginPopup.style.display = "block";
            signupPopup.style.display = "none";
        });
    }

    if (showReset) {
        showReset.addEventListener("click", function () {
            resetPopup.style.display = "block";
            loginPopup.style.display = "none";
        });
    }

    if (showLoginFromReset) {
        showLoginFromReset.addEventListener("click", function () {
            loginPopup.style.display = "block";
            resetPopup.style.display = "none";
        });
    }

    if (closeLogin) {
        closeLogin.addEventListener("click", function () {
            loginPopup.style.display = "none";
        });
    }

    if (closeSignup) {
        closeSignup.addEventListener("click", function () {
            signupPopup.style.display = "none";
        });
    }

    if (closeReset) {
        closeReset.addEventListener("click", function () {
            resetPopup.style.display = "none";
        });
    }

    if (closeMessages) {
        closeMessages.addEventListener("click", function () {
            messagesPopup.style.display = "none";
        });
    }

    if (mobileLoginLink) {
        mobileLoginLink.addEventListener("click", function () {
            loginPopup.style.display = "block";
            mobileMenu.style.left = "-100%";
            hamburgerIcon.style.display = "block";
            closeIcon.style.display = "none";
        });
    }

    if (mobileSignupLink) {
        mobileSignupLink.addEventListener("click", function () {
            signupPopup.style.display = "block";
            mobileMenu.style.left = "-100%";
            hamburgerIcon.style.display = "block";
            closeIcon.style.display = "none";
        });
    }

    hamburgerIcon.addEventListener("click", function () {
        console.log("Hamburger icon clicked");
        mobileMenu.style.left = "0";
        hamburgerIcon.style.display = "none";
        closeIcon.style.display = "block";
    });

    closeIcon.addEventListener("click", function () {
        console.log("Close icon clicked");
        mobileMenu.style.left = "-100%";
        hamburgerIcon.style.display = "block";
        closeIcon.style.display = "none";
    });

    if (loginForm) {
        loginForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(loginForm);
            fetch(loginForm.action, {
                method: loginForm.method,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = '/dashboard';
                } else {
                    const formErrorDiv = document.getElementById('error-login_form');
                    formErrorDiv.textContent = data.errors.form;
                    formErrorDiv.style.display = 'block';
                }
            })
            .catch(error => {
                const formErrorDiv = document.getElementById('error-login_form');
                formErrorDiv.textContent = 'An error occurred while trying to log in. Please try again.';
                formErrorDiv.style.display = 'block';
            });
        });
    }

    if (resetForm) {
        resetForm.addEventListener("submit", function (event) {
            event.preventDefault();
            const formData = new FormData(resetForm);
            fetch(resetForm.action, {
                method: resetForm.method,
                headers: {
                    'X-CSRFToken': formData.get('csrfmiddlewaretoken'),
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const resetMessage = document.getElementById("reset-message");
                if (data.message) {
                    resetMessage.style.display = "block";
                    resetMessage.textContent = data.message;
                    resetMessage.className = 'message success';
                    setTimeout(() => {
                        resetMessage.style.display = "none";
                        document.getElementById("reset-popup").style.display = "none";
                    }, 5000);
                } else if (data.error) {
                    resetMessage.style.display = "block";
                    resetMessage.textContent = data.error;
                    resetMessage.className = 'message error';
                    setTimeout(() => {
                        resetMessage.style.display = "none";
                    }, 5000);
                }
            })
            .catch(error => console.error('An error occurred:', error));
        });
    }
});
