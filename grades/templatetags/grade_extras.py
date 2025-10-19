from django import template
import jdatetime

from datetime import date as _date

register = template.Library()

@register.filter
def dict_get(d, key):
    """
    Custom template filter for safely getting a value from a dictionary.
    Usage in template:
        {{ mydict|dict_get:mykey }}
    """
    if isinstance(d, dict):
        return d.get(key, None)
    return None


@register.filter
def get_item(d, key):
    """Alias for dict_get to support templates that use `get_item`."""
    return dict_get(d, key)


@register.filter
def jalali(d):
    """Return a Jalali string YYYY/MM/DD if the object has date_jalali, otherwise format a date object as ISO."""
    if not d:
        return ''
    # if it's a model instance with attribute date_jalali
    if hasattr(d, 'date_jalali') and d.date_jalali:
        return d.date_jalali
    # if it's a date object
    if isinstance(d, _date):
        try:
            jd = jdatetime.date.fromgregorian(date=d)
            return f"{jd.year:04d}/{jd.month:02d}/{jd.day:02d}"
        except Exception:
            return d.isoformat()
    # otherwise fallback to str
    return str(d)
