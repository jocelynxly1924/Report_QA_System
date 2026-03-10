import os
from langchain_openai import ChatOpenAI
from langchain_community.document_compressors import DashScopeRerank
from langchain_classic.schema import Document

def get_embedding_client(model_name='bge-m3', organization='ollama'):
    if organization == 'ollama':
        from langchain_ollama import OllamaEmbeddings
        return OllamaEmbeddings(model='bge-m3:latest')
    elif organization == 'dashscope':
        return ChatOpenAI(model = model_name,
                          api_key=os.environ['DASHSCOPE_API_KEY_XLY'],
                          base_url='https://dashscope.aliyuncs.com/compatible-mode/v1')
    else:
        return ValueError(f'{organization} is not supported!')

def get_llm_client(model_name, organization='dashscope'):
    if organization == 'ollama':
        from langchain_ollama import OllamaLLM
        return OllamaLLM(model='qwen2.5:7b-instruct-q4_K_M')
    elif organization == 'dashscope':
        return ChatOpenAI(model = model_name,
                      api_key=os.environ['DASHSCOPE_API_KEY_XLY'],
                      base_url='https://dashscope.aliyuncs.com/compatible-mode/v1',
                      )

def get_rerank_model(model_name='gte-rerank-v2',top_n=3):
    reranker_ = DashScopeRerank(
        model=model_name,
        dashscope_api_key=os.environ['DASHSCOPE_API_KEY_XLY'],
        top_n=top_n
    )
    return reranker_


if __name__ == '__main__':
    # embedding_client = get_embedding_client(model_name='bge-m3', organization='ollama')
    # llm_client = get_llm_client(model_name='qwen2.5',organization='ollama')
    # llm_client2 = get_llm_client(model_name='qwen-max',organization='dashscope')
    # print(embedding_client)
    # print(llm_client.invoke("hello world"))
    # print(llm_client2.invoke("hello world"))

    reranker = get_rerank_model()
    # 准备文档
    documents = [
        Document(page_content="机器学习是人工智能的一个分支..."),
        Document(page_content="深度学习是机器学习的一种..."),
    ]

    # 压缩/重排序
    compressed_docs = reranker.compress_documents(
        documents=documents,
        query="什么是机器学习"
    )

    print(compressed_docs)
    for doc in compressed_docs:
        print(doc.page_content)
        print(f"分数: {doc.metadata.get('relevance_score', 'N/A')}")
