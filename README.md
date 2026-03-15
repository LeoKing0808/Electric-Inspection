# 电力巡检智能识别工程项目

本仓库已经整理为一个可部署、可联调、可运维的工程项目，面向电力系统巡检图像识别场景，不再只是模型脚本集合。

当前运行时能力包括：

- 鸟巢检测
- 塔身姿态检测
- 企业数据库图片适配层

## 工程目录

```text
apps/        服务入口
src/         应用源码
models/      运行时模型资产
deploy/      Windows / systemd / Nginx 部署模板
config/      环境变量样例
docs/        项目与接口文档
examples/    请求与响应示例
var/         运行时日志和本地产物
research/    训练、实验、演示资产
artifacts/   历史归档与旧交付包
```

可以这样理解：

- `apps/ + src/ + models/` 是可部署运行主干
- `deploy/ + config/` 是交付和运维配套
- `research/` 是研发资产，不应作为生产运行依赖
- `artifacts/` 是历史归档，不参与当前运行

## 可运行服务

### 1. 识别服务

接口：

```text
GET  /healthz
POST /api/v1/inspect
```

请求体：

```json
{
  "task_id": "task-001",
  "image_url": "https://example.com/demo.jpg"
}
```

服务端会下载远程图片，执行鸟巢检测和塔身姿态检测，并返回统一 JSON 结果。

### 2. 企业数据库图片适配层

可选接口：

```text
GET  /healthz
POST /api/v1/image-url
GET  /api/v1/images/<record_id>?expires=...&signature=...
POST /api/v1/inspect-from-db
```

适用于企业图片保存在数据库中，而业务系统只有 `record_id`、附件 ID 或业务主键的场景。

## 本地启动

先安装依赖：

```bash
pip install -r requirements.txt
```

如果机器上还没有 PyTorch：

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

启动识别服务：

```bash
python apps/inspection_service/run.py
```

启动数据库图片适配层：

```bash
python apps/image_adapter/run.py
```

## 默认运行路径

识别服务默认使用以下路径：

- 日志：`var/logs/service.log` 和 `var/logs/audit.log`
- 鸟巢权重：`models/nest_detection/best.pt`
- 铁塔检测权重：`models/tower_tilt_detection/tower_detector/best.pt`
- 倾斜阈值：`models/tower_tilt_detection/thresholds/thresholds.json`

环境变量模板：

- 识别服务：`config/env/inspection.env.example`
- 数据库适配层：`config/env/image_adapter.env.example`

## Docker

构建并运行识别服务：

```bash
docker compose up -d --build
```

当前容器构建只复制运行时目录：

- `apps/`
- `src/`
- `models/`
- `deploy/`
- `config/`

`research/`、`artifacts/` 和 `var/` 不会进入镜像。

## 部署模板

当前可用部署脚本和模板：

- `deploy/windows/start_service.ps1`
- `deploy/windows/start_service.bat`
- `deploy/windows/start_adapter_service.ps1`
- `deploy/windows/start_adapter_service.bat`
- `deploy/systemd/power-inspection.service`
- `deploy/systemd/power-inspection.env.example`
- `deploy/systemd/power-image-adapter.service`
- `deploy/systemd/power-image-adapter.env.example`
- `deploy/nginx/power_inspection.conf`

## 研究资产与历史归档

非运行时内容已经移出根目录主干：

- `research/nest_detection_demo/`：原始鸟巢桌面演示代码
- `research/tower_tilt_detection/`：塔身姿态训练脚本、数据集和实验产物
- `research/runs/`：历史顶层运行产物
- `artifacts/packages/deploy_bundle/`：历史离线交付目录
- `artifacts/packages/power-inspection-deploy.zip`：历史压缩交付包

## 文档

建议按如下顺序阅读：

1. `docs/PROJECT_STRUCTURE_CN.md`
2. `docs/PROJECT_OVERVIEW_CN.md`
3. `docs/DEPLOYMENT.md`
4. `docs/API_INTEGRATION.md`
5. `docs/API_CALL_MANUAL_CN.md`
6. `docs/DATABASE_ADAPTER_CN.md`
7. `docs/DEMO_SCRIPT_CN.md`

## 扩展方向

如果后续要继续增加巡检任务，可以扩展 `src/power_inspection/pipeline.py`，并把新的任务结果追加到 `results` 字段下。
