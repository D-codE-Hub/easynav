import frappe
from frappe.tests import IntegrationTestCase

from easynav.api.navigation import build_navigation


class TestEasyNavSettings(IntegrationTestCase):
	"""EasyNav Settings only holds the site-wide options; the items belong to each user."""

	def setUp(self):
		frappe.set_user("Administrator")
		self.settings = frappe.get_doc("EasyNav Settings")

	def test_has_no_items_table(self):
		self.assertFalse(frappe.get_meta("EasyNav Settings").get_table_fields())

	def test_disabled_switches_the_menu_off_for_everyone(self):
		self.settings.enabled = 0
		self.settings.save()
		self.assertEqual(
			build_navigation(), {"enabled": False, "position": "bottom-right", "button": {}, "items": []}
		)

	def test_button_options_are_site_wide(self):
		self.settings.update(
			{"enabled": 1, "position": "Top Left", "button_label": "Go", "button_icon": "star"}
		)
		self.settings.save()
		data = build_navigation()
		self.assertEqual(data["position"], "top-left")
		self.assertEqual(data["button"], {"label": "Go", "icon": "star"})
