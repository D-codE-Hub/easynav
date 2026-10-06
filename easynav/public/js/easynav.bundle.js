// EasyNav: global floating navigation for Frappe Desk.
// Loaded on every Desk page via `app_include_js`.
(function () {
	if (window.easynav) return;

	const ROOT_ID = "easynav-root";
	const DEFAULT_ICON = "menu";
	const USER_NAVIGATION = "EasyNav User Navigation";
	const TYPE_ICONS = {
		DocType: "list",
		Page: "layout-dashboard",
		Report: "chart-bar",
		Dashboard: "layout-dashboard",
		URL: "external-link",
	};
	const HOVER_CLOSE_DELAY = 150;
	const LONG_PRESS_DELAY = 550;
	const HOVER_QUERY = "(hover: hover) and (pointer: fine)";
	const POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left"];

	const easynav = {
		_mounted: false,
		config: null,
		root: null,
		button: null,
		menu: null,
		_hover_timer: null,
		_press_timer: null,
		_long_pressed: false,
		_editor_opened_at: 0,
		_pinned: false, // opened by click: stays open until outside click / Esc / second click

		// Configuration is delivered in frappe.boot (see easynav/boot.py).
		get_config() {
			return (frappe.boot && frappe.boot.easynav) || null;
		},

		init() {
			if (this._mounted) return;
			if (!frappe.session || frappe.session.user === "Guest") return;

			this.config = this.get_config();
			this._mounted = true;
			this.render();
		},

		// Re-fetch the configuration from the server (e.g. after the user saved their shortcuts).
		// Not called on route changes: the boot payload is already current for the session.
		refresh() {
			return frappe
				.call({ method: "easynav.api.navigation.get_navigation", type: "GET" })
				.then((r) => {
					this.config = r.message || null;
					this.render();
				});
		},

		// Route changes never rebuild the UI; this only repairs it if something removed it from the DOM.
		ensure_mounted() {
			if (
				this._mounted &&
				this.config &&
				this.config.enabled &&
				!document.getElementById(ROOT_ID)
			) {
				this.render();
			}
		},

		render() {
			// Always keep exactly one instance, even if init somehow runs twice.
			$(`#${ROOT_ID}`).remove();
			this.root = this.button = null;

			const config = this.config;
			// No items is not a reason to hide: the menu is where a user starts adding their own.
			if (!config || !config.enabled) return;

			const position = POSITIONS.includes(config.position)
				? config.position
				: "bottom-right";
			const label = (config.button && config.button.label) || __("EasyNav");
			// the editor has no visible control of its own, so the tooltip is where it is advertised
			const hint = this.has_hover()
				? __("Right-click to edit your shortcuts")
				: __("Press and hold to edit your shortcuts");

			const $root = $("<div>", {
				id: ROOT_ID,
				class: `easynav-root easynav-root--${position}`,
			});
			const $button = $("<button>", {
				type: "button",
				class: "easynav-button",
				"aria-haspopup": "true",
				"aria-expanded": "false",
				"aria-label": label,
				title: `${label} · ${hint}`,
			}).append(this.get_icon_html(config.button && config.button.icon));

			const $menu = this.build_menu(config.items || []);

			$root.append($menu, $button).appendTo(document.body);
			this.root = $root[0];
			this.button = $button[0];
			this.menu = $menu[0];

			this.bind_events($root, $button);
		},

		// Labels and targets are user-entered text: only ever set via .text()/attr().
		build_menu(items) {
			const $menu = $("<div>", {
				class: "easynav-menu",
				role: "menu",
				"aria-label": __("EasyNav"),
			});

			items.forEach((item) => {
				const $item = $("<a>", {
					class: "easynav-item",
					role: "menuitem",
					tabindex: "-1",
					href: this.get_href(item),
				});
				$item.append(
					$("<span>", { class: "easynav-item-icon" }).append(
						this.get_icon_html(item.icon || TYPE_ICONS[item.type], "sm")
					),
					$("<span>", { class: "easynav-item-label" }).text(item.label)
				);
				$item.data("easynav-item", item);
				$menu.append($item);
			});

			if (!items.length) {
				$menu.append(
					$("<div>", { class: "easynav-empty" }).text(
						this.has_hover()
							? __("No shortcuts yet. Right-click the button to add some.")
							: __("No shortcuts yet. Press and hold the button to add some.")
					)
				);
			}

			return $menu;
		},

		has_hover() {
			return window.matchMedia(HOVER_QUERY).matches;
		},

		// Real href keeps middle-click / copy-link working; plain clicks are routed in on_item_click.
		get_href(item) {
			const href = item.type === "URL" ? item.url : item.path;
			return this.is_safe_url(href) ? href : "#";
		},

		on_item_click(e) {
			const item = $(e.currentTarget).data("easynav-item");
			this.close();

			// let the browser handle ctrl/cmd/shift-click and middle-click (native new tab/window)
			if (!item || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey || e.button > 0) return;

			e.preventDefault();
			this.navigate(item);
		},

		// Every user owns their shortcuts. There is no visible control for this: the editor opens on
		// right-click (or the keyboard's context-menu key) and on a long press on touch screens.
		// The document is created on first use; the server only ever returns the session user's own.
		customize() {
			// a long press can also fire `contextmenu` on some devices: open once
			if (Date.now() - this._editor_opened_at < 1000) return;
			this._editor_opened_at = Date.now();

			this.close();
			return frappe
				.call({ method: "easynav.api.navigation.get_user_navigation" })
				.then((r) => {
					if (r.message) frappe.set_route("Form", USER_NAVIGATION, r.message);
				});
		},

		// Explicit handling per type. Never assigns item.target to window.location directly.
		navigate(item) {
			switch (item.type) {
				case "DocType":
				case "Page":
				case "Report":
				case "Dashboard":
					return this.open_route(item);
				case "URL":
					return this.open_url(item);
				default:
					console.warn("EasyNav: unsupported item type", item.type);
			}
		},

		// Routes are resolved and permission-checked by the server (easynav/api/navigation.py).
		open_route(item) {
			if (item.open_in_new_tab) {
				if (this.is_safe_url(item.path)) this.open_new_tab(item.path);
				return;
			}
			if (Array.isArray(item.route) && item.route.length) {
				frappe.set_route(...item.route);
			} else if (this.is_safe_url(item.path)) {
				window.location.assign(item.path);
			}
		},

		open_url(item) {
			if (!this.is_safe_url(item.url)) {
				frappe.show_alert({
					message: __("EasyNav: blocked an unsafe link"),
					indicator: "red",
				});
				return;
			}
			if (item.open_in_new_tab) this.open_new_tab(item.url);
			else window.location.assign(item.url);
		},

		open_new_tab(url) {
			window.open(url, "_blank", "noopener,noreferrer");
		},

		// Mirrors easynav/easynav/validation.py: http(s) URLs or same-origin paths only.
		is_safe_url(url) {
			if (typeof url !== "string" || !url.trim() || /[\\\s]/.test(url)) return false;
			if (url.startsWith("/")) return !url.startsWith("//");
			try {
				const parsed = new URL(url);
				return ["http:", "https:"].includes(parsed.protocol) && !!parsed.host;
			} catch (e) {
				return false;
			}
		},

		bind_events($root, $button) {
			$button.on("click", () => {
				// the tap that ends a long press must not also toggle the menu
				if (this._long_pressed) {
					this._long_pressed = false;
					return;
				}
				this.toggle();
			});

			$button.on("contextmenu", (e) => {
				e.preventDefault();
				this.customize();
			});
			$button.on("touchstart", () => {
				this._long_pressed = false;
				clearTimeout(this._press_timer);
				this._press_timer = setTimeout(() => {
					this._long_pressed = true;
					this.customize();
				}, LONG_PRESS_DELAY);
			});
			$button.on("touchend touchmove touchcancel", () => clearTimeout(this._press_timer));

			// Hover is an enhancement for mouse users only; click/tap always works.
			if (this.has_hover()) {
				$root.on("mouseenter", () => {
					clearTimeout(this._hover_timer);
					this.open();
				});
				$root.on("mouseleave", () => {
					clearTimeout(this._hover_timer);
					if (this._pinned) return;
					this._hover_timer = setTimeout(() => this.close(), HOVER_CLOSE_DELAY);
				});
			}

			$root.on("click", ".easynav-item", (e) => this.on_item_click(e));

			$root.on("keydown", (e) => this.on_keydown(e));
		},

		on_keydown(e) {
			const $items = $(this.menu).find(".easynav-item");
			const index = $items.index(document.activeElement);

			if (e.key === "Escape" && this.is_open()) {
				e.preventDefault();
				this.close();
				this.button.focus();
			} else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
				e.preventDefault();
				if (!this.is_open()) this.open();
				const step = e.key === "ArrowDown" ? 1 : -1;
				const next = index === -1 ? (step === 1 ? 0 : $items.length - 1) : index + step;
				$items.get((next + $items.length) % $items.length).focus();
			}
		},

		is_open() {
			return !!this.root && this.root.classList.contains("easynav-root--open");
		},

		open() {
			if (!this.root || this.is_open()) return;
			this.root.classList.add("easynav-root--open");
			this.button.setAttribute("aria-expanded", "true");
		},

		close() {
			this._pinned = false;
			if (!this.root || !this.is_open()) return;
			this.root.classList.remove("easynav-root--open");
			this.button.setAttribute("aria-expanded", "false");
		},

		// A click always pins the menu open (even if hover already opened it); a second click closes it.
		toggle() {
			if (this.is_open() && this._pinned) {
				this.close();
			} else {
				this.open();
				this._pinned = true;
			}
		},

		// Fall back to the default icon when the configured name is not in Frappe's sprite.
		get_icon_html(name, size = "md") {
			// The sprite may not be in the DOM yet at first render; only reject unknown names once it is.
			const sprite_ready = !!document.getElementById(`icon-${DEFAULT_ICON}`);
			const valid =
				name &&
				/^[\w-]+$/.test(name) &&
				(!sprite_ready || document.getElementById(`icon-${name}`));
			return frappe.utils.icon(valid ? name : DEFAULT_ICON, size, "", "", "", true);
		},
	};

	window.easynav = easynav;
	$(document).ready(() => easynav.init());

	// Registered once at load (never in render), so there are no duplicate handlers.
	$(document).on("click", (e) => {
		if (easynav.is_open() && !easynav.root.contains(e.target)) easynav.close();
	});
	$(document).on("page-change", () => {
		easynav.close();
		easynav.ensure_mounted();
	});
})();
