from .models import Order

class PaymentStateSyncMiddleware:
    """ Middleware to synchronize payment state between the session and the database after webhook is hit"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        
        # Logic before the view
        if not request.session.get("is_payment_processing", False):
            return self.get_response(request)
        
        user = request.user if request.user.is_authenticated else None
        session_id = request.session.session_key
        
        order = Order.objects.filter(
            user=user,
            session_id=session_id,
            order_status="pending"
        ).order_by("-created_at").first()

        if not order:
            request.session["is_payment_processing"] = False
            request.session["item_count"] = 0

        response = self.get_response(request)

        return response