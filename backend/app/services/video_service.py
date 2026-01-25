"""视频合成服务 - 使用 FFmpeg 将 PPT 截图和音频合成为视频"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from app.config import settings


def synthesize_video(task_id: str, ppt_path: str, audio_dir: str, screenshot_dir: Optional[str] = None) -> str:
    """
    将 PPT 截图和音频合成为视频

    优先使用用户上传的截图，如果不存在则使用 LibreOffice 转换

    Args:
        task_id: 任务 ID
        ppt_path: PPT 文件路径
        audio_dir: 音频文件目录
        screenshot_dir: 截图目录（可选，如果提供则优先使用）

    Returns:
        合成后的视频文件路径
    """
    path = Path(ppt_path)
    if not path.exists():
        raise FileNotFoundError(f"PPT 文件不存在: {ppt_path}")

    # 确保视频输出目录存在
    video_dir = settings.static_dir / "video" / task_id
    video_dir.mkdir(parents=True, exist_ok=True)

    output_path = video_dir / f"{path.stem}.mp4"

    # 检查音频文件（按页码数字排序）
    all_audio = list(Path(audio_dir).glob("page_*.mp3"))
    if not all_audio:
        raise RuntimeError(f"音频文件不存在: {audio_dir}")

    # 解析页码的辅助函数
    def extract_audio_page_num(f) -> int:
        import re
        name = f.name if hasattr(f, 'name') else str(f)
        match = re.search(r'page_(\d+)', name, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return 999999

    audio_files = sorted(all_audio, key=extract_audio_page_num)

    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_img_dir = os.path.join(temp_dir, "images")
        os.makedirs(temp_img_dir, exist_ok=True)

        # 步骤1: 获取截图
        print(f"步骤1: 获取幻灯片截图...")
        image_files = []

        # 解析页码的辅助函数
        def extract_page_num(filename: str) -> int:
            import re
            # 格式1: page_1.png, page_2.png
            match = re.search(r'page_(\d+)', filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
            # 格式2: 幻灯片1.jpeg, 幻灯片2.png
            match = re.search(r'幻灯片(\d+)', filename)
            if match:
                return int(match.group(1))
            # 格式3: slide_1.png
            match = re.search(r'slide_?(\d+)', filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
            # 格式4: slide-1.png
            match = re.search(r'slide-(\d+)', filename, re.IGNORECASE)
            if match:
                return int(match.group(1))
            return 999999  # 未识别的放最后

        # 优先使用用户上传的截图
        if screenshot_dir and Path(screenshot_dir).exists():
            print("使用用户上传的截图...")

            # 收集所有支持的图片文件
            all_files = []
            for ext in ['*.png', '*.jpg', '*.jpeg', '*.gif']:
                all_files.extend(Path(screenshot_dir).glob(ext))

            # 按页码排序
            sorted_files = sorted(all_files, key=lambda f: extract_page_num(f.name))

            for i, img_file in enumerate(sorted_files):
                page_num = extract_page_num(img_file.name)
                dest_file = os.path.join(temp_img_dir, f"slide-{page_num}.png")
                shutil.copy2(img_file, dest_file)
                image_files.append(dest_file)
                print(f"  页面 {page_num}: {img_file.name}")
        else:
            print("使用 LibreOffice 转换截图...")
            # 如果没有上传的截图，使用 LibreOffice 转换
            temp_ppt_path = os.path.join(temp_dir, path.name)
            shutil.copy2(ppt_path, temp_ppt_path)

            # 使用 LibreOffice 将 PPT 转换为 PDF
            pdf_path = os.path.join(temp_dir, f"{path.stem}.pdf")
            cmd = [
                "soffice",
                "--headless",
                "--convert-to", "pdf",
                "--outdir", temp_dir,
                temp_ppt_path
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                raise RuntimeError(f"LibreOffice 转换失败: {result.stderr}")

            if not os.path.exists(pdf_path):
                raise RuntimeError(f"PDF 文件未生成: {pdf_path}")

            # 使用 pdftoppm 将 PDF 转换为图片
            ppm_prefix = os.path.join(temp_img_dir, "slide")
            cmd = [
                "pdftoppm",
                "-png",
                "-f", "1",
                "-l", "1000",
                pdf_path,
                ppm_prefix
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                print(f"pdftoppm 警告: {result.stderr.decode()}")

            image_files = sorted(Path(temp_img_dir).glob("slide-*.png"))

        if not image_files:
            raise RuntimeError("没有导出任何幻灯片图片")

        print(f"找到 {len(image_files)} 张截图")

        # 步骤2: 使用 FFmpeg 合成视频
        print(f"步骤2: 使用 FFmpeg 合成视频...")
        _create_video_with_ffmpeg(image_files, audio_files, str(output_path))

        print(f"视频已生成: {output_path}")
        return str(output_path)


def _create_video_with_ffmpeg(image_files: list, audio_files: list, output_path: str) -> None:
    """使用 FFmpeg 将图片和音频合成为视频"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=10)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise RuntimeError("未安装 FFmpeg，请运行: brew install ffmpeg")

    # 清理之前的输出文件
    if Path(output_path).exists():
        Path(output_path).unlink()

    # 获取第一张图片的分辨率
    first_img_path = image_files[0] if image_files else None
    img_width = 1920
    img_height = 1080
    if first_img_path:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height",
                 "-of", "csv=p=0", first_img_path],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and ',' in result.stdout:
                w, h = result.stdout.strip().split(',')
                img_width = int(w)
                img_height = int(h)
        except Exception:
            pass

    # 获取所有音频时长
    audio_durations = []
    for audio_file in audio_files:
        audio_durations.append(_get_audio_duration(str(audio_file)))

    # 创建临时目录存放分段视频
    with tempfile.TemporaryDirectory() as temp_dir:
        segments = []

        # 逐个创建视频片段（图片+对应音频）
        for i, (img_file, audio_file) in enumerate(zip(image_files, audio_files)):
            segment_path = os.path.join(temp_dir, f"segment_{i}.mp4")
            duration = audio_durations[i] if i < len(audio_durations) else 5.0

            # 构建缩放滤镜
            if img_width > 1920 or img_height > 1080:
                scale_filter = "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
            elif img_width < 1280:
                scale_filter = f"scale={img_width}:{img_height}"
            else:
                scale_filter = f"scale={img_width}:{img_height}"

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", str(duration),
                "-i", str(img_file),
                "-i", str(audio_file),
                "-vf", scale_filter,
                "-map", "0:v",  # 映射第一路视频流（图片）
                "-map", "1:a",  # 映射第二路音频流
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                # 使用 AAC 编码确保兼容性
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-pix_fmt", "yuv420p",
                segment_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                print(f"分段 {i} 创建失败: {result.stderr.decode()[:200]}")
                # 使用简单方式创建
                _create_video_simple(image_files, audio_files, output_path)
                return

            if Path(segment_path).exists():
                segments.append(segment_path)

        if len(segments) == 0:
            raise RuntimeError("没有成功创建任何视频分段")

        # 如果只有一个分段，直接重命名
        if len(segments) == 1:
            shutil.copy2(segments[0], output_path)
            return

        # 使用 concat 滤镜连接所有分段
        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for segment in segments:
                f.write(f"file '{segment}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0:
            print(f"合并失败: {result.stderr.decode()[:200]}")
            # 如果合并失败，复制第一个分段
            if segments:
                shutil.copy2(segments[0], output_path)
                return
            raise RuntimeError(f"视频合并失败: {result.stderr.decode()}")

    if not Path(output_path).exists():
        raise RuntimeError("视频文件未生成")


def _create_video_simple(image_files: list, audio_files: list, output_path: str) -> None:
    """简单方式合成视频 - 逐个创建分段再合并"""
    import subprocess

    # 获取第一张图片的分辨率
    first_img = image_files[0] if image_files else None
    img_width, img_height = 1920, 1080
    if first_img:
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height",
                 "-of", "csv=p=0", first_img],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and ',' in result.stdout:
                w, h = result.stdout.strip().split(',')
                img_width, img_height = int(w), int(h)
        except Exception:
            pass

    # 获取音频时长
    audio_durations = [_get_audio_duration(str(a)) for a in audio_files]

    with tempfile.TemporaryDirectory() as temp_dir:
        segments = []

        # 逐个创建视频片段
        for i, (img_file, audio_file) in enumerate(zip(image_files, audio_files)):
            segment_path = os.path.join(temp_dir, f"seg_{i}.mp4")
            duration = audio_durations[i] if i < len(audio_durations) else 5.0

            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-t", str(duration),
                "-i", str(img_file),
                "-i", str(audio_file),
                "-vf", f"scale={img_width}:{img_height}",
                "-map", "0:v",  # 映射视频
                "-map", "1:a",  # 映射音频
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-shortest",
                "-pix_fmt", "yuv420p",
                segment_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)
            if result.returncode != 0:
                raise RuntimeError(f"分段 {i} 创建失败: {result.stderr.decode()}")

            if Path(segment_path).exists():
                segments.append(segment_path)

        if len(segments) == 0:
            raise RuntimeError("没有成功创建视频分段")

        # 合并分段
        if len(segments) == 1:
            shutil.copy2(segments[0], output_path)
            return

        concat_file = os.path.join(temp_dir, "concat.txt")
        with open(concat_file, 'w') as f:
            for seg in segments:
                f.write(f"file '{seg}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_file,
            "-c", "copy",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)
        if result.returncode != 0:
            # 合并失败则复制第一个分段
            if segments:
                shutil.copy2(segments[0], output_path)
                return
            raise RuntimeError(f"合并失败: {result.stderr.decode()}")

    if not Path(output_path).exists():
        raise RuntimeError("视频文件未生成")


def _get_audio_duration(audio_path: str) -> float:
    """获取音频文件时长（秒）"""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return float(result.stdout.strip())
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        pass

    return 5.0
