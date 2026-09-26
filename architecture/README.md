# 架构图使用指南

[本地项目文档](../local-docs/README.md) 是阅读入口。本目录保存可维护的图源：

- `likec4/model.c4` 是架构事实的单一来源；`likec4/views.c4` 选择系统边界和运营内部视图。LikeC4 的组件表示运行职责，而不是目录的一一映射。仓库外的 reveille、训记 API、Gmail、opencode 和 Discord 作为外部系统出现。
- `diagrams/source/runtime-dependencies.d2` 解释本机运行依赖；`daily-report.d2` 与 `task-health.d2` 描述具体操作流程，不作为另一份架构模型。生成的 SVG 位于 `diagrams/generated/`，与源图一起维护。

## 本机查看

需 Node、npm、D2 CLI、Docker（本机 Kroki 镜像 `yuzutech/kroki:0.32.1`）；首次运行先在 `architecture/` 执行 `npm ci`，并预先拉取镜像。所有图仅发往 `127.0.0.1` 的本机 Kroki，不发送至公共服务。

```sh
./architecture/scripts/validate
./architecture/scripts/render-all
./architecture/scripts/serve
# 打开 http://localhost:5173，在 viewer 中切换 context / operations
```

`validate` 会校验 LikeC4、D2 语法与 D2 的本地渲染；`render-all` 将 SVG 更新到 `diagrams/generated/`。修改 D2 后必须同步更新并检查生成的 SVG；不要直接编辑 SVG。LikeC4 使用原生 viewer 而非 Kroki；如需额外导出静态 PNG，可运行 `architecture/node_modules/.bin/likec4 export png architecture/likec4 --flat -o architecture/diagrams/generated`，但还需安装与 Playwright 版本匹配的 Chromium headless shell。不要把真实 profile、邮件内容或密钥放进图中。
