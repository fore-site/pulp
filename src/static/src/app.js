document.addEventListener("DOMContentLoaded", () => {
    const getDropdownRoots = () => Array.from(document.querySelectorAll("[data-dropdown-root]"));

    const closeDropdown = (root) => {
        if (!root) return;

        const toggle = root.querySelector("[data-dropdown-toggle]");
        const menu = root.querySelector("[data-dropdown-menu]");

        if (!menu) return;

        menu.classList.add("hidden");

        if (toggle) {
            toggle.setAttribute("aria-expanded", "false");
        }
    };

    const openDropdown = (root) => {
        const toggle = root.querySelector("[data-dropdown-toggle]");
        const menu = root.querySelector("[data-dropdown-menu]");

        if (!menu) return;

        getDropdownRoots().forEach((dropdownRoot) => {
            if (dropdownRoot !== root) {
                closeDropdown(dropdownRoot);
            }
        });

        menu.classList.remove("hidden");

        if (toggle) {
            toggle.setAttribute("aria-expanded", "true");
        }
    };

    const syncDrawerScrollLock = () => {
        const hasOpenDrawer = document.querySelector("[data-drawer-container]:not(.hidden)");
        document.body.classList.toggle("overflow-hidden", Boolean(hasOpenDrawer));
    };

    const closeDrawer = (root) => {
        if (!root) return;

        const trigger = root.querySelector("[data-drawer-open]");
        const container = root.querySelector("[data-drawer-container]");

        if (!container) return;

        container.classList.add("hidden");
        container.setAttribute("aria-hidden", "true");

        if (trigger) {
            trigger.setAttribute("aria-expanded", "false");
        }

        syncDrawerScrollLock();
    };

    const openDrawer = (root) => {
        if (!root) return;

        const trigger = root.querySelector("[data-drawer-open]");
        const container = root.querySelector("[data-drawer-container]");

        if (!container) return;

        document.querySelectorAll("[data-drawer-root]").forEach((drawerRoot) => {
            if (drawerRoot !== root) {
                closeDrawer(drawerRoot);
            }
        });

        container.classList.remove("hidden");
        container.setAttribute("aria-hidden", "false");

        if (trigger) {
            trigger.setAttribute("aria-expanded", "true");
        }

        syncDrawerScrollLock();
    };

    document.addEventListener("click", (event) => {
        const dropdownToggle = event.target.closest("[data-dropdown-toggle]");
        if (dropdownToggle) {
            event.preventDefault();
            event.stopPropagation();

            const root = dropdownToggle.closest("[data-dropdown-root]");
            const menu = root?.querySelector("[data-dropdown-menu]");

            if (!root || !menu) return;

            if (menu.classList.contains("hidden")) {
                openDropdown(root);
            } else {
                closeDropdown(root);
            }

            return;
        }

        const drawerOpen = event.target.closest("[data-drawer-open]");
        if (drawerOpen) {
            event.preventDefault();
            openDrawer(drawerOpen.closest("[data-drawer-root]"));
            return;
        }

        const drawerClose = event.target.closest("[data-drawer-close], [data-drawer-overlay]");
        if (drawerClose) {
            event.preventDefault();
            closeDrawer(drawerClose.closest("[data-drawer-root]"));
            return;
        }

        getDropdownRoots().forEach((root) => {
            if (!root.contains(event.target)) {
                closeDropdown(root);
            }
        });
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape") {
            getDropdownRoots().forEach(closeDropdown);
            document.querySelectorAll("[data-drawer-root]").forEach(closeDrawer);
        }
    });

    document.body.addEventListener("htmx:afterSwap", () => {
        document.querySelectorAll("[data-drawer-root]").forEach(closeDrawer);
    });
});

// log all htmx events to the console (after scripts are loaded).
window.addEventListener("load", () => {
    if (window.htmx && typeof window.htmx.logAll === "function") {
        window.htmx.logAll();
    }
});
