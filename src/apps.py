from django.apps import AppConfig
import decimal

class SrcConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'src'

    def ready(self):
        """Set default rounding in decimal.quantize() method to ROUND_HALF_UP"""
        context = decimal.getcontext()
        context.rounding = decimal.ROUND_HALF_UP
        decimal.DefaultContext.rounding = decimal.ROUND_HALF_UP