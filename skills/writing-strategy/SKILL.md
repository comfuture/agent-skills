---
name: writing-strategy
description: Choose writing and narrative strategies from a curated bilingual strategy set, then produce a Markdown article outline or table of contents. Use when the user asks how to structure a draft, essay, article, post, proposal, column, case study, story, marketing copy, or other writing based on a topic, material, purpose, audience/readers, tone, or language. The skill selects a best-fit strategy, avoids overusing generic problem-solution frames, keeps Korean and English strategy names as canonical references, and displays strategy names in the user's output language unless bilingual names are explicitly requested.
license: CC-BY-NC-SA-4.0
---

# Writing Strategy

## Core Workflow

Use this skill to recommend how to structure a piece of writing, not to draft the full article unless the user asks for the full draft.

1. Infer the user's input language. Output strategy names, overview, rationale, and outline in that language. Use the exact Korean strategy name for Korean input and the exact English strategy name for English input. Keep both names in references for lookup stability, but do not show bilingual paired names unless the user explicitly asks.
2. Extract the writing situation: topic, source material, purpose, intended reader, desired tone, length, and any constraints. If key details are missing, make light assumptions and proceed; ask only when the strategy choice would be genuinely risky.
3. Load [references/index.md](references/index.md) for selection cues. Shortlist 4-6 plausible strategies across different narrative modes.
4. Apply the generic-frame guard before choosing: do not default to `Problem → Solution`, `Status → Problem → Solution`, `Problem → Analysis → Solution → Outcome`, `Introduction → Body → Conclusion`, `Goal → Obstacle → Solution`, or `Need → Solution → Satisfaction` unless the user's material clearly demands a direct fix, status report, diagnostic proposal, or standard essay.
5. Choose one best strategy and 2-3 alternatives. Read only the detailed reference files for the chosen strategy and the alternatives.
6. Produce a Markdown response with the recommended strategy, a short fit rationale, and a complete article outline or table of contents adapted to the user's topic. Then show the alternative strategies in the same output language and invite the user to choose one if they want the outline reframed.

## Output Shape

For Korean input, use this order:

```markdown
## 추천 글쓰기 전략
**정확한 한국어 전략명**

선택 이유: ...

## 글의 전체 구조
1. ...
2. ...

## 대안 전략
- **정확한 한국어 전략명**: ...
- **정확한 한국어 전략명**: ...
```

For English input, use this order:

```markdown
## Recommended Writing Strategy
**Exact English Strategy Name**

Why it fits: ...

## Article Outline
1. ...
2. ...

## Alternative Strategies
- **Exact English Strategy Name**: ...
- **Exact English Strategy Name**: ...
```

Keep the outline specific to the user's material. Do not return a generic template with placeholder-only headings. If the user provides several materials, weave them into the section headings or section notes.

## Strategy Names

The exact strategy names are:

