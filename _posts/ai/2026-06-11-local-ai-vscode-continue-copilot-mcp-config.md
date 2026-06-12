---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: 本地 AI 开发环境搭建 — VS Code Continue / Copilot MCP 插件配置实践
excerpt: |
  从零配置 VS Code 的 Continue 和 Copilot MCP 插件，打通本地大模型与 AI 编码助手的完整工作流。
author: FriesI23
date: 2026-06-11 09:00:00 +0800
category: tools
tags:
  - ai
  - vscode
  - mcp
  - continue
  - copilot
---

最近一直在折腾本地 AI 编码助手的环境，从 [Ollama][ollama] 到 [LM Studio][lm-studio]，再到 VS Code 的 [Continue][continue] 和 [Copilot][github-copilot] MCP 插件，零零散散踩了不少坑。
云端方案固然方便，但隐私、成本、定制化这些需求一上来，还是得自己搭一套本地链路。

因此在这里记录一下完整的配置过程：从硬件选型、本地模型部署、MCP 服务器接入，到 Continue 和 Copilot 插件的联动使用。

> **版本说明**：本文基于 VS Code 1.124.0（内置 Copilot）和 Continue 1.3.38 编写，插件更新较快，部分界面和配置项可能随版本变化。

这篇文章分为两大部分：AI 编码助手配置和 MCP 服务器配置，两者同等重要——前者决定 AI 的能力上限，后者决定 AI 能调用哪些工具。
希望能帮到同样想在本机跑 AI 编码助手的朋友。

## 1. 为什么需要本地 AI + MCP

云端 AI 编码助手（如 [GitHub Copilot][github-copilot]、[Cursor][cursor] 等）已经非常强大了，但有几个场景我还是倾向于本地方案：

- **隐私敏感项目**：有些代码实在不愿意上传到第三方服务。
- **定制化工具链**：通过 [MCP][mcp]（Model Context Protocol）把本地命令、数据库查询、项目特定知识暴露给 AI，这是云端方案做不到的。
- **成本可控**：本地模型推理不产生 API 调用费用，对重度用户来说长期来看更划算。

## 2. 机器配置与实际模型选型

最近选模型的时候踩了不少坑，最大的教训就是：别光看"参数量"这个数字，硬件瓶颈才是决定日常体验的关键。

