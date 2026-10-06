# Copyright (c) 2026, D-codE and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.rename_doc import rename_doc

from easynav.easynav.validation import MAX_ITEMS, get_item_error

DOCTYPE = "EasyNav User Navigation"


class EasyNavUserNavigation(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from easynav.easynav.doctype.easynav_item.easynav_item import EasyNavItem

		items: DF.Table[EasyNavItem]
		user: DF.Link
	# end: auto-generated types

	def validate(self):
		# a user may only create and edit their own list; support users may do so for anyone.
		# does not rely on the permission hooks: holds even for code that saves with ignore_permissions
		if self.user != frappe.session.user and not _is_support_user(frappe.session.user):
			frappe.throw(_("You can only edit your own shortcuts"), frappe.PermissionError)

		if len(self.items) > MAX_ITEMS:
			frappe.throw(_("You can add at most {0} navigation items").format(MAX_ITEMS))

		for item in self.items:
			if not item.enabled:
				continue
			if error := get_item_error(item):
				frappe.throw(_("Row #{0}: {1}").format(item.idx, error), title=_("Invalid Navigation Item"))

	def on_update(self):
		self.clear_boot_cache()

	def on_trash(self):
		self.clear_boot_cache()

	def clear_boot_cache(self):
		# the menu is delivered in the owner's cached bootinfo, whoever made the change
		frappe.cache.hdel("bootinfo", self.user)


def _is_support_user(user: str) -> bool:
	"""Administrator and System Managers may view and fix any user's shortcuts."""
	return user == "Administrator" or "System Manager" in frappe.get_roles(user)


def has_permission(doc, ptype="read", user=None):
	user = user or frappe.session.user

	return doc.user == user or _is_support_user(user)


def get_permission_query_conditions(user):
	user = user or frappe.session.user
	if _is_support_user(user):
		return ""

	return f"(`tab{DOCTYPE}`.name = {frappe.db.escape(user)})"


def delete_user_navigation(doc, method=None):
	"""User `on_trash`: the Link to the user would otherwise block deleting it."""
	frappe.delete_doc(DOCTYPE, doc.name, ignore_permissions=True, ignore_missing=True)


def rename_user_navigation(doc, method=None, old=None, new=None, merge=False):
	"""User `after_rename`: the document is named after its user, so it follows the rename."""
	if not frappe.db.exists(DOCTYPE, old):
		return

	if frappe.db.exists(DOCTYPE, new):
		# users were merged: the surviving user keeps their own shortcuts
		frappe.delete_doc(DOCTYPE, old, ignore_permissions=True)
	else:
		rename_doc(DOCTYPE, old, new, force=True, ignore_permissions=True, show_alert=False)
