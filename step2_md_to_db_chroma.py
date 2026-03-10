import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter,MarkdownTextSplitter
from langchain_chroma import Chroma
from model.model_factory import get_embedding_client
from langchain_community.retrievers import BM25Retriever
from utils.rewrite_md_splitter_new import MarkdownWithParentSplitter
# from utils.rewrite_bm25_retriever_with_scores import BM25RetrieverWithScores

def _cut_document(file_path,
                 chunk_size = 550,
                 separators = None,
                 overlap_rate=0.1,
                 print_chunks = False,):
    if separators is None:
        separators = ["\n\n# ", "\n\n", "。", "；", "\n", " ", ""]

    print("##############开始加载并切割文档##############")

    # Document split
    loader = TextLoader(file_path=file_path, encoding="utf-8")
    data = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size,
                                              chunk_overlap=int(chunk_size*overlap_rate),
                                              separators = separators,)
    chunks = splitter.split_documents(data)
    print(f"文档切割完成！共生成{len(chunks)}个片段。")

    if print_chunks:
        for i,chunk in enumerate(chunks):
            print(f"\nchunk {i+1}:————————————————————————————————————————————————————————————\n")
            print(chunk.page_content)

    return chunks # list of documents

def _cut_document_md(file_path,
                     chunk_size=600,
                     separators = None,
                     overlap_rate=0.1,
                     print_chunks=True, ):
    """加载并拆分markdown文档，为每个chunk补全父标题"""
    from langchain_community.document_loaders import TextLoader

    # 加载文档
    loader = TextLoader(file_path=file_path, encoding="utf-8")
    data = loader.load()

    # 初始化自定义拆分器
    splitter = MarkdownWithParentSplitter(
        chunk_size=chunk_size,  # 每个块的最大字符数
        chunk_overlap=int(chunk_size * overlap_rate),  # 块之间的重叠字符数
    )

    # 拆分文档
    chunks = splitter.split_documents(data)

    # 可选：打印拆分后的chunk
    if print_chunks:
        for i, chunk in enumerate(chunks):
            print(f"\n===== chunk {i + 1} =====")
            print(chunk.page_content)

    return chunks


def md_to_chroma_db(embedding_model,
             cut_mode,
             db_name,
             use_cosine_similarity=False,
             db_path = "./chroma_db",
             db_status = "persistent",
             folder_path = "data/clean_data",
             chunk_size = 550,
             separators = None,
             overlap_rate=0.1,
             print_chunks = True,
            ):

    # 存档：version 1
    # cut_mode = "normal"
    # ,
    # db_name = "Cloud_Music_Report",

    if cut_mode == "normal":
        cutter = _cut_document
    elif cut_mode == "md":
        cutter = _cut_document_md
    else:
        raise ValueError("Invalid cut_mode. Please choose 'normal' or 'md'.")

    # 遍历文件夹中的所有文件
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        chunks_ = cutter(
            file_path = file_path,
            chunk_size = chunk_size,
            separators = separators,
            overlap_rate=overlap_rate,
            print_chunks = print_chunks)

        # vector store
        if db_status == "persistent":
            if use_cosine_similarity:
                vector_store = Chroma(
                    collection_name=db_name,
                    embedding_function=embedding_model,
                    persist_directory=db_path,
                    collection_metadata={"hnsw:space": "cosine"}  # 这个设置现在才真正生效
                )
            else:
                vector_store = Chroma(collection_name=db_name,
                                      embedding_function=embedding_model,
                                      persist_directory=db_path
                                      )
        else:
            vector_store = Chroma(collection_name=db_name,
                                  embedding_function=embedding_model)
        print("##############正在存入Chroma数据库中##############")
        vector_store.add_documents(chunks_)
        print("数据库存入完成！")