本地跑模型，核心瓶颈有两个：一是内存容量（决定能装多大的模型），二是[内存带宽](#glossary-bandwidth)（决定 [token](#glossary-token) 吐出来的速度）。
下面以我手头的两台机器和实际使用的模型为例，结合硬件参数和体感体验给出选型建议。

### 2.1. 桌面机：RTX 4090 + i7-14700 + 64GB

这台机器通过 LM Studio 暴露本地服务，是日常编码的主力。RTX 4090 的 24GB GDDR6X [显存](#glossary-vram)配合约 1008 GB/s 的内存带宽，在消费级显卡里属于第一梯队。

我在这台机器上主要使用的模型：

| 模型            | [架构](#glossary-architecture) | 磁盘占用 | [激活参数](#glossary-active-params) | 推理体验           |
| --------------- | ------------------------------ | -------- | ----------------------------------- | ------------------ |
| qwen3.6 27b     | 稠密                           | 17 GB    | 27B                                 | 流畅，日常主力     |
| qwen3-coder 30b | MoE                            | 19 GB    | 3.3B                                | 体感偏慢，不推荐   |
| gemma4 26b      | MoE                            | 17 GB    | 3.8B                                | 流畅，MoE 优势明显 |
| gpt-oss 20b     | MoE                            | ~12 GB   | ~3.6B                               | 备选，够用         |

这里有一个值得展开的坑：qwen3-coder 30b 虽然激活参数只有 3.3B，但体感上 token 生成速度并不理想。
原因不在于"激活参数少就快"——MoE 架构每层要选哪些"专家"参与计算，而且 30B 的总参数量意味着每次推理都要从显存读取全部专家权重，实际内存访问量远大于 3.3B 对应的理论值（一点私货：选模型时别被"激活参数"这个数字骗了，总参数对内存压力的影响更大）。

相比之下，gemma4 26b 同样是 MoE 架构（25.2B 总参 / 3.8B 激活），但磁盘占用更小（17 GB vs 19 GB），"专家选择"的开销相对更低，体感明显更流畅。

**强烈建议**在 24GB 显存的机器上，优先选 17-20 GB 量级的模型，留出 4-7 GB 给上下文和运行时开销。
超过 20 GB 的模型虽然能塞进显存，但一旦上下文变长，就容易触发 [CPU offload](#glossary-cpu-offload)，速度会断崖式下降。

### 2.2. MacBook Pro：M4 Pro + 48GB [统一内存](#glossary-unified-memory)

这台机器通过 Ollama 本地使用，适合移动办公和深度分析场景。M4 Pro 的统一内存带宽约 200 GB/s，只有 RTX 4090 的五分之一左右，但 48GB 容量是实打实的优势。

我在这台机器上实际使用的模型：

| 模型                  | 架构 | 磁盘占用 | 激活参数 | 推理体验                 |
| --------------------- | ---- | -------- | -------- | ------------------------ |
| qwen3.6 35b-mlx       | MoE  | 22 GB    | ~3B      | 可用，MLX 格式有硬件加速 |
| qwen3-coder 30b       | MoE  | 19 GB    | 3.3B     | 可用，适合代码深度分析   |
| deepseek-coder-v2 16b | MoE  | 8.9 GB   | ~2.4B    | 流畅，日常编码够用       |
| codestral 22b         | 稠密 | 13 GB    | 22B      | 流畅，代码生成质量高     |
| hermes3 8b            | 稠密 | 4.7 GB   | 8B       | 非常流畅，轻量任务       |
| qwen2.5-coder 1.5b    | 稠密 | 986 MB   | 1.5B     | 极快，补全专用           |
| nomic-embed-text      | 嵌入 | 274 MB   | -        | 向量检索，几乎无感       |

M4 Pro 的内存带宽虽然弱，但 [MLX 格式](#glossary-mlx)对 Apple Silicon 有原生优化，
qwen3.6 35b-mlx 的推理体验比同量级 [GGUF 格式](#glossary-gguf)好不少。
对于需要更强推理能力的场景（比如复杂架构设计、多文件重构），
35B 稠密模型在 MacBook 上的表现反而比 4090 上跑 27B 更有深度。

### 2.3. 关于 CPU offload 的取舍

当模型大小超过 GPU 显存时，推理框架会把部分计算任务挪到系统内存，
由 CPU 分担。这个策略的代价很大：

- **RTX 4090 + 64GB DDR5**：GPU 和系统内存之间靠 PCIe 总线通信，理论带宽约 64 GB/s，只有显存带宽的六分之一。一旦触发 offload，
  token 生成速度会从每秒几十个降到个位数。
- **M4 Pro 统一内存**：GPU 和 CPU 共享同一条内存总线，不存在"跨设备搬运数据"的问题，offload 的惩罚远小于桌面方案。

因此我的经验法则是：

- 桌面端：模型 + 上下文尽量控制在显存以内，宁可换小一点的模型也不要触发 offload。
- Mac 端：统一内存架构下 offload 惩罚较小，可以大胆用更大的模型，用容量换推理深度。

### 2.4. 跨设备工作流

结合两台机器的特点，我的实际分工是：

- **桌面端（4090）**：qwen3.6 27b 做日常编码主力，gemma4 26b 做备选。响应速度快，适合高频交互。
- **MacBook（M4 Pro）**：qwen3.6 35b-mlx 做深度分析，deepseek-coder-v2 16b 做移动办公时的日常编码。
- **轻量任务**：hermes3 8b 或 qwen2.5-coder 1.5b，两台机器都能秒回，适合快速问答和简单补全。

两者通过同一套 VS Code 配置（Continue + MCP）无缝衔接，只需切换 `apiBase` 地址。

## 3. 本地模型部署方案选型

在配置插件之前，需要先跑通本地模型服务。目前个人开发者最常用的方案是 Ollama 和 LM Studio，下面将两者的适用范围和上手难度做一个对比。

### 3.1. Ollama

[Ollama][ollama] 是目前最轻量的本地模型部署工具，支持 macOS 和 Windows 平台。安装方式很简单：

```bash
# macOS 安装
brew install ollama

# Windows 安装（winget）
winget install Ollama.Ollama

# Windows 安装（choco）
choco install ollama
```

安装后一条命令即可拉取模型并启动服务（默认 `11434` 端口）：

```bash
ollama pull qwen2.5:14b
ollama serve
```

Ollama 的模型库覆盖了主流开源模型，量化版本（如 `q4_k_m`）对显存要求也比较友好。

我从实际使用角度说几个体会：Ollama 虽然提供了 GUI，但功能比较简陋，可配置项不多。
如果想自定义模型（比如调整系统提示词或改变采样参数），得手写 `Modelfile` 然后 `ollama create` 重新生成模型，server 端也不能通过界面调参，只能命令行附加环境变量。
但这反过来也让它很适合自动化场景：CI 流水线里一条 `ollama pull` 就能拉起服务，和脚本联动也很方便，不需要额外处理 GUI 进程。

### 3.2. LM Studio

[LM Studio][lm-studio] 同样支持 macOS 和 Windows，提供了一个完整的 GUI 界面，模型下载、加载、对话都在图形界面里完成。

```bash
# macOS 安装
brew install --cask lm-studio

# Windows 安装（winget）
winget install LM-Studio.lm-studio

# Windows 安装（choco）
choco install lm-studio
```

和 Ollama 相反，LM Studio 的参数调优可以在界面里通过滑块完成，不需要手写配置文件。如果想对比不同模型的效果，直接在 GUI 里切换就行。

但我实际使用中也有几个感受：LM Studio 的 GUI 虽然方便，但也带来了额外开销，资源占用比 Ollama 稍重。
更关键的是，把它集成到 CI 或自动化脚本里不太容易——比如我想通过脚本控制模型加载、调整参数、再启动服务，LM Studio 没有像 Ollama 那样干净的命令行接口，和 shell 脚本联动的成本比较高。

### 3.3. 两者的取舍

两者都提供了 server 能力，但设计取向不同。Ollama 偏向命令行和自动化，CI 集成友好，自定义程度高但需要手动写 `Modelfile` 并重新创建模型。LM Studio 偏向交互体验，GUI 可配置项多，但高度自定义（比如和脚本联动）相对不容易。

我手头的分工是：桌面端（4090）用 LM Studio 暴露服务，因为日常编码时通过 GUI 调参更直观；MacBook 上用 Ollama，因为移动场景下我更看重轻量，而且 `ollama pull` 在终端里一条命令就能搞定。

两者暴露的 API 端口略有不同：Ollama 默认 `http://localhost:11434`，LM Studio 默认 `http://localhost:1234`（OpenAI 兼容模式）。
后续章节以 Ollama 为例，但 LM Studio 的配置思路完全一致，只需替换 `apiBase` 地址即可。

## 4. Continue 插件配置

[Continue][continue] 是一个开源的 AI 编码助手插件，支持接入任意模型提供商（包括本地 [Ollama][ollama] 和 [LM Studio][lm-studio]）。这是本文 AI 配置部分的核心。

### 4.1. 安装与基础配置

在 VS Code 扩展市场安装 `Continue` 后，配置文件通常位于 `~/.continue/` 目录或工作区根目录的 `.continue/config.yaml`。

### 4.2. 模型配置

Continue 的模型配置是整篇配置的核心。结合前文两台机器的硬件特点和模型选型，下面将按角色拆分配置。

#### 4.2.1. Chat 模型

Chat 模型用于对话面板的深度交互，是日常使用频率最高的角色。我根据两台机器分别配置了本地和云端（Home Cloud）两套模型：

```yaml
models:
  # —— 本地 Ollama（MacBook M4 Pro）——
  - name: Qwen3.6 35B (Local)
    provider: ollama
    model: qwen3.6:35b-mlx
    roles:
      - chat
    capabilities:
      - tool_use
      - image_input
    defaultCompletionOptions:
      contextLength: 65536

  # —— Home Cloud LM Studio（桌面 RTX 4090）——
  - name: Qwen3.6 27B (Home Cloud)
    provider: lmstudio
    model: qwen/qwen3.6-27b
    apiBase: http://<internal-hostname>:1234/v1
    apiKey: sk-lm-<PLACEHOLDER>
    requestOptions:
      timeout: 120000
    roles:
      - chat
    capabilities:
      - tool_use
      - image_input

  - name: Qwen3.6 35B (Home Cloud)
    provider: lmstudio
    model: qwen/qwen3.6-31b-qat
    apiBase: http://<internal-hostname>:1234/v1
    apiKey: sk-lm-<PLACEHOLDER>
    requestOptions:
      timeout: 120000
    defaultCompletionOptions:
      contextLength: 65536
    roles:
      - chat
    capabilities:
      - tool_use
      - image_input

  - name: Gemma4 26B (Home Cloud)
    provider: lmstudio
    model: google/gemma-4-26b-a4b-qat
    apiBase: http://<internal-hostname>:1234/v1
    apiKey: sk-lm-<PLACEHOLDER>
    requestOptions:
      timeout: 120000
    defaultCompletionOptions:
      contextLength: 32768
    roles:
      - chat
    capabilities:
      - tool_use
      - image_input

  # —— 其他角色模型（edit/apply/autocomplete/embed/rerank）见下文 ——
  # - name: ...
  #   ...
```

几个配置细节值得说明：

- **`roles: [chat]`**：明确声明该模型用于对话角色。Continue 支持 `chat` / `edit` / `apply` / `autocomplete` / `embed` / `rerank` 等角色，一个模型可以兼任多个角色。
- **`capabilities`**：`tool_use` 表示模型支持工具调用（即 MCP 工具），`image_input` 表示支持图片输入。
  不是所有模型都支持这些能力，配置时根据模型实际能力勾选即可。
- **`contextLength`**：上下文窗口大小。qwen3.6 系列原生支持 65536 的上下文，而 gemma4 26b 我设为 32768——
  桌面端显存有限，上下文太长容易触发 CPU offload（见 [2.3 节](#23-关于-cpu-offload-的取舍)）。
- **`requestOptions.timeout`**：LM Studio 远程调用设置了 120 秒超时，因为桌面端模型较大，复杂问题推理时间可能较长。

#### 4.2.2. Edit 和 Apply 模型

Edit 角色负责在编辑器中直接修改代码，Apply 角色将修改应用到文件。这两个角色对代码理解能力要求较高，我选了 qwen3-coder 30b：

```yaml
models:
  - name: Qwen3 Coder 30B (Local)
    provider: ollama
    model: qwen3-coder:30b
    roles:
      - chat
      - edit
      - apply
    capabilities:
      - tool_use
    defaultCompletionOptions:
      temperature: 0.7
      contextLength: 32768

  - name: Qwen3 Coder 30B (Home Cloud)
    provider: lmstudio
    model: qwen/qwen3-coder-30b
    apiBase: http://<internal-hostname>:1234/v1
    apiKey: sk-lm-<PLACEHOLDER>
    requestOptions:
      timeout: 120000
    defaultCompletionOptions:
      contextLength: 32768
    roles:
      - chat
      - edit
      - apply
    capabilities:
      - tool_use

  # —— 其他角色模型（chat/autocomplete/embed/rerank）见上文/下文 ——
  # - name: ...
  #   ...
```

qwen3-coder 在代码生成和修改方面表现突出，虽然前文提到它在 4090 上的 token 生成速度一般，
但 edit/apply 场景不需要高频交互，深度更重要。`temperature: 0.7` 让输出在创造性和稳定性之间取得平衡。

#### 4.2.3. 自动补全模型

自动补全对响应速度要求极高，模型太大反而影响体验。我选了 qwen2.5-coder 1.5b——虽然只有 1.5B 参数，
但针对代码任务做了专门训练，补全质量完全够用：

```yaml
models:
  - name: Qwen2.5 Coder 1.5B (Local)
    provider: ollama
    model: qwen2.5-coder:1.5b
    roles:
      - autocomplete
    capabilities:
      - tool_use
    autocompleteOptions:
      disable: false
      maxPromptTokens: 1024
      debounceDelay: 250
      modelTimeout: 150
      maxSuffixPercentage: 0.2
      prefixPercentage: 0.3
      onlyMyCode: true

  # —— 其他角色模型（chat/edit/apply/embed/rerank）见上文/下文 ——
  # - name: ...
  #   ...
```

`autocompleteOptions` 的几个关键参数：

- **`maxPromptTokens: 1024`**：限制每次补全请求的上下文大小，避免把整个文件都发给模型。
- **`debounceDelay: 250`**：输入停止 250ms 后再触发补全，避免打字过程中频繁请求。
- **`modelTimeout: 150`**：150ms 超时——补全要快，超时了就放弃，别让用户等。
- **`onlyMyCode: true`**：只索引用户自己的代码文件，不扫描 `node_modules` 等第三方库，减少噪音。

#### 4.2.4. 嵌入和重排序模型

嵌入模型用于代码库的向量检索，重排序模型对检索结果进行精排。两者配合可以让 AI 更准确地找到项目中的相关代码：

```yaml
models:
  - name: Nomic Embed Text V1.5 (Local)
    provider: ollama
    model: nomic-embed-text:v1.5
    roles:
      - embed
    embedOptions:
      maxChunkSize: 512
      maxBatchSize: 4

  - name: Huggingface-tei Reranker (Local)
    provider: huggingface-tei
    model: tei
    apiBase: http://localhost:18082
    apiKey: <PLACEHOLDER>
    roles:
      - rerank

  # —— 其他角色模型（chat/edit/apply/autocomplete）见上文 ——
  # - name: ...
  #   ...
```

nomic-embed-text 只有 274 MB，几乎不占资源，但检索效果出乎意料地好。
[Huggingface TEI][huggingface-tei]（Text Embeddings Inference）重排序服务跑在本地 `18082` 端口，
对检索结果做二次排序后，AI 引用代码的准确率有明显提升。

### 4.3. 上下文提供者配置

Continue 的 `context` 配置决定了 AI 能访问哪些本地信息源。以下是我的配置：

```yaml
context:
  - provider: code
  - provider: diff
  - provider: terminal
  - provider: open
    params:
      onlyPinned: true
  - provider: clipboard
  - provider: tree
  - provider: debugger
    params:
      stackDepth: 3
  - provider: repo-map
    params:
      includeSignatures: false
  - provider: os
```

这些上下文提供者的作用：

| 提供者      | 作用                                                  |
| ----------- | ----------------------------------------------------- |
| `code`      | 引用当前工作区的代码文件                              |
| `diff`      | 提供未提交的代码变更                                  |
| `terminal`  | 读取终端输出，帮助诊断命令执行结果                    |
| `open`      | 当前打开的文件（`onlyPinned: true` 只包含固定标签页） |
| `clipboard` | 剪贴板内容，方便粘贴后直接让 AI 处理                  |
| `tree`      | 项目目录结构                                          |
| `debugger`  | 调试器状态，`stackDepth: 3` 限制栈深度                |
| `repo-map`  | 仓库符号索引，`includeSignatures: false` 减少开销     |
| `os`        | 操作系统信息                                          |

**强烈建议**不要把所有上下文提供者都打开——每个提供者都会增加 prompt 的 token 消耗，
按需启用即可。比如 `debugger` 只在调试场景下有用，平时可以关掉。

### 4.4. 跨设备无缝切换

两套模型配置（本地 Ollama + Home Cloud LM Studio）的好处是：

- **在 MacBook 上**：优先使用本地 Ollama 模型，不依赖网络。
- **在桌面端**：通过 `apiBase` 连接桌面 LM Studio 服务，用 4090 的算力。
- **桌面机宕机时**：MacBook 上的本地模型可以无缝接管，不影响工作。

切换不需要改配置——Continue 会在 Chat 面板里列出所有可用模型，下拉菜单选一个就行。

### 4.5. 核心功能

- **Chat 面板**：在编辑器侧边栏直接与模型对话，支持引用当前文件内容和选中代码。
- **Tab 自动补全**：基于本地模型的代码补全，配置 `autocomplete` 角色后生效。
- **自定义指令**：通过 `.continue/rules` 定义项目级编码规范，让 AI 输出符合你的风格。

### 4.6. MCP 服务器配置

Continue 的 MCP 服务器配置独立于 VS Code 用户级 `mcp.json`，位于 `~/.continue/mcpServers/vscode-mcp.json`。
下面是我实际使用的两个 MCP 服务器：

```bash
$ cat ~/.continue/mcpServers/vscode-mcp.json
{
  "mcpServers": {
    "filesystem": {
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "."
      ],
      "autoApprove": "true",
      "command": "npx"
    },
    "context7": {
      "name": "context7",
      "command": "npx",
      "args": [
        "-y",
        "@upstash/context7-mcp"
      ]
    }
  }
}
```

- `filesystem` 服务器让 AI 能直接读写当前工作区文件。
- `context7` 则提供了额外的上下文检索能力，适合在大型项目中快速定位相关代码。

注意 Continue 的 MCP 配置和 VS Code 内置的 `mcp.json` 是两套独立体系，前者给 Continue 用，后者给 Copilot 用。
两者可以同时启用，AI 工具会根据当前使用的插件选择对应的 MCP 服务器。

## 5. Copilot 模型与 MCP 配置

[GitHub Copilot][github-copilot] 从 2025 年起开始支持 [MCP][mcp] 服务器接入，这意味着你可以将本地工具直接暴露给 Copilot。
和 Continue 类似，Copilot 的配置也分为两部分：先配置模型（config），再配置 MCP 服务器。

### 5.1. Config 配置

Copilot 的模型配置现在可以通过 VS Code 内置的 UI 界面完成，无需手动编辑 JSON 文件。
具体流程如下：

1. 点开 Copilot Chat 聊天输入框底部的模型选择下拉菜单，在列表最下方的 "Other" 选项旁点击 **齿轮图标**（Manage Language Models）。
2. 在打开的界面中点击右上角的 **"Add Models"** 按钮，并在下拉菜单中选择 **"Custom Endpoint"**。

   ![copilot-custom-model](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/2026-06-11-local-ai-vscode-continue-copilot-mcp-config-pic-01.png){: width="600"}

3. 输入模型的群组名称（Group Name，如 LM-Studio）并回车。
4. 随后输入该端点的显示名称（Display Name）并回车，接着系统会提示输入 API Key（由于是本地 LM Studio，这里可以随便输入任意非空字符串，比如 "lm-studio" 或 "not-needed"）并回车。
5. 接着选择 API 类型，本地 LM Studio 通常选择 **"Chat Completions"**。
6. 填完这些后，VS Code 会自动打开 `chatLanguageModels.json` 配置文件。你只需在 `models` 数组中将 `"url"` 改为 `http://localhost:1234/v1`，并将 `"id"` 改为你在 LM Studio 中加载的具体模型 ID，保存并关闭文件即可。
7. 回到聊天面板的模型下拉菜单中，选中刚刚添加的本地模型开始使用。

配置完成后，VS Code 会将配置写入 `~/Library/Application Support/Code/User/chatLanguageModels.json`（macOS）。
一个典型的配置文件如下：

```json
[
  {
    "name": "Copilot",
    "settings": {},
    "vendor": "copilot"
  },
  {
    "name": "Ollama",
    "url": "http://localhost:11434",
    "vendor": "ollama"
  },
  // LM-Studio
  {
    "apiKey": "<PLACEHOLDER>",
    "apiType": "chat-completions",
    "models": [
      {
        "id": "google/gemma-4-31b-qat",
        "maxInputTokens": 32000,
        "maxOutputTokens": 16000,
        "name": "Gemma4 31B",
        "toolCalling": true,
        "url": "http://<internal-hostname>:1234/v1",
        "vision": true
      },
      {
        "id": "qwen/qwen3.6-27b",
        "maxInputTokens": 64000,
        "maxOutputTokens": 16000,
        "name": "Qwen3.6 27B",
        "toolCalling": true,
        "url": "http://<internal-hostname>:1234/v1",
        "vision": true,
        "defaultCompletionOptions": {
          "temperature": 0.2,
          "topP": 0.9
        }
      }
    ]
  }
]
```

几个配置细节值得说明：

- **`vendor: "copilot"`**：GitHub 官方的云端模型服务，无需额外配置 API Key，开箱即用。
- **`vendor: "ollama"`**：本地 Ollama 服务，只需指定 `url` 即可接入，和 Continue 的 Ollama 配置思路一致。
- **`vendor: "customendpoint"`**：自定义端点（如 LM Studio），需要配置 `apiKey`、`apiType` 以及具体的模型列表。
- **`toolCalling`**：标记该模型支持工具调用（即 MCP 工具）。只有开启这个选项，Copilot 才能调用 MCP 服务器暴露的工具。
- **`vision`**：标记该模型支持图片输入，适合多模态场景。
- **`defaultCompletionOptions`**：采样参数，如 `temperature` 和 `topP`。`temperature: 0.2` 让输出更稳定，适合代码生成场景。

我的实际配置中，桌面端（4090）通过 Custom Endpoint 接入了 LM Studio 上的 qwen3.6 27b 和 gemma4 31b，
MacBook 上则通过 Ollama 接入了本地的 qwen3.6 35b-mlx。切换模型时，在 Copilot Chat 面板的下拉菜单里选一个就行——

### 5.2. MCP 服务器配置

Copilot 的 MCP 能力通过 VS Code 用户级 `mcp.json` 实现，当 MCP 服务器启动后，Copilot 会自动发现可用工具。
没什么好说的，配好 `mcp.json` 就能用。

一个典型的 `mcp.json` 如下：

```json
{
  "servers": {
    "github-mcp": {
      "type": "http",
      "url": "https://example.com/mcp/",
      "gallery": "https://example.com/gallery",
      "version": "1.0.0"
    },
    "drawio": {
      "command": "npx",
      "args": ["-y", "@drawio/mcp"]
    }
  },
  "inputs": []
}
```

配置分为两类启动方式：

- **HTTP 类型**：通过 `type: "http"` 指定远程 MCP 端点，适合云端服务。
- **命令类型**：通过 `command` + `args` 本地启动进程，适合本地工具。

注意 Continue 的 MCP 配置（`~/.continue/mcpServers/`）和 VS Code 内置的 `mcp.json` 是两套独立体系，前者给 Continue 用，后者给 Copilot 用。
两者可以同时启用，AI 工具会根据当前使用的插件选择对应的 MCP 服务器。

### 5.3. 与 Continue 的分工

两者不是替代关系，更像是互补。下面列了一个对比表：

| 能力       | Continue             | Copilot                              |
| ---------- | -------------------- | ------------------------------------ |
| 代码补全   | ✅ 可配置            | ✅ 内置                              |
| 自定义规则 | ✅ `.continue/rules` | ✅ `.github/copilot-instructions.md` |
| 多模型切换 | ✅ 灵活              | ⚠️ 有限                              |
| 开源       | ✅                   | ❌                                   |

我的使用习惯是：日常编码靠 Copilot 的行级补全降低输入成本，遇到复杂问题切换到 Continue 用本地模型做深度对话——
代码不会离开本机，这点对我来说很重要。

## 6. 实际工作流

结合两个插件和 MCP 服务器，一个典型的本地 AI 开发工作流如下：

1. **日常编码**：Copilot 提供行级补全，降低输入成本。
2. **复杂问题**：切换到 Continue，使用本地模型进行深度对话，代码不会离开本机。
3. **工具调用**：通过 MCP 服务器，AI 可以直接执行本地命令、查询数据库、读取项目文档。
4. **规则约束**：通过项目级指令文件，确保 AI 输出符合团队规范。

## 7. 需要注意

### MCP 服务器无法启动

这是最常见的问题，排查步骤：

- 检查 `mcp.json` 的 JSON 语法是否正确，一个多余的逗号就能让整个配置失效。
- 查看 VS Code 日志：`~/Library/Application Support/Code/logs/<session>/mcpServer.*.log`，日志里通常会有明确的错误信息。
- 确认 `command` 字段对应的可执行文件在 `PATH` 中，可以用 `which` 命令验证。

### 模型响应慢

- 检查显存是否充足，考虑使用量化模型（如 `q4_k_m`）。
- 调整 `num_ctx` 参数以控制上下文窗口大小，上下文越大推理越慢。
- 如果用的是 LM Studio，可以在界面里直接调参，比较直观。

### Continue 与 Copilot 补全冲突

两者可以同时启用，但 Tab 补全只能由一个提供。在 Continue 配置中设置 `tabAutocompleteModel` 后，
Continue 会接管补全功能。如果你希望 Copilot 继续提供补全，把 Continue 里的 `tabAutocompleteModel` 去掉就行。

## a. LM Studio 加载配置实践

上面提到了 qwen3.6 27b 是桌面端的主力模型，下面补充一下在 LM Studio 中的具体加载配置。
这部分内容比较细，但实际体验下来，正确的参数设置对显存占用和推理速度影响很大。

**模型来源**：从 Hugging Face 下载 `unsloth/Qwen3.6-27B-GGUF`，推荐 `UD-Q4_K_XL` 量化版本（次选 `UD-Q4_K_M`）。
注意不要下载带 `mmproj` 的版本——那是视觉组件，白占约 0.9 GB 显存，纯文本任务用不上。

**LM Studio 加载参数**：

| 参数                    | 推荐值                    | 说明                                                    |
| ----------------------- | ------------------------- | ------------------------------------------------------- |
| Context Length          | `65536`（手动填写）       | 不要用默认值 `262144`，上下文窗口越大 KV Cache 占用越高 |
| GPU Offload             | `64 / 64`（全部层上 GPU） | 确保模型权重完全驻留显存                                |
| KV Cache Type           | `Q8_0`（K 和 V 都设）     | 比默认精度省约一半 KV 显存                              |
| Offload KV Cache to GPU | ✓ 开启                    | 保持开启                                                |
| Flash Attention         | ✓ 开启                    | 默认已开，无需改动                                      |
| Vision / mmproj         | ✗ 不加载                  | 纯文本编码不需要视觉组件                                |

**预计显存占用（24 GB RTX 4090）**：

- 模型权重：~17 GB
- KV Cache（Q8 @ 64K）：~2 GB
- CUDA overhead：~1 GB
- **合计约 20 GB**，余量约 4 GB，日常编码够用 ✅

**Agent 模式补充**：Thinking mode 单次输出可达 32K–81K tokens，这是爆显存的主要原因。
建议在 `Inference Parameters` → `Max Tokens` 设为 `≤ 16384`，或者在 system prompt 里加一句 `Keep your thinking concise.` 来限制输出长度。

## b. 词汇表

本文涉及的部分专业术语，供快速查阅。

> <a id="glossary-token"></a>
> **Token**：大模型处理文本的基本单位。可以粗略理解为"字"或"词碎片"——
> 一个英文单词通常是一个 token，一个汉字可能是一个或半个 token。
> 模型的上下文窗口大小、生成速度等通常以 token 数为单位。

> <a id="glossary-bandwidth"></a>
> **内存带宽（Memory Bandwidth）**：内存每秒能传输的数据量，单位通常是 GB/s。
> 带宽越高，模型从内存读取权重的速度越快，token 生成也就越快。
> 可以类比为"水管粗细"——水管越粗，单位时间流过的水越多。

> <a id="glossary-vram"></a>
> **显存（VRAM, Video RAM）**：GPU 的专用内存，类似于 CPU 的系统内存但带宽更高。
> 模型推理时权重数据需要加载到显存中，显存大小决定了你能跑多大的模型。
> RTX 4090 的显存为 24GB，而 MacBook 的统一内存则同时充当显存和系统内存。

> <a id="glossary-architecture"></a>
> **模型架构**：本文主要涉及两种——
>
> - **稠密（Dense）**：模型的所有参数在每次推理时都参与计算。参数量越大，推理越慢，但通常质量更高。
> - **MoE（Mixture of Experts，混合专家）**：模型内部有多个"专家"子网络，每次推理只激活其中一部分。总参数量可以很大，但实际参与计算的参数较少。理论上更高效，但实际表现取决于具体实现。

> <a id="glossary-active-params"></a>
> **激活参数（Active Parameters）**：MoE 模型中，每次推理实际参与计算的参数量。
> 注意：虽然激活参数决定计算量，但总参数仍会影响内存带宽压力，因为全部权重都需要从内存中读取。

> <a id="glossary-cpu-offload"></a>
> **CPU Offload**：当模型太大、放不下 GPU 显存时，推理框架会把部分计算层"卸载"到系统内存中，由 CPU 分担计算。
> 由于系统内存带宽远低于显存带宽，offload 后推理速度会明显下降。在统一内存架构（如 Apple Silicon）上，这个惩罚较小。

> <a id="glossary-unified-memory"></a>
> **统一内存（Unified Memory）**：Apple Silicon（M 系列芯片）的内存架构，CPU 和 GPU 共享同一块物理内存，不存在传统 PC 上"显存"和"系统内存"的分离。
> 好处是模型不会受限于显存大小，代价是内存带宽低于独立显卡。

> <a id="glossary-mlx"></a>
> **MLX 格式**：[Apple MLX][apple-mlx] 推出的机器学习框架原生模型格式，针对 Apple Silicon 的 GPU 和神经网络引擎做了硬件级优化。
> 同量级模型，MLX 格式在 Mac 上的推理速度通常优于 [GGUF 格式][gguf]。

> <a id="glossary-gguf"></a>
> **GGUF 格式**：大模型通用的量化模型文件格式（GGML 的继任者），被 [Ollama][ollama]、[LM Studio][lm-studio] 等主流推理工具支持。
> 跨平台兼容性好，但在 Apple Silicon 上的加速效果不如 MLX 格式。

## 参考资料

- [Continue - Plugin](https://marketplace.visualstudio.com/items?itemName=Continue.continue)
- [GitHub Copilot](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot)
- [Qwen](https://qwenlm.github.io/)
- [Gemma](https://ai.google.dev/gemma)
- [Nomic Embed Text](https://nomic.ai/resources/nomic-embed-text)

<!-- refs -->

[ollama]: https://ollama.com/
[lm-studio]: https://lmstudio.ai/
[continue]: https://continue.dev/
[github-copilot]: https://github.com/features/copilot
[mcp]: https://modelcontextprotocol.io/
[cursor]: https://www.cursor.com/
[apple-mlx]: https://ml.apple.com/
[huggingface-tei]: https://huggingface.co/docs/text-embeddings-inference/en/index
[gguf]: https://github.com/ggerganov/ggml/blob/master/docs/gguf.md
