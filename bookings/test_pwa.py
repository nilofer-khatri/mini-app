from django.test import TestCase


class PwaTests(TestCase):
    def test_manifest_describes_the_app(self):
        response = self.client.get("/manifest.webmanifest")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "SalonSlotly")
        self.assertEqual(data["display"], "standalone")
        self.assertGreaterEqual(len(data["icons"]), 2)

    def test_service_worker_is_served_from_the_root(self):
        response = self.client.get("/sw.js")
        self.assertEqual(response.status_code, 200)
        self.assertIn("javascript", response["Content-Type"])
        self.assertEqual(response["Service-Worker-Allowed"], "/")

    def test_offline_page_loads(self):
        self.assertEqual(self.client.get("/offline/").status_code, 200)