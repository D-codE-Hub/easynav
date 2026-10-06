// Copyright (c) 2026, D-codE and contributors
// For license information, please see license.txt

frappe.ui.form.on("EasyNav User Navigation", {
	setup(frm) {
		// DocTypes and Pages are searched through EasyNav, so only the ones the user can open are
		// offered; the other types use the standard, permission-aware link search
		frm.set_query("link_to", "items", (doc, cdt, cdn) => {
			const row = locals[cdt][cdn];
			return ["DocType", "Page"].includes(row.type)
				? { query: "easynav.api.search.search_targets" }
				: {};
		});
		frm.set_query("kanban_board", "items", (doc, cdt, cdn) => {
			return { filters: { reference_doctype: locals[cdt][cdn].link_to } };
		});
	},

	refresh(frm) {
		const own = frm.doc.user === frappe.session.user;
		frm.toggle_display("user", !own);
		if (own) {
			frm.page.set_title(__("My Shortcuts"));
		} else {
			// only support users get here
			frm.set_intro(__("You are editing the shortcuts of {0}.", [frm.doc.user.bold()]), "blue");
		}
	},

	// apply changes immediately instead of waiting for a full reload;
	// a support user editing someone else's shortcuts has nothing to refresh
	after_save(frm) {
		if (window.easynav && frm.doc.user === frappe.session.user) window.easynav.refresh();
	},
});

frappe.ui.form.on("EasyNav Item", {
	// a value picked for the previous type is meaningless for the new one
	type(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, { link_to: "", url: "", doc_view: "", kanban_board: "" });
	},

	link_to(frm, cdt, cdn) {
		frappe.model.set_value(cdt, cdn, "kanban_board", "");
	},

	doc_view(frm, cdt, cdn) {
		if (locals[cdt][cdn].doc_view !== "Kanban") {
			frappe.model.set_value(cdt, cdn, "kanban_board", "");
		}
	},
});
