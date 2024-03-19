from django.template import Library
from wagtail.models import Site
from django.conf import settings

def is_absolute_url(url):
    if url.startswith("http"):
        return True
    split = url.split("/")
    if len(split) > 1 and split[0] == "":
        return False
    if len(split) > 2 and "." in split[0]:
        return True
    return False

static_url = getattr(settings, "STATIC_URL", "")
is_absolute_static_url = static_url.startswith("http") or is_absolute_url(static_url)

register = Library()

@register.simple_tag(takes_context=True)
def absolute_static(context, path):
    request = context.get("request")
    site = context.get("site")
    if is_absolute_static_url:
        return static_url + path
    if request:
        return f"{request.scheme}://{request.get_host()}{static_url}{path}"
    if not site:
        site = Site.objects.get(is_default_site=True)
    return f"{site.root_url}{static_url}{path}"