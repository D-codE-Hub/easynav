# Copyright (c) 2026, D-codE and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class EasyNavItem(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		enabled: DF.Check
		icon: DF.Data | None
		label: DF.Data | None
		link_to: DF.DynamicLink | None
		open_in_new_tab: DF.Check
		order: DF.Int
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		type: DF.Literal["DocType", "Page", "Report", "Dashboard", "URL"]
		url: DF.Data | None
	# end: auto-generated types

	pass
