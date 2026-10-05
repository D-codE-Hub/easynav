from urllib.parse import urlsplit

import frappe
from frappe import _

ALLOWED_SCHEMES = ("http", "https")


def is_safe_url(url: str | None) -> bool:
	"""Allow absolute http(s) URLs and same-origin paths starting with a single `/`."""
	url = (url or "").strip()
	if not url or any(ch in url for ch in "\\\n\r\t"):
		return False

	if url.startswith("/"):
		return not url.startswith("//")

	parts = urlsplit(url)
	return parts.scheme.lower() in ALLOWED_SCHEMES and bool(parts.netloc)


def get_item_error(item) -> str | None:
	"""Return a message describing why a navigation item is invalid, or None if it is valid."""
	label = (item.label or "").strip()
	target = (item.target or "").strip()

	if not label:
		return _("Label is required")
	if not target:
		return _("Target is required")

	if item.type == "DocType":
		if not frappe.db.exists("DocType", target):
			return _("DocType {0} does not exist").format(frappe.bold(target))
		if frappe.db.get_value("DocType", target, "istable"):
			return _("{0} is a child table and cannot be opened directly").format(frappe.bold(target))
	elif item.type == "Page":
		if not frappe.db.exists("Page", target):
			return _("Page {0} does not exist").format(frappe.bold(target))
	elif item.type == "Report":
		if not frappe.db.exists("Report", target):
			return _("Report {0} does not exist").format(frappe.bold(target))
	elif item.type == "URL":
		if not is_safe_url(target):
			return _("Only http(s) URLs and paths starting with / are allowed")
	else:
		return _("Unsupported type {0}").format(frappe.bold(item.type or ""))

	return None
