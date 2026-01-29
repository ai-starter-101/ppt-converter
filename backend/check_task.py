#!/usr/bin/env python3
"""检查任务数据"""
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

from app.database import engine
from sqlmodel import Session, select
from app.models import Task

def check_task(task_id):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if not task:
            print(f"任务 {task_id} 不存在")
            return

        print("=" * 50)
        print(f"任务ID: {task.id}")
        print(f"文件名: {task.filename}")
        print(f"状态: {task.status}")
        print(f"幻灯片数量: {task.slide_count}")
        print()
        print("数据检查:")
        print(f"  slides_content: {'有' if task.slides_content else '空'}")
        print(f"  slides_script: {'有' if task.slides_script else '空'}")
        print(f"  slides_audio: {'有' if task.slides_audio else '空'}")
        print(f"  slides_screenshots: {'有' if task.slides_screenshots else '空'}")

        # 解析数据
        from app.models import parse_slides_json

        slides = parse_slides_json(task.slides_content)
        audios = parse_slides_json(task.slides_audio)
        screenshots = parse_slides_json(task.slides_screenshots)

        print()
        print("详细数据:")
        print(f"  幻灯片数量: {len(slides)}")
        print(f"  音频记录数量: {len(audios)}")
        print(f"  截图记录数量: {len(screenshots)}")

        # 检查每页的音频和截图
        print()
        print("每页检查:")
        for slide in slides[:5]:  # 只显示前5页
            page = slide['page_num']
            audio = next((a for a in audios if a.get('page_num') == page), None)
            screenshot = next((s for s in screenshots if s.get('page_num') == page), None)
            audio_ok = '✓' if audio and audio.get('audio_path') else '✗'
            screenshot_ok = '✓' if screenshot and screenshot.get('screenshot_path') else '✗'
            print(f"  第{page}页: 音频={audio_ok}, 截图={screenshot_ok}")

        print()
        print("合成视频条件检查:")
        has_all_audio = all(
            any(a.get('page_num') == s['page_num'] and a.get('audio_path')
                for a in audios)
            for s in slides
        )
        has_any_screenshot = any(
            s.get('screenshot_path') for s in screenshots
        )
        print(f"  所有页面都有音频: {has_all_audio}")
        print(f"  有上传截图: {has_any_screenshot}")
        print(f"  可以合成视频: {has_all_audio and has_any_screenshot}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("task_id", help="任务ID")
    args = parser.parse_args()
    check_task(args.task_id)
