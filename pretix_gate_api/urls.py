from django.urls import re_path

from . import views


urlpatterns = [
    re_path(
        r"^api/custom/gates/$",
        views.GateListView.as_view(),
        name="gates",
    ),

    re_path(
        r"^api/custom/devices/$",
        views.DeviceListView.as_view(),
        name="devices",
    ),

    re_path(
        r"^api/custom/devices/(?P<device_id>[0-9]+)/gate/$",
        views.DeviceGateView.as_view(),
        name="device-gate",
    ),
]