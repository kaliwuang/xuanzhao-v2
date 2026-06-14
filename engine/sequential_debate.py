#!/usr/bin/env python3
"""
玄照 v2.0 - 串行审判辩论引擎 v2

"传纸"机制：
1. 发言人写下原文（一张纸）
2. 纸传给审判者1号，他在原文下面写修正意见
3. 再传给2号，2号看到原文+1号意见，写自己的新意见
4. 逐个传递，后面的能看到前面所有人的意见
5. 全部审完后，整张纸传回发言人
6. 发言人根据意见修正，再递交给全员审核
7. 循环直到全员90%+通过且修正点极少
8. 第二位发言时能看到第一位的完整审核档案

通过 SSE 实时推送。
"""
import json
import logging
import time
from typing import List, Dict, Optional, Generator
from dataclasses import dataclass, field
from .perspective_engine import PerspectiveOpinion, FIGURES
from .llm_client import LLMClient

logger = logging.getLogger(__name__)


@dataclass
class JudgeFeedback:
    """单个审判者的意见"""
    judge_name: str
    judge_method: str
    passed: bool  # 是否通过
    feedback: str  # 修正意见（新观点）
    score: int  # 准确分数 0-100


@dataclass
class Paper:
    """一张辩论纸：原文 + 所有审判意见"""
    speaker_name: str
    speaker_method: str
    original_text: str  # 发言人原文（不可修改）
    revision: str  # 发言人修正后的版本
    attempt: int  # 第几轮
    feedbacks: List[JudgeFeedback] = field(default_factory=list)
    pass_rate: float = 0.0
    avg_score: float = 0.0
    final_passed: bool = False


@dataclass
class SpeakerArchive:
    """一个发言人的完整审核档案"""
    speaker_name: str
    speaker_method: str
    papers: List[Paper] = field(default_factory=list)  # 每轮的纸
    final_statement: str = ""  # 最终通过的发言
    total_attempts: int = 0


