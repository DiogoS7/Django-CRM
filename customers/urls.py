from django.urls import path

from . import views

app_name = "customers"

urlpatterns = [
    path("", views.home, name="home"),
    path("customers/", views.customer_list, name="list"),
    path("customers/new/", views.customer_create, name="create"),
    path("customers/<int:pk>/", views.customer_detail, name="detail"),
    path("customers/<int:pk>/edit/", views.customer_update, name="update"),
    path("customers/<int:pk>/delete/", views.customer_delete, name="delete"),
    path("customers/<int:pk>/status/", views.customer_set_status, name="set_status"),
    path("customers/<int:pk>/activity/", views.activity_create, name="log_activity"),
]
