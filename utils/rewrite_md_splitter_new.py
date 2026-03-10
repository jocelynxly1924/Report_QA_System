from typing import Iterable,List

from langchain_classic.text_splitter import MarkdownTextSplitter
from langchain_core.documents import Document


class MarkdownWithParentSplitter(MarkdownTextSplitter):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 初始化5级标题的实时状态变量
        self.current_level1_title = ''  # # 级标题
        self.current_level2_title = ''  # ## 级标题
        self.current_level3_title = ''  # ### 级标题
        self.current_level4_title = ''  # #### 级标题
        self.current_level5_title = ''  # ##### 级标题

    @staticmethod
    def make_catalogue(file: List[Document]):
        """提取1-5个#开头的标题，生成目录列表"""
        catalogue = []
        file_content = file[0].page_content
        for line in file_content.split('\n'):
            clean_line = line.strip()
            # 匹配1-5个# + 空格开头的标题行
            if clean_line.startswith(('# ', '## ', '### ', '#### ', '##### ')):
                catalogue.append(clean_line)
        return catalogue

    def update_title_level(self, title: str):
        """根据标题更新对应层级的实时标题，同时重置子层级标题"""
        # 统计标题的#数量（层级）
        level = title.count('#')

        # 更新对应层级标题，并重置更低层级（子层级）的标题
        if level == 1:
            self.current_level1_title = title
            self.current_level2_title = ''
            self.current_level3_title = ''
            self.current_level4_title = ''
            self.current_level5_title = ''
        elif level == 2:
            self.current_level2_title = title
            self.current_level3_title = ''
            self.current_level4_title = ''
            self.current_level5_title = ''
        elif level == 3:
            self.current_level3_title = title
            self.current_level4_title = ''
            self.current_level5_title = ''
        elif level == 4:
            self.current_level4_title = title
            self.current_level5_title = ''
        elif level == 5:
            self.current_level5_title = title

    def get_current_parent_titles(self):
        """获取当前有效的所有父标题（非空的层级标题）"""
        parent_titles = []
        # 按层级从高到低收集非空标题
        if self.current_level1_title:
            parent_titles.append(self.current_level1_title)
        if self.current_level2_title:
            parent_titles.append(self.current_level2_title)
        if self.current_level3_title:
            parent_titles.append(self.current_level3_title)
        if self.current_level4_title:
            parent_titles.append(self.current_level4_title)
        if self.current_level5_title:
            parent_titles.append(self.current_level5_title)
        return parent_titles

    def split_documents(self, documents: Iterable[Document]) -> list[Document]:
        """重写拆分函数：实时更新层级标题，为每个chunk补全父标题"""
        docs = list(documents)
        if not docs:
            return []

        # 1. 提取目录 & 获取完整文本
        catalogue = self.make_catalogue(docs)
        full_text = docs[0].page_content
        lines = full_text.split('\n')

        # 2. 先用父类方法拆分得到原始chunks（保留基础拆分逻辑）
        raw_chunks = super().split_documents(docs)
        processed_chunks = []

        # 3. 遍历完整文本，先初始化所有层级标题的实时状态
        self.current_level1_title = ''
        self.current_level2_title = ''
        self.current_level3_title = ''
        self.current_level4_title = ''
        self.current_level5_title = ''

        # 4. 处理每个原始chunk
        for chunk in raw_chunks:
            chunk_content = chunk.page_content.strip()
            if not chunk_content:
                continue

            # 4.1 找到chunk在完整文本中的起始位置，确定对应的层级标题
            # 取chunk前50字符定位（避免空行干扰）
            chunk_start_marker = chunk_content[:50] if len(chunk_content) > 50 else chunk_content
            chunk_start_idx = full_text.find(chunk_start_marker)

            # 4.2 从文本开头遍历到chunk起始位置，更新层级标题状态
            temp_level1 = self.current_level1_title
            temp_level2 = self.current_level2_title
            temp_level3 = self.current_level3_title
            temp_level4 = self.current_level4_title
            temp_level5 = self.current_level5_title

            for line_idx, line in enumerate(lines):
                line_pos = full_text.find(line)
                if line_pos > chunk_start_idx and line_pos != -1:
                    break  # 超过chunk起始位置，停止更新

                clean_line = line.strip()
                if clean_line in catalogue:  # 是标题行，更新层级
                    self.update_title_level(clean_line)

            # 4.3 获取当前chunk对应的所有父标题
            parent_titles = self.get_current_parent_titles()
            parent_titles_str = '\n'.join(parent_titles) + '\n\n' if parent_titles else ''

            # 4.4 判断chunk是否以标题开头，按规则补全
            first_line = chunk_content.split('\n')[0].strip()
            if not first_line.startswith(('# ', '## ', '### ', '#### ', '##### ')):
                # chunk不以标题开头：补全父标题 + 原内容
                new_content = parent_titles_str + chunk_content
            else:
                # chunk以标题开头：先更新该标题的层级，再补父标题（排除自身避免重复）
                self.update_title_level(first_line)
                parent_titles = self.get_current_parent_titles()[:-1]  # 去掉当前标题
                parent_titles_str = '\n'.join(parent_titles) + '\n\n' if parent_titles else ''
                new_content = parent_titles_str + chunk_content

            # 4.5 恢复临时状态（避免影响下一个chunk）
            self.current_level1_title = temp_level1
            self.current_level2_title = temp_level2
            self.current_level3_title = temp_level3
            self.current_level4_title = temp_level4
            self.current_level5_title = temp_level5

            # 4.6 生成新的Document对象
            processed_chunk = Document(
                page_content=new_content,
                metadata=chunk.metadata
            )
            processed_chunks.append(processed_chunk)

        return processed_chunks