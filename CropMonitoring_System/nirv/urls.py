from django.urls import path
from . import views

urlpatterns = [
    path("", views.nirv_map, name="nirv_map"),
    path("multi/", views.nirv_map_multi, name="nirv_map_multi"),

    path("api/graph/", views.graph_data, name="nirv_graph_data"),
    path("api/years/", views.available_years, name="nirv_available_years"),
    path("api/states/", views.available_states, name="nirv_available_states"),
    path("api/multi-graph/", views.multi_graph_data, name="nirv_multi_graph_data"),

]



