# Documents传入prompt前的格式化

def format_docs_for_context(docs):
    """
    将Document列表格式化为：
    文档内容1
    元数据: {'source': 'file1.pdf', 'page': 1}

    文档内容2
    元数据: {'source': 'file2.pdf', 'page': 5}
    """
    # formatted_docs = ['【文档内容】\n\n']
    formatted_docs = []
    for doc in docs:
        # 文档内容
        content = doc.page_content
        # 元数据转换为字符串格式
        metadata_str = str(doc.metadata)
        # 组合成指定格式
        formatted_doc = f"【文档内容】：\n{content}\n【元数据】: {metadata_str}"
        formatted_docs.append(formatted_doc)

    # 用两个换行符分隔不同文档
    return "\n————————————\n".join(formatted_docs)