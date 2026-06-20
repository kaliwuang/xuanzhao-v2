"""
玄照 v2.0 装甲壳子 (XuanzhaoShell)

设计目标：任何AI agent装载进去，都能完美使用玄照的全部功能。
不需要懂内部实现，不需要会排盘，不需要懂玄学。

用法：
    from shell import XuanzhaoShell, Soul, AgentAdapter

    # 1. 创建壳子
    shell = XuanzhaoShell()

    # 2. 注入灵魂（可选，不注入用默认108视角）
    shell.load_soul(Soul.from_file("my_soul.yaml"))

    # 3. 装载agent
    shell.mount(my_agent)

    # 4. 一键运行
    result = shell.run(birth="2005-06-09 11:50", location="呼和浩特",
                       gender="男", question="事业如何")
"""
import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Protocol, Callable
from pathlib import Path

# 确保项目根目录在路径中
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# 1. Soul — 灵魂配置层
# ============================================================

@dataclass
class FigureSoul:
    """单个人物的灵魂定义"""
    id: str
    name: str
    title: str
    category: str  # 术士/哲人/谋士/异人
    faction: str   # 传统/创新/综合
    expertise: List[str]       # 擅长领域
    primary_method: str        # 主用术法
    thinking_model: Dict       # 思维模型
    catchphrase: str           # 口头禅
    bio: str                   # 简介
    soul: Dict = field(default_factory=dict)  # 灵魂细节


@dataclass
class Soul:
    """
    灵魂配置 — 定义壳子的"人格"

    可以：
    - 从文件加载（YAML/JSON）
    - 从默认108视角继承
    - 动态添加/删除人物
    - 完全自定义一套新人格
    """
    figures: Dict[str, FigureSoul] = field(default_factory=dict)
    style: Dict[str, Any] = field(default_factory=dict)  # 全局风格配置

    @classmethod
    def from_file(cls, path: str) -> 'Soul':
        """从YAML/JSON文件加载灵魂配置"""
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"灵魂配置文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            if path.suffix in ('.yaml', '.yml'):
                import yaml
                data = yaml.safe_load(f)
            else:
                data = json.load(f)

        soul = cls()
        for fig_data in data.get('figures', []):
            fid = fig_data.get('id', '')
            if not fid:
                continue
            soul.figures[fid] = FigureSoul(
                id=fid,
                name=fig_data.get('name', ''),
                title=fig_data.get('title', ''),
                category=fig_data.get('category', ''),
                faction=fig_data.get('faction', ''),
                expertise=fig_data.get('expertise', []),
                primary_method=fig_data.get('primary_method', ''),
                thinking_model=fig_data.get('thinking_model', {}),
                catchphrase=fig_data.get('catchphrase', ''),
                bio=fig_data.get('bio', ''),
                soul=fig_data.get('soul', {}),
            )
        soul.style = data.get('style', {})
        return soul

    @classmethod
    def default(cls) -> 'Soul':
        """加载默认的108视角灵魂"""
        default_path = PROJECT_ROOT / "perspectives" / "figures.json"
        if default_path.exists():
            return cls.from_file(str(default_path))
        return cls()

    @classmethod
    def minimal(cls, figures: List[Dict]) -> 'Soul':
        """从最小配置创建灵魂（传入人物列表）"""
        soul = cls()
        for fig_data in figures:
            fid = fig_data.get('id', fig_data.get('name', ''))
            soul.figures[fid] = FigureSoul(**{k: fig_data.get(k, '' if isinstance(v, str) else [])
                                               for k, v in FigureSoul.__dataclass_fields__.items()
                                               if k in fig_data})
        return soul

    def merge(self, other: 'Soul') -> 'Soul':
        """合并两个灵魂（other覆盖self）"""
        merged = Soul()
        merged.figures = {**self.figures, **other.figures}
        merged.style = {**self.style, **other.style}
        return merged

    def subset(self, ids: List[str] = None, category: str = None,
               faction: str = None, expertise: str = None) -> 'Soul':
        """筛选子集"""
        filtered = {}
        for fid, fig in self.figures.items():
            if ids and fid not in ids:
                continue
            if category and fig.category != category:
                continue
            if faction and fig.faction != faction:
                continue
            if expertise and expertise not in fig.expertise:
                continue
            filtered[fid] = fig
        return Soul(figures=filtered, style=self.style)

    @property
    def count(self) -> int:
        return len(self.figures)

    def list_figures(self) -> List[Dict]:
        return [{"id": f.id, "name": f.name, "title": f.title,
                 "category": f.category, "primary_method": f.primary_method}
                for f in self.figures.values()]


# ============================================================
# 2. AgentAdapter — 标准化agent接口
# ============================================================

