from django.contrib.auth import get_user_model
from django.test import Client, TestCase


class AutentikasiTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="admin_uji", password="uji12345")
        self.client = Client()

    def test_logout_get_tidak_diizinkan(self):
        self.client.force_login(self.user)
        response = self.client.get("/logout/")
        self.assertEqual(response.status_code, 405)

    def test_logout_post_berhasil(self):
        self.client.force_login(self.user)
        response = self.client.post("/logout/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/login/")
        response_beranda = self.client.get("/")
        self.assertEqual(response_beranda.status_code, 302)
        self.assertIn("/login/", response_beranda.url)

    def test_halaman_utama_memuat_form_logout_post(self):
        self.client.force_login(self.user)
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/logout/"')
        self.assertContains(response, 'method="post"')
        self.assertContains(response, "csrfmiddlewaretoken")
