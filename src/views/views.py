from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from django.contrib.auth import login
from django.contrib import messages
from src.models import Series, Sku, Book, BookEvent, Genre, Category, Cart, CartItem
from ..forms import CustomUserCreationForm, CartUpdateForm
from django.db.models import Q, Subquery, OuterRef, F
from django.template.loader import render_to_string
from django_htmx.middleware import HtmxDetails
from ..utils.common import FilterSort, base_book_queryset, get_user_and_session, get_cart, get_cart_items_and_forms, store_price_and_count
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from datetime import timedelta

class HtmxHttpRequest(HttpRequest):
    htmx: HtmxDetails

# Create your views here.

class IndexView(generic.TemplateView):
    template_name = 'src/index.html'
    seven_days = timezone.now().replace(hour=0, minute=0, microsecond=0) - timedelta(days=7)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        base_queryset = base_book_queryset(Sku)
        
        manga = (base_queryset.filter(book__is_featured=True, book__series__category__name='manga', published_at__gte=self.seven_days)
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        comic = (base_queryset.filter(book__is_featured=True, book__series__category__name='comic', published_at__gte=self.seven_days)
                 .order_by('book__series', '-published_at', 'price_usd')
                 .distinct('book__series'))
        hot_deals = base_queryset.filter(book__is_featured=True, discount_percent__gt=0).order_by('-discount_percent')[:10]

        trending = (base_queryset.filter(book__trending_score__gt=0).order_by('book', 'book__trending_score').distinct('book')[:10]
                     )
        
        comic_bestselling = (base_queryset
                              .filter(book__series__category__name='comic', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

        manga_bestselling = (base_queryset
                              .filter(book__series__category__name='manga', book__bestseller_score__gt=0)
                              .order_by('book', 'book__bestseller_score').distinct('book')[:10])

        context['new_manga_release'] = manga
        context['new_comic_release'] = comic
        context['trending'] = trending
        context['hot_deals'] = hot_deals
        context['comic_bestselling'] = comic_bestselling
        context['manga_bestselling'] = manga_bestselling

        return context

class BookListView(generic.ListView):
    model = Sku
    template_name = 'src/book_list.html'
    context_object_name = 'books'

    def get_queryset(self):
        self.category = get_object_or_404(Category, name__iexact=self.kwargs.get('category'))

        # Fetch filters and sort params 
        genre_filters = self.request.GET.getlist('g')
        featured = self.request.GET.get('featured')
        format = self.request.GET.get('f')
        sort_by = self.request.GET.get('sort')
        latest_release = self.request.GET.get('r')

        # Create a distinct queryset, one sku per book
        distinct_skus = (Sku.objects.filter(book__series__category=self.category)
        .distinct('book')
        .annotate(distinct_id=Subquery(
            Sku.objects.filter(book=OuterRef('book')).order_by('price_usd')
            .values('id')[:1]
        )).values_list('distinct_id', flat=True))

        # Create a base queryset
        books = base_book_queryset(Sku).filter(id__in=distinct_skus).order_by('book__title')
        
        # Filter and sort Skus if params exist
        filter_sort = FilterSort(books, sort_by, format, featured, genre_filters, latest_release)
        books = filter_sort.filter_skus()

        if self.request.htmx:
            self.template_name = "partials/book_card.html"
    
        return books
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        genres = Genre.objects.filter(categories__name=self.category.name)

        context['category'] = self.category.name.capitalize()
        context['genres'] = genres
        context['selected_genres'] = [int(g) for g in self.request.GET.getlist('g')]
        context['formats'] = ['hardcover', 'paperback', 'digital']
        context['selected_format'] = self.request.GET.get('f')
        context['selected_sort'] = self.request.GET.get('sort')
        context['latest_release'] = self.request.GET.get('r')

        return context
               
class ProductDetailView(generic.DetailView):
    model = Sku
    template_name = 'src/product_detail.html'
    context_object_name = 'sku'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        selected_format = self.request.GET.get('f', 'digital')
        public_id = self.kwargs.get('uuid')

        default_format_sku = Sku.objects.filter(format=selected_format.capitalize(), public_id=public_id, is_discontinued=False, book__is_deleted=False).select_related('book__series').get()
        BookEvent.objects.create(sku=default_format_sku, event_type='view')

        context['format'] = selected_format
        context['default_sku'] = default_format_sku

        return context

class SeriesIndexView(generic.ListView):
    model = Series
    context_object_name = 'series_list'
    template_name = 'src/series_index.html'

    def get_queryset(self):
        series_type = self.kwargs.get('series_type')
        category = get_object_or_404(Category, name__iexact=series_type)
        series = (Series.objects.filter(category=category))
        return series
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = self.kwargs.get('series_type').capitalize()
        return context

class SeriesDetailView(generic.TemplateView):
    template_name = 'src/series_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        series = get_object_or_404(Series, public_id=self.kwargs.get('uuid'))
        sku_list = Sku.objects.filter(book__series=series, is_discontinued=False, book__is_deleted=False, book__series__is_deleted=False).order_by('book', 'book__series__title').distinct('book')
        book_count = Book.objects.filter(series=series, sku__is_discontinued=False, is_deleted=False, series__is_deleted=False).count()

        context['sku_list'] = sku_list
        context['book_count'] = book_count
        context['series'] = series

        return context

@require_GET
def search_results_view(request):  
    query = request.GET.get('q')
    base_queryset = base_book_queryset(Sku)

    try:
        results = (base_queryset
                   .filter(Q(book__title__icontains=query) | Q(book__authors__name__icontains=query) | Q(isbn_number__icontains=query))
                   .distinct('book'))
    except Sku.DoesNotExist:
        return render(request, 'src/search_results.html', {"results": None, "query": query})
    else:
        return render(request, 'src/search_results.html', {"results": results, "query": query})

@require_http_methods(['GET', 'POST'])
def signup(request):
    if request.POST:
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=True)
            login(request, user)
            return HttpResponseRedirect(reverse('home'))
        else:
            return render(request, 'src/signup.html', {"form": form})
    else:
        form = CustomUserCreationForm()
        return render(request, 'src/signup.html', {"form": form})

class HotDealsView(generic.TemplateView):
    template_name = 'src/deals.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_queryset = base_book_queryset(Sku)

        manga_deals = base_queryset.filter(book__series__category__name='manga', discount_percent__gte=50).order_by('discount_percent')
        comic_deals = base_queryset.filter(book__series__category__name='comic', discount_percent__gte=50).order_by('discount_percent')

        context['manga_deals'] = manga_deals
        context['comic_deals'] = comic_deals
        return context

class CartView(generic.TemplateView):
    template_name = 'src/cart.html'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get user object if authenticated, create session instance as well
        user = self.request.user if self.request.user.is_authenticated else None
        if not self.request.session.session_key:
            self.request.session.create()
        session_id = self.request.session.session_key

        context['cart_items_and_forms'] = get_cart_items_and_forms(user, session_id)
        return context
    
    def post(self, request, **kwargs):
        # Get user object if authenticated, create session instance as well
        user, session_id = get_user_and_session(request)

        # Get cart related to user or session_id, create cart if it doesn't exist
        cart = get_cart(user, session_id)

        # Get and validate form data
        sku_id = request.POST.get('sku_id')
        sku = get_object_or_404(Sku, id=sku_id)
        
        # Create or update cart item table
        updated = CartItem.objects.filter(
            sku=sku,
            cart=cart).update(quantity=F('quantity') + 1)
        
        if not updated:
            CartItem.objects.create(sku=sku, cart=cart, quantity=1)

        # Get total item count in a cart and store it in user session
        store_price_and_count(request, cart)

        next_url = request.POST.get('next') or request.META.get('HTTP_REFERER')
        if next_url:
            next_url = next_url.strip()

        # validate the next parameter and ensure user has not tampered with it
        is_safe = url_has_allowed_host_and_scheme(
            url=next_url,
            allowed_hosts=request.get_host(),
            require_https=False
        )
        if request.htmx:
            return HttpResponse(request.session['item_count'])

        if next_url and is_safe:
            return redirect(next_url)
        return redirect('home')

@require_POST
def update_and_delete_cart(request: HtmxHttpRequest):
    """View to update cart contents or clear cart"""

    user, session_id = get_user_and_session(request)
    cart = get_cart(user, session_id)

    action = request.POST.get('action')
    sku_id = request.POST.get('sku_id')
    if sku_id:
        sku = get_object_or_404(Sku, id=sku_id)
    
    form = CartUpdateForm({'quantity': request.POST.get('quantity')})
    if action == 'clear':
        CartItem.objects.filter(cart=cart).delete()
    elif form.is_valid():
        quantity = int(form.cleaned_data.get('quantity'))
        if action == 'add':
            new_qty = quantity + 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        elif action == 'subtract':
            new_qty = quantity - 1
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=new_qty)
        elif action == 'delete':
            CartItem.objects.filter(sku=sku, cart=cart).delete()
        else:
            CartItem.objects.filter(sku=sku, cart=cart).update(quantity=quantity)
    else:
        pass
    
    # Get total item count in a cart and store it in user session
    store_price_and_count(request, cart)

    if request.htmx and action != 'delete':
        context = {"cart_items_and_forms": get_cart_items_and_forms(user, session_id)}
        cart_main_target = render(request, 'src/cart.html#cart_items', context).content.decode()
        cart_count_oob = f'<span id="cart-count" hx-swap-oob="true">{request.session['item_count']}</span>'
        return HttpResponse(cart_main_target + cart_count_oob)
        # return render(request, 'src/cart.html#cart_items', context)
    elif request.htmx and action == 'delete':
        response = HttpResponse()
        response['HX-Redirect'] = reverse('cart')
        return response
    return redirect('cart')

class OrderCheckoutView(generic.FormView):
    pass

def order_checkout(request, id):
    return HttpResponse('You have placed an order on %s.' % id)
