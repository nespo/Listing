document.addEventListener("DOMContentLoaded", function () {
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
    const mobileMenu = document.getElementById("mobile-menu");
    const mobileLoginLink = document.getElementById("mobile-login");
    const mobileSignupLink = document.getElementById("mobile-signup");
    const loginForm = document.getElementById("login-popup")?.querySelector("form");
    const resetForm = document.getElementById("reset-form");
    const signupForm = document.getElementById("signup-form");

    // Toggle dropdown content visibility
    accountIcon.addEventListener("click", function (event) {
        dropdownContent.style.display = dropdownContent.style.display === "block" ? "none" : "block";
        event.stopPropagation();
    });

    // Close dropdown if clicked outside
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

    hamburgerIcon.addEventListener("click", function (event) {
        const isMenuOpen = mobileMenu.style.left === "0px";
        if (isMenuOpen) {
            mobileMenu.style.left = "-100%";
            hamburgerIcon.src = "https://cdn-icons-png.flaticon.com/512/1828/1828859.png"; // Hamburger menu icon
        } else {
            mobileMenu.style.left = "0";
            hamburgerIcon.src = "https://cdn-icons-png.flaticon.com/512/1828/1828778.png"; // Cross icon
        }
        event.stopPropagation();
    });

    if (mobileLoginLink) {
        mobileLoginLink.addEventListener("click", function () {
            loginPopup.style.display = "block";
            mobileMenu.style.left = "-100%";
            hamburgerIcon.src = "https://cdn-icons-png.flaticon.com/512/1828/1828859.png"; // Reset icon to hamburger menu
        });
    }

    if (mobileSignupLink) {
        mobileSignupLink.addEventListener("click", function () {
            signupPopup.style.display = "block";
            mobileMenu.style.left = "-100%";
            hamburgerIcon.src = "https://cdn-icons-png.flaticon.com/512/1828/1828859.png"; // Reset icon to hamburger menu
        });
    }

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
                    window.location.href = '/dashboard'; // Redirect to dashboard on successful login
                } else {
                    displayErrors(data.errors);
                }
            })
            .catch(error => console.error('An error occurred:', error));
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

    if (signupForm) {
        signupForm.addEventListener("submit", function (event) {
            event.preventDefault();
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
                if (data.success) {
                    signupPopup.style.display = "none";
                    let messagesPopupContent = document.querySelector("#messages-popup .messages-container");
                    if (!messagesPopupContent) {
                        messagesPopup.innerHTML = `
                            <div class="popup-content">
                                <span class="close" id="close-messages">&times;</span>
                                <div class="messages-container"></div>
                            </div>
                        `;
                        messagesPopupContent = document.querySelector("#messages-popup .messages-container");
                    }
                    messagesPopupContent.innerHTML = `<div class="message success">Your account has been sent to get admin approval.</div>`;
                    messagesPopup.style.display = "block";
                } else {
                    displayErrors(data.errors);
                }
            })
            .catch(error => console.error('An error occurred:', error));
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
});