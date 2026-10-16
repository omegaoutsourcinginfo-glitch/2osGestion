from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("<str:code>/", views.project_detail, name="project_detail"),
]
