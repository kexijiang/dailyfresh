
from django.contrib import admin
from django.urls import path, include

from ..order.views import OrderPlaceView, OrderCommitView

urlpatterns = [
    path('place/', OrderPlaceView.as_view(), name='place'),  # 订单模块展示
    path('commit/', OrderCommitView.as_view(), name='commit')

]
