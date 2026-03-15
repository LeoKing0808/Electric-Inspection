# 接口对接规范

## 1. 文档目的

本文档面向企业系统开发人员，说明如何将电力巡检智能识别服务接入现有业务平台。

当前服务统一提供一条识别接口，用于对单张图片同时执行：

- 鸟巢检测
- 塔身姿态检测

## 2. 接口地址

标准接口如下：

```text
POST /api/v1/inspect
```

健康检查接口：

```text
GET /healthz
```

正式对接时，企业应使用部署后的域名或服务器地址，例如：

```text
https://inspection.example.com/api/v1/inspect
```

## 3. 鉴权方式

请求头必须携带：

```text
Content-Type: application/json
```

如果服务端启用了 token 鉴权，则调用方还需携带以下任一请求头：

```text
Authorization: Bearer your-token
```

或：

```text
X-API-Key: your-token
```

## 4. 请求体

请求体格式固定为：

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/patrol/task001.jpg"
}
```

字段说明：

- `task_id`：调用方任务编号，服务端原样返回
- `image_url`：图片下载地址，必须是服务端可直接访问的 `http/https` 地址

## 5. 图片来源要求

当前服务只支持远程图片 URL，不支持：

- 上传本地文件
- 传 Windows 或 Linux 本地路径
- 传数据库主键、附件 ID、文件 ID
- 直接连接企业数据库读取图片

调用方需要保证：

- `image_url` 可以从服务端所在机器访问
- 图片内容可直接下载
- 图片可被 OpenCV 正常解码

## 6. 企业数据库公网 IP 场景说明

如果企业已经有数据库公网 IP，需要区分两种情况：

### 6.1 可直接接入

如果企业已经能够提供可下载图片地址，例如：

```text
https://enterprise.com/api/file/download?id=12345
https://enterprise.com/static/patrol/task001.jpg
https://oss.enterprise.com/patrol/task001.jpg
```

则可以直接把该地址作为 `image_url` 调用本服务。

### 6.2 不能直接接入

如果企业当前只有：

- 数据库公网 IP
- 数据库表中的图片二进制字段
- 文件 ID、附件 ID、对象主键

则不能直接调用当前接口。

原因是当前服务是“图片 URL 识别接口”，不是“数据库直连接口”。

## 7. 推荐接入方式

推荐企业按以下链路接入：

1. 企业业务系统生成图片下载 URL
2. 企业业务系统调用识别接口
3. 传入 `task_id + image_url`
4. 接收统一 JSON 结果
5. 将结果落库或写入业务流程

## 8. 成功返回结构

成功返回示例：

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/patrol/task001.jpg",
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

## 9. 错误返回结构

错误返回示例：

```json
{
  "task_id": "task-20260315-001",
  "image_url": "https://files.example.com/patrol/task001.jpg",
  "status": "error",
  "message": "failed to download image: 404 Client Error"
}
```

常见状态码：

- `200`：请求成功
- `400`：请求参数错误或图片下载失败
- `401`：鉴权失败
- `500`：服务内部异常或模型配置异常

## 10. 字段重点

企业接入时通常重点关注以下字段：

- `task_id`
- `status`
- `message`
- `elapsed_ms`
- `results.nest_detection.count`
- `results.nest_detection.detections`
- `results.tower_tilt_detection.count`
- `results.tower_tilt_detection.summary`
- `results.tower_tilt_detection.detections`

## 11. 接口边界

当前接口边界如下：

- 单张图片同步调用
- 固定任务集合，当前为鸟巢检测和塔身姿态检测
- 图片拉取方式为 `http/https`
- 当前下载模块不支持额外请求头、Cookie 或签名逻辑注入

如果企业图片源带鉴权或专线访问规则，需要按企业要求扩展下载模块。

## 12. 对接建议

建议企业联调时按以下顺序推进：

1. 先用少量可公开访问图片完成接口联调
2. 再切换到企业正式图片源
3. 对齐返回字段和告警等级
4. 再考虑更多任务扩展和性能优化
