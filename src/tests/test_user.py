from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.cache import cache
from django.test import Client

class UserManagerTest(TestCase):

    def test_create_user(self):
        User = get_user_model()
        user = User.objects.create_user(email='testuser@gmail.com', password='testpass')
        self.assertEqual(user.email, 'testuser@gmail.com')
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        
        with self.assertRaises(AttributeError):
            user.username
        with self.assertRaises(TypeError):
            User.objects.create_user()
        with self.assertRaises(TypeError):
            User.objects.create_user(email='')
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='test')

    def test_create_superuser(self):
        User = get_user_model()
        user = User.objects.create_superuser(email='testsuper@gmail.com', password='superpass')
        self.assertEqual(user.email, 'testsuper@gmail.com')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_superuser)

        with self.assertRaises(AttributeError):
            user.username
        with self.assertRaises(TypeError):
            User.objects.create_superuser()
        with self.assertRaises(TypeError):
            User.objects.create_superuser(email='')
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email='', password='testing')

    def test_user_perms(self):
        User = get_user_model()
        user = User.objects.create_superuser(email='test@gmail.com',password='Gogoanime')
        self.assertTrue(user.has_perm('src.view_book'))

class RateLimitTestCase(TestCase):
    def setUp(self):
        User = get_user_model()
        # Clear the cache before each test to ensure a clean state
        cache.clear()
        # Create a test user
        self.user = User.objects.create_user(email='testuser', password='testpass')
        self.client = Client()
        self.login_url = reverse('login')

    @override_settings(RATELIMIT_ENABLE=True)
    def test_login_rate_limit(self):
        # Simulate 3 failed login attempts
        for i in range(3):
            response = self.client.post(self.login_url, {
                'username': 'wronguser', 
                'password': 'wrongpass'
            })
            self.assertEqual(response.status_code, 200) # Or 401, depending on your setup

        # The 4th attempt from the same IP should be blocked with a 429
        response = self.client.post(self.login_url, {
            'username': 'wronguser', 
            'password': 'wrongpass'
        })
        self.assertEqual(response.status_code, 403)