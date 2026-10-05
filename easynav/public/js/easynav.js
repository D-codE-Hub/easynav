// EasyNav: global floating navigation for Frappe Desk.
// Loaded on every Desk page via `app_include_js`.
(function () {
	if (window.easynav) return;

	const easynav = {
		_mounted: false,
		config: null,

		// Configuration is delivered in frappe.boot (see easynav/boot.py).
		get_config() {
			return (frappe.boot && frappe.boot.easynav) || null;
		},

		init() {
			if (this._mounted) return;
			if (!frappe.session || frappe.session.user === "Guest") return;

			this.config = this.get_config();
			this._mounted = true;
		},
	};

	window.easynav = easynav;
	$(document).ready(() => easynav.init());
})();
