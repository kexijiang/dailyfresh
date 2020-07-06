from datetime import datetime
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, redirect
# Create your views here.
from django.urls import reverse
from django.views.generic import View
from django_redis import *
from ..goods.models import GoodsSKU
from ..user.models import Address
from .models import OrderInfo, OrderGoods


class OrderPlaceView(View):

    def post(self,request):
        '''提交订单显示'''
        # 获取参数
        sku_ids= request.POST.getlist('sku_ids')
        # 校验参数
        if not sku_ids:
            # 跳转至购物车页面
            return redirect(reverse('cart:show'))

        # 业务处理
        conn = get_redis_connection('default')
        user = request.user
        cart_key = 'cart_%d'%user.id
        skus =[]
        total_count = 0
        total_price = 0
        for sku_id in sku_ids:
            # 根据商品id获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 获取商品数量
            count = conn.hget(cart_key, sku_id)
            print(count)
            print(cart_key)
            print(sku_id)
            # 商品小计
            amount = int(count)*int(sku.price)
            # 累加计算商品总数量以及总价格
            total_count += int(count)
            total_price += int(amount)
            sku.count = int(count)
            sku.amount = amount
            skus.append(sku)
        # 定义运费
        transit_price = 10
        # 实付款
        total_pay = total_price + transit_price
        # 收货地址
        addrs = Address.objects.filter(user=user)
        # 组织上下文
        sku_ids = ','.join(sku_ids)
        context = {
            'skus':skus,
            'total_count':total_count,
            'total_price':total_price,
            'total_pay':total_pay,
            'transit_price':transit_price,
            'addrs':addrs,
            'sku_ids':sku_ids
        }
        return render(request, 'place_order.html', context=context)


class OrderCommitView(View):
    ''' 订单提交 '''
    @transaction.atomic
    def post(self, request):
        # 判断是否登录
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res':0,'errmsg':'用户未登录'})
        # 数据获取及校验
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')
        sku_ids = request.POST.get('sku_ids')
        # 检验数据是否全部存在
        if not all([addr_id, pay_method, sku_ids]):
            return JsonResponse({'res': 1, 'errmsg': '参数不完整'})
        # 检验支付方式是否存在
        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '支付方式不合法'})
        # 检验地址是否存在
        try:
            addr = Address.objects.get(id=addr_id)
        except Address.DoesNotExist:
            return JsonResponse({'res': 3, 'errmsg': '地址非法'})

        # todo: 创建订单核心业务
        # 组织参数
        # 订单id：年月日时分秒+用户id
        order_id = datetime.now().strftime('%Y%m%d%H%M%S')+str(user.id)
        # 运费
        transit_price = 10
        # 总数目和总金额
        total_count = 0
        total_price = 0
        save_id = transaction.savepoint()
        # todo:向df_order_info表中添加一条记录
        try:
            order = OrderInfo.objects.create(order_id=order_id,
                                            user=user,
                                            addr=addr,
                                            pay_method=pay_method,
                                            total_count=total_count,
                                            total_price=total_price,
                                            transit_price=transit_price
                )
            sku_ids = sku_ids.split(',')
            conn = get_redis_connection('default')
            cart_key = 'cart_%d'%user.id
            for sku_id in sku_ids:
                # 获取商品信息
                try:
                    # 加for_update别的事务碰到此数据会阻塞
                    sku = GoodsSKU.objects.select_for_update().get(id=sku_id)
                except:
                    # 商品不存在
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res': 4, 'errmsg': '商品不存在'})
                # 从redis中获取用户所要购买的商品数量
                count = int(conn.hget(cart_key, sku_id))
                # 判断商品库存是否充足
                if sku.stock <= count:
                    transaction.savepoint_rollback(save_id)
                    return JsonResponse({'res':6,'errmsg':'商品库存不足'})
                # todo: 用户订单中有几个商品，则向df_order_goods表中加入几条记录
                OrderGoods.objects.create(
                    order=order,
                    sku=sku,
                    count=count,
                    price=sku.price
                )
                # todo: 更新商品的库存与销量
                sku.stock -= int(count)
                sku.sales += int(count)
                sku.save()
                # todo: 累加计算订单商品的总数量和总价格
                amount = sku.price*int(count)
                total_count += int(count)
                total_price += amount

            # todo: 更新订单信息表中的商品总数量和总价格
            order.total_count = total_count
            order.total_price = total_price
            order.save()
        except Exception as e:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'message': '订单提交失败'})
        # 提交事务
        transaction.savepoint_commit(save_id)
        # todo: 清除用户购物车中对应的记录
        conn.hdel(cart_key, *sku_ids)

        # 返回应答
        return JsonResponse({'res': 5, 'message': '添加成功'})