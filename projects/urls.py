from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path(
        "autocomplete/",
        views.project_search_autocomplete,
        name="search_autocomplete",
    ),
    path("<str:code>/", views.project_detail, name="project_detail"),
]
