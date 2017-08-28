from django import template
register = template.Library()


@register.filter
def lindex(List, i):
    return List[int(i)]
