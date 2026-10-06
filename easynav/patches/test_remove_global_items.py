import frappe
from frappe.tests import IntegrationTestCase

from easynav.patches.remove_global_items import execute

USER_NAVIGATION = "EasyNav User Navigation"


class TestRemoveGlobalItems(IntegrationTestCase):
	def test_deletes_only_the_old_site_wide_items(self):
		for label in ("Global 1", "Global 2"):
			frappe.get_doc(
				{
					"doctype": "EasyNav Item",
					"parent": "EasyNav Settings",
					"parenttype": "EasyNav Settings",
					"parentfield": "items",
					"label": label,
					"type": "URL",
					"url": "https://example.com",
				}
			).db_insert()

		frappe.delete_doc(USER_NAVIGATION, "Administrator", ignore_missing=True)
		frappe.get_doc(
			{
				"doctype": USER_NAVIGATION,
				"user": "Administrator",
				"items": [{"label": "Mine", "type": "URL", "url": "https://example.com"}],
			}
		).insert()

		# running twice must be harmless
		execute()
		execute()

		self.assertEqual(frappe.db.count("EasyNav Item", {"parenttype": "EasyNav Settings"}), 0)
		labels = [row.label for row in frappe.get_doc(USER_NAVIGATION, "Administrator").items]
		self.assertEqual(labels, ["Mine"])
