from django.contrib.auth.forms import AuthenticationForm
from django.contrib.admin import AdminSite
from django.contrib.gis import admin

import nested_admin

from .models import Category, MainRepresentation, OpeningHours, OpeningPeriod, PointOfInterest


class UserAdmin(AdminSite):
    site_header="Contribuer"
    login_form = AuthenticationForm

    def has_permission(self, request):
        return request.user.is_active

user_admin_site = UserAdmin(name="useradmin")

class OpeningHoursInline(nested_admin.NestedTabularInline):
    model = OpeningHours

class OpeningPeriodInline(nested_admin.NestedTabularInline):
    model = OpeningPeriod
    inlines = [OpeningHoursInline]
    extra = 0

class MainRepresentationInline(nested_admin.NestedTabularInline):
    model = MainRepresentation

class PointOfInterestUserAdmin(admin.OSMGeoAdmin, nested_admin.NestedModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(owner=request.user)

    list_display = ('name', 'commune')

    exclude = ['owner', 'dt_id', 'dt_categories', 'note_of_interest']

    fieldsets = (
        (None, {
            'fields': [
                'name',
                'description',
                'category',
                'subcategory',
                'location',
                ('street_address', 'commune'),
                ('email', 'phone', 'website')]
        }),
        ("Horaires d'ouverture", {
            # 'classes': ('collapse',),
            'fields': ('is_always_open',),
        }),
    )

    inlines = [OpeningPeriodInline, MainRepresentationInline]

    class Media:
        js = (
        '/static/admin/js/hide_opening_period.js',
        '/static/admin/js/subcategory.js',
    )

user_admin_site.register(PointOfInterest, PointOfInterestUserAdmin)