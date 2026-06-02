# 知识库模块
from .index import build_index, search_by_features, search_by_query
from .search import KnowledgeSearch

__all__ = ["build_index", "search_by_features", "search_by_query", "KnowledgeSearch"]
