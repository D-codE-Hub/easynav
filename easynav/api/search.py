import frappe
from frappe.app_state import get_disabled_modules
from frappe.desk.search import validate_and_sanitize_search_inputs
from frappe.permissions import get_doctypes_with_read


def _search_doctypes(txt: str) -> list[list[str]]:
	filters = [["istable", "=", 0]]
	if txt:
		filters.append(["name", "like", f"%{txt}%"])
	if disabled_modules := get_disabled_modules():
		filters.append(["module", "not in", list(disabled_modules)])
	if frappe.session.user != "Administrator":
		# narrows the query to the user's roles; has_permission below stays the authority
		filters.append(["name", "in", get_doctypes_with_read() or [""]])

	names = frappe.get_all("DocType", filters=filters, pluck="name", order_by="name asc")
	return [[name] for name in names if frappe.has_permission(name, "read")]


def _search_pages(txt: str) -> list[list[str]]:
	filters = [["name", "like", f"%{txt}%"]] if txt else []
	or_filters = [["title", "like", f"%{txt}%"]] if txt else []
	pages = frappe.get_all(
		"Page", filters=None if or_filters else filters, or_filters=filters + or_filters, pluck="name"
	)
	return [[name] for name in sorted(pages) if frappe.get_cached_doc("Page", name).is_permitted()]


_SEARCHES = {"DocType": _search_doctypes, "Page": _search_pages}


@frappe.whitelist()
@validate_and_sanitize_search_inputs
def search_targets(
	doctype: str,
	txt: str,
	searchfield: str | None = None,
	start: int = 0,
	page_len: int = 10,
	filters: dict | list | str | None = None,
) -> list[list[str]]:
	"""Link query for `link_to` of an EasyNav Item: only what the session user is allowed to open.

	Normal users cannot search Pages at all, and the standard DocType search lists every
	DocType whether or not the user can read it.
	"""
	if doctype not in _SEARCHES:
		return []

	results = _SEARCHES[doctype]((txt or "").strip())
	return results[start : start + page_len]
