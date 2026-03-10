import os
import pickle
import jieba
import numpy as np
from oauthlib.uri_validate import query
from rank_bm25 import BM25Okapi
from hashlib import md5
from typing import List, Union, Optional
from step2_md_to_db_chroma import _cut_document,_cut_document_md

class BM25RetrieverPlus:
    """BM25检索器，支持缓存和增量更新"""

    def __init__(self, cache_dir="./bm25_db"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.bm25 = None
        self.all_chunks = []
        self.tokenized_corpus = []
        self.current_params = None

    def _get_folder_hash(self, folder_path):
        """计算文件夹的哈希值，为了判断文件是否发生变化，以决定是否需要重新构建索引。"""
        hash_md5 = md5()
        for filename in sorted(os.listdir(folder_path)):
            file_path = os.path.join(folder_path, filename)
            if os.path.isfile(file_path):
                hash_md5.update(filename.encode())
                hash_md5.update(str(os.path.getmtime(file_path)).encode())
        return hash_md5.hexdigest()

    def _get_cache_path(self, folder_path, cut_mode, chunk_size, overlap_rate):
        """生成缓存文件路径"""
        folder_hash = self._get_folder_hash(folder_path)
        return os.path.join(
            self.cache_dir,
            f"bm25_{cut_mode}_{chunk_size}_{overlap_rate}_{folder_hash}.pkl"
        )

    def build_index(self,
                    folder_path: str,
                    cut_mode: str,
                    chunk_size: int = 550,
                    separators: list = None,
                    overlap_rate: float = 0.1,
                    cutter_funcs: dict = None,
                    print_chunks: bool = False,
                    force_rebuild: bool = False): # force_rebuild: 是否强制重建
        """构建BM25索引"""

        # 保存当前参数
        self.current_params = {
            'folder_path': folder_path,
            'cut_mode': cut_mode,
            'chunk_size': chunk_size,
            'overlap_rate': overlap_rate
        }

        cache_path = self._get_cache_path(folder_path, cut_mode, chunk_size, overlap_rate)

        # 尝试从缓存加载
        if not force_rebuild and os.path.exists(cache_path):
            try:
                print(f"从缓存加载BM25索引: {cache_path}")
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    self.all_chunks = cached_data['chunks']
                    self.tokenized_corpus = cached_data['tokenized_corpus']
                    self.bm25 = BM25Okapi(self.tokenized_corpus)
                print(f"缓存加载成功，共 {len(self.all_chunks)} 个文档块")
                return self
            except Exception as e:
                print(f"缓存加载失败: {e}，将重新构建")

        # 选择切割函数
        if cutter_funcs:
            cutter = cutter_funcs.get(cut_mode)
        else:
            if cut_mode == "normal":
                cutter = _cut_document
            elif cut_mode == "md":
                cutter = _cut_document_md
            else:
                raise ValueError("Invalid cut_mode. Please choose 'normal' or 'md'.")

        # 切割文档
        print(f"正在切割文档，模式: {cut_mode}...")
        self.all_chunks = []
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            chunks_ = cutter(
                file_path=file_path,
                chunk_size=chunk_size,
                separators=separators,
                overlap_rate=overlap_rate,
                print_chunks=print_chunks
            )
            self.all_chunks.extend(chunks_)

        print(f"文档切割完成，共 {len(self.all_chunks)} 个文档块")

        # 中文分词
        print("正在进行中文分词...")
        self.tokenized_corpus = [
            list(jieba.cut(doc.page_content)) for doc in self.all_chunks
        ]

        # 创建BM25模型
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        # 保存到缓存
        print(f"保存BM25索引到缓存: {cache_path}")
        cached_data = {
            'chunks': self.all_chunks,
            'tokenized_corpus': self.tokenized_corpus,
            'params': self.current_params
        }
        with open(cache_path, 'wb') as f:
            pickle.dump(cached_data, f)

        return self

    def invoke(self,
                 query: Union[str, List[str]],  # 查询字符串或查询列表
                 top_k: int = 3,
                 with_score: bool = False) -> List:

        """检索相关文档(Retrieve)"""

        if self.bm25 is None:
            raise ValueError("请先调用build_index()构建索引")

        # 处理查询
        if isinstance(query, str):
            queries = [query]
            single_query = True
        else:
            queries = query
            single_query = False

        all_results = []
        for q in queries:
            tokenized_query = list(jieba.cut(q))
            scores = self.bm25.get_scores(tokenized_query)
            top_k_indices = np.argsort(scores)[-top_k:][::-1]

            if with_score:
                results = []
                for idx in top_k_indices:
                    if scores[idx] > 0:
                        results.append((self.all_chunks[idx], float(scores[idx])))
                all_results.append(results)
            else:
                results = [self.all_chunks[idx] for idx in top_k_indices if scores[idx] > 0]
                all_results.append(results)

        return all_results[0] if single_query else all_results

    def save(self, save_path: str):
        """保存检索器状态"""
        with open(save_path, 'wb') as f:
            pickle.dump({
                'chunks': self.all_chunks,
                'tokenized_corpus': self.tokenized_corpus,
                'params': self.current_params
            }, f)
        print(f"检索器已保存到: {save_path}")

    def load(self, load_path: str):
        """加载检索器状态"""
        with open(load_path, 'rb') as f:
            data = pickle.load(f)
            self.all_chunks = data['chunks']
            self.tokenized_corpus = data['tokenized_corpus']
            self.current_params = data.get('params')
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        print(f"检索器已从 {load_path} 加载，共 {len(self.all_chunks)} 个文档块")
        return self


if __name__ == '__main__':
    bm25_retriever = BM25RetrieverPlus(cache_dir="./bm25_db")

    # 构建索引（如果缓存存在会自动加载）
    bm25_retriever.build_index(
        folder_path="data/clean_data", # 原始数据目录
        cut_mode="md",
        chunk_size=550,
        overlap_rate=0.1,
        force_rebuild=False  # 设置为True可以强制重建
    )

    print(
        bm25_retriever.invoke(
                              query = [
                                  "2025年度，网易云音乐的研发费用较2024年变化了多少？",
                                  '2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
                                  '网易云音乐2025年度的总收入是多少？'],
                              with_score=True))

    # print(bm25_retriever.invoke(
    #     '请结合财报中关于“支柱二规则”的披露，说明其对网易云音乐未来税负的潜在影响，并评估其对公司净利润的可能影响',
    #     with_score=True))