
"""
URL configuration for fuego project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Authentication
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.authtoken')),

    # Chat API
    path('api/', include('chat.urls')),
    path('api/', include('community.urls')),
]
