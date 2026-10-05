// Copyright (c) 2026, D-codE and contributors
// For license information, please see license.txt

const EASYNAV_TARGET_HINTS = {
	DocType: __("DocType name, e.g. Customer"),
	Page: __("Page name, e.g. sales-dashboard"),
	Report: __("Report name, e.g. Sales Analytics"),
	URL: __("https://example.com or /app/..."),
};

frappe.ui.form.on("EasyNav Settings", {
	// apply changes immediately instead of waiting for a full reload
	after_save() {
		if (window.easynav) easynav.refresh();
	},
});

frappe.ui.form.on("EasyNav Item", {
	type(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		const grid_row = frm.fields_dict.items.grid.get_row(cdn);
		const target = grid_row && grid_row.grid_form && grid_row.grid_form.fields_dict.target;
		if (target) {
			target.df.description = EASYNAV_TARGET_HINTS[row.type] || "";
			target.refresh();
		}
	},
});
