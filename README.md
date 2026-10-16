# 音频跟读生成器

按静音位置拆分音频，为每个片段生成“原读 N 遍 + 跟读 M 遍”的练习音频，并在切换时插入提示音。

## 环境要求

- uv：统一管理 Python、项目虚拟环境和 Python 依赖。
- FFmpeg：独立的系统工具，不由 uv 安装，用于 MP3、AAC 等格式的读取与导出。可加入 `PATH`，也可在 `config.yaml` 的 `ffmpeg.directory` 中指定位置（见“FFmpeg 配置”）。
- 桌面环境：程序使用 Python 自带的 Tkinter 弹出文件选择窗口。Linux 上可能需要额外安装 Tk 的系统运行库。

Windows 可在 PowerShell 中使用 uv 官方安装脚本：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装后重新打开终端，确认以下命令可用：

```powershell
uv --version
ffmpeg -version
ffprobe -version
```

## 初始化与运行

在项目根目录执行：

```powershell
uv sync --locked
uv run --locked python main.py
```

uv 会按 `.python-version` 选择 Python 3.13，必要时自动下载 uv 管理的 Python，并在项目内创建 `.venv`。无需自行安装 Python、手动激活虚拟环境或执行 `pip install`。

Windows 也可以直接双击 `starter.bat`；启动脚本会切换到项目目录，并通过 uv 同步锁定的依赖后运行程序。首次运行需要联网下载 Python 或缺失的依赖。

选择一个或多个音频文件后，按终端提示设置原读遍数、跟读遍数、静音阈值等参数。输出文件位于第一个所选音频旁的 `原读N遍-跟读M遍` 文件夹内，文件名添加 `_processed` 后缀。

## 配置

默认设置位于 `config.yaml`。如需个人设置，可以在同一目录创建 `config.local.yaml`，只填写需要覆盖的字段，例如：

```yaml
defaults:
  origin_times: 2
  repeat_times: 3
```

本地配置会递归覆盖默认配置，且已被 `.gitignore` 忽略。四个提示音 MP3 文件应保留在项目根目录，文件名通过 `config.yaml` 的 `markers` 配置指定。

## FFmpeg 配置

程序用 FFmpeg 读写音频：`ffmpeg` 负责转码与导出，`ffprobe` 负责读取音频信息。二者可以放在 `PATH` 中，也可以用配置指定：

```yaml
ffmpeg:
  directory: ""     # ffmpeg 与 ffprobe 所在目录
  ffmpeg_path: ""   # 可选：直接指定 ffmpeg 可执行文件
  ffprobe_path: ""  # 可选：直接指定 ffprobe 可执行文件
```

查找顺序为逐项回退：

1. `ffmpeg_path` / `ffprobe_path` 指定的文件；
2. `directory` 目录下的 `ffmpeg.exe` / `ffprobe.exe`（非 Windows 为 `ffmpeg` / `ffprobe`）；
3. 系统 `PATH`。

`ffmpeg_path` 与 `ffprobe_path` 填相对路径时以 `directory` 为基准；`directory` 填相对路径时以项目目录为基准；三者都支持 `~` 与 `%VAR%` / `$VAR` 形式的环境变量。两项都找不到时，程序会在启动时提示并退出。

本机路径建议写在 `config.local.yaml`（已被忽略，不会提交）：

```yaml
ffmpeg:
  directory: C:\ZQ\Dev\DevTools\ffmpeg\bin
```

启动时会打印实际使用的 `ffmpeg` 与 `ffprobe` 路径及来源，便于排查。

### 获取 FFmpeg（Windows）

ffmpeg.org 为 Windows 推荐的两个来源：

- gyan.dev 的 release essentials ZIP（推荐，解压即用，已含 MP3 编解码）：https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip
- GitHub 上的 BtbN 构建：https://github.com/BtbN/FFmpeg-Builds/releases/latest

解压到固定目录后，把其中的 `bin` 目录填到 `ffmpeg.directory` 即可，无需修改系统 `PATH`。注意 gyan.dev 的 git master 与 full 变体只提供 `.7z`。

## Python 与依赖管理

- `.python-version` 固定 Python 3.13 系列；`pyproject.toml` 声明支持的 Python 范围和直接依赖。
- 仅使用 uv 管理的 Python，不依赖系统 `python` 命令或全局 Python 包。
- `pydub` 负责音频处理，`PyYAML` 负责读取配置。
- Python 3.13 已移除标准库 `audioop`，因此显式安装 `audioop-lts`，兼容 `pydub` 的音频操作。
- `uv.lock` 记录精确依赖版本、来源和校验值，应与 `pyproject.toml`、`.python-version` 一起提交；`.venv` 不应提交。
- 项目按脚本应用管理，不打包或安装项目本身，保留现有脚本与音频资源的相对路径。

常用命令：

```powershell
uv add <包名>
uv remove <包名>
uv lock --upgrade
uv sync --locked
uv run --locked python main.py
```

添加、删除或升级依赖后，检查并提交 `pyproject.toml` 和 `uv.lock` 的变更。日常启动使用 `--locked`，配置与锁文件不一致时会报错，而不是静默改写锁文件。

如果要切换 Python 的次版本，请同时调整 `.python-version` 和 `pyproject.toml` 的 `requires-python`，再执行 `uv lock` 与 `uv sync --locked`，并验证音频处理及 Tkinter 兼容性。