class SequentialDebateEngine:
    """串行审判辩论引擎 v2 — 传纸机制"""

    def __init__(self):
        self.llm = LLMClient()
        self.archives: List[SpeakerArchive] = []  # 已完成的档案
        self.all_final_statements: List[str] = []  # 所有最终发言

    def run_debate(self, opinions: List[PerspectiveOpinion],
                   question: str) -> Generator[dict, None, None]:
        """运行辩论，yield SSE事件"""
        self.archives = []
        self.all_final_statements = []
        total = len(opinions)

        yield self._sse("start", {
            "total_speakers": total,
            "question": question,
        })

        for idx, speaker in enumerate(opinions):
            archive = SpeakerArchive(
                speaker_name=speaker.figure_name,
                speaker_method=speaker.primary_method,
            )

            yield self._sse("speaker_start", {
                "index": idx + 1,
                "total": total,
                "speaker": speaker.figure_name,
                "method": speaker.primary_method,
            })

            # 获取审判者列表
            judges = [o for o in opinions if o.figure_id != speaker.figure_id]

            # 发言循环
            max_attempts = 5
            current_text = ""
            paper = None

            for attempt in range(1, max_attempts + 1):
                # 第一步：发言人写/修正原文
                if attempt == 1:
                    current_text = self._speaker_write(
                        speaker, question, self.all_final_statements
                    )
                else:
                    # 根据上一轮的纸修正
                    current_text = self._speaker_revise(
                        speaker, question, paper, self.all_final_statements
                    )

                yield self._sse("statement", {
                    "speaker": speaker.figure_name,
                    "attempt": attempt,
                    "text": current_text,
                })

                # 第二步：传纸——逐人审核
                paper = Paper(
                    speaker_name=speaker.figure_name,
                    speaker_method=speaker.primary_method,
                    original_text=current_text,
                    revision=current_text,
                    attempt=attempt,
                )

                for j_idx, judge in enumerate(judges):
                    # 审判者看到：原文 + 之前所有人的意见
                    fb = self._judge_write_feedback(
                        judge, speaker, paper, question,
                        self.all_final_statements
                    )
                    paper.feedbacks.append(fb)

                    # 计算当前通过率和平均分
                    passed_count = sum(1 for f in paper.feedbacks if f.passed)
                    paper.pass_rate = passed_count / len(paper.feedbacks)
                    paper.avg_score = sum(f.score for f in paper.feedbacks) / len(paper.feedbacks)

                    # 每5人或最后1人推一次进度
                    if (j_idx + 1) % 5 == 0 or j_idx == len(judges) - 1:
                        yield self._sse("judgment_progress", {
                            "speaker": speaker.figure_name,
                            "attempt": attempt,
                            "judge": judge.figure_name,
                            "judge_index": j_idx + 1,
                            "total_judges": len(judges),
                            "passed": fb.passed,
                            "score": fb.score,
                            "feedback": fb.feedback[:80],
                            "pass_rate": round(paper.pass_rate * 100, 1),
                            "avg_score": round(paper.avg_score, 1),
                        })

                    # 提前结束判断：剩余全过也到不了90%
                    remaining = len(judges) - j_idx - 1
                    if passed_count + remaining < len(judges) * 0.9 and j_idx > 20:
                        yield self._sse("early_stop", {
                            "speaker": speaker.figure_name,
                            "attempt": attempt,
                            "reason": f"通过率{round(paper.pass_rate*100,1)}%已无法达到90%",
                        })
                        break

                archive.papers.append(paper)

                # 判断是否通过：90%+ 且平均分90+ 且修正点极少
                non_trivial_feedbacks = [
                    f for f in paper.feedbacks
                    if not f.passed and len(f.feedback) > 5
                ]

                if paper.pass_rate >= 0.9 and paper.avg_score >= 85:
                    paper.final_passed = True
                    archive.final_statement = current_text
                    archive.total_attempts = attempt
                    self.all_final_statements.append(current_text)
                    self.archives.append(archive)

                    yield self._sse("speaker_passed", {
                        "speaker": speaker.figure_name,
                        "attempt": attempt,
                        "pass_rate": round(paper.pass_rate * 100, 1),
                        "avg_score": round(paper.avg_score, 1),
                        "text": current_text,
                    })
                    break
                else:
                    # 未通过，汇总错误传回发言人
                    errors = [
                        {"judge": f.judge_name, "feedback": f.feedback, "score": f.score}
                        for f in paper.feedbacks if not f.passed
                    ]
                    yield self._sse("speaker_rejected", {
                        "speaker": speaker.figure_name,
                        "attempt": attempt,
                        "pass_rate": round(paper.pass_rate * 100, 1),
                        "avg_score": round(paper.avg_score, 1),
                        "errors": errors[:8],
                    })
            else:
                # 强制通过
                paper.final_passed = True
                archive.final_statement = current_text
                archive.total_attempts = max_attempts
                self.all_final_statements.append(current_text)
                self.archives.append(archive)

                yield self._sse("speaker_forced", {
                    "speaker": speaker.figure_name,
                    "attempts": max_attempts,
                    "pass_rate": round(paper.pass_rate * 100, 1),
                })

        # 辩论结束
        yield self._sse("debate_end", {
            "total_speakers": len(self.archives),
            "summary": self._generate_summary(),
        })

    def _speaker_write(self, speaker: PerspectiveOpinion,
                       question: str, previous: List[str]) -> str:
        """发言人写下原文"""
        prev_context = ""
        if previous:
            prev_context = "\n\n已通过的前人发言（不得重复）：\n"
            for i, s in enumerate(previous[-10:], 1):
                prev_context += f"{i}. {s[:100]}\n"

        prompt = f"""你正在扮演{speaker.figure_name}（{speaker.primary_method}）参与一场关于"{question}"的辩论。

你的立场：{speaker.stance}
核心观点：{'；'.join(speaker.key_points[:3])}
{prev_context}

请发表你的观点。要求：
1. 必须提出新观点，不得与前人重复
2. 结合{speaker.primary_method}术法分析
3. 直接给观点，200字以内"""

        try:
            return self.llm.chat([{"role": "user", "content": prompt}],
                                 temperature=0.8, max_tokens=500).strip()
        except Exception as e:
            logger.warning(f"发言失败: {e}")
            return f"【{speaker.figure_name}】{speaker.stance}。{'；'.join(speaker.key_points[:2])}"

    def _speaker_revise(self, speaker: PerspectiveOpinion,
                        question: str, paper: 'Paper',
                        previous: List[str]) -> str:
        """发言人根据审核意见修正"""
        # 整理审核意见
        feedback_text = ""
        for fb in paper.feedbacks:
            status = "✓通过" if fb.passed else "✗需修正"
            feedback_text += f"  {fb.judge_name}（{fb.judge_method}，{fb.score}分，{status}）：{fb.feedback}\n"

        prompt = f"""你正在扮演{speaker.figure_name}参与辩论。

问题：{question}

你的上一版发言：
{paper.original_text}

以下是审核意见（你需要根据这些意见修正）：
{feedback_text}

要求：
1. 保留你的核心立场
2. 修正被指出的错误
3. 200字以内
4. 直接给出修正后的发言"""

        try:
            return self.llm.chat([{"role": "user", "content": prompt}],
                                 temperature=0.7, max_tokens=500).strip()
        except Exception as e:
            logger.warning(f"修正失败: {e}")
            return paper.original_text

    def _judge_write_feedback(self, judge: PerspectiveOpinion,
                              speaker: PerspectiveOpinion,
                              paper: Paper, question: str,
                              all_previous: List[str]) -> JudgeFeedback:
        """审判者在纸上写下自己的意见（传纸机制）"""
        # 构建"纸"的内容：原文 + 之前审判者的意见
        paper_text = f"【发言人：{speaker.figure_name}（{speaker.primary_method}）】\n{paper.revision}\n"

        if paper.feedbacks:
            paper_text += "\n--- 审核意见 ---\n"
            for fb in paper.feedbacks:
                status = "通过" if fb.passed else "需修正"
                paper_text += f"[{fb.judge_name}（{fb.judge_method}）{fb.score}分 {status}] {fb.feedback}\n"

        prompt = f"""你正在扮演{judge.figure_name}（{judge.primary_method}）审核一张辩论发言纸。

问题：{question}

以下是这张纸的内容（原文在上，之前审核者的意见在下）：
{paper_text}

你是第{len(paper.feedbacks)+1}位审核者。你的任务：
1. 从{judge.figure_name}的角度审核这段发言是否正确
2. 你的意见必须与之前审核者不同，提出新角度
3. 如果你没有新补充，就说"无新补充，同意通过"
4. 给出准确分数（0-100，90以上算通过）

严格按JSON返回：{{"passed": true/false, "score": 85, "feedback": "你的意见"}}"""

        try:
            resp = self.llm.chat([{"role": "user", "content": prompt}],
                                 temperature=0.5, max_tokens=300)
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("```")[1]
                if resp.startswith("json"):
                    resp = resp[4:]
            data = json.loads(resp)
            score = data.get("score", 80)
            return JudgeFeedback(
                judge_name=judge.figure_name,
                judge_method=judge.primary_method,
                passed=score >= 90,
                feedback=data.get("feedback", "无新补充"),
                score=score,
            )
        except Exception as e:
            logger.warning(f"审核解析失败 ({judge.figure_name}): {e}")
            return JudgeFeedback(
                judge_name=judge.figure_name,
                judge_method=judge.primary_method,
                passed=True,
                feedback="无新补充，同意通过",
                score=90,
            )

    def _generate_summary(self) -> str:
        """生成辩论总结"""
        n = len(self.archives)
        total_attempts = sum(a.total_attempts for a in self.archives)
        avg = total_attempts / n if n else 0
        methods = set()
        for a in self.archives:
            methods.add(a.speaker_method)

        summary = f"辩论完成。{n}位发言者，{len(methods)}种术法。"
        summary += f"平均每人{avg:.1f}轮通过。"
        high = sum(1 for a in self.archives if a.total_attempts == 1)
        summary += f"其中{high}人首轮即通过。"
        return summary

    def _sse(self, event: str, data: dict) -> dict:
        return {"event": event, "data": data}
