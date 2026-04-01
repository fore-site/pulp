from django import template

register = template.Library()

@register.inclusion_tag('partials/stars.html')
def to_stars(rating: float):
    """Turns average rating value to stars"""
    if rating > 5.0:
        raise template.TemplateSyntaxError("Average rating cannot exceed 5.0")

    # Split float value into a list of its individual figures e.g 2.3 to ['2','3']
    rating_split = f'{rating}'.split('.')
    
    # Populate a list with 'full' if the significant number is > 0, leave empty otherwise
    rating_list = ['full' for _ in range(int(rating_split[0]))]
    
    # Append 'half' if the number after the decimal is > 4
    if int(rating_split[1]) > 4:
        rating_list.append('half')

    # If the list is not fully populated after the above operations, append 'empty'
    while len(rating_list) < 5:
        rating_list.append('empty')
    
    return {"rating_list": rating_list, "average_rating": rating}

