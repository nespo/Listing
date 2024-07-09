document.addEventListener("DOMContentLoaded", function () {
    const accountIcon = document.getElementById("account-icon");
    const dropdownContent = document.getElementById("dropdown-content");

    accountIcon.addEventListener("click", function (event) {
        dropdownContent.style.display = dropdownContent.style.display === "block" ? "none" : "block";
        event.stopPropagation();
    });

    window.addEventListener("click", function (event) {
        if (!event.target.closest("#account-icon") && !event.target.closest("#dropdown-content")) {
            dropdownContent.style.display = "none";
        }
    });

    const hamburgerIcon = document.getElementById("hamburger-icon");
    const closeIcon = document.getElementById("close-icon");
    const mobileMenu = document.getElementById("mobile-menu");

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

});