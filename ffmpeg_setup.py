"""解析 config.yaml 中的 FFmpeg 位置,并接管 pydub 的实际调用路径。

pydub 默认只在 PATH 中查找可执行文件:ffmpeg 用于转码与导出,ffprobe 用于读取音频信息。
当 FFmpeg 没有加入 PATH 时,可在 config.yaml 的 ffmpeg 段中指定位置,
由本模块解析为绝对路径后写回 pydub。
"""
import os
import shutil
from types import SimpleNamespace

from pydub import AudioSegment
from pydub import utils as pydub_utils

# 与 pydub 保持一致:优先 ffmpeg/ffprobe,其次兼容 avconv/avprobe。
_ENCODER_NAMES = ("ffmpeg", "avconv")
_PROBER_NAMES = ("ffprobe", "avprobe")


def _expand_path(value, base_dir):
    """展开环境变量与 ~;相对路径按 base_dir 转成绝对路径。"""
    text = os.path.expandvars(os.path.expanduser(str(value).strip()))
    if not text:
        return ""
    if not os.path.isabs(text):
        text = os.path.join(base_dir, text)
    return os.path.normpath(text)


def _executable_name(name):
    return f"{name}.exe" if os.name == "nt" else name


def _resolve(label, key, configured_path, directory, names, base_dir, notes):
    """按“显式文件路径 -> 指定目录 -> PATH”的顺序解析可执行文件。"""
    if configured_path:
        candidate = _expand_path(configured_path, directory or base_dir)
        if os.path.isfile(candidate):
            notes.append(f"{label}: {candidate} (来自 ffmpeg.{key} 配置)")
            return candidate
        notes.append(f"{label}: ffmpeg.{key} 指向的文件不存在,已忽略 -> {candidate}")

    if directory:
        for name in names:
            candidate = os.path.join(directory, _executable_name(name))
            if os.path.isfile(candidate):
                notes.append(f"{label}: {candidate} (来自 ffmpeg.directory 配置)")
                return candidate
        notes.append(f"{label}: ffmpeg.directory 下未找到 {_executable_name(names[0])} -> {directory}")

    for name in names:
        found = shutil.which(name)
        if found:
            notes.append(f"{label}: {found} (来自 PATH)")
            return found

    notes.append(f"{label}: 未找到")
    return None


def configure_ffmpeg(settings, base_dir):
    """按配置设置 pydub 使用的 ffmpeg 与 ffprobe。

    返回 SimpleNamespace(ffmpeg=..., ffprobe=..., notes=[...]);未解析到的项为 None,
    notes 是便于排查的逐项说明。
    """
    config = getattr(settings, "ffmpeg", None) or SimpleNamespace()
    directory = _expand_path(getattr(config, "directory", "") or "", base_dir)

    notes = []
    ffmpeg_path = _resolve(
        "ffmpeg", "ffmpeg_path", getattr(config, "ffmpeg_path", ""), directory,
        _ENCODER_NAMES, base_dir, notes,
    )
    ffprobe_path = _resolve(
        "ffprobe", "ffprobe_path", getattr(config, "ffprobe_path", ""), directory,
        _PROBER_NAMES, base_dir, notes,
    )

    if ffmpeg_path:
        # converter 在 pydub 导入时就已确定,必须显式覆盖。
        AudioSegment.converter = ffmpeg_path
    if ffprobe_path:
        # pydub 只在 PATH 中查找 ffprobe(pydub.utils.get_prober_name),这里接管为解析结果。
        pydub_utils.get_prober_name = lambda: ffprobe_path

    return SimpleNamespace(ffmpeg=ffmpeg_path, ffprobe=ffprobe_path, notes=notes)
