# 工程目录说明

当前项目已经按“可运行工程”和“研究资产”拆分为以下顶层结构：

```text
apps/        服务入口
src/         业务源码
models/      运行时模型资产
deploy/      Windows / systemd / Nginx 部署模板
config/      环境变量样例
docs/        工程与接口文档
examples/    请求与响应样例
var/         运行时日志等产物
research/    训练、实验、演示资产
artifacts/   历史打包产物
```

推荐理解方式：

- `apps/` + `src/` + `models/` 是部署必需部分
- `deploy/` + `config/` 是交付与运维部分
- `research/` 是研发资产，不应进入生产镜像
- `artifacts/` 是历史离线包归档，不参与当前运行
