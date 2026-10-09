# 离线测试报告

最终 pytest：52 项，失败/错误 0。所有模型请求为 mock，真实 API 调用数 0。

命令：`.venv/bin/python -m pytest -q --junitxml=docs/test_results.xml`。原始 JUnit 记录保留在同目录。

未执行：真实 DeepSeek 请求、真实 MATH 推理、性能优劣和统计非劣实验。未将这些项目报告为通过。

| 测试 | 状态 |
|---|---|
| `tests.test_stage1.test_taxonomy[Prealgebra-prealgebra]` | PASS |
| `tests.test_stage1.test_taxonomy[Algebra-algebra]` | PASS |
| `tests.test_stage1.test_taxonomy[Intermediate Algebra-intermediate_algebra]` | PASS |
| `tests.test_stage1.test_taxonomy[Geometry-geometry]` | PASS |
| `tests.test_stage1.test_taxonomy[Number Theory-number_theory]` | PASS |
| `tests.test_stage1.test_taxonomy[Counting & Probability-counting_probability]` | PASS |
| `tests.test_stage1.test_taxonomy[Precalculus-precalculus]` | PASS |
| `tests.test_stage1.test_base_and_no_network` | PASS |
| `tests.test_stage1.test_problem_rejects_gold` | PASS |
| `tests.test_stage2.test_schema_roundtrip_and_unknown_status` | PASS |
| `tests.test_stage2.test_multi_trace_distillation` | PASS |
| `tests.test_stage2.test_unrelated_and_too_few` | PASS |
| `tests.test_stage2.test_no_generalization_response` | PASS |
| `tests.test_stage2.test_duplicate_merge_needs_revalidation` | PASS |
| `tests.test_stage2.test_contaminated_trace_excluded` | PASS |
| `tests.test_stage2.test_oversize_not_truncated` | PASS |
| `tests.test_stage3_4.test_admission_insufficient_and_harm` | PASS |
| `tests.test_stage3_4.test_build_cost_cannot_be_free` | PASS |
| `tests.test_stage3_4.test_old_unproven_bank_rejected` | PASS |
| `tests.test_stage3_4.test_overlap_id_text_and_nearduplicate` | PASS |
| `tests.test_stage3_4.test_paired_validator_actual_flow` | PASS |
| `tests.test_stage3_4.test_subject_filter_and_unknown` | PASS |
| `tests.test_stage3_4.test_router_selects_cheap_reliable_not_similarity` | PASS |
| `tests.test_stage3_4.test_default_router_rejects_small_sample_uncertainty` | PASS |
| `tests.test_stage3_4.test_freeze_and_lifecycle` | PASS |
| `tests.test_stage5.test_gold_canary_through_router_retry_bank_and_evaluator` | PASS |
| `tests.test_stage5.test_wrong_but_formatted_answer_never_triggers_gold_retry` | PASS |
| `tests.test_stage5.test_usage_missing_counted_and_cached` | PASS |
| `tests.test_stage5.test_real_usage_preferred` | PASS |
| `tests.test_stage5.test_checkpoint_binding_and_idempotency` | PASS |
| `tests.test_stage5.test_interrupted_resume_does_not_repeat_finished_tasks` | PASS |
| `tests.test_stage5.test_all_modes_offline[base_onepass]` | PASS |
| `tests.test_stage5.test_all_modes_offline[flowevo_goldfree]` | PASS |
| `tests.test_stage5.test_all_modes_offline[flowevo_context_goldfree]` | PASS |
| `tests.test_stage5.test_all_modes_offline[bot_template]` | PASS |
| `tests.test_stage5.test_all_modes_offline[subject_strategy]` | PASS |
| `tests.test_stage5.test_all_modes_offline[subject_strategy_admission]` | PASS |
| `tests.test_stage5.test_all_modes_offline[subject_strategy_costaware]` | PASS |
| `tests.test_stage5.test_answer_extraction_nested_fraction_and_decimal` | PASS |
| `tests.test_stage5.test_verified_execution_has_narrow_scope` | PASS |
| `tests.test_stage5.test_budget_fails_before_transport` | PASS |
| `tests.test_stage6.test_cli_offline_end_to_end` | PASS |
| `tests.test_stage6.test_dry_run_ignores_paid_config_and_key` | PASS |
| `tests.test_stage6.test_public_prompt_budget_and_fair_format` | PASS |
| `tests.test_stage6.test_truncated_call_cannot_be_reused_as_success` | PASS |
| `tests.test_stage6.test_data_split_reproducible_and_not_math500` | PASS |
| `tests.test_stage6.test_stage0_audit_and_missing_repo` | PASS |
| `tests.test_stage6.test_all_seven_schema_examples` | PASS |
| `tests.test_stage6.test_native_humaneval_mbpp_preserved` | PASS |
| `tests.test_stage6.test_feedback_exposure_detector` | PASS |
| `tests.test_stage6.test_near_duplicate_different_subjects_stay_together` | PASS |
| `tests.test_stage6.test_build_bank_resume_is_content_stable` | PASS |

独立 wheel 安装检查已通过：从 `.wheelcheck` 的 site-packages、在 `/tmp` 目录以 `python -I` 执行 3 道 dry-run 题，真实 API 调用为0；许可证随 wheel 打包。见 `WHEEL_INSTALL_CHECK.json`。
