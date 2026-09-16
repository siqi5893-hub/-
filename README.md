# 抖音媒体提取器

一个可以直接上传到 GitHub 的小型项目：输入抖音分享链接，下载视频或转换为 MP3。包含命令行、网页界面、Docker 部署和自动化测试。

## 功能

- 支持 `v.douyin.com`、`douyin.com` 和 `iesdouyin.com` 官方 HTTPS 链接
- 视频下载与 MP3 音频提取
- 可选 Netscape 格式 Cookie，适配需要登录态的作品
- 命令行与手机友好的网页界面
- Docker Compose 部署
- 链接域名白名单、无 Shell 执行、并发限制和安全响应头
- Cookie、下载文件和 `.env` 默认不会进入 Git

## 本机运行

系统需安装 Python 3.10+ 和 FFmpeg。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

将 Cookie 导出为 Netscape 格式并放在项目外，随后：

```bash
export DOUYIN_COOKIES=/绝对路径/cookies.txt
douyin-extract 'https://v.douyin.com/你的链接/'
douyin-extract --type audio 'https://v.douyin.com/你的链接/'
```

启动网页：

```bash
export APP_TOKEN='换成足够长的随机值'
douyin-extract-web
```

访问 `http://127.0.0.1:8080`。默认只监听本机。

## Docker Compose

1. 将 Cookie 文件保存为项目根目录的 `cookies.txt`；它已被 `.gitignore` 排除。
2. 新建 `.env`，写入 `APP_TOKEN=一个足够长的随机值`。
3. 执行：

```bash
docker compose up -d --build
```

Compose 在 Linux VPS 上使用宿主网络，以减少部分平台对 Docker NAT 请求的误拦截；Web 服务仍只监听 `127.0.0.1:8080`。如需互联网访问，建议通过带 HTTPS 和身份验证的反向代理开放，不要直接暴露开发服务器。Docker Desktop 不完整支持这一网络模式，在 macOS/Windows 上可删除 `network_mode: host` 并改用端口映射。

## 测试

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## 上传 GitHub

```bash
git init
git add .
git commit -m 'Initial release'
git branch -M main
git remote add origin https://github.com/你的用户名/douyin-media-extractor.git
git push -u origin main
```

上传前运行 `git status`，确认其中没有 `cookies.txt`、`.env` 或下载的媒体文件。

## 安全边界

- 后端只接受列入白名单的抖音官方域名，以降低 SSRF 风险。
- 调用 `yt-dlp` 时使用参数数组，不经过 Shell。
- 同一进程一次只执行一个提取任务，避免小型服务器被并发任务拖垮。
- 只读 Cookie 会先复制到权限为 `0600` 的临时文件，任务结束后立即删除；源文件不会被 `yt-dlp` 回写。
- 公网监听必须设置 `APP_TOKEN`；生产环境仍应使用 Nginx/Caddy HTTPS 和更完善的认证。
- 项目不会绕过付费、私密作品或平台权限控制。

## 说明

网站结构变化时可能需要升级 `yt-dlp`。请只保存你有权下载的内容，并遵守平台服务条款、著作权规则与所在地法律。