- [핵심 3가지 포인트 강조 / 3 Key Points](references/3_key_points.md)
- [5 WHY 분석 / 5 Whys Analysis](references/5_whys_analysis.md)
- [유사 사례 → 비교 분석 → 시사점 / Analogy → Comparison → Takeaway](references/analogy_comparison_takeaway.md)
- [주목 → 관심 → 욕구 → 행동 / Attention → Interest → Desire → Action (AIDA)](references/attention_interest_desire_action_aida.md)
- [변화 전 → 변화 후 구조 / Before → After](references/before_after.md)
- [변화 전 → 변화 후 → 다음 과제 / Before → After → Next Challenge](references/before_after_next_challenge.md)
- [여정 기반 구조 / Before → Journey → After](references/before_journey_after.md)
- [사례 → 분석 → 시사점 / Case → Analysis → Implication](references/case_analysis_implication.md)
- [원인 → 결과 구조 / Cause → Effect](references/cause_effect.md)
- [도전 → 전략 → 성과 / Challenge → Strategy → Result](references/challenge_strategy_result.md)
- [인물 중심 이야기 / Character-Driven Story](references/character_driven_story.md)
- [비교 → 선택 구조 / Compare → Decide](references/compare_decide.md)
- [경쟁사 비교 → 자사 강점 / Competitor Comparison → Own Strength](references/competitor_comparison_own_strength.md)
- [컨셉 → 표현 사례 → 적용 팁 / Concept → Expression → Tips](references/concept_expression_tips.md)
- [컨셉 소개 → 기능 설명 → 사용 예시 / Concept → Features → Use Case](references/concept_features_use_case.md)
- [논란 → 다각도 분석 → 제안 / Controversy → Analysis → Proposal](references/controversy_analysis_proposal.md)
- [고객 이야기 중심 / Customer-Centric Story](references/customer_centric_story.md)
- [불만 → 대안 → 변화 / Dissatisfaction → Alternative → Transformation](references/dissatisfaction_alternative_transformation.md)
- [반전 구조 (예상 깨기 → 새로운 관점) / Expectation Break → New Perspective](references/expectation_break_new_perspective.md)
- [경험 → 교훈 → 적용 / Experience → Lesson → Application](references/experience_lesson_application.md)
- [사실 → 인사이트 → 실행 구조 / Fact → Insight → Action](references/fact_insight_action.md)
- [사실 → 해석 → 논평 / Fact → Interpretation → Commentary](references/fact_interpretation_commentary.md)
- [실패 → 극복 → 성공 사례 / Failure → Overcome → Success](references/failure_overcome_success.md)
- [특징 → 장점 → 혜택 구조 / Feature → Advantage → Benefit (FAB)](references/feature_advantage_benefit_fab.md)
- [목표 → 장애물 → 극복 방안 / Goal → Obstacle → Solution](references/goal_obstacle_solution.md)
- [한 줄 메시지 → 근거 나열 / Headline → Supporting Points](references/headline_supporting_points.md)
- [주목 → 메시지 → 행동 요청 / Hook → Message → Call-to-Action](references/hook_message_call_to_action.md)
- [서론 → 본론 → 결론 / Introduction → Body → Conclusion](references/introduction_body_conclusion.md)
- [이슈 → 쟁점 → 결론 / Issue → Debate → Conclusion](references/issue_debate_conclusion.md)
- [키워드 나열 → 의미 부여 / Keywords → Meaning](references/keywords_meaning.md)
- [시장 분석 → 기회 포착 → 실행 계획 / Market → Opportunity → Execution](references/market_opportunity_execution.md)
- [오해 → 진실 → 확신 / Misunderstanding → Truth → Conviction](references/misunderstanding_truth_conviction.md)
- [니즈 → 솔루션 → 만족 구조 / Need → Solution → Satisfaction](references/need_solution_satisfaction.md)
- [관찰 → 패턴 → 인사이트 / Observation → Pattern → Insight](references/observation_pattern_insight.md)
- [고통 → 제안 → 기대 효과 / Pain → Claim → Gain](references/pain_claim_gain.md)
- [과거 → 현재 → 미래 구조 / Past → Present → Future](references/past_present_future.md)
- [현상 → 인사이트 → 대안 제시 / Phenomenon → Insight → Proposal](references/phenomenon_insight_proposal.md)
- [문제 → 분석 → 해결책 → 기대 효과 / Problem → Analysis → Solution → Outcome](references/problem_analysis_solution_outcome.md)
- [문제 → 해결 구조 / Problem → Solution](references/problem_solution.md)
- [의문 → 실험 → 결론 / Question → Experiment → Conclusion](references/question_experiment_conclusion.md)
- [질문 → 탐색 → 발견 / Question → Exploration → Discovery](references/question_exploration_discovery.md)
- [반응 유도형 (질문 → 상상 → 정리) / Question → Imagination → Resolution](references/question_imagination_resolution.md)
- [인용 → 해석 → 적용 / Quote → Interpretation → Application](references/quote_interpretation_application.md)
- [현황 → 문제점 → 해결책 / Status → Problem → Solution](references/status_problem_solution.md)
- [SWOT → 전략 → 실행 / SWOT → Strategy → Execution](references/swot_strategy_execution.md)
- [긴장 → 이완 → 결론 / Tension → Relief → Resolution](references/tension_relief_resolution.md)
- [시간 흐름 기반 전개 / Time-Based Narrative](references/time_based_narrative.md)
- [트렌드 → 사례 → 실행 / Trend → Example → Action (TEA)](references/trend_example_action_tea.md)
- [트렌드 → 기회 → 대응 전략 / Trend → Opportunity → Strategy](references/trend_opportunity_strategy.md)
- [관점 제시 → 근거 제시 → 설득 / Viewpoint → Evidence → Persuasion](references/viewpoint_evidence_persuasion.md)
- [비전 → 계획 → 실행 / Vision → Plan → Action](references/vision_plan_action.md)
- [현장 목소리 → 인사이트 / Voice from Field → Insight](references/voice_from_field_insight.md)
- [고객의 말 → 공감 → 제안 / Voice of Customer → Empathy → Proposal](references/voice_of_customer_empathy_proposal.md)
- [왜 → 무엇 → 어떻게 / Why → What → How](references/why_what_how.md)
