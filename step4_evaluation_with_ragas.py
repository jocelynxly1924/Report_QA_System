import os
import time
import pandas as pd
from datasets import Dataset
from ragas.embeddings.base import LangchainEmbeddingsWrapper
from ragas.llms.base import LangchainLLMWrapper
# evaluate即将在最新版中被删除。新版本中用Experiment替代
from ragas.evaluation import evaluate
from ragas.metrics import (
    answer_relevancy,
    faithfulness,
    context_recall,
    context_precision,
)
from ragas import config
# 注意！引用的python文件中函数不可在main外被调用，只能在main中调用。不然无法import
from model.model_factory import get_llm_client, get_embedding_client

os.environ['MAX_CONCURRENCY'] = '1' # 没用


def evaluate_results(emb_model, llm_model, version,
                     input_path="results/results.xlsx",
                     output_path="results/results_eval_ragas.xlsx"):
    # 读取数据
    df = pd.read_excel(input_path, sheet_name=version, dtype=str)
    df = df.fillna('')

    # 准备存储结果的列表
    results_list = []

    v_embedding = LangchainEmbeddingsWrapper(emb_model)
    v_llm = LangchainLLMWrapper(llm_model)

    # 逐条处理
    for idx in range(len(df)):
        print(f"处理第 {idx + 1}/{len(df)} 条...")

        # 提取单条数据
        question = df.iloc[idx]["questions"]
        ground_truth = df.iloc[idx]["ground_truth"]
        context = df.iloc[idx]["contexts"]
        answer = df.iloc[idx]["answers"]

        # 创建单条数据的dataset
        data = {
            "user_input": [question],
            "reference": [ground_truth],
            "retrieved_contexts": [[context]],
            "response": [answer]
        }
        dataset = Dataset.from_dict(data)

        try:
            # 评估单条数据
            result = evaluate(
                dataset=dataset,
                metrics=[
                    answer_relevancy,
                    faithfulness,
                    context_recall,
                    context_precision,
                ],
                llm=v_llm,
                embeddings=v_embedding,
            )

            # 提取结果
            result_df = result.to_pandas()

            # 保存结果
            results_list.append({
                'questions': question,
                'ground_truth': ground_truth,
                'contexts': context,
                'answers': answer,
                'answer_relevancy': result_df.iloc[0]['answer_relevancy'],
                'faithfulness': result_df.iloc[0]['faithfulness'],
                'context_recall': result_df.iloc[0]['context_recall'],
                'context_precision': result_df.iloc[0]['context_precision']
            })

            print(f"第 {idx + 1} 条完成")

        except Exception as e:
            print(f"第 {idx + 1} 条失败: {e}")
            # 失败时保存原始数据，评估指标为空
            results_list.append({
                'questions': question,
                'ground_truth': ground_truth,
                'contexts': context,
                'answers': answer,
                'answer_relevancy': None,
                'faithfulness': None,
                'context_recall': None,
                'context_precision': None
            })

        # 每条记录之间暂停一下，避免请求太快
        time.sleep(1)

    # 保存所有结果
    final_df = pd.DataFrame(results_list)

    # 保存到Excel
    sheet_name = f"{version}_eval"
    if os.path.exists(output_path):
        with pd.ExcelWriter(output_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            final_df.to_excel(writer, sheet_name=sheet_name, index=False)
    else:
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            final_df.to_excel(writer, sheet_name=sheet_name, index=False)

    print(f"完成！结果已保存到 {output_path}")

if __name__=="__main__":
    emb = get_embedding_client(model_name='bge-m3', organization='ollama')
    llm = get_llm_client(model_name='qwen3-max', organization='dashscope')
    evaluate_results(
        emb_model=emb,
        llm_model=llm,
        version="version4_hybrid",
        input_path="results/examples.xlsx",
        output_path="results/results_eval_ragas.xlsx"
    )

