
from django.contrib import admin
from django.urls import path, include

from .views import CartAddView, CartInfoView,CartUpdateView,CartDeleteView
app_name = 'cart'
urlpatterns = [
    path('add/', CartAddView.as_view(), name='add'),  # 购物车模块
    path('info/', CartInfoView.as_view(), name='show'), # 返回页面
    path('update/', CartUpdateView.as_view(), name='update'), # 购物车记录更新
    path('delete/', CartDeleteView.as_view(), name='delete'), # 删除购物车记录
]
