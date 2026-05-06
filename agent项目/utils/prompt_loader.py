
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger_handler import logger
from utils.path_tool import get_abs_path
from utils.config_handler import prompts_conf

def load_system_prompts():
    try:
        system_prompt_path=get_abs_path(prompts_conf["main_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_system_prompts] 配置文件中缺少 {e}")
        raise e
    try:
        return open(system_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[load_system_prompts] 读取系统提示词失败: {e}")
        raise e

def load_rag_prompts():
    try:
        rag_prompt_path=get_abs_path(prompts_conf["rag_summarize_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_rag_prompts] 配置文件中缺少 {e}")
        raise e
    try:
        return open(rag_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[load_rag_prompts] 读取系统提示词失败: {e}")
        raise e

def load_report_prompts():
    try:
        report_prompt_path=get_abs_path(prompts_conf["report_prompt_path"])
    except KeyError as e:
        logger.error(f"[load_report_prompts] 配置文件中缺少 {e}")
        raise e
    try:
        return open(report_prompt_path, "r", encoding="utf-8").read()
    except Exception as e:
        logger.error(f"[load_report_prompts] 读取系统提示词失败: {e}")
        raise e

if __name__ == "__main__":
    print(load_system_prompts())