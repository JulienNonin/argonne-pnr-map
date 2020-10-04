from django.core import serializers
from django.http import JsonResponse, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render
from django.views.generic import ListView

from django.contrib.gis.geos import Polygon
from django.contrib.gis.db import models
from django.db.models import Case, Count, Exists, F, OuterRef, Value, When


from .models import Category, Commune, OpeningPeriod, OpeningHours, PointOfInterest, SubCategory, Variable
from . import utils

import datetime
import json

class IndexView(ListView):
    template_name = 'tourism/index.html'
    context_object_name = 'category_list'

    def get_queryset(self):
        return Category.objects.order_by('order')

# def detail(request):
#     # return JsonResponse({"error": False}, status=200)
#     if request.is_ajax and request.method == "GET":
#         poi_id = request.GET.get("poi_id", None)
#         try:
#             poi = get_object_or_404(PointOfInterest, pk=poi_id)
#             poi_json = serializers.serialize('json', [poi, ])
#             return JsonResponse({"instance": poi_json}, status=200)
#         except PointOfInterest.DoesNotExist:
#             return JsonResponse({}, status=400)
#     return JsonResponse({}, status=400)

def ajax_get_view(view_function):
    def wrapper(request):
        if request.is_ajax and request.method == "GET":
            return view_function(request)
        else:
            return HttpResponseNotAllowed(('GET',))
    return wrapper

@ajax_get_view
def admin_get_subcategory(request):
    id = request.GET.get('id', '')
    subcategories = SubCategory.objects.filter(
        category_id=int(id)
        ).values('id', 'name')
    return JsonResponse({"subcategories": list(subcategories)}, status=200)
    # return HttpResponse(json.dumps(result), content_type="application/json")


@ajax_get_view
def detail(request):
    poi_id = request.GET.get("poi_id", None)
    poi = get_object_or_404(PointOfInterest, pk=poi_id)

    if date_start_str := request.GET.get("date-from", None):
        date_start = datetime.datetime.strptime(date_start_str, '%Y-%m-%d').date()
        date_end = datetime.datetime.strptime(
            request.GET.get("date-to", "9999-12-31"), '%Y-%m-%d'
        ).date()
        opening_schema = OpeningPeriod.objects.filter(
            place=poi,
            valid_from__lte=date_end,
            valid_through__gte=date_start,
            # openingperiod__openinghours__weekday__in = utils.get_isoweekdays_btw_dates(date_start, date_end),
        ).first()
        content = {
            'poi': poi,
            'requested_opening_schema': opening_schema
        }

    else: # get current opening_schema
        opening_schema = OpeningPeriod.objects.filter(
            place=poi,
            valid_from__lte=datetime.date.today(),
            valid_through__gte=datetime.date.today()).first()
        content = {
            'poi': poi,
            'current_opening_schema': opening_schema
        }
    return render(request, 'tourism/index/_detail.html', content)

@ajax_get_view
def visible_poi(request):
    DAYS_XN = Variable.objects.get_or_create(name="XN", defaults={'value':10})[0].value
    DAYS_XP = Variable.objects.get_or_create(name="XP", defaults={'value':3})[0].value
    # Retrieve data
    categories = json.loads(request.GET.get("categories", None))
    name = json.loads(request.GET.get("name", None))

    # Retrieve dates
    date_start = datetime.datetime.strptime(
        request.GET.get("date-from", "2000-1-1"),
        '%Y-%m-%d'
    ).date()
    date_end = datetime.datetime.strptime(
        request.GET.get("date-to", "3000-12-31"),
        '%Y-%m-%d'
    ).date()

    if date_end < date_start:
        return render(
            request,
            'tourism/index/_poi_loader.html',
            {"error": f"La date de fin doit être supérieure à {date_start}."}
        )
    # Retrieve bounds
    # bounds = request.GET.get("bounds", None)
    # bounds_old = request.GET.get("boundsOld", None)  # not set if no move
    # geom_new = utils.to_geom(bounds)  # current zone (after zoom/drag)
    # geom_old = utils.to_geom(bounds_old)  # previous zone (bedore zoom/drag)
    # geom = geom_new - geom_old # new POis are inside this geometry

    # Query
    date_end_later = date_end + datetime.timedelta(days=DAYS_XN)  # XN
    date_end_near = date_end + datetime.timedelta(days=DAYS_XP)  # XP
    openingperiod_later = OpeningPeriod.objects.filter(
        place=OuterRef('pk'),
        valid_from__lte=date_end_later,
        valid_through__gte=date_start,
        openinghours__weekday__in=utils.get_isoweekdays_btw_dates(date_start, date_end_later),
    )
    openingperiod_near = openingperiod_later.filter(
        valid_from__lte=date_end_near,
        openinghours__weekday__in=utils.get_isoweekdays_btw_dates(date_start, date_end_near),
    )
    openingperiod_now = openingperiod_near.filter(
        valid_from__lte=date_end,
        openinghours__weekday__in=utils.get_isoweekdays_btw_dates(date_start, date_end),
    )
    
    poi_list = PointOfInterest.objects.filter(
        # location__within=geom_new,
        category__tag__in=categories,
    ).annotate(
        num_opening_periods=Count('openingperiod'),
        opening_score=Case(
            When(is_always_open=True, then=Value(2)),
            When(Exists(openingperiod_now), then=Value(5)),
            When(Exists(openingperiod_near), then=Value(4)),
            When(Exists(openingperiod_later), then=Value(3)),
            When(num_opening_periods__gt=0, then=Value(1)),
            default=Value(0),
            output_field=models.PositiveSmallIntegerField(),
        ),
        # score=F('opening_score') + F('note_of_interest'),
    )

    if name:
        poi_by_commune_name = poi_list.filter(commune__name__icontains = name)
        poi_by_name = poi_list.filter(name__icontains = name)
        poi_list = poi_by_commune_name.union(poi_by_name)

    content = {
        'poi_list': poi_list.order_by('-opening_score'),
    }
    return render(request, 'tourism/index/_poi_loader.html', content)

@ajax_get_view
def best_poi(request):
    NI_P = Variable.objects.get_or_create(name="P", defaults={'value':3/5})[0].value
    POI_BY_PAGE = 10
    ids = json.loads(request.GET.get("ids", "[]"))
    whens = [When(pk=id, then=opening_score) for id, opening_score in ids.items()]
    page = int(request.GET.get("page", 0))

    # best_results = PointOfInterest.objects.filter(pk__in = ids).order_by('name')[page*POI_BY_PAGE : (page+1)*POI_BY_PAGE]
    best_results = PointOfInterest.objects.filter(pk__in=ids.keys()).annotate(
        opening_score=Case(
            *whens,
            default=0,
            output_field=models.PositiveSmallIntegerField(),
        ),
        score= 2 * NI_P * F('note_of_interest') + 2 * (1 - NI_P) * F('opening_score'),
    ).order_by('-score')[page*POI_BY_PAGE : (page+1)*POI_BY_PAGE]

    content = {
        'poi_list': best_results,
        # 'debug': ids
    }
    return render(request, 'tourism/index/_best_results.html', content)

# == DEBUG COMMUNE ==
class CommuneView(ListView):
    template_name = 'tourism/commune.html'
    context_object_name = 'commune_list'

    def get_queryset(self):
        return Commune.objects.all()