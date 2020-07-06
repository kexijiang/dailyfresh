# -*- coding:utf-8 -*-
import datetime
import re
from django.conf import settings
from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.core import paginator
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from itsdangerous import TimedJSONWebSignatureSerializer as Seriallizer

from ..order.models import OrderInfo, OrderGoods
from ..goods.models import GoodsSKU
from ..user.models import User, Address
from django.views.generic import View
from itsdangerous import SignatureExpired
from django.core.mail import send_mail
from utils.mixin import *
from django_redis import get_redis_connection

# Create your views here.
# /user/register
from celery_tasks.tasks import send_register_active_email


class RegisterView(View):
    """显示注册页面"""

    def get(self, request):
        return render(request, 'register.html')

    '''注册处理'''

    def post(self, request):
        # 接收数据
        username=request.POST.get('user_name')
        password=request.POST.get('pwd')
        email=request.POST.get('email')
        allow=request.POST.get('allow')
        # 进行数据校验
        if not all([username, password, email]):
            return render(request, 'register.html', {'errmsg': '数据不完整'})
        # 校验邮箱格式
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'errmsg': '邮箱格式不正确'})

        if allow != 'on':
            return render(request, 'register.html', {'errmsg': '请同意协议'})
        # 校验用户名是否存在
        try:
            user=User.objects.get(username=username)
        except User.DoesNotExist:
            user=None
        if user:
            return render(request, 'register.html', {'errmsg': '用户名已存在'})
        # 进行业务处理：
        user=User()
        user.set_password(password)
        user.username=username
        user.password=password
        user.email=email
        user.is_active=0  # 设置账户状态 未进行激活
        user.save()

        # 激活链接中需要包含用户的身份信息，并且要加密：
        # 加密用户的身份信息：生成激活的token
        seriallizer=Seriallizer(settings.SECRET_KEY, 3600)
        info={'confirm': user.id}
        token=str(seriallizer.dumps(info), encoding="utf-8")
        print('加密过的信息为：' + token)
        # 发送激活邮件，包含激活链接：
        # subject = '天天生鲜欢迎信息'
        # message = ''
        # html_message = '<h1>{},欢迎成为天天生鲜注册会员<h1><br/><h3>请点击下面链接激活您的账户</h3><br/><a href="http://127.0.0.1:8000/user/active/{}">http://127.0.0.1:8000/user/active/{}</a>'.format(username,token,token)
        # sender = 'kxjiang01@qq.com'
        # receiver = [email]
        # send_mail(subject,message,sender,receiver,html_message=html_message)
        # print("发送邮件成功")
        send_register_active_email.delay(email, username, token)
        # 返回应答,跳转到首页
        return redirect(reverse('goods:index'))


class ActiveView(View):

    def get(self, request, token):
        '''用户激活'''
        # 解密：获取要激活的用户信息
        seriallizer=Seriallizer(settings.SECRET_KEY, 3600)
        try:
            info=seriallizer.loads(token)
            user_id=info['confirm']
            user=User.objects.get(id=user_id)
            user.is_active=1
            user.save()
            return HttpResponseRedirect(reverse('user:login'))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse("激活链接已过期")


class LoginView(View):
    """登录"""

    def get(self, request):
        """显示登录页面"""
        if 'username' in request.COOKIES:
            username=request.COOKIES.get('username').encode("iso-8859-1").decode('utf8')
            checked='checked'
        else:
            username=''
            checked=''
        # 使用模板
        return render(request, 'login.html', {'username': username, 'checked': checked})

    def post(self, request):
        """登录校验"""
        # 获取数据
        username=request.POST.get('username')
        password=request.POST.get('pwd')
        # 判断用户名密码是否存在
        if not all([username, password]):
            return render(request, 'login.html', {'errmsg': '数据不完整'})
        # user1 = authenticate(username=username,password=password)
        # user = User.objects.get(username=username)
        search_dict=dict()
        search_dict['username']=username
        search_dict['password']=password
        user=User.objects.filter(**search_dict).first()
        print(user)
        print("username=" + username + ";password=" + password)
        # 业务处理，登录经验
        if user is not None:
            # 账户是否激活
            if user.is_active:
                print("用户已激活")
                # 系统的登录方法，会将登录id放入session
                login(request, user)
                # 获取登陆后要跳转的地址
                next_url=request.GET.get('next', reverse('goods:index'))
                # 跳转到next_url
                response=redirect(next_url)
                # 判断是否需要记住用户名
                remember=request.POST.get('remember')
                if remember == 'on':
                    # 记住用户名
                    response.set_cookie("username", bytes(username, 'utf-8').decode('ISO-8859-1'),
                                        max_age=3600 * 24 * 7)
                else:
                    response.delete_cookie('username')
                # 返回响应
                print("成功返回响应")
                return response
            else:
                return render(request, 'login.html', {'errmsg': '账户未激活'})
        else:
            return render(request, 'login.html', {'errmsg': '用户名密码错误'})


