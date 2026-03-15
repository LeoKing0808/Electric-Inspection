# API 调用手册

## 1. 适用对象

本文档面向以下人员：

- 项目演示人员
- 联调开发人员
- 企业接口测试人员

目标是帮助调用方快速完成接口测试、结果查看和常见问题排查。

## 2. 当前演示环境

当前演示环境如下：

```text
接口地址: http://47.98.17.103/api/v1/inspect
健康检查: http://47.98.17.103/healthz
鉴权方式: Authorization: Bearer 88888888
```

说明：

- `88888888` 仅建议用于当前演示环境
- 正式部署时应替换为随机长 token

## 3. 调用前检查

在发起请求前，请先确认：

- 服务地址可访问
- `GET /healthz` 返回正常
- token 正确
- 图片 URL 可被云服务器访问
- 图片 URL 指向的是实际图片资源，而不是数据库连接地址

健康检查示例：

```powershell
curl.exe "http://47.98.17.103/healthz"
```

## 4. 调用方式

### 4.1 请求方法

```text
POST /api/v1/inspect
```

### 4.2 请求头

```text
Content-Type: application/json
Authorization: Bearer 88888888
```

### 4.3 请求体

```json
{
  "task_id": "demo-task-001",
  "image_url": "https://images.enterprise.com/patrol/task001.jpg"
}
```

字段说明：

- `task_id`：调用方任务编号，返回结果中原样带回
- `image_url`：云服务器可访问的图片地址

## 5. PowerShell 调用示例

```powershell
$headers = @{
  "Content-Type" = "application/json"
  "Authorization" = "Bearer 88888888"
}

$body = @{
  task_id = "demo-task-001"
  image_url = "https://images.enterprise.com/patrol/task001.jpg"
} | ConvertTo-Json

Invoke-RestMethod `
  -Uri "http://47.98.17.103/api/v1/inspect" `
  -Method Post `
  -Headers $headers `
  -Body $body | ConvertTo-Json -Depth 20
```

## 6. curl 调用示例

```bash
curl -X POST "http://47.98.17.103/api/v1/inspect" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer 88888888" \
  -d '{
    "task_id": "demo-task-001",
    "image_url": "https://images.enterprise.com/patrol/task001.jpg"
  }'
```

## 7. Python 调用示例

```python
import requests

url = "http://47.98.17.103/api/v1/inspect"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer 88888888",
}
payload = {
    "task_id": "demo-task-001",
    "image_url": "https://images.enterprise.com/patrol/task001.jpg",
}

response = requests.post(url, headers=headers, json=payload, timeout=120)
response.raise_for_status()
print(response.json())
```

## 8. 返回结构说明

成功返回示例：

```json
{
  "task_id": "demo-task-001",
  "image_url": "https://images.enterprise.com/patrol/task001.jpg",
  "status": "success",
  "message": "ok",
  "elapsed_ms": 734.15,
  "image": {
    "width": 1120,
    "height": 1494,
    "download_bytes": 276304
  },
  "results": {
    "nest_detection": {
      "task_name": "nest_detection",
      "count": 1,
      "class_counts": {
        "nest": 1
      },
      "detections": []
    },
    "tower_tilt_detection": {
      "task_name": "tower_tilt_detection",
      "count": 1,
      "warning_threshold_deg": 12.0058,
      "critical_threshold_deg": 20.384,
      "summary": {
        "normal": 1,
        "warning": 0,
        "critical": 0,
        "unreliable": 0
      },
      "detections": []
    }
  }
}
```

重点字段：

- `task_id`：任务编号
- `status`：调用状态
- `message`：结果说明
- `elapsed_ms`：总耗时
- `results.nest_detection.count`：鸟巢数量
- `results.nest_detection.detections`：鸟巢检测框
- `results.tower_tilt_detection.summary`：塔身姿态状态汇总
- `results.tower_tilt_detection.detections[].apparent_tilt_deg`：视倾角

## 9. 关于图片地址的正确理解

当前接口只接收 `http/https` 图片地址，不支持：

- Windows 本地路径
- Linux 本地路径
- 调用方电脑上的 `127.0.0.1`
- 数据库连接串
- 数据库主键或附件 ID

以下写法都不能直接调用：

```text
C:\Users\Administrator\Desktop\test_images\a.jpg
/home/user/images/a.jpg
http://127.0.0.1:9000/a.jpg
mysql://db-host:3306/power
image_id=12345
```

原因：

- 识别服务运行在云服务器，不在调用方电脑上
- 云服务器无法直接读取调用方本地磁盘
- `127.0.0.1` 对云服务器来说指向云服务器自己
- 当前服务不是数据库直连接口

## 10. 企业数据库公网 IP 场景说明

如果企业当前已经有数据库公网 IP，仍需进一步确认：

- 企业是否已经提供了可下载图片 URL

可以直接调用的情况：

```text
https://enterprise.com/api/file/download?id=12345
https://enterprise.com/static/patrol/task001.jpg
https://oss.enterprise.com/patrol/task001.jpg
```

不能直接调用的情况：

- 只有数据库公网 IP
- 只有图片在数据库中的二进制字段
- 只有业务主键或附件 ID

结论：

**企业数据库公网 IP 本身不能直接替代 `image_url`。**

## 11. 如何验证图片 URL 可用

最稳妥的方法是在识别服务所在服务器上执行：

```bash
curl -I "https://images.enterprise.com/patrol/task001.jpg"
```

如果服务端能够返回 `200`，再发起正式识别请求。

## 12. 常见错误

### 12.1 401 Unauthorized

原因：

- 没带 token
- token 错误

处理：

- 检查 `Authorization: Bearer 88888888`

### 12.2 400 image_url is required

原因：

- 请求体中没有 `image_url`
- `image_url` 为空

### 12.3 400 failed to download image

原因：

- 图片地址不可访问
- 云服务器无法下载图片
- 图片内容不是合法图片

处理：

- 在云服务器执行 `curl -I 图片URL`

### 12.4 502 Bad Gateway

原因：

- Nginx 到后端服务异常
- 后端进程异常退出

处理：

- 查看 `var/logs/service.log`
- 查看 `var/logs/audit.log`
- 查看 `/var/log/nginx/error.log`

## 13. 建议

- 演示阶段可继续使用当前公网地址
- 正式对接建议使用域名和 HTTPS
- 正式对接前请替换演示 token
- 企业若暂时只有数据库公网 IP，建议先补图片下载服务层
