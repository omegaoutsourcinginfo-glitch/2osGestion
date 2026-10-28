from django import template
from django.contrib.admin.views.main import PAGE_VAR

register = template.Library()


@register.simple_tag
def changelist_page_url(cl, page):
    """Build a changelist URL for a given page number, keeping filters."""
    return cl.get_query_string({PAGE_VAR: page})
