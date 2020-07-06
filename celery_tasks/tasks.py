#使用selery
# -*- coding:utf-8 -*-
import time

from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE","dailyfresh.settings")
django.setup()
app = Celery('celery_tasks.tasks',broker='redis://62.234.90.228:6400/8')
app.conf['imports'] = ['celery_tasks.tasks', ]
from apps.goods.models import IndexTypeGoodsBanner, IndexPromotionBanner, GoodsType, IndexGoodsBanner
from django.template import loader
@app.task
def send_register_active_email(to_email,username,token):
    '''发送激活邮件'''
    subject = '天天生鲜欢迎信息'
    message = ''
    html_message = '<h1>{},欢迎成为天天生鲜注册会员<h1><br/><h3>请点击下面链接激活您的账户</h3><br/><a href="http://49.234.214.32:8000/user/active/{}">http://49.234.214.32:8000/user/active/{}</a>'.format(
        username, token, token)
    sender = 'kxjiang01@qq.com'
    receiver = [to_email]
    send_mail(subject, message, sender, receiver, html_message=html_message)
    print("发送邮件成功")
    # time.sleep(5)
@app.task
def generate_static_index_html():
    '''产生首页静态页面'''
    # 使用模板
    print("接收到生成首页静态页面的请求...")
    # 获取商品的种类信息
    types = GoodsType.objects.all()
    print("接收到生成首页静态页面的请求,处理中...")
    # 获取首页轮播商品信息
    goods_banners = IndexGoodsBanner.objects.all().order_by('index')
    print("接收到生成首页静态页面的请求,处理中1...")
    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by('index')
    print("接收到生成首页静态页面的请求,处理中2...")
    # 获取首页分类商品展示信息
    for type1 in types:  # GoodsType
            print(type1)
            # 获取type种类首页分类商品的图片展示信息
            image_banners = IndexTypeGoodsBanner.objects.filter(type=type1,distype_type=1).order_by('index')
            # 获取type种类首页分类商品的文字展示信息
            title_banners = IndexTypeGoodsBanner.objects.filter(type=type1,distype_type=0).order_by('index')
            print("接收到生成首页静态页面的请求,处理中3...")
            # 动态给type增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
            type1.image_banners = image_banners
            type1.title_banners = title_banners
            print("接收到生成首页静态页面的请求,处理中4...")

    # 组织模板上下文
    context = {'types': types,
               'goods_banners': goods_banners,
               'promotion_banners': promotion_banners}
    print("接收到生成首页静态页面的请求,处理中5...")
    # 使用模板
    # 1.加载模板文件,返回模板对象
    temp = loader.get_template('static_index.html')
    print("接收到生成首页静态页面的请求,处理中6...")
    # 2.模板渲染
    static_index_html = temp.render(context)
    print("接收到生成首页静态页面的请求,处理中7...")
    # 生成首页对应静态文件
    save_path = os.path.join(settings.BASE_DIR, 'static/index.html')
    print("接收到生成首页静态页面的请求,处理中8...")
    print("静态文件路径为："+save_path)
    with open(save_path, 'w') as f:
        f.write(static_index_html)
    print("生成首页静态文件完成...")