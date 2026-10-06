import frappe
from frappe import _

from easynav.easynav.validation import get_item_error, get_item_target, is_safe_url

POSITIONS = {
	"Bottom Right": "bottom-right",
	"Bottom Left": "bottom-left",
	"Top Right": "top-right",
	"Top Left": "top-left",
}
DEFAULT_ICON = "menu"
USER_NAVIGATION = "EasyNav User Navigation"
UNORDERED = 10**9


def _slug(name: str) -> str:
	return frappe.scrub(name).replace("_", "-")


# DocType View -> route parts after ["List", doctype]; the URL uses the same parts in lower case
_LIST_VIEWS = {
	"List": ["List"],
	"Report Builder": ["Report"],
	"Dashboard": ["Dashboard"],
	"Calendar": ["Calendar", "default"],
	"Kanban": ["Kanban"],
	"Image": ["Image"],
}
# permission needed to open a view, when it is more than read
_VIEW_PERMISSIONS = {"New": "create", "Report Builder": "report"}


def _resolve_doctype(item) -> dict | None:
	target = item.link_to.strip()
	if not frappe.has_permission(target, "read"):
		return None

	slug = _slug(target)
	if frappe.get_meta(target).issingle:
		return {"route": ["Form", target], "path": f"/app/{slug}"}

	doc_view = item.doc_view or ""
	if doc_view in _VIEW_PERMISSIONS and not frappe.has_permission(target, _VIEW_PERMISSIONS[doc_view]):
		return None

	if doc_view == "New":
		return {"route": [slug, "new"], "path": f"/app/{slug}/new"}
	if doc_view == "Tree":
		return {"route": ["Tree", target], "path": f"/app/{slug}/view/tree"}
	if doc_view in _LIST_VIEWS:
		parts = _LIST_VIEWS[doc_view]
		route, path = ["List", target, *parts], f"/app/{slug}/view/{'/'.join(parts).lower()}"
		if doc_view == "Kanban" and item.kanban_board:
			route.append(item.kanban_board)
			path += f"/{item.kanban_board}"
		return {"route": route, "path": path}

	return {"route": ["List", target], "path": f"/app/{slug}"}


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


def _resolve_dashboard(target: str) -> dict | None:
	if not frappe.has_permission("Dashboard", "read", doc=target):
		return None

	return {"route": ["dashboard-view", target], "path": f"/app/dashboard-view/{target}"}


_RESOLVERS = {
	"Page": _resolve_page,
	"Report": _resolve_report,
	"Dashboard": _resolve_dashboard,
}


def _resolve_item(item) -> dict | None:
	"""Return the frontend payload for one item, or None if it is invalid or not permitted."""
	if not item.enabled:
		return None

	if error := get_item_error(item):
		# one bad item must never break the menu; leave a trace for administrators
		frappe.logger("easynav").warning(f"Skipping navigation item #{item.idx} ({item.label}): {error}")
		return None

	target = get_item_target(item)
	if item.type == "URL":
		if not is_safe_url(target):
			return None
		resolved = {"url": target}
	else:
		resolved = _resolve_doctype(item) if item.type == "DocType" else _RESOLVERS[item.type](target)
		if resolved is None:
			return None

	return {
		"label": item.label.strip(),
		"icon": (item.icon or "").strip() or None,
		"type": item.type,
		"open_in_new_tab": bool(item.open_in_new_tab),
		**resolved,
	}


def _get_user_rows(user: str) -> list:
	"""Return the navigation items the user configured for themselves."""
	if not frappe.db.exists(USER_NAVIGATION, user):
		return []

	return frappe.get_cached_doc(USER_NAVIGATION, user).items


def build_navigation() -> dict:
	"""Build the navigation payload for the session user.

	The site-wide settings are read without a permission check on purpose: normal users cannot
	read EasyNav Settings, but they should get the menu. The items always come from the session
	user's own EasyNav User Navigation, and only the ones the user is allowed to open are
	included, so nothing is exposed that they could not reach through Frappe itself.
	"""
	user = frappe.session.user
	empty = {"enabled": False, "position": "bottom-right", "button": {}, "items": []}

	if not user or user == "Guest":
		return empty

	settings = frappe.get_cached_doc("EasyNav Settings")
	if not settings.enabled:
		return empty

	rows = sorted(_get_user_rows(user), key=lambda row: (row.order or UNORDERED, row.idx))

	items = [item for row in rows if (item := _resolve_item(row))]

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


@frappe.whitelist(methods=["POST"])
def get_user_navigation() -> str:
	"""Return the name of the session user's EasyNav User Navigation, creating it on first use."""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Log in to edit your shortcuts"), frappe.PermissionError)

	# users have no create permission: this is the only way a document comes to exist
	if not frappe.db.exists(USER_NAVIGATION, user):
		frappe.get_doc({"doctype": USER_NAVIGATION, "user": user}).insert(ignore_permissions=True)

	return user
