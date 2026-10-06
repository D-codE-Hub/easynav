import frappe


def execute():
	"""Move the old free-text `target` into `link_to` (DocType/Page/Report) or `url` (URL)."""
	if not frappe.db.has_column("EasyNav Item", "target"):
		return

	item = frappe.qb.DocType("EasyNav Item")
	for fieldname, is_url in (("url", True), ("link_to", False)):
		(
			frappe.qb.update(item)
			.set(item[fieldname], item.target)
			.where(item.type == "URL" if is_url else item.type != "URL")
			.where(item[fieldname].isnull() | (item[fieldname] == ""))
			.where(item.target.isnotnull() & (item.target != ""))
			.run()
		)