class LogoutView(View):
    """用户退出登录"""

    def get(self, request):
        # 清除用户的session信息
        logout(request)
        # 跳转至登录页面
        return redirect(reverse('user:login'))


# /user/info
class UserInfoView(LoginRequiredMixin, View):
    def get(self, request):
        """显示"""
        # request.user
        # 如果用户未登录-->AnonymousUser类的实例
        # 如果用户登录了-->User类的实例
        # 获取用户的个人信息
        user=request.user
        address=Address.objects.get_default_address(user)
        # 获取用户的历史浏览记录
        # from redis import StrictRedis
        # sr = StrictRedis(host="49.234.214.32", port='6379', db=9)
        con=get_redis_connection('default')
        history_key='history_%d' % user.id
        # 获取用户最新浏览的5个商品的id
        sku_ids=con.lrange(history_key, 0, 4)
        print("历史浏览记录的商品id数组为:")
        print(sku_ids)
        # 从数据库查询用户浏览的商品的具体信息
        # goods_li = GoodsSKU.objects.filter(id__in=sku_ids)
        # goods_res = []
        # for a_id in sku_ids:
        #     for goods in goods_li:
        #         if a_id == goods.id:
        #             goods_res.append(goods)
        goods_li=[]
        for id in sku_ids:
            goods=GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        # 组织上下文
        context={
            'page': 'info',
            'address': address,
            'goods_li': goods_li
        }

        # django框架会自动将request.user对象传给模板文件
        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):

    def get(self, request, page):
        user = request.user
        orders = OrderInfo.objects.filter(user=user)
        for order in orders:
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count*order_sku.price
                # 保存订单商品小计
                order_sku.amount = amount
            # 保存订单状态标题
            order.order_status = OrderInfo.ORDER_STATUS[order.order_status]
            # 保存订单商品信息
            order.order_skus = order_skus
        # 对数据进行分页
        paginator = Paginator(orders, 2)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1
        # 获取第page页的Page实例对象
        order_page = paginator.page(page)
        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数少于5页，页面显示所有页数
        # 2.如果当前是前3页，显示前1-5页
        # 3.如果是后3页，显示后5页
        # 4.其他情况，显示当前页的前两页，当前页，当前页的后两页
        num_pages=paginator.num_pages
        if num_pages < 5:
            pages=range(1, num_pages + 1)
        elif page <= 3:
            pages=range(1, 6)
        elif num_pages - page <= 2:
            pages=range(num_pages - 4, num_pages + 1)
        else:
            pages=range(page - 2, page + 3)
        # 组织上下文
        context = {
            'order_page':order_page,
            'pages':pages,
            'page':orders
        }
        # 使用模板
        return render(request, 'user_center_order.html', context)


# /user/site
class UserAddressView(LoginRequiredMixin, View):
    def get(self, request):
        user=request.user
        address=Address.objects.get_default_address(user)
        return render(request, 'user_center_site.html', {'page': 'site', 'address': address})

    def post(self, request):
        """添加地址"""
        # 接收数据
        receiver=request.POST.get("receiver")
        addr=request.POST.get("addr")
        zip_code=request.POST.get("zip_code")
        phone=request.POST.get("phone")
        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, 'user_center_site.html', {'errmsg': '数据不完整'})
        # if not re.match(r'^1[3|4|5|7|8][0-9]{9}s', phone):
        #     return render(request, 'user_center_site.html', {'errmsg': '电话号码格式不对'})
        user=request.user
        # 业务处理：地址添加
        address=Address.objects.get_default_address(user)
        if address:
            is_default=False
        else:
            is_default=True
        # 添加地址
        Address.objects.create(user=user, addr=addr, receiver=receiver,
                               zip_code=zip_code,
                               phone=phone,
                               is_default=is_default
                               )
        # 返回应答,刷新地址页面
        return redirect(reverse('user:address'))
