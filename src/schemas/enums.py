from enum import StrEnum

class SectionType(StrEnum):
    """
    教材板块类型
    描述教材内容的原始排版和教学意图结构。
    """
    VOCABULARY_SCENE = "vocabulary_scene"  # 词汇场景：通常包含图片和词汇列表
    DIALOGUE = "dialogue"                  # 对话：角色之间的对话练习
    EXERCISE = "exercise"                  # 练习：具体的习题
    NARRATIVE = "narrative"                # 叙事/故事：故事阅读
    PHONICS = "phonics"                    # 自然拼读：发音练习
    ACTIVITY = "activity"                  # 活动：互动任务或游戏
    GRAMMAR = "grammar"                    # 语法：语法规则讲解
    UNKNOWN = "unknown"                    # 未知：默认值

class BlockType(StrEnum):
    """
    内容块类型
    描述经 Context Engine 归一化处理后的原子数据结构。
    """
    CONVERSATION = "conversation"          # 对话/剧本：包含角色轮次 (turns)
    PROSE = "prose"                        # 文章/散文：段落文本
    VERSE = "verse"                        # 韵文/诗歌：诗行和韵律
    VOCABULARY_LIST = "vocabulary_list"    # 词汇表：单词及其上下文
    PHONICS_RULE = "phonics_rule"          # 拼读规则：目标音和例词
    COMPARISON_DATA = "comparison_data"    # 对比数据：多维度对比表
    SPATIAL_MAP = "spatial_map"            # 空间/地图：位置关系描述
    SEQUENCE_FLOW = "sequence_flow"        # 顺序流程：时间轴或步骤
    MATCHING = "matching"                  # 匹配/连线：项目之间的对应关系
    GRAMMAR_STRUCTURE = "grammar_structure" # 语法结构：公式、句型或规则
    GENERIC = "generic"                    # 通用/其他：未特定结构化的内容

class AssetType(StrEnum):
    """
    资源类型
    """
    IMAGE = "image"                        # 图片资源
    AUDIO = "audio"                        # 音频资源

class ExerciseType(StrEnum):
    """
    练习题类型 (16种)
    对应不同的 Exercise Model Schema。
    """
    MCQ_TEXT = "mcq_text"                  # 文本选择题
    MCQ_IMAGE = "mcq_image"                # 图片选择题
    TRUE_FALSE = "true_false"              # 判断题
    FILL_IN_BLANKS = "fill_in_blanks"      # 填空题
    SENTENCE_ORDERING = "sentence_ordering" # 句子排序
    SEQUENCE_ORDERING = "sequence_ordering" # 序列排序
    ERROR_CORRECTION = "error_correction"  # 改错题
    TABLE_COMPLETION = "table_completion"  # 表格补全
    SHORT_ANSWER = "short_answer"          # 简答题
    WRITING_PROMPT = "writing_prompt"      # 写作提示
    CATEGORIZATION = "categorization"      # 分类题
    MATCHING = "matching"                  # 配对题
    ROLE_PLAY_PROMPT = "role_play_prompt"  # 角色扮演提示
    TEXT_SHADOWING = "text_shadowing"      # 文本跟读/影子练习
    LISTENING_COMPREHENSION = "listening_comprehension" # 听力理解
    PHONICS_PRACTICE = "phonics_practice"  # 拼读练习

class GradeLevel(StrEnum):
    """
    年级等级
    对应小学 1-6 年级的 A/B 册。
    """
    G1A = "1A"
    G1B = "1B"
    G2A = "2A"
    G2B = "2B"
    G3A = "3A"
    G3B = "3B"
    G4A = "4A"
    G4B = "4B"
    G5A = "5A"
    G5B = "5B"
    G6A = "6A"
    G6B = "6B"

class DifficultyLevel(StrEnum):
    """
    难度等级
    """
    EASY = "Easy"                          # 简单
    MEDIUM = "Medium"                      # 中等
    HARD = "Hard"                          # 困难

class ExerciseGenerationStatus(StrEnum):
    """
    练习题生成状态
    注意：为了兼容现有数据库约束 ('pending', 'approved', 'rejected')，
    进行了如下映射：
    - GENERATING -> pending (生成中视为待定)
    - GENERATION_FAILED -> rejected (生成失败)
    - PENDING -> pending (生成成功，待审核)
    - NEEDS_REVISION -> pending (需修改也视为待定，或应由人工改为 approved/rejected)
    """
    GENERATING = "pending"                 # 系统正在生成 (映射到 pending)
    GENERATION_FAILED = "rejected"         # 生成失败 (映射到 rejected)
    PENDING = "pending"                    # 待审核 (生成成功)
    APPROVED = "approved"                  # 审核通过
    REJECTED = "rejected"                  # 审核驳回
    NEEDS_REVISION = "pending"             # 需要修改 (映射到 pending)
