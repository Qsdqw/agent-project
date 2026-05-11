"""
为整个工程提供统一的绝对路径
"""
import os

def get_project_root() -> str:
    """
    获取项目根目录
    """
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return project_root


def get_abs_path(relative_path: str) -> str:
    """
    获取绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)


if __name__ == "__main__":
    print(get_abs_path("config/config.txt"))