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
        预处理 Section 数据。
        1. 从数据库获取 Section, Unit, Book 信息。
        2. 调用 ContextEngine 进行标准化。
        3. 将结果保存到 section_preprocessing 表。
        """
        if not self.db:
            raise Exception("Database connection not initialized")

        # 1. Fetch Section with nested Unit and Book data
        # Note: Supabase JS syntax is different from Python.
        # Python supabase client uses postgrest syntax.
        # We need to fetch step by step or use a complex query if relations are set up.
        # Let's fetch section first.
        
        section_resp = self.db.table("book_sections").select("*").eq("id", section_id).single().execute()
        if not section_resp.data:
            raise Exception(f"Section {section_id} not found")
        section = section_resp.data
        
        unit_resp = self.db.table("book_units").select("*").eq("id", section['unit_id']).single().execute()
        if not unit_resp.data:
            raise Exception(f"Unit {section['unit_id']} not found")
        unit = unit_resp.data
        
        book_resp = self.db.table("books").select("*").eq("id", unit['book_id']).single().execute()
        if not book_resp.data:
            raise Exception(f"Book {unit['book_id']} not found")
        book = book_resp.data

        # 2. Normalize
        # Construct dictionaries expected by ContextEngine
        section_data = {
            "section_type": section.get("type"),
            "content": section.get("content"),
            "visual_context": section.get("visual_context")
        }
        
        unit_meta = {
            "unit_id": unit.get("unit_number"),
            "learning_objectives": unit.get("learning_objectives")
        }
        
        book_meta = {
            "title": book.get("title"),
            "grade_level": book.get("grade_level")
        }
        
        standardized_context = self.context_engine.normalize(section_data, book_meta, unit_meta, section_id)
        
        # 3. Save to DB
        # Check if exists
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
            
        return standardized_context