class AgentAdapter(Protocol):
    """
    Agent适配器接口 — 任何agent只需实现这3个方法

    1. think(context)    — 接收排盘数据，返回思考过程
    2. speak(opinion)    — 接收视角意见，返回发言
    3. judge(opinions)   — 接收所有意见，返回最终判断
    """

    def think(self, context: 'AnalysisContext') -> 'Thought':
        """
        思考：接收排盘数据，返回你的分析

        Args:
            context: 包含七术排盘结果、问题、命主信息

        Returns:
            Thought对象，包含你的分析结论
        """
        ...

    def speak(self, opinion: 'OpinionContext') -> str:
        """
        发言：以你的风格表达观点

        Args:
            opinion: 包含你的立场、引用数据、关键点

        Returns:
            你的发言文本
        """
        ...

    def judge(self, opinions: List['OpinionContext']) -> 'Judgment':
        """
        裁决：综合所有意见，给出最终判断

        Args:
            opinions: 所有视角的意见列表

        Returns:
            最终判断
        """
        ...


# ============================================================
# 3. 数据结构
# ============================================================

@dataclass
class AnalysisContext:
    """分析上下文 — 传给agent的全部信息"""
    birth: str
    location: str
    gender: str
    question: str
    corrected_time: Any = None    # 真太阳时校正结果
    udm: Any = None               # 统一数据模型（七术排盘结果）
    bazi: Dict = field(default_factory=dict)
    ziwei: Dict = field(default_factory=dict)
    liuyao: Dict = field(default_factory=dict)
    qimen: Dict = field(default_factory=dict)
    liuren: Dict = field(default_factory=dict)
    taiyi: Dict = field(default_factory=dict)
    astro: Dict = field(default_factory=dict)
    cross_validation: Dict = field(default_factory=dict)
    raw_results: Dict = field(default_factory=dict)


@dataclass
class Thought:
    """思考结果"""
    figure_id: str
    stance: str           # 支持/反对/中立/补充
    confidence: float     # 0-1
    reasoning: str        # 推理过程
    key_points: List[str] # 关键论点
    referenced_data: Dict = field(default_factory=dict)


@dataclass
class OpinionContext:
    """意见上下文"""
    thought: Thought
    figure: FigureSoul
    context: AnalysisContext
    other_opinions: List['OpinionContext'] = field(default_factory=list)


@dataclass
class Judgment:
    """最终裁决"""
    conclusion: str
    confidence: float
    consensus_points: List[str]
    dissent_points: List[str]
    recommendations: List[str]


# ============================================================
# 4. XuanzhaoShell — 核心壳子
# ============================================================

