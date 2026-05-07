import yaml
import os
import re
from dotenv import load_dotenv

from utils.path_tool import get_abs_path

dotenv_path = get_abs_path(".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)


def _resolve_env_vars(value):
    if isinstance(value, str):
        pattern = r'\$\{(\w+)(?::([^}]*))?\}'
        def replace_match(match):
            env_name = match.group(1)
            default = match.group(2) if match.group(2) else ''
            return os.environ.get(env_name, default)
        return re.sub(pattern, replace_match, value)
    elif isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [_resolve_env_vars(item) for item in value]
    return value


def load_rag_config(config_path: str = get_abs_path("config/rag.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _resolve_env_vars(config)


def load_chroma_config(config_path: str = get_abs_path("config/chroma.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _resolve_env_vars(config)


def load_prompts_config(config_path: str = get_abs_path("config/prompts.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _resolve_env_vars(config)


def load_agent_config(config_path: str = get_abs_path("config/agent.yml"), encoding: str = "utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        config = yaml.load(f, Loader=yaml.FullLoader)
    return _resolve_env_vars(config)


rag_conf = load_rag_config()
chroma_conf = load_chroma_config()
prompts_conf = load_prompts_config()
agent_conf = load_agent_config()

if __name__ == "__main__":
    print(rag_conf["chat_model_name"])
