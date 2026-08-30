//
// NJANGI TRACKER - MAIN JAVASCRIPT
//

// Mobile navigation
const menuToggle = document.getElementById("menuToggle");
const navLinks = document.getElementById("navLinks");

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

// Close mobile menu after clicking a navigation link
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

// Update footer year automatically
const currentYear = document.getElementById("currentYear");
currentYear.textContent = new Date().getFullYear();

// Simple scroll-reveal animation
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

// Smoothly focus the main content when Get Started is clicked
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
