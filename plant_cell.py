import numpy as np
import matplotlib.pyplot as plt


# 定义植物细胞类
class Cell(object):

    def __init__(self, total_sunlight, position):
        self.total_sunlight=total_sunlight  # 细胞接触的阳光总量
        self.position=position  # 细胞所在位置


# 定义植物胞群算法主体类
class ZWBQ(object):
    # D的意思是d维的数组
    def __init__(self,D, all_total_sunlight=100, number=100):
        self.all_total_sunlight=all_total_sunlight  # 总的阳光总量
        self.number=number  # 细胞数量
        self.cells = np.
    # 计算每个细胞接触的阳光总量
    def total_sunlight(self,Cells):
        pass
    # 计算最强光照位置
    def strongest_light_position(self):
        pass