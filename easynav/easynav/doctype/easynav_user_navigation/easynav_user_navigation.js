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

	onload(frm) {
		// "Add" for an ordinary user can only mean their own list, and they have just one:
		// open it (it is created on first use) instead of showing an empty form
		if (frm.is_new() && !frappe.user.has_role("System Manager")) {
			frappe.call({ method: "easynav.api.navigation.get_user_navigation" }).then((r) => {
				if (r.message) frappe.set_route("Form", frm.doctype, r.message);
			});
		}
	},

	refresh(frm) {
		const own = frm.doc.user === frappe.session.user;
		const is_support_user = frappe.user.has_role("System Manager");

		// support users pick whose list they are adding; everyone else only ever sees their own
		frm.toggle_display("user", is_support_user && (frm.is_new() || !own));
		if (frm.is_new()) return;

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
