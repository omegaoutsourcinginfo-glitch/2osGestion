from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path(
        "autocomplete/",
        views.project_search_autocomplete,
        name="search_autocomplete",
    ),
    path(
        "dashboard/",
        views.dashboard_home,
        name="dashboard_home",
    ),
    path(
        "dashboard/recent/",
        views.dashboard_recent,
        name="dashboard_recent",
    ),
    path(
        "<str:code>/fiche/",
        views.project_fiche,
        name="project_fiche",
    ),
    path(
        "<str:code>/onglet/<str:tab>/",
        views.project_tab,
        name="project_tab",
    ),
    path("<str:code>/", views.project_detail, name="project_detail"),
]
