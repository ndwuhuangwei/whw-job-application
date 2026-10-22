# whw-job-application

一个显式调用的中文求职技能：核实岗位 → 选择现有简历 → 高亮审阅修改 → 生成可编辑 LaTeX 与 PDF → 核对网申字段，停在最终提交前。

适合已有简历和项目资料、希望按具体 JD 做有依据的小幅调整的人。它是一套由助手执行的流程与辅助工具，不是后台自动海投程序。

## 核心行为

- 默认推荐 3 个岗位，给出来源、匹配证据与缺口。
- 比较最相关的 10 份不同简历版本；不足时读完全部相关版本，不要求凑数。
- 优先保留好原文，通过排序、裁剪、拼接已有表述完成适配，必要时才改写。
- 选岗位、选基底与目标路径、决定修改，三处由用户做决定；已有决定不重复询问。
- 审阅稿保留原文、改动高亮、稳定条目 ID；尊重用户手改。
- 正式 PDF 必须来自同版本可编辑 LaTeX，并交付 `src/build.sh`。
- 网站填写需要相应授权，逐字段读回核验，默认不点击最终提交。

## 安装到 Codex

将整个仓库目录安装为 `whw-job-application`，不能只复制 `SKILL.md`。仓库发布后，可将仓库链接交给 Codex 的 `$skill-installer` 安装；也可手动放入个人技能目录 `~/.agents/skills/whw-job-application/`。目录中应直接包含 `SKILL.md`，不要多套一层仓库目录。

Windows 的 `~` 是自己的用户目录；如使用自定义技能位置，以当前宿主配置为准。若已有同名私人版，先备份并选择要使用的版本，避免覆盖个人配置或同时加载两份同名技能。

新技能未显示时重启 Codex，再从技能菜单选择，或输入 `$whw-job-application`。本技能保留 `allow_implicit_invocation: false`，普通求职问答不自动启动整个流程。官方说明：[Build skills](https://learn.chatgpt.com/docs/build-skills)。

## 第一次使用

1. 准备一个自己的求职工作目录，放入现有简历与可读取的项目资料。
2. 将 [配置模板](assets/project-profile.example.md) 复制到该目录，命名为 `job-application.local.md`，填写资料路径与实际工具环境。只填当前阶段需要的内容即可。
3. 在这个工作目录中开启对话，明确指出配置路径，再提供招聘链接、JD 或已有申请状态。

例如：

```text
$whw-job-application
使用当前目录的 job-application.local.md。
下面是目标 JD；请从我的现有简历中推荐基底，先不要修改正式文件。
……粘贴 JD……
```

也可以从中间继续：

```text
$whw-job-application
继续这份 application-state.json（附文件或提供其绝对路径）。
```

建议私人工作目录结构：

```text
my-job-search/
├── job-application.local.md
├── resumes/              # 自己的现有简历
├── materials/            # 项目材料或来源说明
├── private/              # 私人填表资料
└── applications/         # 申请状态、审阅稿与正式成品
```

上述目录不属于技能公开仓库。没有现有简历时，可以先分析岗位；创建首份简历需要真实个人材料与明确授权，技能不会虚构基底。

## 环境要求

| 功能 | 所需能力 | 不可用时 |
|---|---|---|
| 阅读 JD、给出建议 | 助手、用户材料；核实在线岗位需要网络读取 | 分析已提供内容，标注在线状态待核实 |
| 简历索引与指纹 | 项目选定的 Python 3.10+，仅标准库 | 使用宿主等价文件读取能力 |
| 正式 PDF | Bash、XeLaTeX，以及模板所用 TeX 包/字体 | 保留源码与诊断，不标记 PDF 已完成 |
| 网申填写 | 可用的宿主浏览器控制与本人登录 | 交付字段建议与未完成项 |
| 手机审阅 | 本地 HTML；内嵌编辑、Sites 为可选增强 | 交付可下载 HTML 与聊天反馈方式 |

Windows 可使用 Git Bash；macOS/Linux 可使用 Bash。不要使用未安装的路径或假定拥有某个 Conda 环境。依赖安装遵循使用者的工具权限与项目规则。

本仓库不捆绑第三方技能、连接器、字体或登录信息。`job-match`、`job-apply` 仅在已安装且适用时复用；`great-resume`、`make-resume` 只在用户显式调用时启用。未安装这些技能不妨碍使用核心流程。

## LaTeX 模板与构建

优先沿用用户自己的简历模板；缺少模板时，将 [assets/latex](assets/latex/) 中两个文件复制到已确认目标版本的 `src/`，用真实材料替换提示文字。模板是可编译骨架，不是可直接投递的示例履历。

在 Bash 中运行：

```bash
bash build.sh resume.tex '简历-目标公司.pdf'
```

脚本以自身目录定位文件，可从其他目录调用。第一参数为 `src/` 内主 `.tex` 文件名；省略时优先 `resume.tex`，否则只允许一个候选。第二参数是输出 PDF 文件名，默认 `resume.pdf`，输出位于 `src/` 上级。输出名不接受路径。

实际调用 XeLaTeX 两次；任何一次失败都不覆盖旧 PDF，诊断保存在 `src/.build.*`。编译不代表内容和版式通过验收，正式交付还需核对文案并逐页查看。

## 辅助脚本与测试

以下命令在仓库根目录执行；`python` 指自己选定的解释器，参数路径替换为实际值：

```bash
python -X utf8 scripts/resume_tools.py catalog --root /path/to/resumes
python -X utf8 scripts/resume_tools.py fingerprint /absolute/path/to/resume.tex
python -X utf8 scripts/resume_tools.py verify /absolute/path/to/application-state.json
python -X utf8 -m unittest discover -s tests -v
```

索引只覆盖包含 `src/*.tex` 的版本，不能代替查找 PDF/HTML 简历；时间戳以 UTC 输出，只用于发现线索。文件哈希不证明用户已确认、事实正确或排版合格。退出码：0 成功/全部未变，1 扫描有错或发现变化，2 输入错误。

测试包含标准库工具回归与真实 XeLaTeX 构建检查。编译工具缺失时对应测试会跳过；Windows 可将 `BASH_EXECUTABLE` 设置为 Git Bash 可执行文件的实际路径。人工流程案例见 [tests/resume-writing-cases.md](tests/resume-writing-cases.md)，它们不是已完成的盲测结果。

## License

[MIT License](LICENSE)
