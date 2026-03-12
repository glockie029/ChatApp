# DevSecOps 学习指南

这份指南按“先跑通，再打坏，再修复”的顺序设计。

## 阶段 1：建立安全基线

目标：

- 能正常启动 API
- 知道默认模式下哪些接口可见
- 知道训练模式如何开启

建议动作：

1. 复制 `.env.example` 为 `.env`
2. 启动服务并访问 `/`、`/health`、`/messages/`
3. 用 `POST /messages/` 发一条包含 `secret` 或 `token` 的消息
4. 观察 `risk_tags` 和 `/moderation/summary`

你应该学到：

- 配置开关如何影响攻击面
- 健康检查为什么重要
- 输入校验和简单业务规则如何形成“最小防线”

## 阶段 2：理解训练接口的风险

目标：

- 明确哪些接口是故意保留的漏洞点
- 学会把漏洞能力与默认运行态隔离

建议动作：

1. 使用 `ENABLE_UNSAFE_ROUTES=true` 启动服务
2. 访问 `/unsafe_messages/` 和 `/unsafe_search/`
3. 对比安全搜索和不安全搜索的实现差异

重点代码：

- [chat.py#L70](/Users/mac/Documents/GitHub/ChatApp/api/endpoints/chat.py#L70)
- [chat.py#L134](/Users/mac/Documents/GitHub/ChatApp/api/endpoints/chat.py#L134)

你应该学到：

- 为什么“带洞功能”必须显式开关控制
- 为什么练习项目也要区分默认安全态和训练态

## 阶段 3：演练 SAST 门禁

目标：

- 让 Bandit 从绿色变成告警
- 理解为什么流水线会阻断

建议动作：

1. 运行 `bandit -r . -x ./venv,./test_main.py -f json -o bandit_report.json`
2. 观察当前默认结果
3. 删除 [chat.py#L140](/Users/mac/Documents/GitHub/ChatApp/api/endpoints/chat.py#L140) 和 [chat.py#L153](/Users/mac/Documents/GitHub/ChatApp/api/endpoints/chat.py#L153) 上的 `# nosec B608`
4. 再跑一次 Bandit
5. 再运行 `python3 security_gate.py bandit`

你应该学到：

- 工具发现漏洞和流水线阻断是两层逻辑
- `# nosec` 的使用边界
- 为什么测试文件要从 SAST 范围中排除

## 阶段 4：演练 SCA 门禁

目标：

- 理解依赖版本也会导致流水线失败
- 学会用最小变更修复供应链告警

建议动作：

1. 先运行 `safety check -r requirements.txt --json`
2. 如果想故意制造问题，把 `requests` 降到明显过旧版本
3. 再运行 `python3 security_gate.py safety`
4. 把依赖升回安全版本，重新验证

你应该学到：

- SCA 检查的是依赖，而不是业务代码
- 依赖修复通常是最快的安全收益来源

## 阶段 5：进入容器与 CI/CD

目标：

- 让项目具备容器化交付能力
- 理解流水线里哪些步骤是“质量门”

建议动作：

1. 阅读 `Dockerfile`
2. 运行 `docker compose up --build`
3. 阅读 `Jenkinsfile`，按顺序理解：
   - 依赖安装
   - 单元测试
   - SAST
   - SCA
   - 启动与验证

你应该学到：

- 为什么容器镜像也属于交付物的一部分
- 为什么“测试通过”和“可安全发布”不是一回事

## 推荐练习路线

第 1 次练习：

- 只跑安全基线
- 不打开训练接口
- 理解路由、配置、测试、门禁的关系

第 2 次练习：

- 打开训练接口
- 手动触发不安全写入和搜索
- 对照源码理解风险点

第 3 次练习：

- 移除 `# nosec`
- 观察 Bandit 和 `security_gate.py` 的输出
- 恢复标记，再看流水线回到什么状态

第 4 次练习：

- 故意降级依赖
- 观察 Safety 报告
- 升级依赖并重新验证