class XuanzhaoShell:
    """
    玄照装甲壳子 — 统一入口

    用法：
        shell = XuanzhaoShell()
        result = shell.run(birth="2005-06-09 11:50", location="呼和浩特",
                           gender="男", question="事业如何")
    """

    def __init__(self, llm_config: Dict = None):
        """
        Args:
            llm_config: LLM配置 {"api_key": "...", "base_url": "...", "model": "..."}
        """
        self._soul = None
        self._agent = None
        self._llm_config = llm_config or {}
        self._engines = {}
        self._lazy_init = True

    def _ensure_init(self):
        """延迟初始化引擎（避免import时加载全部）"""
        if not self._lazy_init:
            return

        from engine.time_engine import get_time_engine
        from engine.base import EngineOrchestrator
        from engine.bazi_engine import BaziEngine
        from engine.astro_engine import AstroEngine
        from engine.ziwei_engine import ZiWeiEngine
        from engine.liuyao_engine import LiuYaoEngine
        from engine.qimen_engine import QiMenEngine
        from engine.liuren_engine import LiuRenEngine
        from engine.taiyi_engine import TaiYiEngine

        self._te = get_time_engine()
        self._orch = EngineOrchestrator()
        self._engines = {
            'bazi': BaziEngine(),
            'astro': AstroEngine(),
            'ziwei': ZiWeiEngine(),
            'liuyao': LiuYaoEngine(),
            'qimen': QiMenEngine(),
            'liuren': LiuRenEngine(),
            'taiyi': TaiYiEngine(),
        }
        for eng in self._engines.values():
            self._orch.register(eng)

        # 配置LLM
        if self._llm_config:
            import config
            if self._llm_config.get('api_key'):
                config.LLM_API_KEY = self._llm_config['api_key']
            if self._llm_config.get('base_url'):
                config.LLM_BASE_URL = self._llm_config['base_url']
            if self._llm_config.get('model'):
                config.LLM_MODEL = self._llm_config['model']

        self._lazy_init = False

    # ---- 灵魂管理 ----

    def load_soul(self, soul: Soul) -> 'XuanzhaoShell':
        """注入灵魂配置"""
        self._soul = soul
        return self

    @property
    def soul(self) -> Soul:
        if self._soul is None:
            self._soul = Soul.default()
        return self._soul

    # ---- Agent管理 ----

    def mount(self, agent: AgentAdapter) -> 'XuanzhaoShell':
        """装载agent"""
        self._agent = agent
        return self

    # ---- 核心功能 ----

    def analyze(self, birth: str, location: str, gender: str) -> AnalysisContext:
        """
        纯排盘（不调LLM）— 返回七术排盘结果

        任何agent都可以只调这个方法拿数据，自己处理后续逻辑。
        """
        self._ensure_init()

        gender_int = 1 if gender in ("男", "male", "m", "1") else 0
        corrected = self._te.correct(birth, location)
        udm = self._orch.run_all(corrected, gender_int)

        ctx = AnalysisContext(
            birth=birth, location=location, gender=gender, question="",
            corrected_time=corrected, udm=udm,
            raw_results={'corrected': corrected, 'udm': udm},
        )

        # 填充各引擎结果
        ctx.bazi = self._extract_bazi(udm)
        ctx.ziwei = self._extract_ziwei(udm)
        ctx.liuyao = self._extract_liuyao(udm)
        ctx.qimen = self._extract_qimen(udm)
        ctx.liuren = self._extract_liuren(udm)
        ctx.taiyi = self._extract_taiyi(udm)
        ctx.astro = self._extract_astro(udm)

        return ctx

    def predict(self, birth: str, location: str, gender: str,
                question: str = "") -> Dict:
        """
        完整预测流程：排盘 + 视角推理 + 交叉验证 + 辩论

        Args:
            birth: 出生时间 "YYYY-MM-DD HH:MM"
            location: 出生地
            gender: 性别
            question: 问题（可选）

        Returns:
            完整预测结果dict
        """
        self._ensure_init()

        # 1. 排盘
        ctx = self.analyze(birth, location, gender)
        ctx.question = question

        # 2. 视角推理
        perspectives = self._run_perspectives(ctx)

        # 3. 交叉验证
        validation = self._run_validation(ctx, perspectives)

        # 4. 辩论（如果有LLM）
        debate_result = None
        if self._llm_config.get('api_key'):
            debate_result = self._run_debate(ctx, perspectives)

        return {
            "analysis": {
                "birth": birth, "location": location, "gender": gender,
                "question": question,
                "corrected_time": str(ctx.corrected_time.true_solar) if ctx.corrected_time else None,
                "bazi": ctx.bazi,
                "ziwei": ctx.ziwei,
                "liuyao": ctx.liuyao,
                "qimen": ctx.qimen,
                "liuren": ctx.liuren,
                "taiyi": ctx.taiyi,
                "astro": ctx.astro,
            },
            "perspectives": perspectives,
            "validation": validation,
            "debate": debate_result,
        }

    def run(self, birth: str, location: str, gender: str,
            question: str = "") -> Dict:
        """
        一键运行 — predict的别名，更直观
        """
        return self.predict(birth, location, gender, question)

    def paipan(self, birth: str, location: str, gender: str) -> Dict:
        """
        排盘接口 — 返回格式化的排盘结果
        """
        ctx = self.analyze(birth, location, gender)
        return {
            "bazi": ctx.bazi,
            "ziwei": ctx.ziwei,
            "liuyao": ctx.liuyao,
            "qimen": ctx.qimen,
            "liuren": ctx.liuren,
            "taiyi": ctx.taiyi,
            "astro": ctx.astro,
        }

    # ---- 内部方法 ----

    def _run_perspectives(self, ctx: AnalysisContext) -> List[Dict]:
        """运行视角推理"""
        from engine.perspective_engine import PerspectiveEngine
        pe = PerspectiveEngine()

        # 如果有自定义soul，替换默认figures
        if self._soul and self._soul.count > 0:
            # 写入临时figures文件
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8')
            json.dump({"figures": [
                {
                    "id": f.id, "name": f.name, "title": f.title,
                    "category": f.category, "faction": f.faction,
                    "expertise": f.expertise, "primary_method": f.primary_method,
                    "thinking_model": f.thinking_model, "catchphrase": f.catchphrase,
                    "bio": f.bio, "soul": f.soul,
                }
                for f in self._soul.figures.values()
            ]}, tmp, ensure_ascii=False)
            tmp.close()
            # 临时替换figures路径
            orig_path = pe._figures_path if hasattr(pe, '_figures_path') else None

        try:
            opinions = pe.generate_opinions(ctx.udm, ctx.question)
            return [
                {
                    "figure_id": op.figure_id,
                    "figure_name": op.figure_name,
                    "figure_title": op.figure_title,
                    "primary_method": op.primary_method,
                    "stance": op.stance,
                    "confidence": op.confidence,
                    "reasoning": op.reasoning,
                    "key_points": op.key_points,
                    "quotes": getattr(op, 'quotes', []),
                    "referenced_data": op.referenced_data,
                }
                for op in opinions
            ]
        except Exception as e:
            return [{"error": str(e)}]

    def _run_validation(self, ctx: AnalysisContext, perspectives: List[Dict]) -> Dict:
        """运行交叉验证"""
        from engine.cross_validator import CrossValidator
        cv = CrossValidator()
        try:
            return cv.validate(ctx.udm, perspectives)
        except Exception as e:
            return {"error": str(e)}

    def _run_debate(self, ctx: AnalysisContext, perspectives: List[Dict]) -> Dict:
        """运行辩论"""
        from engine.sequential_review_debate import SequentialReviewDebate
        from engine.llm_client import LLMClient

        llm = LLMClient(
            api_key=self._llm_config['api_key'],
            base_url=self._llm_config.get('base_url', ''),
            model=self._llm_config.get('model', ''),
        )
        debate = SequentialReviewDebate(llm)
        try:
            return debate.run(ctx.udm, perspectives, ctx.question)
        except Exception as e:
            return {"error": str(e)}

    # ---- 数据提取 ----

    def _extract_bazi(self, udm) -> Dict:
        """从UDM提取八字数据"""
        result = {}
        GAN_WX = {'甲':'木','乙':'木','丙':'火','丁':'火','戊':'土',
                   '己':'土','庚':'金','辛':'金','壬':'水','癸':'水'}
        try:
            if getattr(udm, 'bazi_year', None):
                result['year'] = {'ganzhi': udm.bazi_year.ganzhi}
        except Exception: pass
        try:
            if getattr(udm, 'bazi_month', None):
                result['month'] = {'ganzhi': udm.bazi_month.ganzhi}
        except Exception: pass
        try:
            if getattr(udm, 'bazi_day', None):
                result['day'] = {'ganzhi': udm.bazi_day.ganzhi}
        except Exception: pass
        try:
            if getattr(udm, 'bazi_hour', None):
                result['hour'] = {'ganzhi': udm.bazi_hour.ganzhi}
        except Exception: pass
        try:
            dm = getattr(udm, 'day_master', None)
            if dm:
                if isinstance(dm, str):
                    result['day_master'] = {'gan': dm, 'wuxing': GAN_WX.get(dm, '')}
                elif hasattr(dm, 'gan'):
                    result['day_master'] = {
                        'gan': dm.gan,
                        'wuxing': dm.wuxing.value if hasattr(dm, 'wuxing') and dm.wuxing else '',
                    }
        except Exception: pass
        try:
            if udm.wuxing_score:
                result['wuxing_score'] = {k.value if hasattr(k, 'value') else k: v
                                           for k, v in udm.wuxing_score.items()}
        except Exception: pass
        return result

    def _extract_ziwei(self, udm) -> Dict:
        try:
            if hasattr(udm, 'ziwei') and udm.ziwei:
                return udm.ziwei if isinstance(udm.ziwei, dict) else {}
        except Exception:
            pass
        return {}

    def _extract_liuyao(self, udm) -> Dict:
        try:
            if hasattr(udm, 'liuyao') and udm.liuyao:
                return udm.liuyao if isinstance(udm.liuyao, dict) else {}
        except Exception:
            pass
        return {}

    def _extract_qimen(self, udm) -> Dict:
        try:
            if hasattr(udm, 'qimen') and udm.qimen:
                return udm.qimen if isinstance(udm.qimen, dict) else {}
        except Exception:
            pass
        return {}

    def _extract_liuren(self, udm) -> Dict:
        try:
            if hasattr(udm, 'liuren') and udm.liuren:
                return udm.liuren if isinstance(udm.liuren, dict) else {}
        except Exception:
            pass
        return {}

    def _extract_taiyi(self, udm) -> Dict:
        try:
            if hasattr(udm, 'taiyi') and udm.taiyi:
                return udm.taiyi if isinstance(udm.taiyi, dict) else {}
        except Exception:
            pass
        return {}

    def _extract_astro(self, udm) -> Dict:
        try:
            if hasattr(udm, 'astro') and udm.astro:
                return udm.astro if isinstance(udm.astro, dict) else {}
        except Exception:
            pass
        return {}


# ============================================================
# 5. 快捷函数
# ============================================================

def quick_analyze(birth: str, location: str, gender: str,
                  question: str = "", llm_config: Dict = None) -> Dict:
    """
    一行代码搞定完整预测

    result = quick_analyze("2005-06-09 11:50", "呼和浩特", "男", "事业如何")
    """
    shell = XuanzhaoShell(llm_config=llm_config)
    return shell.run(birth, location, gender, question)


def quick_paipan(birth: str, location: str, gender: str) -> Dict:
    """
    一行代码搞定排盘

    result = quick_paipan("2005-06-09 11:50", "呼和浩特", "男")
    """
    shell = XuanzhaoShell()
    return shell.paipan(birth, location, gender)
