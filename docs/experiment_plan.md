# 推荐系统大作业：NeuMF vs LightGCN 对比实验

## 一、项目概述

本项目基于 **MovieLens-1M** 数据集，实现并对比两类协同过滤推荐算法：

- **传统深度学习方法**：GMF、MLP、NeuMF（Neural Collaborative Filtering, WWW'17）
- **图神经网络方法**：LightGCN（SIGIR'20）——作为本项目的**创新对比项**

核心研究问题：**图卷积捕获的高阶协同信号，能否比 MLP 的非线性交互建模带来更好的推荐效果？**

## 二、数据集

| 数据集 | 用户数 | 物品数 | 评分数 | 稀疏度 |
|---|---|---|---|---|
| MovieLens-1M | 6,040 | 3,706 | 1,000,209 | 95.53% |

**数据划分方式**：留一法（Leave-One-Out）
- 训练集：每个用户除最后一次交互外的所有记录
- 测试集：每个用户的最后一次交互 + 99 个随机负样本，共 100 个候选排序

数据来源：[hexiangnan/neural_collaborative_filtering/Data](https://github.com/hexiangnan/neural_collaborative_filtering/tree/master/Data)

## 三、对比算法

### 3.1 GMF（Generalized Matrix Factorization）
- 用户/物品 embedding -> 逐元素乘积 -> 线性输出层
- 最简单的基线，只建模线性交互

### 3.2 MLP（Multi-Layer Perceptron）
- 用户/物品 embedding -> 拼接 -> 多层全连接 + ReLU -> 输出层
- 通过非线性变换捕获复杂交互模式

### 3.3 NeuMF（Neural Matrix Factorization）
- **GMF + MLP 双通道融合**：分别提取线性和非线性交互特征，拼接后通过预测层输出
- 论文：He et al., "Neural Collaborative Filtering", WWW 2017

### 3.4 LightGCN（Light Graph Convolutional Network）
- 构建用户-物品**二部图**，通过多层轻量级图卷积聚合邻域信息
- 去掉了 GCN 中的特征变换和非线性激活，只保留**邻域聚合**
- 捕获用户-物品之间的**高阶连通性**
- 论文：He et al., "LightGCN: Simplifying and Powering GCN for Recommendation", SIGIR 2020

## 四、评估指标

| 指标 | 含义 | 公式 |
|---|---|---|
| **HR@10** | 命中率，测试物品是否出现在 Top-10 推荐列表中 | HR = 命中用户数 / 全部用户数 |
| **NDCG@10** | 归一化折扣累积增益，关注命中位置（越靠前越好） | NDCG = DCG / IDCG |

评估协议：对每个用户，将 1 个正样本 + 99 个负样本排序，计算 Top-10 指标。

## 五、实验计划

### 实验 1：四模型横向对比

在**完全相同的数据划分**下，对比 GMF / MLP / NeuMF / LightGCN。

### 实验 2：消融实验（针对 NeuMF）

| 实验变量 | 取值范围 | 目的 |
|---|---|---|
| Embedding 维度 | {8, 16, 32, 64} | 分析表示能力对效果的影响 |
| 负采样比 | {1, 2, 4, 8} | 分析正负样本比例的影响 |
| MLP 层数 | {2层, 3层, 4层} | 分析网络深度的影响 |

### 实验 3：训练过程可视化

- Loss 随 epoch 下降曲线
- HR@10 / NDCG@10 随 epoch 变化曲线
- NeuMF vs LightGCN 的收敛速度对比

## 六、技术路线补充

当前仓库已经补充了一个适合前后端联调的后端原型：
- 统一推荐接口
- 热门推荐、用户协同过滤、内容相似推荐三个基线
- 数据库 schema 与 API 文档草案

这部分可以先支撑 UI 和答辩演示，后续再替换为 NeuMF / LightGCN 的真实结果。

## 七、参考文献

1. He X, Liao L, Zhang H, et al. Neural Collaborative Filtering[C]. WWW, 2017.
2. He X, Deng K, Wang X, et al. LightGCN: Simplifying and Powering Graph Convolution Network for Recommendation[C]. SIGIR, 2020.
3. Rendle S, Krichene W, Zhang L, et al. Neural Collaborative Filtering vs. Matrix Factorization Revisited[C]. RecSys, 2020.
