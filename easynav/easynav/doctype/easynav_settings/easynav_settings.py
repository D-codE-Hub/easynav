# Copyright (c) 2026, D-codE and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from easynav.easynav.validation import get_item_error


class EasyNavSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from easynav.easynav.doctype.easynav_item.easynav_item import EasyNavItem

		button_icon: DF.Icon | None
		button_label: DF.Data | None
		enabled: DF.Check
		items: DF.Table[EasyNavItem]
		position: DF.Literal["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
	# end: auto-generated types

	def validate(self):
		for item in self.items:
			if error := get_item_error(item):
				frappe.throw(_("Row #{0}: {1}").format(item.idx, error), title=_("Invalid Navigation Item"))

	def on_update(self):
		frappe.clear_cache()
