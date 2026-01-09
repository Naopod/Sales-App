"""
Custom template tags and filters
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get item from dictionary by key
    Usage: {{ mydict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def intcomma(value):
    """
    Format number with comma thousands separator
    Usage: {{ value|intcomma }}
    """
    try:
        return "{:,}".format(int(value))
    except (ValueError, TypeError):
        return value
