import pytest
from unittest.mock import MagicMock, patch
from src.gateway import AIServiceGateway
from src.orchestrator.context_engine import StandardizedContext, MetaInfo, PedagogicalGoals, NormalizedContent

@pytest.fixture
def real_gateway():
    gateway = AIServiceGateway()
    return gateway

def test_preprocess_section_flow_real_db(real_gateway):
    # 使用真实的 section_id
    section_id = "01c55a99-a0be-4b51-8c34-f4270a04dab0"
    
    # 执行预处理
    result = real_gateway.preprocess_section(section_id)
    
    # 验证结果结构
    assert isinstance(result, StandardizedContext)
    assert result.meta.section_id == section_id
    assert result.meta.book_id is not None
    assert result.meta.unit_id is not None
    
    # 验证数据库中是否已保存
    db = real_gateway.db
    saved_resp = db.table("section_preprocessing").select("*").eq("section_id", section_id).execute()
    assert len(saved_resp.data) > 0
    print(f"Successfully verified persistence for section_id: {section_id}")
    
    print("\nPreprocess Real DB Integration Test Passed!")
    print(f"Section ID: {section_id}")
    print("Result Meta:", result.meta)

if __name__ == "__main__":
    # 如果作为脚本执行，手动运行
    try:
        # 手动创建 gateway 实例
        gateway = AIServiceGateway()
        test_preprocess_section_flow_real_db(gateway)
    except Exception as e:
        print(f"Test Failed: {e}")
        import traceback
        traceback.print_exc()
