from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client
from django.conf import settings


class FDFSStorage(Storage):
    """fast dfs文件存储类"""

    def __init__(self, client_conf=None, base_host_port=None):
        if client_conf == None:
            client_conf=settings.FDFS_DEFAULT_CONF
        self.client_conf=client_conf
        if base_host_port == None:
            base_host_port=settings.FDFS_BASE_HOST_PORT
        self.base_host_port=base_host_port
    def _open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def _save(self, name, content):
        """保存文件时使用"""
        # name:你选择上传文件的名字
        # content:包含你上传文件内容的File对象
        client=Fdfs_client(self.client_conf)
        res=client.upload_by_buffer(content.read())
        if res.get('Status') != 'Upload successed.':
            # 上传失败
            raise Exception("上传到fastdfs服务器失败！")
        filename=res.get('Remote file_id')
        return filename

    def exists(self, name):
        """Django判断文件名是否可用"""
        return False

    def url(self, name):
        """返回图片文件的url"""

        return self.base_host_port + name
