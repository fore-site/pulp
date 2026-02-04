from django.contrib.auth import get_user_model
from django.test import TestCase

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
