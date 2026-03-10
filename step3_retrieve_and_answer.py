import os
import time

import pandas as pd
# from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.tools import tool

from model.model_factory import get_llm_client, get_embedding_client
from step2_md_to_db_bm25 import BM25RetrieverPlus
from step2_md_to_db_chroma import get_chroma_retriever,md_to_bm25_temp_and_retrieve
from utils.document_template import format_docs_for_context

# question_list = ["2025年度，网易云音乐的研发费用较2024年变化了多少？"]

info_list = pd.read_excel("results/examples.xlsx", sheet_name="data")

question_list = info_list["questions"].to_list()

print(question_list)

def retrieve_and_answer(emb_model,
                     llm_model,
                     questions,
                     db_name,
                     method = "Chroma",
                     top_k=3,
                     bm25_add_top_k = 0,
                     hybrid_top_k = 5,
                     reranker_top_k = 3,
                     alpha_=0.25,
                     use_reranker = False,
                     print_document = False,
                     write_document = True,
                     output_path = "results/examples.xlsx"):
    # db_name = "Cloud_Music_Report"

    db_path = ''
    if method == "Chroma":
        db_path = "./chroma_db"

    elif method == "hybrid":
        db_path = {'chroma':"./chroma_db_cosine",
                   'bm25':"./bm25_db",}

    elif method == "BM25":
        db_path = "./bm25_db"

    template = """
            请根据上下文用简洁但完整的语句回答问题：

            已知信息：{context}

           【重要规则】

            1. 不要输出无关信息

            2. 不要捏造信息

            3. 如果上下文包含多个相关信息，请综合所有相关内容给出完整回答。如果不同部分信息存在矛盾，请指出矛盾点。

            4. 若基于已知信息无法回答，则输出“对不起，基于现有消息我无法回答您的问题。”
               特殊情况：如果已知信息有与问题匹配的内容，但内容为“该领域未有记录/数据”，判定为信息充足，可以回答。
               例如：
              - 问题：网易云音乐2025年的重大投资有哪些？
              - 上下文：我们于2025年并无作出或持有任何重大投资。
              - 回答：网易云音乐2025年并无作出或持有任何重大投资。

           【特殊规则】

            1. 如果用户询问中包含比例/数据比较，如果信息有涉及原始数据，也需要给出具体的原始数据。
               例如：
               - 问题：2025年上半年，网易云音乐的毛利率较2024年同期提升了多少？
               - 回答：2025年上半年，网易云音乐的毛利率较2024年同期提升了1.4%，从2024年的35.0%提升至2025年的36.4%。

            2. 如果用户询问非数字型问题，用总结语句与实际的例子结合回答，不要只返回笼统信息。
               例如：
               - 问题：网易云音乐2025年在原创音乐中的主要进展；
               - 回答：“发力说唱等特色品类，多首自制说唱曲目广受好评，包括《两难》《莫愁乡》《熄灭》《暗流》《洗牌》。……”

            用户提问：
            """
    prompt = ChatPromptTemplate.from_messages(
        [("system", template), ("human", "{question}")]
    )

    if questions is None:
        questions = question_list

    retriever_ = None
    retriever_chroma = None
    retriever_bm25 = None

    if method != "hybrid":

        if method == "Chroma":
            """获取retriever，通过chain批量回答"""

            retriever_ = get_chroma_retriever(embedding_model=emb_model, db_name=db_name,
                                              top_k=top_k, chromadb_path=db_path)
        elif method == "BM25":

            retriever_ = BM25RetrieverPlus(cache_dir=db_path)
            # 需要多一步加载索引
            retriever_.build_index(
                folder_path="data/clean_data",
                cut_mode="md",
                chunk_size=550,
                overlap_rate=0.1,
                force_rebuild=False  # 关键：设为False就会从缓存加载！不会重新构建
            )

        # chain
        # parser = StrOutputParser()
        chain = ({"context": lambda x: format_docs_for_context(retriever_.invoke(x)),
                  "question": RunnablePassthrough()}
                 | prompt
                 | llm_model) #| parser

    else:    # method == "hybrid":
        retriever_chroma = get_chroma_retriever(embedding_model=emb_model, db_name=db_name,
                                                top_k=top_k, chromadb_path=db_path.get("chroma",""),
                                                use_cosine_similarity=True,
                                                return_vector_store=True)
        retriever_bm25 = BM25RetrieverPlus(cache_dir=db_path.get("bm25",""))
        # 需要多一步加载索引
        retriever_bm25.build_index(
            folder_path="data/clean_data",
            cut_mode="md",
            chunk_size=550,
            overlap_rate=0.1,
            force_rebuild=False  # 关键：设为False就会从缓存加载！不会重新构建
        )

        from utils.hybrid_fusion_function import hybrid_function

        # @tool
        def hybrid_retriever(retriever1, retriever2, question_):
            """分别调用chroma_db和bm25两个检索器"""
            docs1 = retriever1.similarity_search_with_score(question_, k = top_k)
            docs2 = retriever2.invoke(question_, top_k = top_k+bm25_add_top_k, with_score=True)

            return {'chroma_docs_with_scores':docs1,
                    'bm25_docs_with_scores':docs2,
                    'return_score': False,
                    'alpha': alpha_} # return_score：下一步hybrid是否返回分数。设为true则doc template会有问题


        if use_reranker:

            from model.model_factory import get_rerank_model
            reranker = get_rerank_model(top_n=reranker_top_k)

            def reranker_function(question_, doc_s):
                reranked_docs = reranker.compress_documents(doc_s, question_)
                return reranked_docs


            chain = (RunnableParallel({
                    "context": lambda x: format_docs_for_context(
                        reranker_function(question_=x,
                                          doc_s=hybrid_function.invoke(
                                              hybrid_retriever(retriever_chroma, retriever_bm25, x)))
                    ),
                    "question": RunnablePassthrough()
                })
                | prompt
                | llm_model)

        else:
            chain = (RunnableParallel({
                    "context": lambda x: format_docs_for_context(
                        hybrid_function.invoke(hybrid_retriever(retriever_chroma, retriever_bm25, x))
                    ),
                    "question": RunnablePassthrough()
                })
                | prompt
                | llm_model)

    print("##############LLM正在思考中##############")

    start_time = time.time()
    response_list = chain.batch(questions, config={"max_concurrency": 1})
    end_time = time.time()
    print(f"LLM思考时间：{end_time - start_time}秒")

    retrieved_docs = None

    hybrid_scores_list = []

    if write_document or print_document:
        if method == "Chroma":
            retrieved_docs = retriever_.batch(questions)
        elif method == "BM25":
            retrieved_docs = retriever_.invoke(questions, with_score=True)
        elif method == "hybrid":
            # 处理 hybrid 检索结果
            retrieved_docs = []
            hybrid_scores_list = []  # 用于保存详细的分数信息

            for question in questions:
                # 分别调用两个检索器
                chroma_results = retriever_chroma.similarity_search_with_score(question, k=top_k)
                bm25_results = retriever_bm25.invoke(question, with_score=True, top_k=top_k+bm25_add_top_k)

                if use_reranker:
                    # === 有 reranker 的情况 ===
                    # 先获取 hybrid 结果（用于 rerank 的输入）
                    hybrid_results = hybrid_function.invoke({
                        'chroma_docs_with_scores': chroma_results,
                        'bm25_docs_with_scores': bm25_results,
                        'alpha': alpha_,
                        'top_k': hybrid_top_k if 'hybrid_top_k' in locals() else top_k,
                        'print_details': False,
                        'return_score': False  # 只需要文档列表
                    })

                    # 调用 reranker
                    from model.model_factory import get_rerank_model
                    reranker = get_rerank_model(top_n=reranker_top_k)
                    reranked_docs = reranker.compress_documents(hybrid_results, question)
                    retrieved_docs.append(reranked_docs)

                    # 为了保存分数信息，需要重新获取带分数的 hybrid 结果
                    hybrid_results_with_scores = hybrid_function.invoke({
                        'chroma_docs_with_scores': chroma_results,
                        'bm25_docs_with_scores': bm25_results,
                        'alpha': alpha_,
                        'top_k': hybrid_top_k if 'hybrid_top_k' in locals() else top_k,
                        'print_details': False,
                        'return_score': True  # 这次返回带分数的格式
                    })

                    # 保存 hybrid 的分数信息（用于参考）
                    score_details = [
                        {
                            'hybrid_score': item['hybrid_score'],
                            'chroma_score': item['chroma_score'],
                            'bm25_score': item['bm25_score']
                        }
                        for item in hybrid_results_with_scores
                    ]
                    hybrid_scores_list.append(score_details)

                else:
                    # === 没有 reranker 的情况（原有逻辑保持不变） ===
                    hybrid_results_with_scores = hybrid_function.invoke({
                        'chroma_docs_with_scores': chroma_results,
                        'bm25_docs_with_scores': bm25_results,
                        'alpha': alpha_,
                        'top_k': hybrid_top_k if 'hybrid_top_k' in locals() else top_k,
                        'print_details': False,
                        'return_score': True  # 返回带详细分数的格式
                    })

                    # 分离文档和分数信息
                    docs = [item['doc'] for item in hybrid_results_with_scores]
                    score_details = [
                        {
                            'hybrid_score': item['hybrid_score'],
                            'chroma_score': item['chroma_score'],
                            'bm25_score': item['bm25_score']
                        }
                        for item in hybrid_results_with_scores
                    ]

                    retrieved_docs.append(docs)
                    hybrid_scores_list.append(score_details)

    # 把结果写入原excel
    if write_document:
        info_list["answers"] = [response.content for response in response_list]

        if method == "Chroma":
            info_list["contexts"] = [format_docs_for_context(doc) for doc in retrieved_docs]

        elif method == "BM25":
            docs_all = []
            scores_all = []
            for question_retrievals in retrieved_docs:
                doc_for_question = []
                scores_for_question = []
                for doc, score in question_retrievals:
                    doc_for_question.append(doc)
                    scores_for_question.append(f"{score:.4f}")
                docs_all.append(format_docs_for_context(doc_for_question))
                scores_all.append(scores_for_question)
            info_list["contexts"] = docs_all
            info_list["scores"] = scores_all

        elif method == "hybrid":
            # 保存文档
            info_list["contexts"] = [format_docs_for_context(doc) for doc in retrieved_docs]

            # 保存详细的分数信息
            if hybrid_scores_list:
                formatted_scores = []
                for scores in hybrid_scores_list:
                    score_strs = []
                    for score_dict in scores:
                        score_strs.append(
                            f"混合:{score_dict['hybrid_score']:.4f}, "
                            f"Chroma:{(1 - score_dict['chroma_score']):.4f}, "
                            f"BM25:{score_dict['bm25_score']:.4f}"
                        )
                    formatted_scores.append("\n".join(score_strs))
                info_list["hybrid_scores"] = formatted_scores

                # 如果有 reranker，还可以保存 rerank 后的分数
                if use_reranker:
                    rerank_scores_list = []
                    for i, docs in enumerate(retrieved_docs):
                        score_strs = []
                        for j, doc in enumerate(docs):
                            score = doc.metadata.get('relevance_score', 'N/A')
                            if score != 'N/A':
                                score_strs.append(f"Rank{j + 1}: {score:.4f}")
                            else:
                                score_strs.append(f"Rank{j + 1}: N/A")
                        rerank_scores_list.append("\n".join(score_strs))
                    info_list["rerank_scores"] = rerank_scores_list

        info_list["tokens"] = [response.response_metadata["token_usage"]["total_tokens"] for response in response_list]
        # 使用mode='a'追加模式以确保其他sheet不受影响，if_sheet_exists='replace':替换同名sheet
        with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            info_list.to_excel(writer, sheet_name="data", index=False)


    if print_document:
        return retrieved_docs, response_list
    else:
        return response_list


