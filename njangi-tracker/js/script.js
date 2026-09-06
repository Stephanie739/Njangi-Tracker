// 

// NJANGI TRACKER - MAIN JAVASCRIPT
// 

// MOBILE NAVIGATION
// These elements come from the navigation menu in index.html.

const menuToggle = document.getElementById("menuToggle");
const navLinks = document.getElementById("navLinks");

// When the menu button is clicked, open or close the mobile menu.

menuToggle.addEventListener("click", () => {
    const isOpen = navLinks.classList.toggle("active");

    menuToggle.setAttribute("aria-expanded", isOpen);

    // Animate hamburger icon
    const bars = menuToggle.querySelectorAll("span");

    if (isOpen) {
        bars[0].style.transform = "translateY(6px) rotate(45deg)";
        bars[1].style.opacity = "0";
        bars[2].style.transform = "translateY(-6px) rotate(-45deg)";
    } else {
        bars[0].style.transform = "none";
        bars[1].style.opacity = "1";
        bars[2].style.transform = "none";
    }
});

// CLOSE MOBILE MENU
// On a phone, close the menu after the user chooses a page section.

const links = navLinks.querySelectorAll("a");

links.forEach((link) => {
    link.addEventListener("click", () => {
        navLinks.classList.remove("active");
        menuToggle.setAttribute("aria-expanded", "false");

        const bars = menuToggle.querySelectorAll("span");
        bars[0].style.transform = "none";
        bars[1].style.opacity = "1";
        bars[2].style.transform = "none";
    });
});

// FOOTER YEAR
// JavaScript gets the current year so we do not have to update the HTML manually.

const currentYear = document.getElementById("currentYear");
currentYear.textContent = new Date().getFullYear();

// SCROLL REVEAL ANIMATION
// Cards start hidden and become visible when they enter the screen.

const revealElements = document.querySelectorAll(
    ".feature-card, .step, .about-card, .about-points, .cta-box"
);

revealElements.forEach((element) => {
    element.classList.add("reveal");
});

const revealObserver = new IntersectionObserver(
    (entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
                observer.unobserve(entry.target);
            }
        });
    },
    {
        threshold: 0.12
    }
);

revealElements.forEach((element) => {
    revealObserver.observe(element);
});

// GET STARTED BUTTON
// Scroll to the features section when the button points to #features.

const getStartedButtons = document.querySelectorAll('a[href="#features"]');

getStartedButtons.forEach((button) => {
    button.addEventListener("click", () => {
        const features = document.getElementById("features");

        if (features) {
            features.scrollIntoView({
                behavior: "smooth",
                block: "start"
            });
        }
    });
});
