# 申请状态与恢复

每个申请一份 application-state.json，放在配置中对应的申请目录（如 applications/<公司或申请目录>/）。已有同目的账本则补齐字段，不建冲突副本。候选阶段可放公司目录。

最小结构示意，不能当作已完成记录：

~~~json
{
  "schema_version": 1,
  "company": "",
  "stage": "recommend_jobs",
  "updated_at": "",
  "scope": {"campaign": "", "entry_urls": [], "constraints": []},
  "job": null,
  "baseline": null,
  "target_dir": null,
  "decisions": [],
  "artifacts": [],
  "review": {"version": null, "ledger_path": null, "pending_ids": []},
  "authorization": {"edit_evidence": null, "fill_evidence": null, "upload_evidence": null},
  "application": {"url": null, "status": "not_started", "persistence": "unknown", "attachment_check": "not_checked"},
  "blockers": [],
  "next_action": "推荐岗位后等待 D1"
}
~~~

## 记录契约

- stage：recommend_jobs、await_job_choice、recommend_base、await_base_choice、review_changes、await_change_decision、build_resume、resume_ready、fill_application、ready_for_user_submit、submitted_observed。只记录实际阶段。
- scope.constraints 含 value、scope（本次/公司批次/已确认全局）、source、confirmed_at；用户撤销则标旧项失效。
- job 含原名、职位 ID、批次、详情 URL、JD 快照及抓取时间；baseline 含源码/PDF 及确认依据。来源快照不存 Cookie 或访问令牌。
- decisions 记录 D1/D2/D3、选择/条目 ID、用户原意简摘、日期、消息/会话引用，关联岗位 ID、基底指纹或审阅版本。跨聊天复用须确保身份、岗位、范围一致且确有用户明确决定。
- authorization 记录当前目标路径、网站岗位、上传文件的授权证据。“选它”仅指当时所问选择，不能扩展为所有后续外部动作。
- artifacts 每项含 role、path（绝对路径）、sha256，可加 verified_at。role 例如 jd、baseline_source、review_html、resume_source、final_pdf。只记真实存在文件。
- review 指向唯一当前版本和账本。多个 HTML 冲突先定位用户编辑，不能只看 mtime 覆盖。
- application 记录字段完成度、附件核验依据、观察时间、保存状态；值保留在原资料/页面，不在状态复写完整隐私信息。

## 变化后的重新核对

| 变化 | 重查范围 |
|---|---|
| 公司、批次、岗位 | 申请规则、匹配、基底、改写、网站授权范围 |
| 同岗 JD 实质更新 | 受影响的匹配/改写，不机械废弃全部已确认内容 |
| 基底源码 | 依赖条目的原文对照、审阅差异与成品 |
| HTML 内容/顺序 | 相关确认项、源码同步和 PDF |
| 正式源码/PDF | 编译、内容、排版和网页附件 |
| 网页刷新/崩溃 | 当前字段、附件、保存状态 |

恢复先运行 resume_tools.py verify 或等价指纹检查。读回变化并更新待审项，不能自动覆盖用户变更。旧状态没有指纹时建立初始观察，不声称旧版已验证。

不同聊天不并发修改同一状态。写前读回、合并较新的用户决定，临时文件写入后替换；无法判断的同字段冲突让用户选择。回退阶段保留历史，不删除用户材料。
