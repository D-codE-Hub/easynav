# Copyright (c) 2026, D-codE and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EasyNavSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		button_icon: DF.Icon | None
		button_label: DF.Data | None
		enabled: DF.Check
		position: DF.Literal["Bottom Right", "Bottom Left", "Top Right", "Top Left"]
	# end: auto-generated types

	def on_update(self):
		frappe.clear_cache()
