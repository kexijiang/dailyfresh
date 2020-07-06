# -*- coding:utf-8 -*-
from django.contrib import admin
from django.urls import path, include, re_path
from apps.goods import views
from apps.goods.views import IndexView, DetailView,ListView

app_name = 'goods'
urlpatterns = [
    path('index/', IndexView.as_view(), name='index'),  # 首页
    path('goods/<str:goods_id>', DetailView.as_view(), name='detail'),  # 详情页
    path('list/<int:type_id>/<int:page>', ListView.as_view(), name='list'),  # 列表页
]
