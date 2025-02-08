"""
URL configuration for djangoProject1 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin

from autobidder_app.views import run_voodoo_parser, ahrefs_data_view, claim_bet, log_list_view, download_ahrefs_data
from django.urls import path
from debug_toolbar.toolbar import debug_toolbar_urls
from autobidder_app.views import all_bets_view, update_max_bet, delete_bet, ahrefs_test_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('run-parser/', run_voodoo_parser, name='run_voodoo_parser'),
    path("", ahrefs_data_view, name="ahrefs_data"),
    path("claim_bet/", claim_bet, name="claim_bet"),
    path('all-bets/', all_bets_view, name='all_bets'),
    path('update-max-bet/<int:bet_id>/', update_max_bet, name='update_max_bet'),
    path('delete-bet/<int:bet_id>/', delete_bet, name='delete_bet'),
    path('logs/', log_list_view, name='log_list'),
                  path("ahrefs-test/", ahrefs_test_view, name="ahrefs_test"),
                  path("download-ahrefs/<str:file_type>/", download_ahrefs_data, name="download_ahrefs"),

 ] + debug_toolbar_urls()

