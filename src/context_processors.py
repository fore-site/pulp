from .forms import SearchBarForm

def search_form(request):
    return {
        'search_bar_form': SearchBarForm()
    }