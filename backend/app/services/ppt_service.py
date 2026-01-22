"""PPT解析服务"""
from pathlib import Path
from typing import List, Dict, Any
from pptx import Presentation


def extract_text_from_ppt(file_path: str) -> List[Dict[str, Any]]:
    """
    从 .pptx 文件中提取每页的文本内容

    Args:
        file_path: PPT 文件路径

    Returns:
        每页文本内容的列表，每项包含 page_num 和 content
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if not path.suffix.lower() == '.pptx':
        raise ValueError("只支持 .pptx 格式的 PowerPoint 文件")

    prs = Presentation(file_path)
    slides = []

    for idx, slide in enumerate(prs.slides, start=1):
        slide_text = []
        slide_images = []

        for shape in slide.shapes:
            # 提取文本框内容
            if hasattr(shape, "text_frame") and shape.text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        slide_text.append(text)

            # 检查是否有图片
            if hasattr(shape, "shape_type"):
                # 检查是否是图片类型
                if shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                    if hasattr(shape, "name"):
                        slide_images.append(shape.name)

        slides.append({
            "page_num": idx,
            "content": "\n".join(slide_text) if slide_text else "[无文本内容]",
            "image_count": len(slide_images)
        })

    return slides


def extract_all_text_from_ppt(file_path: str) -> str:
    """
    提取所有文本内容（兼容旧接口）

    Args:
        file_path: PPT 文件路径

    Returns:
        格式化的文本字符串，每页幻灯片用分隔符区分
    """
    slides = extract_text_from_ppt(file_path)
    result = []
    for slide in slides:
        result.append(f"=== 第 {slide['page_num']} 页 ===\n{slide['content']}")
    return "\n\n".join(result)


def get_ppt_info(file_path: str) -> Dict[str, Any]:
    """
    获取 PPT 文件的基本信息

    Args:
        file_path: PPT 文件路径

    Returns:
        包含文件信息的字典
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    prs = Presentation(file_path)

    return {
        "filename": path.name,
        "slide_count": len(prs.slides),
        "file_size": path.stat().st_size,
        "slides": extract_text_from_ppt(file_path)
    }
