# from typing import Iterable,List
#
# from langchain_classic.text_splitter import MarkdownTextSplitter
# from langchain_community.document_loaders import TextLoader
# from langchain_core.documents import Document
#
#
# class MarkdownWithParentSplitter(MarkdownTextSplitter):
#     def __init__(self, **kwargs):
#         super().__init__(**kwargs)
#
#         # 初始化5级标题的实时状态变量
#         self.current_level1_title = ''  # # 级标题
#         self.current_level2_title = ''  # ## 级标题
#         self.current_level3_title = ''  # ### 级标题
#         self.current_level4_title = ''  # #### 级标题
#         self.current_level5_title = ''  # ##### 级标题
#
#     def make_catalogue(self, file: List[Document]):
#         """提取1-5个#开头的标题，生成目录列表"""
#         catalogue = []
#         file_content = file[0].page_content
#         for line in file_content.split('\n'):
#             clean_line = line.strip()
#             # 匹配1-5个# + 空格开头的标题行
#             if clean_line.startswith(('# ', '## ', '### ', '#### ', '##### ')):
#                 catalogue.append(clean_line)
#         return catalogue
#
#     def update_title_level(self, title: str):
#         """根据标题更新对应层级的实时标题，同时重置子层级标题"""
#         # 统计标题的#数量（层级）
#         level = title.count('#')
#
#         # 更新对应层级标题，并重置更低层级（子层级）的标题
#         if level == 1:
#             self.current_level1_title = title
#             self.current_level2_title = ''
#             self.current_level3_title = ''
#             self.current_level4_title = ''
#             self.current_level5_title = ''
#         elif level == 2:
#             self.current_level2_title = title
#             self.current_level3_title = ''
#             self.current_level4_title = ''
#             self.current_level5_title = ''
#         elif level == 3:
#             self.current_level3_title = title
#             self.current_level4_title = ''
#             self.current_level5_title = ''
#         elif level == 4:
#             self.current_level4_title = title
#             self.current_level5_title = ''
#         elif level == 5:
#             self.current_level5_title = title
#
#     def get_current_parent_titles(self):
#         """获取当前有效的所有父标题（非空的层级标题）"""
#         parent_titles = []
#         # 按层级从高到低收集非空标题
#         if self.current_level1_title:
#             parent_titles.append(self.current_level1_title)
#         if self.current_level2_title:
#             parent_titles.append(self.current_level2_title)
#         if self.current_level3_title:
#             parent_titles.append(self.current_level3_title)
#         if self.current_level4_title:
#             parent_titles.append(self.current_level4_title)
#         if self.current_level5_title:
#             parent_titles.append(self.current_level5_title)
#         return parent_titles
#
#     def split_documents(self, documents: Iterable[Document]) -> list[Document]:
#         """重写拆分函数：实时更新层级标题，为每个chunk补全父标题"""
#         docs = list(documents)
#         if not docs:
#             return []
#
#         # 1. 提取目录 & 获取完整文本
#         catalogue = self.make_catalogue(docs)
#         full_text = docs[0].page_content
#         lines = full_text.split('\n')
#
#         # 2. 先用父类方法拆分得到原始chunks（保留基础拆分逻辑）
#         raw_chunks = super().split_documents(docs)
#         processed_chunks = []
#
#         # 3. 遍历完整文本，先初始化所有层级标题的实时状态
#         self.current_level1_title = ''
#         self.current_level2_title = ''
#         self.current_level3_title = ''
#         self.current_level4_title = ''
#         self.current_level5_title = ''
#
#         # 4. 处理每个原始chunk
#         for chunk in raw_chunks:
#             chunk_content = chunk.page_content.strip()
#             if not chunk_content:
#                 continue
#
#             # 4.1 找到chunk在完整文本中的起始位置，确定对应的层级标题
#             # 取chunk前50字符定位（避免空行干扰）
#             chunk_start_marker = chunk_content[:50] if len(chunk_content) > 50 else chunk_content
#             chunk_start_idx = full_text.find(chunk_start_marker)
#
#             # 4.2 从文本开头遍历到chunk起始位置，更新层级标题状态
#             temp_level1 = self.current_level1_title
#             temp_level2 = self.current_level2_title
#             temp_level3 = self.current_level3_title
#             temp_level4 = self.current_level4_title
#             temp_level5 = self.current_level5_title
#
#             for line_idx, line in enumerate(lines):
#                 line_pos = full_text.find(line)
#                 if line_pos > chunk_start_idx and line_pos != -1:
#                     break  # 超过chunk起始位置，停止更新
#
#                 clean_line = line.strip()
#                 if clean_line in catalogue:  # 是标题行，更新层级
#                     self.update_title_level(clean_line)
#
#             # 4.3 获取当前chunk对应的所有父标题
#             parent_titles = self.get_current_parent_titles()
#             parent_titles_str = '\n'.join(parent_titles) + '\n\n' if parent_titles else ''
#
#             # 4.4 判断chunk是否以标题开头，按规则补全
#             first_line = chunk_content.split('\n')[0].strip()
#             if not first_line.startswith(('# ', '## ', '### ', '#### ', '##### ')):
#                 # chunk不以标题开头：补全父标题 + 原内容
#                 new_content = parent_titles_str + chunk_content
#             else:
#                 # chunk以标题开头：先更新该标题的层级，再补父标题（排除自身避免重复）
#                 self.update_title_level(first_line)
#                 parent_titles = self.get_current_parent_titles()[:-1]  # 去掉当前标题
#                 parent_titles_str = '\n'.join(parent_titles) + '\n\n' if parent_titles else ''
#                 new_content = parent_titles_str + chunk_content
#
#             # 4.5 恢复临时状态（避免影响下一个chunk）
#             self.current_level1_title = temp_level1
#             self.current_level2_title = temp_level2
#             self.current_level3_title = temp_level3
#             self.current_level4_title = temp_level4
#             self.current_level5_title = temp_level5
#
#             # 4.6 生成新的Document对象
#             processed_chunk = Document(
#                 page_content=new_content,
#                 metadata=chunk.metadata
#             )
#             processed_chunks.append(processed_chunk)
#
#         return processed_chunks
#
#
# def _cut_document_md(file_path,
#                      chunk_size=600,
#                      overlap_rate=0.1,
#                      print_chunks=False, ):
#     """加载并拆分markdown文档，为每个chunk补全父标题"""
#     from langchain_community.document_loaders import TextLoader
#
#     # 加载文档
#     loader = TextLoader(file_path=file_path, encoding="utf-8")
#     data = loader.load()
#
#     # 初始化自定义拆分器
#     splitter = MarkdownWithParentSplitter(
#         chunk_size=chunk_size,  # 每个块的最大字符数
#         chunk_overlap=int(chunk_size * overlap_rate),  # 块之间的重叠字符数
#     )
#
#     # 拆分文档
#     chunks = splitter.split_documents(data)
#
#     # 可选：打印拆分后的chunk
#     if print_chunks:
#         for i, chunk in enumerate(chunks):
#             print(f"\n===== chunk {i + 1} =====")
#             print(chunk.page_content)
#
#     return chunks
#
#
# # 测试调用示例
# # if __name__ == "__main__":
# #     chunks = _cut_document_md(
# #         file_path="你的markdown文件路径.md",  # 替换为你的文件路径
# #         chunk_size=600,
# #         overlap_rate=0.1,
# #         print_chunks=True
# #     )
#
#
#
# # 测试示例
# if __name__ == "__main__":
#
#     # 调用分割函数
#     chunks = _cut_document_md('data/clean_data/网易云音乐2025年中（1-6月）业绩报告_.md', print_chunks=True)







#
# from rank_bm25 import BM25Okapi
# import jieba  # 用于中文分词
#
# # 准备文档
# documents = [
#     "网易云音乐2025年总收入达到100亿元",
#     "网易云音乐2024年净利润增长50%",
#     "腾讯音乐2025年第一季度财报发布"
# ]
#
# # 中文分词
# tokenized_docs = [list(jieba.cut(doc)) for doc in documents]
#
# # 初始化BM25
# bm25 = BM25Okapi(tokenized_docs)
#
# # 查询
# query = "网易云音乐2025年度的总收入是多少？"
# tokenized_query = list(jieba.cut(query))
#
# # 获取分数
# scores = bm25.get_scores(tokenized_query)
# print("所有文档的分数:", scores)
#
# # 获取带分数的结果
# doc_scores = list(zip(documents, scores))
# doc_scores.sort(key=lambda x: x[1], reverse=True)
#
# for doc, score in doc_scores[:3]:
#     print(f"文档: {doc}")
#     print(f"BM25分数: {score}")
#     print("-" * 30)
#
