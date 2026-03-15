# 部署指南

## 1. 适用范围

本文档对应整理后的工程目录，适用于以下场景：

- Windows 本地开发或演示
- Linux 本地部署
- 云服务器部署
- 企业内网服务器部署

## 2. 工程必需目录

当前可运行工程最少依赖以下内容：

- `apps/inspection_service/run.py`
- `src/power_inspection/`
- `src/inspection_runtime/`
- `models/nest_detection/best.pt`
- `models/tower_tilt_detection/tower_detector/best.pt`
- `models/tower_tilt_detection/thresholds/thresholds.json`

可选组件：

- `apps/image_adapter/run.py`
- `src/enterprise_image_adapter/`

## 3. 推荐配置

建议最低配置：

- 操作系统：Ubuntu 22.04 LTS 或 Windows 10/11
- Python：3.10 及以上
- CPU：4 vCPU
- 内存：8 GiB
- 磁盘：80 GiB 及以上

如果是正式企业联调，建议至少保持 `4C8G`。

## 4. Python 环境安装

### 4.1 Linux

```bash
cd /opt/power-inspection
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 4.2 Windows

```powershell
cd D:\Electric Detection
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

如果使用 GPU，请自行安装与 CUDA 匹配的 PyTorch，再安装其余依赖。

## 5. 环境变量模板

环境变量样例位置：

- 识别服务：`config/env/inspection.env.example`
- 图片适配层：`config/env/image_adapter.env.example`

Linux systemd 专用样例：

- `deploy/systemd/power-inspection.env.example`
- `deploy/systemd/power-image-adapter.env.example`

## 6. 默认运行路径

识别服务默认路径：

```text
日志目录: var/logs
鸟巢权重: models/nest_detection/best.pt
铁塔权重: models/tower_tilt_detection/tower_detector/best.pt
阈值文件: models/tower_tilt_detection/thresholds/thresholds.json
```

企业数据库适配层默认需要：

- 数据库连接串
- 查询图片 SQL
- 签名密钥
- 识别服务地址

## 7. 直接启动

### 7.1 识别服务

```bash
python apps/inspection_service/run.py
```

Windows 也可使用：

```powershell
deploy\windows\start_service.ps1
```

### 7.2 数据库图片适配层

```bash
python apps/image_adapter/run.py
```

Windows 也可使用：

```powershell
deploy\windows\start_adapter_service.ps1
```

## 8. 健康检查

识别服务：

```bash
curl http://127.0.0.1:8000/healthz
```

适配层：

```bash
curl http://127.0.0.1:8001/healthz
```

## 9. Linux 正式部署

### 9.1 systemd

识别服务：

- `deploy/systemd/power-inspection.service`
- `deploy/systemd/power-inspection.env.example`

适配层：

- `deploy/systemd/power-image-adapter.service`
- `deploy/systemd/power-image-adapter.env.example`

典型步骤：

1. 复制 env 样例并改成正式值
2. 把 service 文件放到 `/etc/systemd/system/`
3. 执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable power-inspection
sudo systemctl start power-inspection
sudo systemctl status power-inspection
```

如果适配层也要常驻运行，再执行：

```bash
sudo systemctl enable power-image-adapter
sudo systemctl start power-image-adapter
sudo systemctl status power-image-adapter
```

### 9.2 Nginx

推荐模式：

- Nginx 对外监听 `80/443`
- 后端识别服务只监听 `127.0.0.1:8000`

模板：

- `deploy/nginx/power_inspection.conf`

## 10. Docker

项目提供了：

- `Dockerfile`
- `docker-compose.yml`

直接执行：

```bash
docker compose up -d --build
```

当前容器只打包运行时目录，不打包 `research/` 和 `artifacts/`。

## 11. 日志与运维

当前识别服务日志目录：

```text
var/logs/service.log
var/logs/audit.log
```

常用命令：

```bash
tail -f var/logs/service.log
tail -f var/logs/audit.log
journalctl -u power-inspection -f
journalctl -u power-image-adapter -f
```

## 12. 上线前检查

建议逐项确认：

- `GET /healthz` 正常
- `POST /api/v1/inspect` 正常
- 生产 token 已替换
- 识别服务可访问企业 `image_url`
- 如果启用适配层，数据库查询能返回真实图片
- `var/logs/` 已持久化
- Docker 或服务器上未把 `research/` 当作运行依赖

## 13. 当前边界

当前部署能力已满足演示和企业联调，但仍有以下边界：

- 单张图片同步调用
- 不提供批量接口
- 不提供任务队列
- 不做多进程或多卡调度
- 数据库适配层仍需按企业实际数据库补齐驱动
