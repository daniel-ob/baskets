from django.urls import include, path

from . import views

urlpatterns = [
    path("", include('allauth.urls')),
    path("profile/", views.profile, name="profile"),
]
