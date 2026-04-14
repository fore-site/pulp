document.addEventListener("DOMContentLoaded", () => {
    const dropdownRoots = Array.from(document.querySelectorAll("[data-dropdown-root]"));

    const closeDropdown = (root) => {
        const toggle = root.querySelector("[data-dropdown-toggle]");
        const menu = root.querySelector("[data-dropdown-menu]");

        if (!menu) return;

        menu.classList.add("hidden");

        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }
    };

    const openDropdown = (root) => {
        dropdownRoots.forEach((dropdownRoot) => {
            if (dropdownRoot !== root) {
                closeDropdown(dropdownRoot);
            }
        });

        const toggle = root.querySelector("[data-dropdown-toggle]");
        const menu = root.querySelector("[data-dropdown-menu]");

        if (!menu) return;

        menu.classList.remove("hidden");

        if (toggle) {
            toggle.setAttribute("aria-expanded", "true");
        }
    };

    dropdownRoots.forEach((root) => {
        const toggle = root.querySelector("[data-dropdown-toggle]");
        const menu = root.querySelector("[data-dropdown-menu]");

        if (!toggle || !menu) return;

        toggle.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();

            const isHidden = menu.classList.contains("hidden");

            if (isHidden) {
                openDropdown(root);
            } else {
                closeDropdown(root);
            }
        });

        menu.addEventListener("click", (event) => {
            event.stopPropagation();
        });
    });

    document.addEventListener("click", (event) => {
        dropdownRoots.forEach((root) => {
            if (!root.contains(event.target)) {
                closeDropdown(root);
            }
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            dropdownRoots.forEach(closeDropdown);
        }
    });
});

// log all htmx events to the console.
htmx.logAll();