# def md_to_bm25_temp_and_retrieve(
#                question,
#                cut_mode,
#                with_score = False,
#                folder_path = "data/clean_data",
#                chunk_size = 550,
#                separators = None,
#                overlap_rate=0.1,
#                print_chunks = True,
#                top_k=3,
#             ):
#     bm25_retriever = None
#
#     if cut_mode == "normal":
#         cutter = _cut_document
#     elif cut_mode == "md":
#         cutter = _cut_document_md
#     else:
#         raise ValueError("Invalid cut_mode. Please choose 'normal' or 'md'.")
#
#     all_chunks = []
#     for filename in os.listdir(folder_path):
#         file_path = os.path.join(folder_path, filename)
#
#         chunks_ = cutter(
#             file_path=file_path,
#             chunk_size=chunk_size,
#             separators=separators,
#             overlap_rate=overlap_rate,
#             print_chunks=print_chunks)
#         all_chunks += chunks_
#
#         # 适配中文
#         # 导入jieba用于中文分词
#         import jieba
#         from rank_bm25 import BM25Okapi
#         import numpy as np
#
#         # 对文档进行中文分词
#         tokenized_corpus = [list(jieba.cut(doc.page_content)) for doc in all_chunks]
#
#         # 对查询进行中文分词
#         tokenized_query = list(jieba.cut(question))
#
#         # 创建BM25模型并计算分数
#         bm25 = BM25Okapi(tokenized_corpus)
#         scores = bm25.get_scores(tokenized_query)
#
#         # 获取top_k个结果的索引
#         top_k_indices = np.argsort(scores)[-top_k:][::-1]
#
#     if with_score:
#         # ====================
#         # 直接使用计算的分数返回结果
#         docs_bm25_with_score = []
#         for idx in top_k_indices:
#             if scores[idx] > 0:  # 只返回有相关性的结果
#                 docs_bm25_with_score.append((all_chunks[idx], float(scores[idx])))
#         return docs_bm25_with_score
#     else:
#         # ====================
#         # 直接返回文档，不再调用原来的BM25Retriever
#         docs_bm25 = [all_chunks[idx] for idx in top_k_indices if scores[idx] > 0]
#         return docs_bm25


def md_to_bm25_temp_and_retrieve(
               question,
               cut_mode,
               with_score = False,
               folder_path = "data/clean_data",
               chunk_size = 550,
               separators = None,
               overlap_rate=0.1,
               print_chunks = True,
               top_k=3,
            ):
    bm25_retriever = None

    if cut_mode == "normal":
        cutter = _cut_document
    elif cut_mode == "md":
        cutter = _cut_document_md
    else:
        raise ValueError("Invalid cut_mode. Please choose 'normal' or 'md'.")

    all_chunks = []
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)

        chunks_ = cutter(
            file_path=file_path,
            chunk_size=chunk_size,
            separators=separators,
            overlap_rate=overlap_rate,
            print_chunks=print_chunks)
        all_chunks += chunks_

    # 适配中文
    # 导入jieba用于中文分词
    import jieba
    from rank_bm25 import BM25Okapi
    import numpy as np

    # 对文档进行中文分词
    tokenized_corpus = [list(jieba.cut(doc.page_content)) for doc in all_chunks]

    # 创建BM25模型
    bm25 = BM25Okapi(tokenized_corpus)

    # 处理单个问题或多个问题
    if isinstance(question, str):
        # 单个问题
        questions = [question]
    else:
        # 假设是列表
        questions = question

    all_results = []
    for q in questions:
        # 对查询进行中文分词
        tokenized_query = list(jieba.cut(q))

        # 计算分数
        scores = bm25.get_scores(tokenized_query)

        # 获取top_k个结果的索引
        top_k_indices = np.argsort(scores)[-top_k:][::-1]

        if with_score:
            # 返回带分数的结果
            docs_bm25_with_score = []
            for idx in top_k_indices:
                if scores[idx] > 0:  # 只返回有相关性的结果
                    docs_bm25_with_score.append((all_chunks[idx], float(scores[idx])))
            all_results.append(docs_bm25_with_score)
        else:
            # 直接返回文档
            docs_bm25 = [all_chunks[idx] for idx in top_k_indices if scores[idx] > 0]
            all_results.append(docs_bm25)

    # 如果输入是单个问题，直接返回结果而不是列表的列表
    if isinstance(question, str):
        return all_results[0]
    else:
        return all_results
