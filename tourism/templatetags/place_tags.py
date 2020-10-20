from django import template
from tourism.models import  Place, PointOfInterest, ZoneOfInterest
register = template.Library()

@register.filter
def is_poi(place):
    try:
        place.pointofinterest
        return True
    except Place.pointofinterest.RelatedObjectDoesNotExist:
        return False

@register.filter
def is_zoi(place):
    try:
        place.zoneofinterest
        return True
    except Place.zoneofinterest.RelatedObjectDoesNotExist:
        return False