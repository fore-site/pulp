from .models import Order, Cart, CartItem

class SyncSessionMiddleware:
    """Middleware to store session key if user is a guest for future cart sync upon login"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # If guest, Save session key 
        if not request.user.is_authenticated and request.session.session_key:
            if not request.session.get('old_session_key'):
                request.session['old_session_key'] = request.session.session_key
        return self.get_response(request)

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
            payment_status__iexact="Processing"
        ).order_by("-created_at").first() if user else Order.objects.filter(
            session_id=session_id,
            payment_status__iexact="Processing"
        ).order_by("-created_at").first()
        
        try:
            if user:
                cart = Cart.objects.get(user=user)
            else:
                cart = Cart.objects.get(session_id=session_id)
        except Cart.DoesNotExist:
            cart = None

        cart_items = CartItem.objects.filter(cart=cart)

        if not order:
            request.session["is_payment_processing"] = False
        if not cart_items:
            request.session["item_count"] = 0

        response = self.get_response(request)

        return response