if __name__=="__main__":
    emb = get_embedding_client(model_name='bge-m3', organization='ollama')
    llm = get_llm_client(model_name='qwen3-max', organization='dashscope')

    # version1: default
    # docs, responses = retrieve_and_answer(emb_model=emb, llm_model=llm, questions=question_list,
    #                                       method = "Chroma"
    #                                       db_name='Cloud_Music_Report',
    #                                       print_document=True,
    #                                       write_document=True)

    # version2: with parent title
    # docs, responses = retrieve_and_answer(emb_model=emb, llm_model=llm, questions=question_list,
    #                                       method = "Chroma"
    #                                       db_name='Cloud_Music_Report_with_parent_title',
    #                                       print_document=True,
    #                                       write_document=True)

    # version3: pure bm25 test
    # docs, responses = retrieve_and_answer(emb_model=emb, llm_model=llm, questions=question_list,
    #                                       db_name='Cloud_Music_Report_with_parent_title', # 其实没用
    #                                       method ="BM25",
    #                                       print_document=True,
    #                                       write_document=True)

    # # version4: hybrid test：335 （version6：355：不行）
    docs, responses = retrieve_and_answer(emb_model=emb, llm_model=llm, questions=question_list,
                                          db_name='Cloud_Music_Report_with_parent_title_Cosine_Similarity',
                                          method ="hybrid",
                                          bm25_add_top_k=2,
                                          print_document=True,
                                          write_document=True
                                          )

    # # version5: hybrid test with reranker
    # 前面几个都在50-60s内完成，这个要160s左右（好像是因为家里网络问题。。。），精确度还一般。
    # docs, responses = retrieve_and_answer(emb_model=emb, llm_model=llm, questions=question_list,
    #                                       db_name='Cloud_Music_Report_with_parent_title_Cosine_Similarity',
    #                                       method ="hybrid",
    #                                       top_k = 5,
    #                                       hybrid_top_k=7,
    #                                       reranker_top_k=4,
    #                                       use_reranker=True,
    #                                       print_document=True,
    #                                       write_document=True
    #                                       )

    # print(responses)
    print([response.content for response in responses])
    for doc in docs:
        print("###############")
        print(doc)

