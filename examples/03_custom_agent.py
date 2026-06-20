"""
示例3：自定义Agent接入 — 任何AI都能装进玄照

场景：你有一个GPT/Claude/本地模型，想让它变成玄学大师。
只需要实现3个方法：think、speak、judge。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shell import XuanzhaoShell, Soul, AnalysisContext, Thought, OpinionContext, Judgment


class MyAgent:
    """
    你的自定义Agent

    这个Agent可以是：
    - GPT-4的wrapper
    - Claude的wrapper
    - 本地LLM的wrapper
    - 甚至是一个规则引擎（不用LLM）
    """

    def __init__(self, name: str, style: str = "务实"):
        self.name = name
        self.style = style

    def think(self, context: AnalysisContext) -> Thought:
        """
        接收排盘数据，返回你的分析

        context里有：
        - context.bazi — 八字数据
        - context.qimen — 奇门数据
        - context.liuren — 六壬数据
        - context.ziwei — 紫微数据
        - context.question — 用户问题
        """
        # 例：简单的八字分析逻辑
        bazi = context.bazi
        day_master = bazi.get('day_master', {})
        wuxing = day_master.get('wuxing', '')

        # 基于五行给出分析
        analysis = {
            '木': '日主属木，性格仁慈，适合文化教育行业',
            '火': '日主属火，性格热情，适合传媒娱乐行业',
            '土': '日主属土，性格稳重，适合房地产金融行业',
            '金': '日主属金，性格果断，适合法律军警行业',
            '水': '日主属水，性格智慧，适合科技物流行业',
        }.get(wuxing, '五行数据不足，无法判断')

        return Thought(
            figure_id=self.name,
            stance='支持',
            confidence=0.7,
            reasoning=f"基于八字分析：{analysis}",
            key_points=[f"日主{wuxing}", analysis],
            referenced_data={'bazi': bazi},
        )

    def speak(self, opinion: OpinionContext) -> str:
        """
        以你的风格表达观点

        opinion里有：
        - opinion.thought — 你的思考结果
        - opinion.figure — 你的人物设定（如果配了soul）
        - opinion.context — 完整上下文
        """
        thought = opinion.thought
        style_prefix = {
            '务实': '从实际角度分析：',
            '学术': '根据命理学原理：',
            '直觉': '我的直觉告诉我：',
        }.get(self.style, '')

        return f"{style_prefix}{thought.reasoning}。关键点：{'、'.join(thought.key_points)}。"

    def judge(self, opinions: list) -> Judgment:
        """
        综合所有意见，给出最终判断

        opinions是所有视角的意见列表
        """
        # 简单多数投票
        stances = [o.thought.stance for o in opinions]
        support = stances.count('支持')
        oppose = stances.count('反对')
        total = len(stances)

        if support > oppose:
            conclusion = f"多数视角支持（{support}/{total}），建议行动"
            confidence = support / total
        elif oppose > support:
            conclusion = f"多数视角反对（{oppose}/{total}），建议观望"
            confidence = oppose / total
        else:
            conclusion = f"意见分歧（{support}支持/{oppose}反对），需进一步分析"
            confidence = 0.5

        return Judgment(
            conclusion=conclusion,
            confidence=confidence,
            consensus_points=[f"支持率{support/total*100:.0f}%"],
            dissent_points=[f"反对率{oppose/total*100:.0f}%"],
            recommendations=[conclusion],
        )


# === 使用 ===
if __name__ == "__main__":
    # 1. 创建你的agent
    agent = MyAgent("我的大师", style="务实")

    # 2. 创建壳子
    shell = XuanzhaoShell()

    # 3. 装载agent
    shell.mount(agent)

    # 4. 排盘（纯本地，不需要LLM）
    ctx = shell.analyze("2005-06-09 12:00", "呼和浩特", "男")

    # 5. 让agent思考
    thought = agent.think(ctx)
    print(f"=== {agent.name}的分析 ===")
    print(f"立场: {thought.stance}")
    print(f"推理: {thought.reasoning}")
    print(f"关键点: {thought.key_points}")

    # 6. 让agent发言
    opinion = OpinionContext(thought=thought, figure=None, context=ctx)
    speech = agent.speak(opinion)
    print(f"\n发言: {speech}")
