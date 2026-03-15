# 电力巡检智能识别项目介绍

## 1. 项目概述

本项目面向电力巡检图像识别场景，将两个已有模型统一封装为一个可部署、可调用、可运维的 HTTP 服务，当前已落地两项能力：

- 鸟巢检测
- 塔身姿态检测

系统输入统一为：

- `task_id`
- `image_url`

系统输出统一为 JSON，结果中同时包含：

- 鸟巢检测结果
- 塔身姿态检测结果
- 图片基础信息
- 接口耗时信息

当前项目的目标不是只提供模型脚本，而是提供一套可以直接进入企业联调流程的识别服务。

## 2. 当前已完成能力

当前版本已经完成以下可交付内容：

- 双模型统一封装为单一识别接口
- 基于公网或内网环境部署为 HTTP 服务
- 基于 `Authorization: Bearer <token>` 或 `X-API-Key` 的接口鉴权
- 基于 `service.log` 和 `audit.log` 的服务日志与审计日志
- 基于 Nginx 的反向代理部署
- 基于 systemd 的 Linux 常驻运行
- 面向企业接入的接口文档、调用手册和演示材料

## 3. 系统形态

当前服务对外暴露两个标准接口：

```text
GET  /healthz
POST /api/v1/inspect
```

整体链路如下：

1. 企业系统提交 `task_id + image_url`
2. 服务下载远程图片
3. 调用鸟巢检测模型
4. 调用塔身姿态检测模型
5. 聚合为统一 JSON 返回
6. 同步写入服务日志和审计日志

当前服务属于单图同步推理接口，适合 PoC、平台联调、演示验证和小规模业务接入。

## 4. 当前识别任务说明

### 4.1 鸟巢检测

当前能力包括：

- 识别图像中的鸟巢目标
- 返回目标框位置、类别和置信度
- 输出检测数量统计

典型字段：

- `results.nest_detection.count`
- `results.nest_detection.class_counts`
- `results.nest_detection.detections[].bbox`
- `results.nest_detection.detections[].confidence`

### 4.2 塔身姿态检测

当前能力包括：

- 自动检测图像中的铁塔目标
- 估计塔身在图像平面内的视倾角
- 给出 `normal / warning / critical / unreliable` 状态分级

典型字段：

- `results.tower_tilt_detection.count`
- `results.tower_tilt_detection.summary`
- `results.tower_tilt_detection.detections[].apparent_tilt_deg`
- `results.tower_tilt_detection.detections[].status`

重要说明：

- 当前输出的是图像平面内的视倾角
- 当前结果不等于经过测绘或外参标定后的真实工程倾角

## 5. 适用场景

当前版本适合以下场景：

- 输电线路日常巡检辅助识别
- 无人机巡检图像自动筛查
- 巡检结果复核
- 后台平台联调
- AI 能力模块 PoC 演示

## 6. 企业接入前提

企业系统接入当前服务时，必须满足一个核心条件：

`image_url` 必须是服务所在服务器可直接访问和下载的 `http/https` 图片地址。

这意味着：

- 企业图片服务器公网地址可以直接接入
- 企业对象存储地址可以直接接入
- 企业业务系统提供的图片下载接口可以直接接入

这也意味着以下情况不能直接接入：

- 只有数据库公网 IP，没有图片下载 URL
- 只有数据库主键、附件 ID、二进制字段
- 只有调用方本地磁盘路径

一句话概括：

**“数据库可访问”不等于“图片 URL 可调用”。**

如果企业图片目前存储在数据库中，推荐先增加一层图片下载服务或对象存储访问层，再与当前识别服务对接。

## 7. 当前部署形态

当前项目支持以下部署形态：

- 云服务器公网部署
- 企业内网私有部署
- Windows 开发环境本地启动
- Linux 服务器常驻运行

典型部署组件包括：

- Python 推理服务
- Nginx 反向代理
- Token 鉴权
- `var/logs/service.log`
- `var/logs/audit.log`

## 8. 当前边界

为避免企业误解，当前版本边界如下：

- 当前只支持单张图片同步调用
- 当前只支持 `http/https` 图片地址
- 当前不支持直接上传文件
- 当前不支持直接连接企业数据库取图
- 当前下载模块不支持自定义请求头、Cookie 或签名参数注入
- 当前塔身姿态结果适合辅助识别和筛查，不直接等同工程测量结果

如果企业图片源需要 Cookie、签名头或专线协议，需要对下载模块做定制适配。

## 9. 落地建议

建议按以下路径推进：

### 第一阶段：PoC 验证

- 使用现有接口完成联调
- 企业提供少量真实图片 URL
- 验证结果结构、时延和可解释性

### 第二阶段：字段对齐

- 对齐 `task_id` 规则
- 对齐返回字段命名
- 对齐告警等级和业务含义

### 第三阶段：业务接入

- 接入企业正式图片源
- 接入企业工单或调度系统
- 增加更多巡检任务
- 用企业样本继续优化模型效果

## 10. 文档阅读顺序

建议按下面顺序阅读本项目文档：

1. `docs/ENTERPRISE_DEMO_CN.md`
2. `docs/DEPLOYMENT.md`
3. `docs/API_INTEGRATION.md`
4. `docs/API_CALL_MANUAL_CN.md`
5. `docs/DEMO_SCRIPT_CN.md`

这五份文档分别对应：

- 项目介绍
- 部署落地
- 企业对接规范
- 调用示例
- 演示讲解
