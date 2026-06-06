# 小红书笔记提取工具

一个提取小红书（RedNote）笔记内容的小工具，支持自动登录、内容提取、OCR 识别和批量下载。提供命令行工具和 Web 界面两种使用方式。

直接粘贴小红书分享文本或笔记链接即可提取。

基于 [asimovVong/xhs-extractor](https://github.com/asimovVong/xhs-extractor) 二次开发。

## 功能

- **自动登录管理**：使用 Playwright 实现网页登录，登录态持久化保存，一次登录长期使用
- **浏览器自动检测**：优先使用系统自带的 Edge 浏览器，没有 Edge 时回退到 Chrome 或 Chromium
- **内容提取**：自动提取笔记标题、正文、作者、图片等完整信息
- **OCR 文字识别**：识别图片中的文字内容，支持流式逐张返回结果
- **批量下载**：支持下载笔记正文（Markdown 格式）和图片到本地
- **Web 界面**：提供图形化界面，提取后可随时触发 OCR、下载等操作
- **命令行工具**：提供 CLI 工具，支持脚本化和自动化

## 快速开始

### 前置要求

- Python 3.8+
- 一个小红书账号

### 安装步骤

**1. 获取项目文件**

使用 Git：

```bash
git clone https://github.com/yourusername/xhs-extractor.git
cd xhs-extractor
```

或者直接下载 ZIP 压缩包：访问项目 GitHub 页面，点击页面右上角的绿色 "Code" 按钮，选择 "Download ZIP"，解压到本地目录后进入该文件夹。

**2. 一键启动**

macOS / Linux 用户双击运行 `一键启动_mac.sh` 文件，或在终端中执行：

```bash
./一键启动_mac.sh
```

Windows 用户双击运行 `一键启动_win.bat` 文件即可。

一键启动脚本会自动完成依赖检查与安装、登录状态检查（未登录时引导登录）以及 Web 界面的启动。首次使用时脚本会自动安装依赖并引导登录，之后直接启动即可。

首次使用会弹出浏览器窗口进行登录，登录态保存在 `xhs_extractor_module/browser_data/` 目录中，请勿分享给他人。

---

### 手动安装

如果你更喜欢手动控制每个步骤，可以按照以下方式操作：

**1. 安装依赖**

```bash
pip install playwright requests beautifulsoup4 streamlit
```

**2. 首次登录**

```bash
python -m xhs_extractor_module.xhs_login
```

这会打开浏览器，完成登录后按回车即可。登录态会自动保存。

**3. 启动 Web 界面**

```bash
streamlit run xhs_extractor_module/web_app.py
```

或者使用命令行工具：

```bash
python -m xhs_extractor_module.cli
```

### 使用方式

#### 方式一：Web 界面

一键启动脚本会自动完成依赖检查、登录检查和启动，无需其他操作。macOS / Linux 用户双击运行 `一键启动_mac.sh`，Windows 用户双击运行 `一键启动_win.bat`。

浏览器会自动打开，你可以直接粘贴小红书分享文本或笔记 URL，工具会自动识别。点击"开始提取"后，正文和图片即刻展示。提取完成后，随时可以点击 OCR 识别、下载图片、下载正文等按钮，无需重建任务。

#### 方式二：命令行工具

```bash
# 交互式模式
python -m xhs_extractor_module.cli

# 直接提取（支持两种输入方式）
python -m xhs_extractor_module.cli "算法面经... http://xhslink.com/o/ABC123 复制后打开【小红书】查看笔记！"
python -m xhs_extractor_module.cli --url "https://www.xiaohongshu.com/explore/..."

# 启用 OCR
python -m xhs_extractor_module.cli --ocr "分享文本..."

# 保存到文件
python -m xhs_extractor_module.cli --output result.txt "分享文本..."
```

#### 方式三：Python API

```python
from xhs_extractor_module.xhs_fetch import fetch_note_from_url

note = fetch_note_from_url("https://www.xiaohongshu.com/explore/...")

print(f"标题: {note.title}")
print(f"作者: {note.author}")
print(f"正文: {note.text}")
print(f"图片: {len(note.images)} 张")
```

## 项目结构

```
xhs-extractor/
├── xhs_extractor_module/     # 核心模块
│   ├── xhs_share.py         # 分享文本解析
│   ├── xhs_login.py         # 登录管理
│   ├── xhs_fetch.py         # 内容抓取
│   ├── xhs_parser.py        # HTML 解析（备用方案）
│   ├── browser_config.py    # 浏览器自动检测与配置
│   ├── ocr.py               # OCR 识别
│   ├── models.py            # 数据模型
│   ├── cli.py               # 命令行工具
│   ├── web_app.py           # Web 应用
│   └── ...
├── README.md                 # 项目说明（本文件）
├── 一键启动_win.bat           # Windows 一键启动
├── 一键启动_mac.sh            # macOS/Linux 一键启动
└── .gitignore
```

## 配置说明

### 可选依赖

OCR 功能（可选）：

```bash
pip install paddleocr paddlepaddle
```

OCR 适用于快速提取图片中的文字信息。如需更准确的识别或深度分析，建议导出 Markdown 后使用多模态 LLM。

LLM 文档整理（可选）：OCR 完成后，可调用 LLM 将碎片化的 OCR 文本整理为连贯文章。需先安装依赖并在界面中配置 API Key。

```bash
pip install openai
```

Web 界面（可选）：

```bash
pip install streamlit
```

### 登录态管理

- 登录态保存在 `xhs_extractor_module/browser_data/` 目录
- 登录态过期后，重新运行登录脚本即可
- 可通过环境变量 `XHS_BROWSER=edge|chrome|chromium` 手动指定浏览器

## 保存的文件结构

```
保存目录/
└── 笔记标题/
    ├── 笔记标题.md          # Markdown 格式的笔记正文
    ├── image_001.jpg        # 图片 1
    ├── image_002.jpg        # 图片 2
    └── ...
```

Markdown 文件包含笔记标题、链接、正文内容和 OCR 结果（如有）。

## 注意事项

1. 本工具仅供个人学习和研究使用，请遵守相关法律法规和网站服务条款
2. 登录信息保存在本地，请妥善保管，不要分享给他人
3. 请合理使用，避免频繁请求，尊重网站服务器
4. 提取的内容请妥善保管，注意隐私保护

## 常见问题

### Q: 提示"未找到登录态"

A: 运行 `python -m xhs_extractor_module.xhs_login` 进行首次登录。

### Q: OCR 功能不可用

A: 安装 OCR 依赖：`pip install paddleocr paddlepaddle`

### Q: 提取失败或内容为空

A: 检查登录态是否过期（重新登录）、确认分享文本中包含有效链接、检查网络连接。

### Q: Web 应用无法启动

A: 确认已安装 streamlit（`pip install streamlit`），并从项目根目录运行（`streamlit run xhs_extractor_module/web_app.py`）。

### Q: 双击 bat / sh 文件没反应

A: macOS 用户右键点击文件，选择"打开方式" → "终端"；或在终端中执行 `chmod +x 文件名.sh && ./文件名.sh`。Windows 用户确保文件扩展名是 `.bat` 而非 `.txt`，如有安全警告选择"仍要运行"。

### Q: 安装依赖很慢或失败

A: 检查网络连接。也可以跳过一键启动，按照上方手动安装步骤执行。

### Q: 登录后仍提示未登录

A: 重新运行 `python -m xhs_extractor_module.xhs_login`，确保在浏览器中成功登录后回到终端按回车确认。
