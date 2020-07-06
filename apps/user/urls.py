# -*- coding:utf-8 -*-
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import path, include
from ..user import views
from ..user.views import *
app_name = 'user'
urlpatterns = [
    path('register/',RegisterView.as_view(),name='register'),
    path('active/<str:token>',ActiveView.as_view(),name='active'),
    path('login/',LoginView.as_view(),name='login'),
    path('logout/',LogoutView.as_view(),name='logout'),
    path('info/',UserInfoView.as_view(),name='info'),
    path('order/<int:page>',UserOrderView.as_view(),name='order'),
    path('site/',UserAddressView.as_view(),name='address'),
]
