# 智能财报问答系统

## 项目简介

本项目是基于大语言模型和知识库的智能财报问答系统，专注于处理网易云音乐业绩报告，通过多阶段流程实现专业、精准的财务信息咨询服务。系统采用RAG（检索增强生成）技术，结合向量检索和关键词检索，为用户提供基于财报数据的智能问答服务。

## 功能特点

- **多阶段数据处理**：从原始Markdown文档到结构化知识库的完整处理流程，包括文档清理、格式转换、表格处理和语义片段切割。
- **多策略检索机制**：支持Chroma向量检索（基于语义相似度）、BM25关键词检索（基于词频）以及两者的混合检索，提高信息获取的准确性和全面性。
- **智能回答生成**：基于Qwen3-max大语言模型，通过结构化Prompt设计约束模型行为，确保回答严格基于检索到的信息，不捏造数据。
- **系统评估框架**：使用RAGAS评估框架对系统性能进行全面评估，包括答案相关性、忠实度、上下文召回率和上下文精确率四个核心维度。

## 技术栈

- **语言模型**：Qwen3-max（通过DashScope API）
- **嵌入模型**：BGE-M3（通过Ollama）
- **向量数据库**：Chroma
- **检索算法**：Chroma向量检索、BM25关键词检索
- **评估框架**：RAGAS
- **工具库**：LangChain、Pandas、Jieba（中文分词）

## 目录结构

```
Project1_DA_Agent/
├── data/
│   ├── raw_data/        # 原始Markdown文档
│   └── clean_data/      # 处理后的文档
├── results/             # 评估结果和示例
│   ├── examples.xlsx    # 示例问题和回答
│   └── results_eval_ragas.xlsx  # RAGAS评估结果
├── step1_preprocess_md.py        # 文档预处理脚本
├── step2_md_to_db_chroma.py      # 文档切割和向量数据库构建
├── step3_retrieve_and_answer.py  # 检索和回答生成
├── step4_evaluation_with_ragas.py  # 系统评估
├── model/               # 模型相关代码
│   └── model_factory.py  # 模型客户端工厂
├── utils/               # 工具函数
│   ├── md_preprocessing.py        # Markdown预处理
│   ├── rewrite_md_splitter_new.py # Markdown智能分割器
│   ├── hybrid_fusion_function.py  # 混合检索融合函数
│   └── document_template.py       # 文档格式化模板
└── .venv/               # 虚拟环境
```

## 安装与环境配置

1. **创建虚拟环境**：
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   # .venv\Scripts\activate  # Windows
   ```

2. **安装依赖**：
   ```bash
   pip install -r requirements.txt
   ```

3. **配置模型**：
   - 确保Ollama已安装并运行BGE-M3模型
   - 配置DashScope API密钥用于Qwen3-max模型访问

## 使用步骤

### 1. 文档预处理
将原始Markdown文档转换为结构化格式：
```bash
python step1_preprocess_md.py
```
此步骤会处理`data/raw_data/`目录下的Markdown文档，生成清理后的文档到`data/clean_data/`目录。

### 2. 构建知识库
将处理后的文档切割并存储到向量数据库：
```bash
python step2_md_to_db_chroma.py
```
此步骤支持两种切割模式：普通文本切割和Markdown智能切割（保留父标题），并将片段存储到Chroma向量数据库。

### 3. 检索与回答
基于用户问题生成回答：
```bash
python step3_retrieve_and_answer.py
```
此步骤支持三种检索策略：
- `Chroma`：纯向量检索
- `BM25`：纯关键词检索
- `hybrid`：向量检索与关键词检索的混合

### 4. 系统评估
使用RAGAS评估框架评估系统性能：
```bash
python step4_evaluation_with_ragas.py
```
评估结果将保存到`results/results_eval_ragas.xlsx`文件。

## 评估结果

基于RAGAS评估框架，系统在四个核心维度的表现如下：

| 评估指标 | 基础版本 | 最新版本 | 提升幅度 |
|---------|---------|---------|---------|
| 答案相关性（answer_relevancy） | 0.6054 | 0.8286 | +36.9% |
| 忠实度（faithfulness） | 0.8664 | 0.8359 | -3.5% |
| 上下文召回率（context_recall） | 0.4625 | 0.7305 | +57.9% |
| 上下文精确率（context_precision） | 0.5682 | 0.8409 | +48.0% |

## 示例查询

以下是系统支持的典型问题示例：
- "网易云音乐2025年度的总收入是多少？"
- "2025年上半年，网易云音乐的毛利率较2024年同期提升了多少？"
- "2025年度，网易云音乐的研发费用较2024年变化了多少？"
- "网易云音乐2025年在原创音乐方面的主要进展有哪些？"

## 注意事项

- 系统仅基于提供的财报数据生成回答，不支持超出文档范围的问题。
- 对于涉及比例/数据比较的问题，系统会提供具体的原始数据。
- 当信息不足时，系统会明确提示"对不起，基于现有消息我无法回答您的问题。"

## 扩展与未来计划

- 支持更多类型的财报文档
- 优化混合检索策略，进一步提高检索准确性
- 增加对话历史管理，支持多轮对话
- 开发Web界面，提升用户体验

## 联系方式

如有问题或建议，请联系项目维护者。