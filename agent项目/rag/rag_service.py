"""
RAG 服务：向量检索 → Cross-Encoder 重排序 → LLM 总结

知识速查：
- 向量检索(Bi-Encoder): 把问题和文档都编码成向量，用余弦相似度匹配
  优点：快（可以预先算好文档向量存 Chroma）
  缺点：粗糙，只算整体语义相似度
- Cross-Encoder: 把"问题+文档"拼接在一起送入 transformer 模型打分
  优点：精准，能捕捉细粒度语义关系
  缺点：慢，不能预计算（必须实时算每一对 问题+文档）
- 两阶段检索：先召后精排，兼顾速度和精度
  阶段1: 向量检索 → 从全库快速召回 top-10
  阶段2: Cross-Encoder → 对 10 篇精排，取 top-3
"""
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from storage.vector import VectorStoreService
from utils.prompt_loader import load_rag_prompts
from langchain_core.prompts import PromptTemplate
from model.factory import get_chat_model
from utils.logger import logger

# 召回阶段取多少篇给 Cross-Encoder 打分
RETRIEVAL_K = 10
# 精排后保留多少篇给 LLM
RERANK_TOP_N = 3


class RagSummarizeService(object):
    def __init__(self):
        self.vector_store = VectorStoreService()
        self.retriever = self.vector_store.get_retriever(k=RETRIEVAL_K)
        self.prompt_text = load_rag_prompts()
        self.prompt_template = PromptTemplate.from_template(self.prompt_text)
        self.model = get_chat_model()
        self.chain = self._init_chain()
        self._reranker = None  # 懒加载：第一次用时才下载模型

    @property
    def reranker(self):
        """懒加载 Cross-Encoder，避免启动时下载模型阻塞，且 HuggingFace 国内被墙时可降级"""
        if self._reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                self._reranker = CrossEncoder("BAAI/bge-reranker-base")
                logger.info("[RAG] Cross-Encoder 模型加载成功")
            except Exception as e:
                logger.warning(f"[RAG] Cross-Encoder 加载失败，跳过重排序: {e}")
                self._reranker = False
        return self._reranker if self._reranker is not False else None

    def _init_chain(self):
        return self.prompt_template | self.model | StrOutputParser()

    def retrieve(self, query: str) -> list[Document]:
        return self.retriever.invoke(query)

    def rerank(self, query: str, docs: list[Document]) -> list[Document]:
        """用 Cross-Encoder 对文档精排，返回 top-N。模型不可用时直接返回原列表"""
        if self.reranker is None:
            return docs
        if len(docs) <= RERANK_TOP_N:
            return docs
        pairs = [[query, doc.page_content] for doc in docs]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:RERANK_TOP_N]]

    def rag_summarize(self, query: str) -> str:
        docs = self.retrieve(query)          # 阶段1: 向量召回 top-10
        docs = self.rerank(query, docs)      # 阶段2: Cross-Encoder 精排取 top-3

        context = ""
        for i, doc in enumerate(docs, 1):
            context += f"[参考资料{i}]:参考资料:{doc.page_content}|参考源数据:{doc.metadata}\n"
        return self.chain.invoke({"input": query, "context": context})


if __name__ == "__main__":
    rag = RagSummarizeService()
    query = "小户型时候哪些扫地机器人"
    print(rag.rag_summarize(query))