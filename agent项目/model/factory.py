"""模型工厂 — 懒加载模式，避免导入时阻塞启动"""
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.chat_models.tongyi import ChatTongyi
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from utils.config_loader import rag_conf

_chat_model = None
_embed_model = None


def get_chat_model() -> BaseChatModel:
    """懒加载 ChatTongyi，首次调用时才初始化"""
    global _chat_model
    if _chat_model is None:
        _chat_model = ChatTongyi(model=rag_conf["chat_model_name"], streaming=True)
    return _chat_model


def get_embed_model() -> Embeddings:
    """懒加载 DashScopeEmbeddings，首次调用时才初始化"""
    global _embed_model
    if _embed_model is None:
        _embed_model = DashScopeEmbeddings(model=rag_conf["embedding_model_name"])
    return _embed_model
