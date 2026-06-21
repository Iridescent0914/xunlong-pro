# 安装指南

本指南提供SmartFin在不同操作系统上的详细安装步骤。

## 系统要求

### 最低要求

- **操作系统**: macOS、Linux 或 Windows 10/11
- **Python**: 3.10 或更高版本
- **内存**: 最低4GB，推荐8GB
- **磁盘空间**: 2GB可用空间
- **网络连接**: 需要稳定的互联网连接（用于LLM API调用和网络搜索）

### 推荐配置

- **Python**: 3.11 或 3.12
- **内存**: 16GB RAM以获得更好性能
- **磁盘空间**: 5GB用于存储生成的项目
- **网络**: 稳定的高速互联网连接

## 分步安装指南

### 1. 安装Python

::: tabs

== macOS

**使用Homebrew（推荐）：**
```bash
# 如果未安装Homebrew，先安装
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装Python
brew install python@3.11

# 验证安装
python3 --version
```

**使用官方安装器：**
从 [python.org](https://www.python.org/downloads/macos/) 下载

== Linux (Ubuntu/Debian)

```bash
# 更新包列表
sudo apt update

# 安装Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip

# 验证安装
python3.11 --version
```

== Linux (CentOS/RHEL)

```bash
# 安装Python 3.11
sudo dnf install python3.11 python3.11-pip

# 验证安装
python3.11 --version
```

== Windows

**使用Python安装器：**
1. 从 [python.org](https://www.python.org/downloads/windows/) 下载
2. 运行安装程序
3. ✅ 勾选 "Add Python to PATH"
4. 点击 "Install Now"

**验证安装：**
```powershell
python --version
```

:::

### 2. 克隆仓库

```bash
# 使用HTTPS
git clone https://github.com/jaguarliuu/SmartFin.git
cd SmartFin

# 或使用SSH
git clone git@github.com:jaguarliuu/SmartFin.git
cd SmartFin
```

::: tip 没有Git？
如果没有安装Git:
- macOS: `brew install git`
- Linux: `sudo apt install git`
- Windows: 从 [git-scm.com](https://git-scm.com/) 下载
:::

### 3. 创建虚拟环境

::: tabs

== macOS/Linux

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 命令提示符现在应该显示 (venv)
```

== Windows (PowerShell)

```powershell
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\Activate.ps1

# 如果遇到执行策略错误：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

== Windows (命令提示符)

```cmd
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate.bat
```

:::

::: warning 保持虚拟环境激活
运行SmartFin之前，始终要激活虚拟环境。激活后终端提示符会显示 `(venv)`。
:::

### 4. 安装Python依赖

```bash
# 升级pip
pip install --upgrade pip

# 安装依赖
pip install -r requirements.txt
```

这将安装所有必需的包，包括：
- LangChain & LangGraph
- OpenAI/Anthropic客户端
- Playwright
- 导出库（WeasyPrint、python-pptx、python-docx）

### 5. 安装系统依赖

#### PDF导出（WeasyPrint）

::: tabs

== macOS

```bash
# 安装系统库
brew install pango gdk-pixbuf libffi
```

== Ubuntu/Debian

```bash
# 安装必需的库
sudo apt-get update
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

== CentOS/RHEL

```bash
# 安装必需的库
sudo yum install -y \
    pango \
    gdk-pixbuf2 \
    libffi-devel
```

== Windows

Windows上的WeasyPrint需要GTK+：

1. 从 [gtk.org](https://www.gtk.org/docs/installations/windows/) 下载GTK+安装器
2. 安装到默认位置
3. 将GTK+添加到PATH

**替代方案：** 使用WSL（Windows子系统Linux）以便更容易安装。

:::

#### 网页搜索（Playwright）

```bash
# 安装Playwright浏览器
playwright install chromium

# 或安装所有浏览器
playwright install
```

::: details Playwright故障排除
如果遇到问题：

```bash
# 为Playwright安装系统依赖
playwright install-deps chromium

# 在Ubuntu/Debian上
sudo apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2
```
:::

### 6. 配置环境变量

#### 创建.env文件

```bash
# 复制示例配置
cp .env.example .env

# 编辑文件
nano .env  # 或使用 vim .env，或你喜欢的编辑器
```

#### 配置LLM提供商

从以下提供商中选择**一个**并添加你的API密钥：

::: code-group

```env [OpenAI]
# OpenAI配置
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o

# 可选：设置为默认提供商
DEFAULT_LLM_PROVIDER=openai
```

```env [Anthropic]
# Anthropic配置
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx
ANTHROPIC_MODEL=claude-3-5-sonnet-20251022

# 可选：设置为默认提供商
DEFAULT_LLM_PROVIDER=anthropic
```

```env [DeepSeek]
# DeepSeek配置
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 可选：设置为默认提供商
DEFAULT_LLM_PROVIDER=deepseek
```

:::

#### 可选：添加搜索API

```env
# Perplexity搜索（推荐）
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxx
PERPLEXITY_MODEL=sonar
```

#### 可选：添加可观测性

```env
# LangFuse配置
LANGFUSE_PUBLIC_KEY=pk-xxxxxxxxxxxxx
LANGFUSE_SECRET_KEY=sk-xxxxxxxxxxxxx
LANGFUSE_HOST=https://cloud.langfuse.com
```

::: tip 获取API密钥
- **OpenAI**: [platform.openai.com](https://platform.openai.com/api-keys)
- **Anthropic**: [console.anthropic.com](https://console.anthropic.com/)
- **DeepSeek**: [platform.deepseek.com](https://platform.deepseek.com/)
- **Perplexity**: [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
- **LangFuse**: [cloud.langfuse.com](https://cloud.langfuse.com/)
:::

### 7. 验证安装

运行验证脚本：

```bash
python -c "
import sys
print(f'Python版本: {sys.version}')

try:
    import langchain
    print('✅ LangChain已安装')
except ImportError:
    print('❌ LangChain未安装')

try:
    import playwright
    print('✅ Playwright已安装')
except ImportError:
    print('❌ Playwright未安装')

try:
    import weasyprint
    print('✅ WeasyPrint已安装')
except ImportError:
    print('❌ WeasyPrint未安装')

print('安装检查完成！')
"
```

### 8. 测试安装

生成第一份报告：

```bash
python SmartFin.py report "测试报告" --verbose
```

如果成功，你应该看到：
- 搜索进度指示器
- 内容生成步骤
- 最终报告保存到 `storage/` 目录

## 安装后配置

### 更新SmartFin

```bash
# 拉取最新更改
git pull origin master

# 更新依赖
pip install -r requirements.txt --upgrade

# 更新Playwright浏览器
playwright install chromium
```

### 卸载

```bash
# 停用虚拟环境
deactivate

# 删除虚拟环境
rm -rf venv

# 删除生成的项目（可选）
rm -rf storage/

# 删除配置
rm .env
```

## 故障排除

### 常见问题

#### 问题：`ModuleNotFoundError`

**解决方案：**
```bash
# 确保虚拟环境已激活
source venv/bin/activate  # macOS/Linux
# 或
.\venv\Scripts\Activate.ps1  # Windows

# 重新安装依赖
pip install -r requirements.txt
```

#### 问题：macOS上WeasyPrint失败

**解决方案：**
```bash
# 重新安装正确的库路径
brew reinstall pango gdk-pixbuf libffi

# 设置库路径
export DYLD_LIBRARY_PATH=/opt/homebrew/lib:$DYLD_LIBRARY_PATH

# 再次尝试
python SmartFin.py export <项目ID> pdf
```

#### 问题：找不到Playwright浏览器

**解决方案：**
```bash
# 重新安装浏览器
playwright install chromium --force

# 或带依赖安装
playwright install chromium --with-deps
```

#### 问题：Linux上权限被拒绝

**解决方案：**
```bash
# 使脚本可执行
chmod +x SmartFin.py

# 或使用python运行
python SmartFin.py report "测试"
```

#### 问题：找不到API密钥

**解决方案：**
- 检查项目根目录是否存在 `.env` 文件
- 验证API密钥格式（无引号、无空格）
- 确保环境变量已加载
- 尝试重启终端

### 获取帮助

如果仍有问题：

1. 查看 [常见问题](/zh/guide/faq)
2. 搜索 [GitHub Issues](https://github.com/jaguarliuu/SmartFin/issues)
3. 创建新issue，包含：
   - 操作系统和Python版本
   - 完整错误信息
   - 重现步骤

## 下一步

现在SmartFin已安装完成：

- 📖 阅读[快速开始指南](/zh/guide/getting-started)
- 🏗️ 理解[系统架构](/zh/guide/architecture)
- 📊 尝试[报告生成](/zh/guide/features/report)
- 📖 探索[小说创作](/zh/guide/features/fiction)
- 🎨 制作[PPT演示](/zh/guide/features/ppt)
