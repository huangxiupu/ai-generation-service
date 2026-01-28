# AI Generation Service

AI Generation Service 是 EngPal 项目的核心后端服务，专门用于通过大语言模型 (LLM) 和多模态 AI 生成高质量的教育内容。该服务采用高度模块化的架构，支持多种 AI 提供商，并拥有一个健壮的 **AIGC 生成流水线**。

## **核心架构**

服务采用分层架构设计，确保了生成过程的可控性和可扩展性：

- **Gateway ([gateway.py](src/gateway.py))**: 统一入口，负责与数据库交互、预处理上下文以及调用流水线。
- **Orchestrator ([orchestrator/](src/orchestrator/))**: 核心编排层，管理复杂的多步骤生成流程。
- **Services ([services/](src/services/))**: 原子服务层，包括文本生成 (`TextGenService`)、图像生成 (`ImageGenService`) 和音频生成 (`AudioGenService`)。
- **Providers ([providers/](src/providers/))**: 适配层，支持 OpenAI、阿里云 (DashScope)、ModelScope 等多种模型供应商。

## **AIGC 生成流水线**

流水线是本服务的灵魂，由 [PipelineController](src/orchestrator/pipeline_controller.py) 统筹，采用 **"骨架-填充" (Skeleton-Hydration)** 模式：

### **1. 文本骨架生成 (Skeleton Generation)**
- **输入**: 标准化后的教学上下文 ([StandardizedContext](src/schemas/orchestration.py)) 和练习类型。
- **执行**: [TextGenService](src/services/text_gen.py) 调用 LLM 生成练习的 JSON 结构。
- **产出**: 一个包含文本内容和 **资源规范 (AssetSpecs)** 的 [ExerciseSkeleton](src/schemas/orchestration.py)。`AssetSpecs` 详细定义了需要生成哪些图片（Prompt、路径）和音频（内容、路径）。

### **2. 资源异步填充 (Asset Hydration)**
- **执行**: 控制器遍历 `AssetSpecs`，根据资源类型调用相应的服务：
    - **图像生成**: [ImageGenService](src/services/image_gen.py) 根据生成的 Prompt 产生视觉素材。
    - **音频生成**: [AudioGenService](src/services/audio_gen.py) 进行文本转语音 (TTS)。
- **特性**: 具备 **幂等性检查**，如果目标路径已存在有效资源，则跳过生成，节省 API 消耗。

### **3. 装配与验证 (Assembly & Validation)**
- **执行**: 生成的资源 URL 会根据 `target_path` 自动回填到练习 JSON 的对应位置。
- **验证**: 使用 [SchemaValidator](src/utils/validation.py) 对最终结果进行严格的格式检查，确保符合前端渲染要求。

## **关键技术特性**

- **动态提示词注册表 ([PromptRegistry](src/utils/prompt_registry.py))**: 使用 Jinja2 模板引擎管理系统级和用户级提示词，支持复杂的逻辑嵌入和 Schema 注入。
- **健壮的 JSON 修复 ([error_handling.py](src/utils/error_handling.py))**: 集成了 `json_repair` 和重试机制，应对 LLM 输出格式不稳定的问题。
- **标准化上下文引擎 ([ContextEngine](src/orchestrator/context_engine.py))**: 将原始教材内容转化为 LLM 易于理解的标准化结构，提高生成的准确度。

## **快速开始**

### **1. 环境准备**
```bash
# 安装依赖
pip install -r requirements.txt
```

### **2. 配置**
在 `src/ai_config.yaml` 或 `.env` 中配置你的 API 密钥和模型参数：
- `CHANNEL_TEXT`: 文本模型通道 (openai/aliyun)
- `MODEL_TEXT`: 使用的具体模型名称
- `SUPABASE_URL` / `SUPABASE_KEY`: 数据库连接

### **3. 启动服务**
```bash
python -m src.main
```
服务将运行在 `http://localhost:8000`。

## **主要 API 接口**

- `POST /api/preprocess`: 预处理教材章节，提取关键词和上下文。
- `POST /api/generate_exercise`: 启动 AIGC 流水线生成指定类型的练习题。

---
*EngPal 内容生成团队维护*
