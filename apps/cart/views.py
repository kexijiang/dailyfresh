from django.shortcuts import render
from django.views.generic import View
from django.http import JsonResponse
from django_redis import get_redis_connection
from utils.mixin import LoginRequiredMixin
from ..goods.models import GoodsSKU

# Create your views here.
# 添加商品到购物车
# 请求方式 ajax post
# 如果涉及数据的增删改，则post方式，否则get方式
# 传递的参数：商品id(sku_id) 商品数量(count)
# /cart/add



class CartAddView(View):
    '''购物车记录添加'''

    def post(self, request):
        '''购物车记录添加'''
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 接收数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 检验商品数量是否正确
        try:
            count = int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})
        # 业务处理
        # 1.先获取购物车记录
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id
        # 先尝试获取sku_id的值，如果sku_id在hash中不存在，hget返回None
        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            # 累加购物车中商品数目
            count += int(cart_count)
        # 检验商品库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
        # 设置hash中sku_id的值,hset方法如果key存在，更新，如果不存在，则新增
        conn.hset(cart_key, sku_id, count)
        total_count = conn.hlen(cart_key)
        # 返回应答
        return JsonResponse({'res': 5, 'total_count':total_count,'errmsg': '添加成功'})


# /cart/info/
class CartInfoView(LoginRequiredMixin,View):
    def get(self,request):
        user = request.user
        # 获取用户对应的商品信息
        # 获取redis数据库连接
        conn = get_redis_connection('default')
        # 组成用户的key
        cart_key = 'cart_%d' % user.id
        # 获取用户key下的所有信息,格式{商品id:商品数量}
        cart_dict = conn.hgetall(cart_key)
        skus = []
        total_price = 0
        total_count = 0
        # 遍历字典获取每个商品的详细信息
        for sku_id in cart_dict.keys():
            count = int(cart_dict[sku_id])
            sku_id = int(sku_id)
            # 根据商品id获取商品详细信息
            sku = GoodsSKU.objects.get(id=sku_id)
            # 计算商品小计
            amount = sku.price*int(count)
            # 动态给sku对象增加一个属性,保存小计
            sku.amount = amount
            # 动态给sku对象增加一个属性,保存商品数量
            sku.count = count
            total_count += int(count)
            total_price += amount
            skus.append(sku)
        # 组织上下文
        context = {
            'total_count' : total_count,
            'total_price' : total_price,
            'skus' : skus
        }
        return render(request, 'cart.html', context)


# 更新购物车中商品数量
# 采用ajax post请求,前端传过来的参数，商品id(sku_id)，商品数量(count)
# /cart/update
class CartUpdateView(View):
    def post(self, request):
        # 接收数据
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        # 接收数据
        sku_id=request.POST.get('sku_id')
        count=request.POST.get('count')
        # 数据校验
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})
        # 检验商品数量是否正确
        try:
            count=int(count)
        except Exception as e:
            return JsonResponse({'res': 2, 'errmsg': '商品数目出错'})
        # 校验商品是否存在
        try:
            sku=GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 商品不存在
            return JsonResponse({'res': 3, 'errmsg': '商品不存在'})

        # 业务处理
        conn=get_redis_connection('default')
        cart_key='cart_%d' % user.id
        # 如果count大于商品库存，则不能更新
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '库存不足'})
        # 更新
        conn.hset(cart_key,sku_id,count)
        # 计算用户购物车中商品的总件数
        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回结果
        return JsonResponse({'res': 5, 'total_count':total_count,'errmsg': '更新成功'})


# 删除购物车中商品
# 采用ajax post请求,前端传过来的参数，商品id(sku_id)
# /cart/delete
class CartDeleteView(View):

    def post(self,request):
        # 数据接收
        user = request.user
        if not user.is_authenticated:
            return JsonResponse({'res': 0, 'errmsg': '请先登录'})
        sku_id = request.POST.get('sku_id')

        # 数据校验
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的商品id'})
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '商品不存在'})
        # 业务处理
        conn = get_redis_connection('default')
        cart_key = 'cart_%d'% user.id
        conn.hdel(cart_key,sku_id)
        # 计算用户购物车中商品的总件数
        total_count=0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)
        # 返回响应
        return JsonResponse({'res': 3, 'total_count': total_count, 'errmsg': '删除成功'})