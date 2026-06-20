# 📚 XunLong Documentation Site Setup Guide

VitePress文档站已成功搭建！以下是完整的使用指南。

## ✅ 已完成的工作

### 1. 项目结构
```
XunLong/
├── docs/                          # 文档站根目录
│   ├── .vitepress/
│   │   └── config.mts            # VitePress配置文件
│   ├── public/
│   │   └── icon.png              # 项目Logo
│   ├── guide/                     # 英文文档
│   │   ├── getting-started.md
│   │   └── architecture.md
│   ├── zh/                        # 中文文档
│   │   ├── guide/
│   │   │   ├── getting-started.md
│   │   │   └── architecture.md
│   │   └── index.md
│   ├── index.md                   # 英文首页
│   ├── package.json
│   ├── README.md
│   └── start.sh                   # 快速启动脚本
├── .github/
│   └── workflows/
│       └── deploy-docs.yml        # GitHub Pages自动部署
└── DOCS_SETUP.md                  # 本文件
```

### 2. 核心功能

✅ **多语言支持** - 中英文无缝切换
✅ **响应式设计** - 完美支持移动端
✅ **全文搜索** - 内置搜索功能
✅ **Mermaid图表** - 支持架构图和流程图
✅ **代码高亮** - 多语言语法高亮
✅ **自动部署** - GitHub Pages自动发布

### 3. 已创建的文档页面

**英文版:**
- 首页 (Home)
- 快速开始 (Getting Started)
- 系统架构 (Architecture)

**中文版:**
- 首页
- 快速开始
- 系统架构

## 🚀 快速开始

### 方法一：使用启动脚本（推荐）

```bash
cd docs
./start.sh
```

### 方法二：手动启动

```bash
cd docs
npm install
npm run docs:dev
```

访问 http://localhost:5173 查看文档站

## 📝 添加新文档

### 1. 创建新页面

```bash
# 英文文档
touch docs/guide/new-page.md

# 中文文档
touch docs/zh/guide/new-page.md
```

### 2. 编写内容

```markdown
# 页面标题

这里是内容...

## 子标题

支持所有Markdown语法，以及：

::: tip 提示
这是一个提示框
:::

​```mermaid
graph LR
    A --> B
​```
```

### 3. 添加到导航

编辑 `docs/.vitepress/config.mts`，在对应的sidebar配置中添加：

```typescript
{
  text: '新页面',
  link: '/guide/new-page'
}
```

## 🎨 自定义配置

### 修改网站信息

编辑 `docs/.vitepress/config.mts`:

```typescript
export default defineConfig({
  title: "你的标题",
  description: "你的描述",
  // ...
})
```

### 修改Logo

替换 `docs/public/icon.png` 为你自己的Logo文件

### 修改主题色

在配置文件中添加自定义CSS变量（如需要）

## 🌐 部署到GitHub Pages

### 前置条件

1. 项目已推送到GitHub
2. 仓库设置中启用GitHub Pages

### 配置步骤

1. **修改base路径**

编辑 `docs/.vitepress/config.mts`，将 `base` 改为你的仓库名：

```typescript
export default defineConfig({
  base: '/你的仓库名/',  // 例如 '/XunLong/'
  // ...
})
```

2. **启用GitHub Pages**

- 进入GitHub仓库 → Settings → Pages
- Source选择 "GitHub Actions"

3. **推送代码**

```bash
git add .
git commit -m "Add VitePress documentation"
git push origin master
```

4. **等待部署**

GitHub Actions会自动构建并部署，通常需要2-3分钟。

5. **访问文档站**

```
https://你的用户名.github.io/你的仓库名/
```

## 📊 文档结构规划

建议按以下结构组织文档：

```
docs/
├── guide/                    # 指南
│   ├── introduction.md       # 项目介绍
│   ├── getting-started.md    # 快速开始
│   ├── installation.md       # 安装
│   ├── architecture.md       # 架构
│   ├── multi-agent.md        # 多智能体
│   ├── workflow.md           # 工作流
│   └── features/             # 功能详解
│       ├── report.md
│       ├── fiction.md
│       ├── ppt.md
│       ├── iteration.md
│       └── export.md
├── api/                      # API文档
│   ├── cli.md               # CLI命令
│   └── configuration.md      # 配置说明
├── advanced/                 # 高级主题
│   ├── custom-templates.md
│   ├── llm-integration.md
│   └── performance.md
└── community/                # 社区
    ├── contributing.md
    ├── changelog.md
    └── faq.md
```

## 🛠️ 常用命令

```bash
# 开发模式（热重载）
npm run docs:dev

# 构建生产版本
npm run docs:build

# 预览生产版本
npm run docs:preview

# 清理缓存
rm -rf .vitepress/cache
```

## 💡 写作技巧

### 使用自定义容器

```markdown
::: tip 提示
这是一个提示
:::

::: warning 警告
这是一个警告
:::

::: danger 危险
这是一个危险警告
:::

::: details 点击展开
这是详细内容
:::
```

### 代码组（Tabs）

```markdown
::: code-group

​```bash [npm]
npm install vitepress
​```

​```bash [pnpm]
pnpm install vitepress
​```

​```bash [yarn]
yarn add vitepress
​```

:::
```

### 徽章

```markdown
<Badge type="info" text="info" />
<Badge type="tip" text="tip" />
<Badge type="warning" text="warning" />
<Badge type="danger" text="danger" />
```

## 🔗 有用的链接

- [VitePress官方文档](https://vitepress.dev/)
- [Markdown扩展语法](https://vitepress.dev/guide/markdown)
- [配置参考](https://vitepress.dev/reference/site-config)
- [主题配置](https://vitepress.dev/reference/default-theme-config)

## ❓ 常见问题

### Q: 如何添加Google Analytics？

在 `config.mts` 中添加：

```typescript
export default defineConfig({
  head: [
    ['script', { async: '', src: 'https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID' }],
    ['script', {}, `window.dataLayer = window.dataLayer || [];
      function gtag(){dataLayer.push(arguments);}
      gtag('js', new Date());
      gtag('config', 'GA_MEASUREMENT_ID');`
    ]
  ]
})
```

### Q: 如何自定义主题？

创建 `docs/.vitepress/theme/index.ts`:

```typescript
import DefaultTheme from 'vitepress/theme'
import './custom.css'

export default DefaultTheme
```

### Q: Mermaid图表不显示？

VitePress 1.0+ 原生支持Mermaid，直接使用 ` ```mermaid ` 代码块即可。

## 🎉 下一步

1. ✅ 完善各个文档页面内容
2. ✅ 添加更多示例和教程
3. ✅ 补充API文档
4. ✅ 添加贡献指南
5. ✅ 配置SEO优化
6. ✅ 添加sitemap

---

**需要帮助？** 查看 [VitePress官方文档](https://vitepress.dev/) 或提issue！
