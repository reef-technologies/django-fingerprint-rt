from django import template

from ..models import RequestFingerprint

register = template.Library()


@register.simple_tag
def hit_count(url: str) -> int:
    return RequestFingerprint.get_count_for_urls([url])[url]
