import re
from urllib.parse import urlsplit

import frappe
from frappe import _

ALLOWED_SCHEMES = ("http", "https")
ICON_PATTERN = re.compile(r"^[\w-]+$")
DOC_VIEWS = ("List", "Report Builder", "Dashboard", "Tree", "New", "Calendar", "Kanban", "Image")
# upper bound per user: the items are sent to the browser on every boot
MAX_ITEMS = 30


def is_safe_url(url: str | None) -> bool:
	"""Allow absolute http(s) URLs and same-origin paths starting with a single `/`."""
	url = (url or "").strip()
	if not url or any(ch in url for ch in "\\\n\r\t"):
		return False

	if url.startswith("/"):
		return not url.startswith("//")

	parts = urlsplit(url)
	return parts.scheme.lower() in ALLOWED_SCHEMES and bool(parts.netloc)


def get_item_target(item) -> str:
	"""Return what an item opens: `url` for URL items, the record named in `link_to` otherwise."""
	value = item.url if item.type == "URL" else item.link_to
	return (value or "").strip()


def _get_doc_view_error(item, meta) -> str | None:
	doc_view = item.doc_view or ""
	# Single DocTypes only have a form, so the view is ignored for them (as Workspace shortcuts do)
	if not doc_view or meta.issingle:
		return None

	if doc_view not in DOC_VIEWS:
		return _("Unsupported DocType View {0}").format(frappe.bold(doc_view))
	if doc_view == "Tree" and not meta.is_tree:
		return _("{0} is not a tree DocType and has no Tree view").format(frappe.bold(meta.name))
	if doc_view == "Kanban" and item.kanban_board:
		reference_doctype = frappe.db.get_value("Kanban Board", item.kanban_board, "reference_doctype")
		if reference_doctype != meta.name:
			return _("Kanban Board {0} does not belong to {1}").format(
				frappe.bold(item.kanban_board), frappe.bold(meta.name)
			)

	return None


def get_item_error(item) -> str | None:
	"""Return a message describing why a navigation item is invalid, or None if it is valid."""
	label = (item.label or "").strip()
	target = get_item_target(item)

	icon = (item.icon or "").strip()

	if not label:
		return _("Label is required")
	if icon and not ICON_PATTERN.match(icon):
		return _("Icon {0} is not a valid icon name").format(frappe.bold(icon))
	if (item.order or 0) < 0:
		return _("Order cannot be negative")
	if not target:
		return _("URL is required") if item.type == "URL" else _("Link To is required")

	if item.type == "DocType":
		try:
			meta = frappe.get_meta(target)  # cached; no query on repeat calls
		except frappe.DoesNotExistError:
			return _("DocType {0} does not exist").format(frappe.bold(target))
		if meta.istable:
			return _("{0} is a child table and cannot be opened directly").format(frappe.bold(target))
		if error := _get_doc_view_error(item, meta):
			return error
	elif item.type == "Page":
		if not frappe.db.exists("Page", target):
			return _("Page {0} does not exist").format(frappe.bold(target))
	elif item.type == "Report":
		if not frappe.db.exists("Report", target):
			return _("Report {0} does not exist").format(frappe.bold(target))
	elif item.type == "Dashboard":
		if not frappe.db.exists("Dashboard", target):
			return _("Dashboard {0} does not exist").format(frappe.bold(target))
	elif item.type == "URL":
		if not is_safe_url(target):
			return _("Only http(s) URLs and paths starting with / are allowed")
	else:
		return _("Unsupported type {0}").format(frappe.bold(item.type or ""))

	return None
