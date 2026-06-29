"""
玄照 v2.0 - Playwright自动化测试

测试Web界面和API接口的基本功能。
"""
import pytest
from playwright.sync_api import Page, expect


BASE_URL = "http://localhost:8080"


class TestHomepage:
    """首页测试"""

    def test_homepage_loads(self, page: Page):
        """首页能正常加载"""
        page.goto(BASE_URL)
        expect(page).to_have_title(lambda t: "玄照" in t)

    def test_homepage_has_form(self, page: Page):
        """首页包含排盘表单"""
        page.goto(BASE_URL)
        # 检查表单元素存在
        expect(page.locator("input[name='birth']")).to_be_visible()
        expect(page.locator("input[name='location']")).to_be_visible()

    def test_homepage_has_perspectives(self, page: Page):
        """首页显示108视角"""
        page.goto(BASE_URL)
        # 检查视角轮播存在
        expect(page.locator(".perspective-carousel, .perspectives, #perspectives")).to_be_visible()


class TestAPI:
    """API接口测试"""

    def test_api_chart(self, page: Page):
        """排盘API正常工作"""
        response = page.request.get(f"{BASE_URL}/api/chart?birth=1990-01-15 08:30&location=北京&gender=1")
        expect(response).to_be_ok()
        data = response.json()
        assert "bazi" in data or "error" not in data

    def test_api_perspectives(self, page: Page):
        """视角API正常工作"""
        response = page.request.get(f"{BASE_URL}/api/perspectives")
        expect(response).to_be_ok()
        data = response.json()
        assert isinstance(data, (list, dict))

    def test_api_cross_validate(self, page: Page):
        """交叉验证API正常工作"""
        response = page.request.get(f"{BASE_URL}/api/cross-validate?birth=1990-01-15 08:30&location=北京&gender=1")
        expect(response).to_be_ok()

    def test_api_debate(self, page: Page):
        """辩论API正常工作"""
        response = page.request.get(f"{BASE_URL}/api/debate?birth=1990-01-15 08:30&location=北京&gender=1&question=事业如何")
        expect(response).to_be_ok()


class TestPerspectivesPage:
    """视角页面测试"""

    def test_perspectives_page_loads(self, page: Page):
        """视角页面能正常加载"""
        page.goto(f"{BASE_URL}/perspectives")
        expect(page).to_have_title(lambda t: "视角" in t or "玄照" in t)

    def test_perspectives_has_figures(self, page: Page):
        """视角页面显示人物列表"""
        page.goto(f"{BASE_URL}/perspectives")
        # 检查至少有一个视角人物
        figures = page.locator(".figure-card, .perspective-item, [data-figure]")
        expect(figures.first).to_be_visible()


class TestDebatePage:
    """辩论页面测试"""

    def test_debate_page_loads(self, page: Page):
        """辩论页面能正常加载"""
        page.goto(f"{BASE_URL}/debate")
        expect(page).to_have_title(lambda t: "辩论" in t or "玄照" in t)

    def test_debate_has_form(self, page: Page):
        """辩论页面包含表单"""
        page.goto(f"{BASE_URL}/debate")
        # 检查表单元素存在
        expect(page.locator("input[name='birth'], #birth")).to_be_visible()


class TestKnowledgeBase:
    """知识库测试"""

    def test_knowledge_search(self):
        """知识库检索功能正常"""
        import sys
        sys.path.insert(0, ".")
        from knowledge.index import search_by_query, build_index

        # 构建索引
        idx = build_index(force=True)
        assert idx["stats"]["total_docs"] > 0

        # 测试搜索
        results = search_by_query("甲木日主")
        assert len(results) > 0

    def test_knowledge_by_method(self):
        """按术法搜索正常"""
        import sys
        sys.path.insert(0, ".")
        from knowledge.search import KnowledgeSearch

        ks = KnowledgeSearch()
        results = ks.search_by_method("八字")
        assert len(results) > 0

    def test_knowledge_by_theme(self):
        """按主题搜索正常"""
        import sys
        sys.path.insert(0, ".")
        from knowledge.search import KnowledgeSearch

        ks = KnowledgeSearch()
        results = ks.search_by_theme("事业")
        assert len(results) > 0


class TestEngines:
    """引擎单元测试（通过TimeEngine预校时）"""

    def _corrected(self):
        from engine.time_engine import TimeEngine
        return TimeEngine().correct("1990-01-15 08:30", "北京")

    def test_bazi_engine(self):
        """八字引擎正常工作"""
        from engine.bazi_engine import BaziEngine
        eng = BaziEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_ziwei_engine(self):
        """紫微引擎正常工作"""
        from engine.ziwei_engine import ZiWeiEngine
        eng = ZiWeiEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_liuyao_engine(self):
        """六爻引擎正常工作"""
        from engine.liuyao_engine import LiuYaoEngine
        eng = LiuYaoEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_qimen_engine(self):
        """奇门引擎正常工作"""
        from engine.qimen_engine import QiMenEngine
        eng = QiMenEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_liuren_engine(self):
        """大六壬引擎正常工作"""
        from engine.liuren_engine import LiuRenEngine
        eng = LiuRenEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_taiyi_engine(self):
        """太乙引擎正常工作"""
        from engine.taiyi_engine import TaiYiEngine
        eng = TaiYiEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None

    def test_astro_engine(self):
        """占星引擎正常工作"""
        from engine.astro_engine import AstroEngine
        eng = AstroEngine()
        result = eng.analyze(self._corrected(), 1)
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
