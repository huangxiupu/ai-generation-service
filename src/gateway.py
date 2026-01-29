from src.config import config
from src.services.text_gen import RealTextGenService, MockTextGenService
from src.services.image_gen import RealImageGenService, MockImageGenService
from src.services.audio_gen import RealAudioGenService, MockAudioGenService
from src.orchestrator.context_engine import ContextEngine
from src.db_client import get_db_client

class AIServiceGateway:
    def __init__(self):
        if config.ENABLE_MOCK:
            print("正在以 MOCK 模式初始化 AIServiceGateway")
            self.text_service = MockTextGenService()
            self.image_service = MockImageGenService()
            self.audio_service = MockAudioGenService()
        else:
            print("正在以 REAL 模式初始化 AIServiceGateway")
            self.text_service = RealTextGenService()
            self.image_service = RealImageGenService()
            self.audio_service = RealAudioGenService()
        
        self.context_engine = ContextEngine(self.text_service)
        self.db = get_db_client()
        
    def generate_text(self, context: dict, exercise_type: str, config: dict = None):
        """
        生成练习的结构化文本内容。
        """
        return self.text_service.generate(context, exercise_type, config)
        
    def generate_image(self, prompt: str, style: str = "textbook_illustration"):
        """
        生成图片 URL。
        """
        return self.image_service.generate(prompt, style)
        
    def generate_audio(self, text: str, voice_id: str = "tongtong", speed: float = 1.0):
        """
        生成音频 URL。
        """
        return self.audio_service.generate(text, voice_id, speed)

    def preprocess_section(self, section_id: str):
        """
        预处理章节 (Section) 数据。
        1. 从数据库获取章节、单元和书籍信息。
        2. 调用 ContextEngine 进行标准化。
        3. 将结果保存到 section_preprocessing 表。
        """
        print(f"[Gateway] 开始预处理章节: {section_id}")
        if not self.db:
            raise Exception("数据库连接未初始化")

        # 1. 获取带有嵌套 Unit 和 Book 数据的 Section
        print(f"[Gateway] 正在从数据库获取章节信息...")
        section_resp = self.db.table("book_sections").select("*").eq("id", section_id).single().execute()
        if not section_resp.data:
            raise Exception(f"未找到 ID 为 {section_id} 的章节")
        section = section_resp.data
        
        print(f"[Gateway] 正在获取单元信息 (unit_id: {section['unit_id']})...")
        unit_resp = self.db.table("book_units").select("*").eq("id", section['unit_id']).single().execute()
        if not unit_resp.data:
            raise Exception(f"未找到 ID 为 {section['unit_id']} 的单元")
        unit = unit_resp.data
        
        print(f"[Gateway] 正在获取书籍信息 (book_id: {unit['book_id']})...")
        book_resp = self.db.table("books").select("*").eq("id", unit['book_id']).single().execute()
        if not book_resp.data:
            raise Exception(f"未找到 ID 为 {unit['book_id']} 的书籍")
        book = book_resp.data
        if not book.get("grade_level"):
            raise Exception(f"书籍 {book.get('title')} 缺少必要的年级信息 (grade_level)")

        # 2. 标准化处理
        print(f"[Gateway] 准备标准化处理...")
        section_data = {
            "section_type": section.get("type"),
            "title": section.get("title"),
            "section_code": section.get("section_code"),
            "content": section.get("content"),
            "visual_context": section.get("visual_context")
        }
        
        unit_meta = {
            "unit_number": unit.get("unit_number"),
            "title": unit.get("title"),
            "learning_objectives": unit.get("learning_objectives")
        }
        
        book_meta = {
            "title": book.get("title"),
            "grade_level": book.get("grade_level")
        }
        
        print(f"[Gateway] 正在调用 context_engine.normalize (可能需要较长时间)...")
        processing_result = self.context_engine.normalize(section_data, book_meta, unit_meta, section_id)
        standardized_context = processing_result.standardized_context
        recommendations = processing_result.recommendations
        
        # 3. 保存预处理结果到数据库
        print(f"[Gateway] 正在保存预处理结果到数据库...")
        # 检查是否已存在记录
        existing = self.db.table("section_preprocessing").select("id").eq("section_id", section_id).execute()
        
        data_to_save = {
            "section_id": section_id,
            "normalized_context": standardized_context.model_dump(), # Pydantic v2
            "preprocessing_version": "1.0"
        }

        if existing.data:
            self.db.table("section_preprocessing").update(data_to_save).eq("section_id", section_id).execute()
        else:
            self.db.table("section_preprocessing").insert(data_to_save).execute()
            
        # 4. 保存推荐结果
        recs_json = [rec.model_dump() for rec in recommendations]
        
        existing_recs = self.db.table("section_exercise_recommendations").select("id").eq("section_id", section_id).execute()
        
        data_to_save_recs = {
            "section_id": section_id,
            "recommended_types": recs_json,
            "analysis_version": 1
        }
        
        if existing_recs.data:
            self.db.table("section_exercise_recommendations").update(data_to_save_recs).eq("section_id", section_id).execute()
        else:
            self.db.table("section_exercise_recommendations").insert(data_to_save_recs).execute()
            
        return standardized_context

    def get_preprocessed_context(self, section_id: str):
        """
        从数据库获取已有的预处理结果。
        """
        from src.schemas.orchestration import StandardizedContext
        
        resp = self.db.table("section_preprocessing").select("normalized_context").eq("section_id", section_id).execute()
        if resp.data and resp.data[0].get("normalized_context"):
            return StandardizedContext(**resp.data[0]["normalized_context"])
        return None
