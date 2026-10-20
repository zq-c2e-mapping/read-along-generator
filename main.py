"""跟读音频生成器:把音频按静音点切句,每句按"原读 N 遍 + 跟读 M 遍"组成一轮并重复 X 轮。

运行: uv run --locked python main.py  (FFmpeg 可在 config.yaml 指定,或加入 PATH)
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog

from pydub import AudioSegment
from pydub.silence import detect_silence

from config import settings
from ffmpeg_setup import configure_ffmpeg


COMBINATION_SHORTCUTS = {
    "1": (1, 1, "a+b"),
    "2": (2, 1, "2a+b"),
    "3": (3, 1, "3a+b"),
    "4": (1, 2, "a+2b"),
    "5": (2, 2, "2a+2b"),
    "6": (3, 2, "3a+2b"),
    "7": (3, 0, "3a+0b"),
    "8": (5, 0, "5a+0b"),
}


def get_user_inputs():
    """读取用户输入,默认值来自 config.yaml。"""
    d = settings.defaults
    inputs = {}
    silence_prompt = "静音阈值(dBFS): 低于此值则静音。例: -10(喇叭声), -30(说话声), -50(呼吸声)。(数值越负,对声音越敏感)"

    print("\n--- 原读/跟读组合快捷方式 ---")
    print("a=原读, b=跟读")
    print("  1: a+b     2: 2a+b   3: 3a+b   4: a+2b")
    print("  5: 2a+2b   6: 3a+2b  7: 3a+0b  8: 5a+0b")
    print("  0: 自定义原读次数、跟读次数和组合重复次数")

    while True:
        try:
            shortcut = input("请选择组合快捷键 (默认: 1): ").strip() or "1"
            if shortcut not in {"0", *COMBINATION_SHORTCUTS}:
                raise ValueError("快捷键必须是 0 到 8")
            break
        except ValueError as e:
            print(f"输入无效: {e}。")

    if shortcut == "0":
        while True:
            try:
                val = input(f"请输入原读遍数 n (默认: {d.origin_times}): ")
                inputs["origin_times"] = int(val) if val else d.origin_times
                if inputs["origin_times"] < 0:
                    raise ValueError("遍数不能为负")
                break
            except ValueError as e:
                print(f"输入无效: {e}. 请输入一个非负整数。")

        while True:
            try:
                val = input(f"请输入跟读遍数 m (默认: {d.repeat_times}): ")
                inputs["repeat_times"] = int(val) if val else d.repeat_times
                if inputs["repeat_times"] < 0:
                    raise ValueError("遍数不能为负")
                break
            except ValueError as e:
                print(f"输入无效: {e}. 请输入一个非负整数。")
    else:
        origin_times, repeat_times, shortcut_name = COMBINATION_SHORTCUTS[shortcut]
        inputs["origin_times"] = origin_times
        inputs["repeat_times"] = repeat_times
        print(f"已选择: {shortcut} = {shortcut_name}")

    while True:
        try:
            val = input(f"请输入‘原读+跟读’组合重复次数 (默认: {d.combination_times}): ")
            inputs["combination_times"] = int(val) if val else d.combination_times
            if inputs["combination_times"] <= 0:
                raise ValueError("重复次数必须为正数")
            break
        except ValueError as e:
            print(f"输入无效: {e}. 请输入一个正整数。")

    while True:
        try:
            val = input(f"请输入分割静音时长阈值 (毫秒, 默认: {d.min_silence_duration_for_split}): ")
            inputs["min_silence_duration_for_split"] = int(val) if val else d.min_silence_duration_for_split
            if inputs["min_silence_duration_for_split"] <= 0:
                raise ValueError("时长必须为正数")
            break
        except ValueError as e:
            print(f"输入无效: {e}. 请输入一个正整数。")

    while True:
        try:
            print(silence_prompt)
            val = input(f"请输入静音判断阈值 (dBFS, 默认: {d.silence_threshold_dbfs}): ")
            inputs["silence_threshold_dbfs"] = float(val) if val else d.silence_threshold_dbfs
            break
        except ValueError as e:
            print(f"输入无效: {e}. 请输入一个数字 (例如 -40, -50.5)。")

    while True:
        try:
            val = input(f"请输入跟读时长倍数 (默认: {d.follow_duration_multiplier}): ")
            inputs["follow_duration_multiplier"] = float(val) if val else d.follow_duration_multiplier
            if inputs["follow_duration_multiplier"] < 0:
                raise ValueError("倍数不能为负")
            break
        except ValueError as e:
            print(f"输入无效: {e}. 请输入一个非负数字。")

    print("\n--- 滴声移除设置 ---")
    while True:
        try:
            val = input(f"是否需要去除首尾滴声? (0:不需要, 1:需要, 默认: {d.remove_beep_sound}): ")
            inputs["remove_beep_sound"] = int(val) if val else d.remove_beep_sound
            if inputs["remove_beep_sound"] not in (0, 1):
                raise ValueError("请输入 0 或 1")
            break
        except ValueError as e:
            print(f"输入无效: {e}.")

    if inputs["remove_beep_sound"] == 1:
        while True:
            try:
                val = input(f"  音频开头是否存在滴声? (0:不存在, 1:存在, 默认: {d.beep_at_start}): ")
                inputs["beep_at_start"] = int(val) if val else d.beep_at_start
                if inputs["beep_at_start"] not in (0, 1):
                    raise ValueError("请输入 0 或 1")
                break
            except ValueError as e:
                print(f"输入无效: {e}.")

        while True:
            try:
                val = input(f"  音频结尾是否存在滴声? (0:不存在, 1:存在, 默认: {d.beep_at_end}): ")
                inputs["beep_at_end"] = int(val) if val else d.beep_at_end
                if inputs["beep_at_end"] not in (0, 1):
                    raise ValueError("请输入 0 或 1")
                break
            except ValueError as e:
                print(f"输入无效: {e}.")
    else:
        inputs["beep_at_start"] = 0
        inputs["beep_at_end"] = 0

    return inputs


def get_script_directory():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def load_marker_audio_safe(base_dir, filename):
    marker_path = os.path.join(base_dir, filename)
    if os.path.exists(marker_path):
        try:
            audio = AudioSegment.from_file(marker_path)
            print(f"  成功加载提示音: {filename}")
            return audio
        except Exception as e:
            print(f"  警告: 无法加载提示音文件 '{filename}'. 原因: {e}")
            return None
    print(f"  警告: 提示音文件 '{filename}' 未找到于 '{base_dir}'.")
    return None


def process_audio_file(audio_path, output_dir, params, markers):
    print(f"\n正在处理文件: {audio_path}")
    try:
        audio = AudioSegment.from_file(audio_path)
    except Exception as e:
        print(f"错误: 无法加载音频文件 {audio_path}. 原因: {e}")
        return

    origin_times = params["origin_times"]
    repeat_times = params["repeat_times"]
    combination_times = params["combination_times"]
    min_silence_len_ms = params["min_silence_duration_for_split"]
    silence_thresh_dbfs = params["silence_threshold_dbfs"]
    follow_duration_multiplier = params["follow_duration_multiplier"]
    remove_beep_sound = params["remove_beep_sound"]
    beep_at_start = params["beep_at_start"]
    beep_at_end = params["beep_at_end"]
    print(f"  滴声移除: remove={remove_beep_sound}, start={beep_at_start}, end={beep_at_end}")

    speech_marker = markers["speech_marker"]
    speech_end_marker = markers["speech_end_marker"]
    read_along_marker = markers["read_along_marker"]
    read_along_end_marker = markers["read_along_end_marker"]
    marker_padding_silence = markers["marker_padding_silence"]

    split_offset = settings.audio.split_offset_ms
    min_split_gap = settings.audio.min_split_gap_ms

    print(f"  音频时长: {len(audio) / 1000:.2f} 秒")
    print(f"  静音阈值: {silence_thresh_dbfs} dBFS, 最小分割静音长度: {min_silence_len_ms} ms")

    raw_silences = detect_silence(audio, min_silence_len=1, silence_thresh=silence_thresh_dbfs, seek_step=1)
    split_points_ms = []
    last_processed_audio_end = 0
    print("  检测到的原始静音段:")
    for silent_start, silent_end in raw_silences:
        silent_duration = silent_end - silent_start
        print(f"    - [{silent_start/1000:.3f}s - {silent_end/1000:.3f}s], 时长 {silent_duration}ms")

        if silent_start < last_processed_audio_end:
            print(f"      跳过(在已处理范围 {last_processed_audio_end/1000:.3f}s 内)。")
            continue

        is_trailing_silence_segment = (silent_end == len(audio))

        if silent_duration >= min_silence_len_ms:
            actual_split_point_calculated = -1

            if is_trailing_silence_segment:
                print(f"      末尾长静音,不产生分割点。")
                last_processed_audio_end = silent_end
                continue

            potential_split_at = silent_end - split_offset
            print(f"      中间长静音,初算分割点: {potential_split_at/1000:.3f}s")
            if potential_split_at >= silent_start:
                actual_split_point_calculated = potential_split_at
            else:
                actual_split_point_calculated = silent_start
                print(f"        修正分割点为静音开始处: {actual_split_point_calculated/1000:.3f}s")

            actual_split_point = max(0, actual_split_point_calculated)

            can_add_split_point = True
            if actual_split_point == -1:
                can_add_split_point = False
                print("      跳过无效分割点 (-1)。")

            if can_add_split_point and split_points_ms:
                if actual_split_point <= split_points_ms[-1]:
                    can_add_split_point = False
                    print(f"      跳过,不晚于上一个分割点 {split_points_ms[-1]/1000:.3f}s。")
                elif (actual_split_point - split_points_ms[-1]) <= min_split_gap:
                    can_add_split_point = False
                    print(f"      跳过,与上一个分割点过近 (<{min_split_gap}ms)。")

            if can_add_split_point:
                split_points_ms.append(actual_split_point)
                print(f"      >>>> 添加分割点: {actual_split_point/1000:.3f}s")

            last_processed_audio_end = silent_end
        else:
            print(f"      不满足分割长度 ({silent_duration}ms < {min_silence_len_ms}ms)。")

    split_points_ms = sorted(set(split_points_ms))
    if split_points_ms:
        print(f"  汇总分割点(秒): {[s/1000 for s in split_points_ms]}")
    else:
        print("  未计算出分割点。")

    segment_boundaries = [0] + split_points_ms + [len(audio)]
    segment_boundaries = sorted(set(s for s in segment_boundaries if 0 <= s <= len(audio)))

    final_boundaries = []
    if segment_boundaries:
        final_boundaries.append(segment_boundaries[0])
        for i in range(1, len(segment_boundaries)):
            if segment_boundaries[i] > segment_boundaries[i - 1]:
                final_boundaries.append(segment_boundaries[i])
    segment_boundaries = final_boundaries

    print(f"  最终边界(秒): {[s/1000 for s in segment_boundaries]}")

    if len(segment_boundaries) < 2:
        segments_initial = [audio] if len(audio) > 0 else []
    else:
        segments_initial = []
        for i in range(len(segment_boundaries) - 1):
            start_ms = segment_boundaries[i]
            end_ms = segment_boundaries[i + 1]
            if end_ms > start_ms:
                segments_initial.append(audio[start_ms:end_ms])

    if not segments_initial:
        print("  分割后为空,跳过。")
        return

    print(f"  初步分割得到 {len(segments_initial)} 个片段。")

    segments = list(segments_initial)
    if remove_beep_sound == 1:
        if beep_at_start == 1 and len(segments) > 0:
            print("  移除开头片段。")
            segments.pop(0)
        if beep_at_end == 1 and len(segments) > 0:
            print("  移除结尾片段。")
            segments.pop(-1)

    if not segments:
        print("  移除滴声后列表为空,跳过。")
        return

    print(f"  剩余 {len(segments)} 个片段用于拼接。")

    new_audio = AudioSegment.empty()
    for segment in segments:
        if len(segment) == 0:
            continue

        for combination_index in range(1, combination_times + 1):
            print(
                f"  片段组合 {combination_index}/{combination_times}: "
                f"原读 {origin_times} 遍 + 跟读 {repeat_times} 遍"
            )

            for i in range(1, origin_times + 1):
                new_audio += segment
                marker_to_add = speech_marker if i < origin_times else speech_end_marker
                if marker_to_add:
                    new_audio += marker_to_add
                    new_audio += marker_padding_silence

            follow_silence_duration_ms = max(0, int(len(segment) * follow_duration_multiplier))
            silence_mono = AudioSegment.silent(duration=follow_silence_duration_ms, frame_rate=audio.frame_rate)
            if audio.channels > 1:
                silence_audio_extended = silence_mono.set_channels(audio.channels)
            else:
                silence_audio_extended = silence_mono

            for j in range(1, repeat_times + 1):
                new_audio += silence_audio_extended
                marker_follow = read_along_marker if j < repeat_times else read_along_end_marker
                if marker_follow:
                    new_audio += marker_follow
                    new_audio += marker_padding_silence

    original_filename = os.path.basename(audio_path)
    filename_base, file_extension = os.path.splitext(original_filename)
    output_extension = file_extension[1:] if file_extension.startswith(".") else (file_extension or settings.output.fallback_format)
    if not output_extension:
        output_extension = settings.output.fallback_format

    output_filename = os.path.join(output_dir, f"{filename_base}_processed.{output_extension}")
    try:
        print(f"  导出: {output_filename}")
        new_audio.export(output_filename, format=output_extension)
        print(f"  成功保存: {output_filename}")
    except Exception as e:
        print(f"错误: 保存 {output_filename} 失败。原因: {e}")
        try:
            fallback = settings.output.fallback_format
            output_filename_fb = os.path.join(output_dir, f"{filename_base}_processed.{fallback}")
            print(f"  尝试以 {fallback.upper()} 格式保存: {output_filename_fb}")
            new_audio.export(output_filename_fb, format=fallback)
            print(f"  成功以 {fallback.upper()} 格式保存。")
        except Exception as e_fb:
            print(f"错误: 兜底格式保存也失败。原因: {e_fb}")


def main():
    script_dir = get_script_directory()

    ffmpeg = configure_ffmpeg(settings, script_dir)
    print("音频后端(FFmpeg):")
    for note in ffmpeg.notes:
        print(f"  - {note}")
    if not (ffmpeg.ffmpeg and ffmpeg.ffprobe):
        print("\n错误: 未找到可用的 FFmpeg 与 FFprobe,无法读取或导出音频。")
        print("  可在 config.yaml 的 ffmpeg.directory 中填写二者所在目录,或把 FFmpeg 加入 PATH。")
        print("  详见 README.md 的“FFmpeg 配置”。")
        return

    root = tk.Tk()
    root.withdraw()
    print("请选择一个或多个音频文件...")
    audio_paths = filedialog.askopenfilenames(
        title="选择音频文件",
        filetypes=(("Audio Files", "*.wav *.mp3 *.aac *.ogg *.flac *.m4a"), ("All files", "*.*")),
    )

    if not audio_paths:
        print("没有选择文件。程序退出。")
        return

    print("\n选中文件:")
    for path in audio_paths:
        print(f"- {path}")

    user_params = get_user_inputs()

    print("\n正在加载提示音文件...")
    marker_padding_silence = AudioSegment.silent(duration=settings.audio.marker_padding_silence_ms)
    markers = {
        "speech_marker": load_marker_audio_safe(script_dir, settings.markers.speech_marker),
        "speech_end_marker": load_marker_audio_safe(script_dir, settings.markers.speech_end_marker),
        "read_along_marker": load_marker_audio_safe(script_dir, settings.markers.read_along_marker),
        "read_along_end_marker": load_marker_audio_safe(script_dir, settings.markers.read_along_end_marker),
        "marker_padding_silence": marker_padding_silence,
    }

    first_audio_parent_dir = os.path.dirname(audio_paths[0])
    folder_name = settings.output.folder_name_template.format(
        origin=user_params["origin_times"],
        repeat=user_params["repeat_times"],
        combination=user_params["combination_times"],
    )
    output_dir = os.path.join(first_audio_parent_dir, folder_name)

    try:
        os.makedirs(output_dir, exist_ok=True)
        print(f"\n输出文件夹 '{output_dir}' 已就绪。")
    except OSError as e:
        print(f"错误: 无法创建输出文件夹 '{output_dir}'. 原因: {e}")
        return

    for audio_path in audio_paths:
        process_audio_file(audio_path, output_dir, user_params, markers)

    print("\n所有处理完成。")


if __name__ == "__main__":
    main()
