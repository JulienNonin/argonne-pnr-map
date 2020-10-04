from django.urls import path

from . import views

app_name = 'tourism'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('get/ajax/poi', views.detail, name='poi_detail'),
    path('get/ajax/lazy', views.visible_poi, name='poi_load'),
    path('get/ajax/best', views.best_poi, name='best_results_load'),
    path('communes', views.CommuneView.as_view(), name='commune'),
    path('get/admin/subcategory', views.admin_get_subcategory, name='admin_get_subcategory'),
]
