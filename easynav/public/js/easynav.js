// EasyNav: global floating navigation for Frappe Desk.
// Loaded on every Desk page via `app_include_js`.
(function () {
	if (window.easynav) return;

	const ROOT_ID = "easynav-root";
	const DEFAULT_ICON = "menu";
	const HOVER_CLOSE_DELAY = 150;
	const POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left"];

	const easynav = {
		_mounted: false,
		config: null,
		root: null,
		button: null,
		menu: null,
		_hover_timer: null,

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

		render() {
			// Always keep exactly one instance, even if init somehow runs twice.
			$(`#${ROOT_ID}`).remove();
			this.root = this.button = null;

			const config = this.config;
			if (!config || !config.enabled || !(config.items || []).length) return;

			const position = POSITIONS.includes(config.position) ? config.position : "bottom-right";
			const label = (config.button && config.button.label) || __("EasyNav");

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
				title: label,
			}).append(this.get_icon_html(config.button && config.button.icon));

			const $menu = this.build_menu(config.items);

			$root.append($menu, $button).appendTo(document.body);
			this.root = $root[0];
			this.button = $button[0];
			this.menu = $menu[0];

			this.bind_events($root, $button);
		},

		// Labels and targets are admin-entered text: only ever set via .text()/attr().
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
					$("<span>", { class: "easynav-item-icon" }).append(this.get_icon_html(item.icon, "sm")),
					$("<span>", { class: "easynav-item-label" }).text(item.label)
				);
				$item.data("easynav-item", item);
				$menu.append($item);
			});

			return $menu;
		},

		// Plain href so the browser handles middle-click / copy link. Routing proper is Phase 8.
		get_href(item) {
			const href = item.type === "URL" ? item.url : item.path;
			return typeof href === "string" && /^(https?:\/\/|\/(?!\/))/.test(href) ? href : "#";
		},

		bind_events($root, $button) {
			$button.on("click", () => this.toggle());

			// Hover is an enhancement for mouse users only; click/tap always works.
			if (window.matchMedia("(hover: hover) and (pointer: fine)").matches) {
				$root.on("mouseenter", () => {
					clearTimeout(this._hover_timer);
					this.open();
				});
				$root.on("mouseleave", () => {
					clearTimeout(this._hover_timer);
					this._hover_timer = setTimeout(() => this.close(), HOVER_CLOSE_DELAY);
				});
			}

			$root.on("click", ".easynav-item", () => this.close());

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
			if (!this.root || !this.is_open()) return;
			this.root.classList.remove("easynav-root--open");
			this.button.setAttribute("aria-expanded", "false");
		},

		toggle() {
			this.is_open() ? this.close() : this.open();
		},

		// Fall back to the default icon when the configured name is not in Frappe's sprite.
		get_icon_html(name, size = "md") {
			const valid = name && /^[\w-]+$/.test(name) && document.getElementById(`icon-${name}`);
			return frappe.utils.icon(valid ? name : DEFAULT_ICON, size, "", "", "", true);
		},
	};

	window.easynav = easynav;
	$(document).ready(() => easynav.init());

	// Registered once at load (never in render), so there are no duplicate handlers.
	$(document).on("click", (e) => {
		if (easynav.is_open() && !easynav.root.contains(e.target)) easynav.close();
	});
	$(document).on("page-change", () => easynav.close());
})();
