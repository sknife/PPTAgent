# PPTAgent

JSON 进，`.pptx` 出。单条命令生成 25-30 张风格一致的演示文稿。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置 API Key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

## 运行

### 方式一：JSON 文件输入

```bash
python main.py input.json output.pptx --mode beauty
```

### 方式二：JSON 字符串直接输入

```bash
python main.py '{"topic":"Python 入门","brief":"帮零基础的人理解变量、循环、函数","audience":"编程零基础"}' out.pptx
```

### 方式三：stdin 管道

```bash
echo '{"topic":"如何挑选咖啡豆","brief":"从烘焙度讲起","audience":"咖啡新手"}' | python main.py result.pptx
```

## 输入格式

```json
{
  "topic": "演示文稿主题",
  "brief": "内容简介（≤500 字）",
  "audience": "目标受众"
}
```

## 生成模式

| 模式 | 参数 | 模型 | 优先级 |
|------|------|------|--------|
| 最大美观度 | `--mode beauty`（默认） | `claude-sonnet-5` | 内容质量优先 |
| 均衡版 | `--mode tradeoff` | `claude-haiku-4-5` | 速度/成本优先 |

## 输出样例

```
[PPTAgent] topic='Python 入门 30 分钟'  mode=beauty
[PPTAgent] Done!  slides=28  tokens=1842+6231  cost=$0.0664  duration=47.2s  output=output.pptx
```

## 项目结构

```
prompt.py      # Step 1：Prompt 模板 + Anthropic SDK 流式调用
parser.py      # Step 2：JSON 提取、Pydantic 校验、硬兜底
renderer.py    # Step 3：python-pptx 绘制（7 种布局）
main.py        # Step 4：CLI 入口，整合全流程
requirements.txt
DESIGN.md      # 架构决策日志
```

## 5 个公开开发集输入示例

可直接复制使用：

```bash
# 1. Python 入门
python main.py '{"topic":"Python 入门 30 分钟","brief":"帮零基础的人理解什么是变量、循环、函数、列表、字典，并能照着写出几行能跑的代码","audience":"编程零基础"}' demos/01_python_beauty.pptx

# 2. 年度复盘
python main.py '{"topic":"2025 我的年度复盘","brief":"这一年我做的几件主要的事、踩过的几个坑、明年想试的方向","audience":"朋友圈分享"}' demos/02_review_beauty.pptx

# 3. 咖啡豆选购
python main.py '{"topic":"如何挑选一款适合自己的咖啡豆","brief":"从烘焙度、产地、处理法、风味描述讲起，给一个挑豆决策框架","audience":"咖啡新手"}' demos/03_coffee_beauty.pptx

# 4. Rust 重写提案
python main.py '{"topic":"给老板讲清楚为什么我们应该用 Rust 重写订单系统","brief":"现在用 Python 写的订单系统在大促时频繁超时，影响下单。希望说服一个非技术背景的 CEO 同意立项","audience":"非技术 CEO"}' demos/04_rust_beauty.pptx

# 5. 京都两日游
python main.py '{"topic":"周末两天玩遍京都","brief":"周六上午到周日晚上，预算人均 3000，希望涵盖经典景点和一两个小众体验","audience":"第一次去日本的游客"}' demos/05_kyoto_beauty.pptx

# 6. AI书单号
python main.py '{"topic":"AI书单号","brief":"现在使用AI构建书单号，幼儿绘本方向，跑通商业模式","audience":"宝妈"}' demos/06_ai_book.pptx
```

Tradeoff 版将 `beauty` 替换为 `tradeoff` 即可。
