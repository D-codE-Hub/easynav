// Copyright (c) 2026, D-codE and contributors
// For license information, please see license.txt

frappe.ui.form.on("EasyNav Settings", {
	setup(frm) {
		// `link_to` lists records of the selected type; child tables cannot be opened directly
		frm.set_query("link_to", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return row.type === "DocType" ? { filters: { istable: 0 } } : {};
		});
	},

	// apply changes immediately instead of waiting for a full reload
	after_save() {
		if (window.easynav) window.easynav.refresh();
	},
});

frappe.ui.form.on("EasyNav Item", {
	// a value picked for the previous type is meaningless for the new one
	type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, { link_to: "", url: "" });
	},
});
