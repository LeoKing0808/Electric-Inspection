# 电力巡检智能识别工程总览

## 1. 项目定位

当前仓库已经整理为一个可落地部署的工程项目，目标是服务电力系统巡检图像识别，而不是单纯存放模型脚本。

现阶段已封装的运行时能力包括：

- 鸟巢检测
- 塔身姿态检测
- 企业数据库图片适配层

其中：

- 识别服务负责下载图片并执行 AI 推理
- 适配层负责把数据库图片记录转换为临时 `image_url`，或直接转发识别请求

## 2. 当前工程目录

项目顶层已经按职责拆分为：

```text
apps/        服务入口
src/         业务源码
models/      运行时模型资产
deploy/      部署模板
config/      环境变量样例
docs/        文档
examples/    接口样例
var/         日志与运行产物
research/    训练、实验、演示资产
artifacts/   历史打包产物
```

理解方式如下：

- `apps/ + src/ + models/` 是运行时主干
- `deploy/ + config/` 是交付和运维配套
- `research/` 是研发资产，不应作为生产运行依赖
- `artifacts/` 是旧离线包归档

## 3. 两个可运行服务

### 3.1 识别服务

入口：

```text
python apps/inspection_service/run.py
```

提供接口：

```text
GET  /healthz
POST /api/v1/inspect
```

标准输入：

```json
{
  "task_id": "task-001",
  "image_url": "https://files.example.com/patrol/task001.jpg"
}
```

处理链路：

1. 企业系统提交 `task_id + image_url`
2. 服务下载远程图片
3. 执行鸟巢检测
4. 执行塔身姿态检测
5. 聚合为统一 JSON
6. 记录运行日志和审计日志

### 3.2 数据库图片适配层

入口：

```text
python apps/image_adapter/run.py
```

提供接口：

```text
GET  /healthz
POST /api/v1/image-url
GET  /api/v1/images/<record_id>?expires=...&signature=...
POST /api/v1/inspect-from-db
```

适用场景：

- 企业图片保存在数据库 BLOB 字段
- 企业系统只有记录 ID、业务主键或附件 ID
- 企业还没有独立的图片下载服务

## 4. 模型与日志位置

当前运行时默认使用以下资产：

- 鸟巢模型：`models/nest_detection/best.pt`
- 铁塔检测模型：`models/tower_tilt_detection/tower_detector/best.pt`
- 塔身阈值：`models/tower_tilt_detection/thresholds/thresholds.json`

日志默认落在：

- `var/logs/service.log`
- `var/logs/audit.log`

## 5. 关键边界

当前识别服务仍然保持一个明确边界：

**它只接受可直接访问的 `http/https` 图片地址，不直接连接企业数据库。**

因此：

- 图片下载 URL 可以直接接入
- 对象存储 URL 可以直接接入
- 静态图片 URL 可以直接接入

但以下内容不能直接传给识别服务：

- 数据库公网 IP
- 数据库连接串
- 数据库主键
- 附件 ID
- 图片二进制字段

如果企业图片在数据库中，应先通过数据库图片适配层转换为临时图片 URL，再接入识别服务。

## 6. 当前工程化改造结果

本次整理后，项目已经完成以下工程化收敛：

- 运行时源码归入 `src/`
- 启动入口归入 `apps/`
- 模型资产统一归入 `models/`
- 训练/演示代码归入 `research/`
- 历史打包产物归入 `artifacts/`
- 日志归入 `var/`
- Docker 构建上下文排除了研究和归档内容

## 7. 推荐阅读顺序

建议按如下顺序阅读：

1. `docs/PROJECT_STRUCTURE_CN.md`
2. `docs/PROJECT_OVERVIEW_CN.md`
3. `docs/DEPLOYMENT.md`
4. `docs/API_INTEGRATION.md`
5. `docs/API_CALL_MANUAL_CN.md`
6. `docs/DATABASE_ADAPTER_CN.md`