# def md_to_db_with_summary(summary_model,
#                           file_path = "data/MinerU_md_trans.md",
#                           chunk_size=600,
#                           separators=None,
#                           overlap_rate=0.1,
#                           print_chunks=False,
#                           print_chunks_summary=False,
#                           db_path = "./chroma_db_temp",
#                           db_name = "Album1_Report_0",
#                           db_status = "persistent",
#                           ):
#     chunks = _cut_document(file_path= file_path,
#                           chunk_size=chunk_size,
#                           separators=separators,
#                           overlap_rate=overlap_rate,
#                           print_chunks=print_chunks)
#     prompt = PromptTemplate(input_variables=["input"],
#                            template="请总结以下文本：{input}")
#     parser = StrOutputParser()
#     chain = {"input":RunnablePassthrough()} | prompt | summary_model | parser
#     print("##############正在总结文本ing##############")
#     chunks = chunks[3:5]
#     print("原始文本：", [chunk.page_content for chunk in chunks])
#     summaries = chain.batch([chunk.page_content for chunk in chunks])
#     # 11行变成8行，效果一般，先不写下去了。具体见教材
#
#     return(summaries)

def get_chroma_retriever(embedding_model,
                         use_cosine_similarity = False,
                         return_vector_store = False,
                         db_name = "Cloud_Music_Report",
                         top_k = 3,
                         chromadb_path = "./chroma_db"):
    if return_vector_store:
        if use_cosine_similarity:
            vector_store = Chroma(collection_name=db_name,
                                  embedding_function=embedding_model,
                                  persist_directory=chromadb_path,
                                  collection_metadata={"hnsw:space": "cosine"})
        else:
            vector_store = Chroma(collection_name=db_name,
                                  embedding_function=embedding_model,
                                  persist_directory=chromadb_path)
        return vector_store
    else:
        retriever_ = Chroma(collection_name=db_name,
                           embedding_function=embedding_model,
                           persist_directory=chromadb_path).as_retriever(search_kwargs={"k": top_k})
        return retriever_


