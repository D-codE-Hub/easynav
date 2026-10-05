import frappe

from easynav.easynav.validation import get_item_error, is_safe_url

POSITIONS = {
	"Bottom Right": "bottom-right",
	"Bottom Left": "bottom-left",
	"Top Right": "top-right",
	"Top Left": "top-left",
}
DEFAULT_ICON = "menu"
UNORDERED = 10**9


def _slug(name: str) -> str:
	return frappe.scrub(name).replace("_", "-")


def _resolve_doctype(target: str) -> dict | None:
	if not frappe.has_permission(target, "read"):
		return None

	if frappe.get_meta(target).issingle:
		return {"route": ["Form", target], "path": f"/app/{_slug(target)}"}

	return {"route": ["List", target], "path": f"/app/{_slug(target)}"}


def _resolve_page(target: str) -> dict | None:
	if not frappe.get_doc("Page", target).is_permitted():
		return None

	return {"route": [target], "path": f"/app/{target}"}


def _resolve_report(target: str) -> dict | None:
	report = frappe.get_doc("Report", target)
	if not report.is_permitted():
		return None

	if report.ref_doctype and not frappe.has_permission(report.ref_doctype, "report"):
		return None

	if report.report_type == "Report Builder":
		return {
			"route": ["List", report.ref_doctype, "Report", target],
			"path": f"/app/{_slug(report.ref_doctype)}/view/report/{target}",
		}

	return {"route": ["query-report", target], "path": f"/app/query-report/{target}"}


_RESOLVERS = {
	"DocType": _resolve_doctype,
	"Page": _resolve_page,
	"Report": _resolve_report,
}


def _resolve_item(item) -> dict | None:
	"""Return the frontend payload for one item, or None if it is invalid or not permitted."""
	if not item.enabled:
		return None

	if error := get_item_error(item):
		# one bad item must never break the menu; leave a trace for administrators
		frappe.logger("easynav").warning(f"Skipping navigation item #{item.idx} ({item.label}): {error}")
		return None

	target = item.target.strip()
	if item.type == "URL":
		if not is_safe_url(target):
			return None
		resolved = {"url": target}
	else:
		resolved = _RESOLVERS[item.type](target)
		if resolved is None:
			return None

	return {
		"label": item.label.strip(),
		"icon": (item.icon or "").strip() or None,
		"type": item.type,
		"target": target,
		"open_in_new_tab": bool(item.open_in_new_tab),
		**resolved,
	}


def build_navigation(user: str | None = None) -> dict:
	"""Build the navigation payload for `user` (default: session user).

	The settings are read without a permission check on purpose: normal users cannot read
	EasyNav Settings, but they should get the menu. Only items the user is allowed to open
	are included, so nothing is exposed that they could not reach through Frappe itself.
	"""
	user = user or frappe.session.user
	empty = {"enabled": False, "position": "bottom-right", "button": {}, "items": []}

	if not user or user == "Guest":
		return empty

	settings = frappe.get_cached_doc("EasyNav Settings")
	if not settings.enabled:
		return empty

	rows = sorted(settings.items, key=lambda row: (row.order or UNORDERED, row.idx))

	session_user = frappe.session.user
	try:
		if user != session_user:
			frappe.set_user(user)
		items = [item for row in rows if (item := _resolve_item(row))]
	finally:
		if user != session_user:
			frappe.set_user(session_user)

	return {
		"enabled": True,
		"position": POSITIONS.get(settings.position, "bottom-right"),
		"button": {
			"label": settings.button_label or "",
			"icon": settings.button_icon or DEFAULT_ICON,
		},
		"items": items,
	}


@frappe.whitelist()
def get_navigation() -> dict:
	return build_navigation()
