"""
玄照 × OpenRath × MiMo 集成示例

用OpenRath的Session/Agent/Workflow架构运行玄照排盘。
"""
import sys
sys.path.insert(0, ".")

from collections.abc import Mapping
from typing import Any
from pydantic import BaseModel, Field

from rath import flow
from rath.flow.tool import FlowToolCall
from rath.session import Session
from rath.session.chunk import ChunkKind


# ============================================================
# 1. 玄照工具（Tool）
# ============================================================

class BaziInput(BaseModel):
    birth: str = Field(description="出生时间，格式：YYYY-MM-DD HH:MM")
    location: str = Field(description="出生地，如：北京")
    gender: str = Field(description="性别：男/女")


class BaziTool(FlowToolCall):
    """八字排盘工具"""
    @property
    def name(self) -> str:
        return "bazi_paipan"

    @property
    def description(self) -> str:
        return "根据出生时间和地点进行八字排盘，返回四柱、十神、喜忌、大运等信息"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return BaziInput.model_json_schema()

    def __call__(self, session: Session, arguments: Mapping[str, Any]) -> dict:
        data = BaziInput.model_validate(dict(arguments))
        try:
            from engine.bazi_engine import BaziEngine
            eng = BaziEngine()
            gender_int = 1 if data.gender in ("男", "male", "m", "1") else 0
            result = eng.analyze(data.birth, data.location, gender_int)
            return {"status": "success", "bazi": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class ZiweiInput(BaseModel):
    birth: str = Field(description="出生时间，格式：YYYY-MM-DD HH:MM")
    location: str = Field(description="出生地")
    gender: str = Field(description="性别：男/女")


class ZiweiTool(FlowToolCall):
    """紫微斗数排盘工具"""
    @property
    def name(self) -> str:
        return "ziwei_paipan"

    @property
    def description(self) -> str:
        return "根据出生时间和地点进行紫微斗数排盘，返回命宫、主星、四化等信息"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return ZiweiInput.model_json_schema()

    def __call__(self, session: Session, arguments: Mapping[str, Any]) -> dict:
        data = ZiweiInput.model_validate(dict(arguments))
        try:
            from engine.ziwei_engine import ZiWeiEngine
            eng = ZiWeiEngine()
            gender_int = 1 if data.gender in ("男", "male", "m", "1") else 0
            result = eng.analyze(data.birth, data.location, gender_int)
            return {"status": "success", "ziwei": result}
        except Exception as e:
            return {"status": "error", "error": str(e)}


class KnowledgeInput(BaseModel):
    query: str = Field(description="搜索关键词，如：甲木日主、事业、感情")


class KnowledgeTool(FlowToolCall):
    """知识库检索工具"""
    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return "从玄照知识库中搜索相关玄学知识，支持八字、紫微、六爻、奇门、大六壬、太乙等"

    @property
    def parameters(self) -> Mapping[str, Any]:
        return KnowledgeInput.model_json_schema()

    def __call__(self, session: Session, arguments: Mapping[str, Any]) -> dict:
        data = KnowledgeInput.model_validate(dict(arguments))
        try:
            from knowledge.search import KnowledgeSearch
            ks = KnowledgeSearch()
            results = ks.search_by_method(data.query) or ks.search_by_theme(data.query)
            if not results:
                from knowledge.index import search_by_query
                results = search_by_query(data.query)
            return {"status": "success", "results": results[:5]}
        except Exception as e:
            return {"status": "error", "error": str(e)}


# ============================================================
# 2. 玄照视角Agent
# ============================================================

PERSPECTIVES = {
    "袁天罡": "你是袁天罡，精通八字和面相。用骨相推命法分析命盘，关注少年看骨、中年看气、老年看神。",
    "诸葛亮": "你是诸葛亮，精通奇门遁甲和兵法。用隆中对推演法分析，先看大势再看细节。",
    "倪海厦": "你是倪海厦，精通紫微斗数和针灸。用三才贯通法分析，天纪看命、人纪看病、地纪看运。",
    "邵雍": "你是邵雍，精通梅花易数和先天象数。用万物类象法分析，取象断测。",
    "鬼谷子": "你是鬼谷子，精通纵横术和六爻。用捭阖之术分析，开合有度。",
}


# ============================================================
# 3. 辅助函数
# ============================================================

def get_user_message(session: Session) -> str:
    """从Session中提取用户消息"""
    for row in session.chunk_table.rows:
        if row.kind == ChunkKind.USER:
            return row.payload.get("content", "")
    return ""


def get_last_assistant_message(session: Session) -> str:
    """从Session中提取最后一条助手消息"""
    for row in reversed(session.chunk_table.rows):
        if row.kind == ChunkKind.ASSISTANT:
            return row.payload.get("content", "") or ""
    return ""


# ============================================================
# 4. 玄照Workflow
# ============================================================

class XuanzhaoWorkflow(flow.Workflow):
    """玄照排盘分析Workflow"""

    def __init__(self, provider: flow.Provider, perspectives: list[str] = None):
        self.provider = provider
        self.perspectives = perspectives or ["袁天罡", "诸葛亮", "倪海厦"]

        # 创建排盘工具
        self.bazi_tool = BaziTool()
        self.ziwei_tool = ZiweiTool()
        self.knowledge_tool = KnowledgeTool()

        # 创建视角Agent
        self.agents = {}
        for name in self.perspectives:
            prompt = PERSPECTIVES.get(name, f"你是{name}，精通命理分析。")
            self.agents[name] = flow.Agent(
                f"""{prompt}

你将使用排盘工具获取命盘数据，然后用你的专业知识分析。

分析要求：
1. 先调用排盘工具获取数据
2. 用你的专业视角分析命盘
3. 给出具体、可执行的建议
4. 用口语化、短句风格表达
5. 不要用AI腔调（首先、其次、综上所述等）""",
                provider,
                tools=[self.bazi_tool, self.ziwei_tool, self.knowledge_tool],
                memory="local",
            )

        # 创建综合Agent
        self.synthesis_agent = flow.Agent(
            """你是玄照的综合分析师。你将收到多个视角的分析结果，需要综合判断。

要求：
1. 找出各视角的共识点
2. 找出各视角的分歧点
3. 给出综合判断和置信度
4. 用极简大实话风格表达
5. 短句加空格做停顿
6. 一击即中告诉用户行还是不行""",
            provider,
        )

    def forward(self, session: Session) -> Session:
        """运行玄照分析流程"""

        # 1. 提取问题
        question = get_user_message(session) or "分析命盘"

        # 2. 运行各视角Agent
        opinions = []
        for name, agent in self.agents.items():
            # 创建分支Session（绑定到本地sandbox）
            branch = Session.from_user_message(
                f"请用{name}的视角分析：{question}"
            ).to("local", spec="./")
            # 运行Agent
            result = agent(branch)
            opinion = get_last_assistant_message(result)
            opinions.append(f"【{name}】{opinion}")
            print(f"  ✓ {name}分析完成")

        # 3. 综合分析
        print("  ⏳ 综合分析中...")
        synthesis_input = Session.from_user_message(
            f"请综合以下分析结果：\n\n" + "\n\n".join(opinions)
        ).to("local", spec="./")
        final = self.synthesis_agent(synthesis_input)

        return final


# ============================================================
# 5. 主函数
# ============================================================

def main():
    """运行玄照OpenRath集成"""

    # 配置MiMo Provider
    provider = flow.Provider(
        model="mimo-v2.5-pro",
        api_key="tp-syfnd40eilysggo5yj75f1ud2ovq9f4jvd2ym6o8b42varvg",
        base_url="https://token-plan-sgp.xiaomimimo.com/v1",
    )

    # 创建Workflow
    workflow = XuanzhaoWorkflow(
        provider,
        perspectives=["袁天罡", "诸葛亮", "倪海厦"],
    )

    # 创建Session（绑定到本地sandbox）
    session = Session.from_user_message(
        "1990年1月15日早上8点半，北京出生，男，事业如何？"
    ).to("local", spec="./")

    # 运行
    print("=== 玄照 × OpenRath × MiMo ===")
    print("正在分析...")
    result = workflow(session)

    # 输出结果
    print("\n=== 综合分析结果 ===")
    final_answer = get_last_assistant_message(result)
    print(final_answer)


if __name__ == "__main__":
    main()
