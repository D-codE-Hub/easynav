import frappe

from easynav.api.navigation import build_navigation


def extend_bootinfo(bootinfo):
	if frappe.session.user == "Guest":
		return

	try:
		bootinfo["easynav"] = build_navigation()
	except Exception:
		# never break Desk boot because of a navigation problem
		frappe.log_error(title="EasyNav: failed to build navigation")
