// EasyNav: global floating navigation for Frappe Desk.
// Loaded on every Desk page via `app_include_js`.
(function () {
	if (window.easynav) return;

	const ROOT_ID = "easynav-root";
	const DEFAULT_ICON = "menu";
	const POSITIONS = ["bottom-right", "bottom-left", "top-right", "top-left"];

	const easynav = {
		_mounted: false,
		config: null,
		root: null,
		button: null,

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

			$root.append($button).appendTo(document.body);
			this.root = $root[0];
			this.button = $button[0];
		},

		// Fall back to the default icon when the configured name is not in Frappe's sprite.
		get_icon_html(name) {
			const valid = name && /^[\w-]+$/.test(name) && document.getElementById(`icon-${name}`);
			return frappe.utils.icon(valid ? name : DEFAULT_ICON, "md", "", "", "", true);
		},
	};

	window.easynav = easynav;
	$(document).ready(() => easynav.init());
})();
