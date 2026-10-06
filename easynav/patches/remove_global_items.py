import frappe


def execute():
	"""Navigation items are per user now (EasyNav User Navigation): drop the old site-wide ones.

	Removing the `items` table from EasyNav Settings leaves its rows behind as orphans.
	"""
	frappe.db.delete("EasyNav Item", {"parenttype": "EasyNav Settings"})
