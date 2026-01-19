"""PPT解析服务"""
from pathlib import Path
from pptx import Presentation


def extract_text_from_ppt(file_path: str) -> str:
    """
    从 .pptx 文件中提取所有文本内容

    Args:
        file_path: PPT 文件路径

    Returns:
        格式化的文本字符串，每页幻灯片用分隔符区分

    Raises:
        FileNotFoundError: 文件不存在
        InvalidPathError: 路径无效
        Exception: 其他解析错误
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    if not path.suffix.lower() == '.pptx':
        raise ValueError("只支持 .pptx 格式的 PowerPoint 文件")

    prs = Presentation(file_path)
    slides_content = []

    for idx, slide in enumerate(prs.slides, start=1):
        slide_text = []
        slide_text.append(f"=== 幻灯片 {idx} ===")

        for shape in slide.shapes:
            if hasattr(shape, "text_frame") and shape.text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text = paragraph.text.strip()
                    if text:
                        slide_text.append(text)

        if len(slide_text) > 1:  # 只有标题
            slides_content.append("\n".join(slide_text))
        else:
            slides_content.append(f"=== 幻灯片 {idx} ===\n[无文本内容]")

    return "\n\n".join(slides_content)


def get_ppt_info(file_path: str) -> dict:
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
    }
