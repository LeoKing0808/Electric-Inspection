# 企业数据库图片适配层说明

## 1. 目的

当前识别服务只接受 `image_url`，不直接读取企业数据库。

本适配层的目标是把企业数据库中的图片记录转换为短时有效的 HTTP 图片地址，或者直接代企业系统转发识别请求，从而接入现有识别服务而不改动其接口契约。

## 2. 适用场景

适配层适用于以下情况：

- 企业图片存在数据库 BLOB 字段
- 企业系统只有记录主键、业务主键或附件 ID
- 企业暂时还没有独立的图片下载服务

## 3. 提供的接口

适配层默认提供以下接口：

```text
GET  /healthz
POST /api/v1/image-url
GET  /api/v1/images/<record_id>?expires=...&signature=...
POST /api/v1/inspect-from-db
```

各接口用途如下：

- `/api/v1/image-url`
  根据数据库记录 ID 生成短时有效的图片 URL
- `/api/v1/images/<record_id>`
  根据签名 URL 读取数据库图片并返回图片内容
- `/api/v1/inspect-from-db`
  直接把 `task_id + record_id` 转换并转发到现有识别服务

## 4. 推荐接入方式

### 方式一：两步式

1. 企业系统调用 `/api/v1/image-url`
2. 获得临时 `image_url`
3. 企业系统再调用原有识别服务 `/api/v1/inspect`

优点：

- 兼容所有现有识别调用方
- 适合逐步替换原有联调链路

### 方式二：一步式

1. 企业系统调用 `/api/v1/inspect-from-db`
2. 适配层内部生成临时图片 URL 并调用识别服务
3. 适配层把识别结果原样返回

优点：

- 企业系统侧改动最小
- 更接近“直接传数据库记录给 AI 识别”

## 5. 关键配置项

适配层通过环境变量工作，核心变量如下：

```text
POWER_IMAGE_ADAPTER_HOST
POWER_IMAGE_ADAPTER_PORT
POWER_IMAGE_ADAPTER_API_TOKEN
POWER_IMAGE_ADAPTER_PUBLIC_BASE_URL
POWER_IMAGE_ADAPTER_DB_URL
POWER_IMAGE_ADAPTER_IMAGE_QUERY
POWER_IMAGE_ADAPTER_IMAGE_FIELD_ENCODING
POWER_IMAGE_ADAPTER_SIGNING_SECRET
POWER_IMAGE_ADAPTER_INSPECTION_API_URL
POWER_IMAGE_ADAPTER_INSPECTION_API_TOKEN
```

其中最关键的是：

- `POWER_IMAGE_ADAPTER_DB_URL`
  数据库连接串
- `POWER_IMAGE_ADAPTER_IMAGE_QUERY`
  读取图片的 SQL，必须包含命名参数 `:record_id`
- `POWER_IMAGE_ADAPTER_SIGNING_SECRET`
  临时图片 URL 的签名密钥
- `POWER_IMAGE_ADAPTER_PUBLIC_BASE_URL`
  识别服务真正能访问到的适配层外部地址

## 6. SQL 约束

SQL 查询结果建议使用以下别名：

```sql
SELECT
  image_blob AS image_data,
  mime_type AS mime_type,
  file_name AS file_name
FROM patrol_images
WHERE id = :record_id
```

适配层默认读取以下三个字段：

- `image_data`
- `mime_type`
- `file_name`

其中：

- `image_data` 必填
- `mime_type` 选填
- `file_name` 选填

## 7. 编码说明

`image_data` 支持以下编码方式：

- `binary`
  数据库直接返回字节流或 BLOB
- `base64`
  数据库存的是 Base64 字符串
- `hex`
  数据库存的是十六进制字符串

通过 `POWER_IMAGE_ADAPTER_IMAGE_FIELD_ENCODING` 指定。

## 8. 数据库驱动说明

项目代码使用的是 SQLAlchemy 抽象层，但数据库驱动仍需按企业实际数据库安装。

例如：

- SQLite：Python 自带，无需额外驱动
- MySQL：常见为 `pymysql`
- PostgreSQL：常见为 `psycopg`
- SQL Server：常见为 `pyodbc`
- Oracle：需按企业驱动方案安装

也就是说，仓库已经提供统一适配代码，但正式接入时仍需补齐与企业数据库匹配的驱动。

## 9. 启动方式

本地启动：

```powershell
python apps/image_adapter/run.py
```

Linux 常驻运行可参考：

- `deploy/systemd/power-image-adapter.service`
- `deploy/systemd/power-image-adapter.env.example`
- `config/env/image_adapter.env.example`

## 10. 示例请求

生成临时图片 URL：

```json
{
  "record_id": "A202603150001",
  "expires_in_sec": 300
}
```

直接从数据库转发识别：

```json
{
  "task_id": "task-20260315-001",
  "record_id": "A202603150001",
  "expires_in_sec": 300
}
```

## 11. 安全建议

建议正式环境至少做到以下几点：

- 为适配层单独配置 API token
- 签名 URL 设置短时有效，例如 300 秒
- `POWER_IMAGE_ADAPTER_PUBLIC_BASE_URL` 使用正式域名或内网固定地址
- 适配层和识别服务尽量部署在同一内网
- 不要把数据库连接串暴露给前端或外部调用方

## 12. 与主识别服务的关系

适配层是可选组件，不替代现有识别服务。

职责划分如下：

- 主识别服务：负责下载图片、模型推理、返回识别结果
- 数据库适配层：负责从数据库取图、生成临时 URL、按需转发识别

这样可以保持主识别服务简洁稳定，同时给企业数据库场景留出扩展位。