if __name__=="__main__":

    # 重建数据库，非必要不True！
    version1_to_db = False
    version2_to_db = False
    version3_to_db = False

    # 调试
    bm25_test = False
    chroma_and_bm25_with_score = False
    chroma_score_test = True
    bm25_score_test = False


    # chunks = _cut_document(print_chunks=True)
    # print(chunks)

    # chunks = _cut_document_md(file_path='data/clean_data/网易云音乐2025年中（1-6月）业绩报告_.md',
    #                           print_chunks=True)
    # print(chunks)

    # print(make_catalogue(file=open('data/clean_data/网易云音乐2025年中（1-6月）业绩报告_.md', 'r', encoding='utf-8')))

    # chunks = _cut_document_md(file_path='data/clean_data/网易云音乐2025年中（1-6月）业绩报告_.md',)

    # version1_to_db
    if version1_to_db:
        print('Version1 开始存入……')
        md_to_chroma_db(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                        cut_mode="normal",
                        db_path="./chroma_db",
                        db_name="Cloud_Music_Report")

    # version2_to_db
    if version2_to_db:
        print('Version2 开始存入……')
        md_to_chroma_db(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                        cut_mode="md",
                        db_path="./chroma_db",
                        db_name="Cloud_Music_Report_with_parent_title")

    # version3_to_db
    # 需要完全不一样的repository
    if version3_to_db:
        print('Version3 开始存入……')
        md_to_chroma_db(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                        cut_mode="md",
                        db_path="./chroma_db_cosine",
                        use_cosine_similarity=True,
                        db_name="Cloud_Music_Report_with_parent_title_Cosine_Similarity")

    # md_to_chroma_db(get_embedding_client(model_name='bge-m3', organization='ollama'))

    # retriever = get_retriever(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'))
    # print(retriever.invoke("网易云音乐2025年度的总收入是多少？"))
    # print(os.path.basename(retriever.invoke("网易云音乐2025年度的总收入是多少？")[0].metadata["source"]))

    if bm25_test:
        """BM25：用普通方法没有获取正确的文段，而用加了Parent title的markdown，成功获取，位于第二个。"""
        """二编：好像并没有成功获取……"""
        question = "2025年度，网易云音乐的研发费用较2024年变化了多少？"
        # question = "网易云音乐2025年度的总收入是多少？"

        print(md_to_bm25_temp_and_retrieve(question=question,
                                           cut_mode="normal",
                                           print_chunks = False))
        print('***********')
        print(md_to_bm25_temp_and_retrieve(question=question,
                                           cut_mode="md",
                                           print_chunks = False))

    if chroma_and_bm25_with_score:

        # chroma db
        chroma_vector_store = get_chroma_retriever(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                                                   db_name="Cloud_Music_Report_with_parent_title_Cosine_Similarity",
                                                   chromadb_path="./chroma_db_cosine",
                                                   return_vector_store = True,
                                                   use_cosine_similarity = True
                                                   )
        results = chroma_vector_store.similarity_search_with_score(
            # "2025年度，网易云音乐的研发费用较2024年变化了多少？",
            # '网易云音乐2025年度的总收入是多少？',
            '2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
            k=3,
        )
        # 返回的是余弦距离，要用1去减得到的才是余弦相似度！
        for doc, score in results:
            print(f"文档内容: {doc.page_content}")
            print(f"评分: {1-score}")
            print(f"元数据: {doc.metadata}")
            print("-" * 50)

        # bm25
        docs_with_scores = md_to_bm25_temp_and_retrieve(
            # question='2025年度，网易云音乐的研发费用较2024年变化了多少？',
            # question='网易云音乐2025年度的总收入是多少？',
            question='2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
            cut_mode="md",
            with_score=True,
            print_chunks = False
        )
        for doc, score in docs_with_scores:
            print(f"文档内容: {doc.page_content}")
            print(f"相似度分数: {score}")
            print(f"元数据: {doc.metadata}")
            print("-" * 50)

    question_lst = [
    '网易云音乐2025年度的总收入是多少？',
    '截至2025年12月31日止年度，网易云音乐的毛利率是多少？',
    '2025年上半年，网易云音乐的在线音乐服务收入同比增长了多少？',
    '网易云音乐2025年度的经调整净利润是多少？',
    '2025年上半年，网易云音乐的社交娱乐服务及其他收入同比下降了多少？',
    '网易云音乐在2025年度确认的递延所得税抵免金额是多少？',
    '截至2025年6月30日，网易云音乐的独立音乐人数量是多少？',
    '2025年上半年，网易云音乐的毛利率较2024年同期提升了多少？',
    '2025年度，网易云音乐的研发费用较2024年变化了多少？',
    '2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
    '2025年，网易云音乐的流动负债和非流动负债分别是多少？',
    '2025年上半年，网易云音乐的支出费用中按性质划分，比上一年增加的费用有哪些?',
    '2025年，网易云音乐为了增强音乐消费体验而做了哪些措施？',
    '网易云音乐2025年的重大投资与重大收购有哪些？',
    '2025年网易云音乐会员订阅收入同比增长了多少？如何进一步提升？',
    '请列出网易云音乐2025年度收入下降的主要原因。',
    '2025年上半年，网易云音乐的销售及市场费用同比下降了多少？主要原因是什么？',
    '网易云音乐在2025年度财报中提到的“Climber”是什么？它的作用是什么？',
    '请根据2025年度财报，说明网易云音乐在原创音乐方面的主要进展。',
    '2025年度，网易云音乐的雇员人数变化情况如何？薪酬总成本是多少？',
    '请简述网易云音乐在2025年上半年的产品创新方面有哪些具体举措？',
    '结合2025年度和2025年上半年财报，分析网易云音乐毛利率持续提升的主要原因，并说明其背后的业务战略调整。',
    '请根据两份财报中的税项部分，解释递延所得税资产确认的背景及其对净利润的影响。',
    '2025年上半年，网易云音乐的“在线音乐服务收入”与“社交娱乐服务及其他收入”呈现相反趋势，请分析这一趋势背后的战略意图及其对公司长期发展的影响。',
    '请结合财报中关于“支柱二规则”的披露，说明其对网易云音乐未来税负的潜在影响，并评估其对公司净利润的可能影响。'
    ]
    question_lst = [
        "2025年度，网易云音乐的研发费用较2024年变化了多少？",
        '2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
        '网易云音乐2025年度的总收入是多少？']

    if chroma_score_test:
        # 余弦相似度
        scores = []
        for question in question_lst:
            print(question)
            retriever = get_chroma_retriever(embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                                          use_cosine_similarity= True,
                                          return_vector_store= True,
                                          top_k = 3,
                                          db_name="Cloud_Music_Report_with_parent_title_Cosine_Similarity",
                                          chromadb_path="./chroma_db_cosine",)
            result = retriever.similarity_search_with_score(question,
                                                            k=3
                                                            )
            scores_for_question = []
            for doc, score in result:
                scores_for_question.append(f"{1-score:.4f}")
            scores.append(scores_for_question)
        print(scores)

        # list of questions
        questions_test = [
            "2025年度，网易云音乐的研发费用较2024年变化了多少？",
            '2025年，网易云音乐的每股基本盈利较2024年的增加了百分之多少？',
            '网易云音乐2025年度的总收入是多少？']
        for question in questions_test:
            print(question)
            retriever = get_chroma_retriever(
                embedding_model=get_embedding_client(model_name='bge-m3', organization='ollama'),
                use_cosine_similarity=True,
                return_vector_store=True,
                top_k=3,
                db_name="Cloud_Music_Report_with_parent_title_Cosine_Similarity",
                chromadb_path="./chroma_db_cosine", )
            result = retriever.similarity_search_with_score(question,
                                                            # k=3
                                                            )
            print(result)

    if bm25_score_test:
        scores = []
        for question in question_lst:
            print(question)
            result = md_to_bm25_temp_and_retrieve(question=question,
                                               cut_mode="md",
                                               with_score=True,
                                               print_chunks = False)
            scores_for_question = []
            for doc, score in result:
                scores_for_question.append(f"{score:.4f}")
            scores.append(scores_for_question)
        print(scores)
        # [['12.1638', '9.4785', '9.0829'], ['20.8719', '20.2053', '17.5975'], ['22.4926', '19.9012', '19.4789'], ['15.4200', '15.3754', '14.8357'], ['23.5557', '23.3827', '23.0788'], ['18.8201', '17.5634', '17.3083'], ['21.4939', '18.8456', '18.2260'], ['22.6824', '20.3832', '20.1974'], ['18.0305', '17.6353', '16.9533'], ['24.4696', '24.1661', '23.9966'], ['19.8530', '19.2448', '19.2343'], ['21.4937', '20.2458', '19.5518'], ['19.9087', '19.7870', '19.0365'], ['24.2698', '18.7778', '14.7759'], ['26.9349', '25.8547', '23.2628'], ['13.4229', '11.7363', '10.9339'], ['23.9333', '23.8373', '22.4753'], ['17.5526', '16.1300', '15.4282'], ['22.1683', '21.0119', '17.7919'], ['20.6668', '15.8954', '13.3706'], ['19.2547', '19.2034', '19.1513'], ['32.0354', '30.2900', '30.2900'], ['27.5129', '24.4954', '24.4816'], ['43.1831', '38.7157', '34.9463'], ['42.7522', '38.3871', '37.3183']]

