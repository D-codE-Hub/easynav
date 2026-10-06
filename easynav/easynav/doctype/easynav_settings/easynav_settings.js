// Copyright (c) 2026, D-codE and contributors
// For license information, please see license.txt

frappe.ui.form.on("EasyNav Settings", {
	// apply changes immediately instead of waiting for a full reload
	after_save() {
		if (window.easynav) window.easynav.refresh();
	},
});
