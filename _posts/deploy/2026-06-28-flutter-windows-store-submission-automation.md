---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: Flutter 应用上架 Microsoft Store：Entra ID 应用注册 + GitHub Actions 自动提交全流程
excerpt: |
  最近给 Flutter 应用接入了 Microsoft Store 的自动化提交流程，
  本以为账号配置会是个一次性的体力活，结果 Partner Center + Entra ID
  这一侧就踩了几个坑，落地 CI 之后又冒出来几个更隐蔽的问题，
  因此在这里记录一下。
author: FriesI23
date: 2026-06-28 02:00:00 +0800
category: deploy
tags:
  - flutter
  - github-action
  - windows
  - microsoft-store
  - ci/cd
---

最近给 Flutter 应用接入了 Microsoft Store 的自动化提交流程。本以为账号配置会是个一次性的体力活——注册、拿凭证、写进 CI——结果合作伙伴中心（Partner Center）和 Entra ID 这一侧本身就踩了几个坑，落地之后 CI 实跑又冒出来几个更隐蔽的问题。因此在这里记录一下。

## 1. 背景

[Table Habit][mhabit-repo] 的发布自动化已经通过 [fastlane][fastlane] 覆盖了 Android（Google Play）和 iOS/macOS（App Store）——Android 侧配置见 [`android/fastlane/Fastfile`][mhabit-fastlane-android]，iOS/macOS 同理。接下来推进 Windows / Microsoft Store。

最初的设想是：Windows 这边也应该能找到类似 fastlane 的现成方案直接套上去。结果翻了一圈官方文档和社区项目，并没有找到一个等价物——最后能用的就是 Microsoft 官方的 [`msstore` CLI][msstore-cli]，剩下的部分（账号配置、CI 拼装）都得自己手动走一遍。

落地 CI 之前需要先确认两件事：

1. 应用必须已在 Partner Center 中创建，拿到应用 ID（Product ID）并在 GitHub 中配置
   ——这个值跟 iOS/macOS 的 Bundle ID 一样是公开标识。
2. 代表 CI 的 Microsoft Entra ID 应用注册（App Registration）必须在
   [合作伙伴中心（Partner Center）][partner-center-entra] 分配「经理 (Windows)」角色。

下面先走一遍 Partner Center + Entra ID + `msstore` CLI 的手动配置流程，再落地代码。最终 CI 落地的成品见：

- [`_submit-windows-store.yml`][mhabit-submit-windows-store-workflow]
- [`build_windows_store`][mhabit-build-windows-store-action]
- [`scripts/build_msix_store.cmd`][mhabit-build-msix-store-script]
- [`scripts/msstore/check_draft_ownership.ps1`][mhabit-check-draft-ownership-script]
- [`scripts/msstore/update_changelog.ps1`][mhabit-update-changelog-script]

## 2. 合作伙伴中心（Partner Center）账号侧配置

### 2.1. 关联 Microsoft Entra ID 租户（Tenant）

可能很多独立开发者跟我一样以为关联 Entra ID 租户（Tenant，以前叫 Azure AD）需要公司账号——其实 **个人开发者账号也能关联 Entra ID 租户**，官方文档明确支持个人账号事后关联 Entra ID 做多用户管理。具体操作步骤：

1. 用注册合作伙伴中心（Partner Center）开发者账号的同一个 Microsoft 账号登录 [entra.microsoft.com][entra-portal]——账号一致，后面关联起来省事。
2. 左侧导航找「标识」→「概述」，或者直接搜"创建租户"，进入创建向导后租户类型选 **Microsoft Entra ID**（不是面向终端用户的 Entra External ID/B2C，那个是给应用做用户认证用的，跟这里的 CI 场景没关系）。
3. 填写组织名称、初始域名（格式固定是 `<自定义前缀>.onmicrosoft.com`，全局唯一，先到先得）和国家/地区，提交创建。
   > 第一次提交的时候撞上了 `Error Code: 715-123280`，换浏览器、清缓存都没用，一度以为是 provisioning 流程被自动校验挡住的已知问题。后来发现根本原因是**当前登录的 Microsoft 账号邮箱本身就没法用来创建 Entra ID 租户**——换一个邮箱重新登录、重新提交就解决了。如果你也撞上这个错误码，先试试换邮箱。
4. 创建过程中会要求绑定一张信用卡——按 [Microsoft Entra ID Free 官方说明][entra-id-free-billing]，这张卡只用于身份验证，是 Entra ID Free 的强制步骤，照提示填实际卡信息即可。
5. 流程一般几分钟就能跑完，完成后页面会自动切到新租户。记下这个租户的域名和 Tenant ID。
6. 回到合作伙伴中心，点右上角齿轮图标 → 「帐户设置」，左侧导航「组织配置文件」分组下选 **Tenants**（这一项没有被本地化，显示的就是英文原文）→「将 Microsoft Entra ID 与合作伙伴中心账号关联」，用第 5 步那个租户里的账号登录确认域名信息，点「确认」完成关联（详见官方文档 [Associate an existing Microsoft Entra ID tenant][associate-existing-tenant]）。关联完成后，合作伙伴中心才能在 2.3 里识别到这个租户下创建的 App Registration。

详见 [Microsoft Entra ID 文档][entra-id-docs]。

![entra.microsoft.com 新建 tenant 流程](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-01%20-2.png){: width="800" }

### 2.2. 创建 CI 用的应用注册（App Registration） {#sec-2-2}

在 Entra ID 租户里创建一个应用注册（App Registration）代表 CI，具体操作步骤（详见 [应用注册快速入门][quickstart-register-app]）：

1. 登录 [entra.microsoft.com][entra-portal]，确认当前租户已经切到 2.1 里新建的那个（右上角齿轮图标可以切换租户）。
2. 左侧导航找到「应用注册」，点击「新注册」。

   ![Entra「应用注册」列表页，左侧导航和「新注册」按钮位置](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-02.png){: width="800" }

3. 填写一个能区分用途的名称（比如 `mhabit-windows-store-ci`）；「受支持的帐户类型」选 **仅单个租户**——这个 app 只代表自己的 CI，不需要兼容多租户或个人账号登录。
4. 「重定向 URI」整段留空——CI 走的是客户端凭据流程（client credentials flow），靠 Client ID + Secret 直接换 token，没有用户登录跳转这一步，不需要配回调地址。

   ![「注册应用程序」表单：受支持的帐户类型选「仅单个租户」，重定向 URI 留空](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-03.png){: width="800" }

5. 点击「注册」，进入应用的概述页，记下 **目录(租户) ID** 和 **应用程序(客户端) ID**——这两个就是后面要用的 Tenant ID 和 Client ID。

   ![应用概述页：应用程序(客户端) ID 与目录(租户) ID 的位置](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-04.png){: width="800" }

6. 左侧导航切到「证书和密码」→「客户端密码」→「新客户端密码」，填写「说明」和「截止期限」（官方推荐 180 天/6 个月），点击「添加」。

   ![「证书和密码」页：新建客户端密码的导航路径与表单](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-05.png){: width="800" }

7. 添加完成后客户端密码列表会多出一行，**「值」**这一列就是 Client Secret，只在这一次完整显示——当场复制保存，刷新或离开页面之后就只剩打码后的样子。注意旁边的「机密 ID」不是密码本身，只是这条密码记录的标识符，别认错。

   ![客户端密码列表：「值」与「机密 ID」是两个不同的字段](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-06.png){: width="800" }

### 2.3. 给 App 分配「经理 (Windows)」角色

回到 Partner Center，路径是 Account settings → User management → Microsoft Entra applications → Add Microsoft Entra application，把上一步创建的 app 加进来并分配角色（详见 [Partner Center 文档][partner-center-entra]）。

角色分配是个多选框——经理 (Windows)、开发人员、业务参与者、财务参与者、营销人员——很容易纠结要不要多选几个才保险。实际上官方文档只要求 **经理 (Windows)** 一个角色，它的权限范围本身已经覆盖"开发人员"能做的操作。

### 2.4. 获取卖家 ID（`MSSTORE_SELLER_ID`） {#sec-2-4}

这是我踩的最迷惑的一个坑。Partner Center 的"标识符"（Identifiers）页面会列出 **Windows 发布者 ID**（`CN=...` 格式，是包签名身份的 Publisher CN）、**Windows Phone 发布者 ID**、**Symantec ID**——这里面 **没有一个**是 Seller ID。

真正的 Seller ID 藏在 **帐户设置 (Account settings) → Legal info**，是一个纯数字——这里有个小陷阱：左侧导航栏里这一项压根没有被本地化，显示的就是英文原文 "Legal info"，只有进去之后页面标题才会同时显示"帐户设置 | 法律信息"。对照一下：

| 名称                    | 位置            | 格式     | 是不是 Seller ID |
| ----------------------- | --------------- | -------- | ---------------- |
| Windows 发布者 ID       | 标识符页面      | `CN=...` | 否               |
| Windows Phone 发布者 ID | 标识符页面      | -        | 否               |
| Symantec ID             | 标识符页面      | -        | 否               |
| Seller ID               | Legal info 页面 | 纯数字   | **是**           |

这个命名上的混淆连官方 `msstore-cli` 的 issue 里都有人在问，文档里笼统说的 "Publisher ID / Seller ID" 和 Partner Center 页面上的实际字段名对不上，第一次确实很难找。

![帐户设置 | Legal info 页面：卖家 ID 与 Windows 发布者 ID、Windows Phone 发布者 ID 同列在「帐户详细信息」里](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-07.png){: width="800" }

## 3. 本机 `msstore` CLI 配置

至此账号侧需要的 4 个值都齐了（租户 ID / Tenant ID、应用程序(客户端) ID / Client ID、客户端密码 / Client Secret、卖家 ID / Seller ID），接下来在本机装 `msstore` CLI 完成认证。

我的环境是 macOS，所以需要先有 `.NET 9 Runtime`，然后：

```shell
brew install microsoft/msstore-cli/msstore-cli
```

安装完成后跑 `reconfigure` 把凭证写进本机配置：

```shell
msstore reconfigure \
  --tenantId <TENANT_ID> \
  --sellerId <SELLER_ID> \
  --clientId <CLIENT_ID> \
  --clientSecret <CLIENT_SECRET>
```

- `TENANT_ID`：[2.2](#sec-2-2) 第 5 步的「目录(租户) ID」
- `SELLER_ID`：[2.4](#sec-2-4) 节的 Seller ID
- `CLIENT_ID`：[2.2](#sec-2-2) 第 5 步的「应用程序(客户端) ID」
- `CLIENT_SECRET`：[2.2](#sec-2-2) 第 7 步的客户端密码「值」

认证完成后用 `apps list` 获取 Product ID，需要跟仓库 README 里已经公开的 Microsoft Store 徽章链接（`apps.microsoft.com/detail/<PRODUCT_ID>`）做一次比对，确认没取错应用：

```shell
msstore apps list

...
✅ Retrieved Managed Applications
┌───┬──────────────┬──────────────┬─────────────────────┐
│   │ ProductId    │ Display Name │ PackageId           │
├───┼──────────────┼──────────────┼─────────────────────┤
│ 1 │ 9N********GZ │ Table Habit  │ Friesi23.TableHabit │
└───┴──────────────┴──────────────┴─────────────────────┘
```

## 4. 写进 GitHub Environment

至此拿到了 5 个值，但 Secrets 和普通变量需要分别处理：

| 值                                                                                        | 性质                                               | 写入方式                                                                                           |
| ----------------------------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `MSSTORE_TENANT_ID` / `MSSTORE_CLIENT_ID` / `MSSTORE_CLIENT_SECRET` / `MSSTORE_SELLER_ID` | 凭证                                               | `gh secret set <NAME> --env store-submission --repo <owner>/<repo>`，终端交互输入，不经过对话历史  |
| `MSSTORE_PRODUCT_ID`                                                                      | 公开标识（跟 iOS/macOS 把 bundle id 直接写死一样） | `gh variable set MSSTORE_PRODUCT_ID --env store-submission --body "<productId>"`，直接写，不用交互 |

没什么好说的，4 个 Secret 自己在终端里敲，`PRODUCT_ID` 因为不是凭证直接用 `gh variable set` 写进去就行。
另外我将所有 KV 都写入了 store-submission 环境，具体放在 repo 全局还是环境都可以。

## 5. CI 落地

落地成 composite action + reusable workflow，方便跟仓库里现有的几个发布 job 拼装。

**新增 composite action `build_windows_store`**：复用 `setup_flutter`，构建命令直接调本机开发者也会跑的 [`scripts/build_msix_store.cmd`][mhabit-build-msix-store-script]，把 Store 身份参数（`--identity-name`/`--publisher` 等）集中写在脚本里，避免在 action 和脚本之间重复一份。`--store` 模式下 msix 不需要本地签名（Microsoft Store 提交时会自行重新签名），所以这个 action 没有签名相关的 input，跟 `build_windows`（GitHub Release 用，要 PFX 签名）完全独立。

**新增 `_submit-windows-store.yml`**：`workflow_call` + `dry_run` 输入，`environment: store-submission`。用官方 `microsoft/microsoft-store-apppublisher` action 装 CLI、`reconfigure` 写认证，然后是后面"坑"里提到的草稿归属校验（[`check_draft_ownership.ps1`][mhabit-check-draft-ownership-script]）——校验通过才会触发耗时的 Windows 构建，没必要为一个不属于这条 CI 的草稿白跑一次构建。`publish` 永远带 `--noCommit`，是否真正执行 `submission publish` 完全交给 `dry_run` 控制。最后一步用后面"坑"里那个细粒度 PAT，把这次的 submission ID 写回 Environment Variable，留给下一次 CI 跑时做归属校验。

**修改 `release-app.yml`**：加一个跟 `build-windows-msix` 并行的 `submit-windows-store` job，只 `needs: pre-build`，不进 `post-build` 的 `needs` 链。另外加了一条 `if`：pre-release 的 tag 直接跳过——Microsoft Store 没有公开的 beta 渠道（package flights/私有受众都是邀请制），pre-release 没有地方可提交。

**修改 `manual-submit.yml`**：加 `windows` 输入（`skip`/`submit` 二选一，没有 track 概念）和对应 job，直接调用，不需要 `resolve-apple-store-track` 那一套。

{% raw %}

```yaml
# _submit-windows-store.yml (part)
on:
  workflow_call:
    inputs:
      dry_run:
        type: boolean
        default: false

jobs:
  submit-windows-store:
    runs-on: windows-2022
    environment: store-submission
    steps:
      - uses: actions/checkout@v6
      - name: Setup Microsoft Store Developer CLI
        uses: microsoft/microsoft-store-apppublisher@v1.3
      - name: Configure Microsoft Store Developer CLI
        shell: pwsh
        env:
          MSSTORE_TENANT_ID: ${{ secrets.MSSTORE_TENANT_ID }}
          MSSTORE_SELLER_ID: ${{ secrets.MSSTORE_SELLER_ID }}
          MSSTORE_CLIENT_ID: ${{ secrets.MSSTORE_CLIENT_ID }}
          MSSTORE_CLIENT_SECRET: ${{ secrets.MSSTORE_CLIENT_SECRET }}
        run: >
          msstore reconfigure
          --tenantId $env:MSSTORE_TENANT_ID
          --sellerId $env:MSSTORE_SELLER_ID
          --clientId $env:MSSTORE_CLIENT_ID
          --clientSecret $env:MSSTORE_CLIENT_SECRET
      # 校验当前 Partner Center 上 pending 的草稿是不是上一次 CI 自己创建
      # 的，不是就跳过，避免覆盖人工在 Partner Center 准备中的草稿。
      - id: ownership
        name: Check pending submission ownership
        shell: pwsh
        run: >
          scripts\msstore\check_draft_ownership.ps1
          -ProductId "${{ vars.MSSTORE_PRODUCT_ID }}"
          -KnownSubmissionId "${{ vars.MSSTORE_LAST_CI_SUBMISSION_ID }}"
      - id: build
        if: ${{ steps.ownership.outputs.proceed == 'true' }}
        uses: ./.github/actions/build_windows_store
      - name: Stage package
        if: ${{ steps.ownership.outputs.proceed == 'true' }}
        shell: pwsh
        env:
          MSIX_PATH: ${{ steps.build.outputs.msix-path }}
        run: msstore publish $env:MSIX_PATH -id ${{ vars.MSSTORE_PRODUCT_ID }} --noCommit
      - id: changelog
        name: Stage changelog metadata
        if: ${{ steps.ownership.outputs.proceed == 'true' }}
        shell: pwsh
        run: >
          scripts\msstore\update_changelog.ps1
          -ProductId "${{ vars.MSSTORE_PRODUCT_ID }}"
      - name: Finalize submission
        if: ${{ steps.ownership.outputs.proceed == 'true' && !inputs.dry_run }}
        shell: pwsh
        run: msstore submission publish ${{ vars.MSSTORE_PRODUCT_ID }}
      - name: Record CI-owned submission Id
        if: ${{ steps.ownership.outputs.proceed == 'true' }}
        shell: pwsh
        env:
          GH_TOKEN: ${{ secrets.MSSTORE_VARS_PAT }}
        run: >
          gh variable set MSSTORE_LAST_CI_SUBMISSION_ID
          --body "${{ steps.changelog.outputs.submission-id }}"
          --env store-submission
          --repo ${{ github.repository }}
```

{% endraw %}

## 坑

代码写完、真实 CI 跑起来之后，又踩了几个一开始没预料到的坑。下面按时间顺序记录。

### setup_flutter 在 cmd 步骤里找不到 flutter/dart

根因很简单但藏得很深：共享 action `setup_flutter` 把 `"<目录>:$PATH"` 整行写进了 `$GITHUB_PATH`。bash 步骤"凑巧"能工作（bash 按 `:` 拆 `PATH`），但 Windows `cmd` 步骤只认 `;` 作为路径分隔符，整行 `:` 直接被当成目录名的一部分，自然找不到 `flutter`/`dart`。

之前四个 `build_*` action 全部用的 bash 步骤，这个 bug 从来没暴露过——Windows Store 这条是第一个用 `cmd` 步骤跑裸 `flutter`/`dart` 命令的消费方。修法也简单：

只写目录本身（去掉 `:$PATH`），对其余四个调用无影响。

### msstore CLI 输出的 JSON 不能直接 ConvertFrom-Json

`msstore submission get` 会把 JSON 当人类可读的文本来打印——按终端列宽强制换行。如果输出里有长的中文字段（编码成 `\uXXXX` 转义），换行边界刚好切到转义序列中间，PowerShell 把多行拼回去再 `ConvertFrom-Json` 就会报 `Invalid Unicode escape sequence`。

本机用同一个真实账号能稳定复现一模一样的截断位置，确认不是网络波动或 CI 特有。修法是截取第一个 `{` 到最后一个 `}` 之间，再去掉所有原始换行——JSON 在 token 之间本来就不在乎空白，真正的换行应该被编码成 `\n` 两个字符，不会是裸换行。

```pwsh
# 示意：截取 { 到 } 之间再去除裸换行
# $raw = msstore submission get ...
# $json = ($raw -join '') -replace '...'
```

这种设计缺陷在非 ASCII 内容上几乎是必现的。

### 官方文档摘要的字段名是错的

网上摘要写的是 `listings[language].whatsNew`，但真实账号读出来的是 `Listings.<lang>.BaseListing.ReleaseNotes`（legacy API 的 PascalCase 形状）。

### 草稿归属标记走了三个方案才落地

CI 需要一种方式来判断"当前线上是否已经有本次构建对应的草稿"，避免重复创建。这个标记存在哪里，前后试了三个方案：

| 方案                                             | 结果     | 放弃/采用原因                                                                                                                                                       |
| ------------------------------------------------ | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 写进 `FriendlyName`                              | 放弃     | 服务端只读/自动生成，写入被静默丢弃（靠真实调一次 `updateMetadata` 再读回来才发现，不是看文档看出来的）                                                             |
| 写进 `Description`                               | 放弃     | 技术上可写，但这是真实展示给 Store 用户的商品描述文案，提交链路没有人工检查点，一旦标记没清理干净就会被真实发布出去                                                 |
| `store-submission` Environment 下的固定 Variable | **采用** | 不读写 Submission 任何字段；中途也试过 `actions/cache`，但 cache 7 天不用会被清理，且清理后的误判不会自动恢复，等于 CI 卡死等人工，因此最后使用 Variable 来存储数据 |

这里有个方法论上的教训："字段技术上可写" ≠ "适合用来存自动化标记"——选状态存储位置时，要先确认**谁会看到这个字段**，而不是只确认能不能写进去。`Description` 就是典型的反例：能写，但用户可见，风险太高。

最终落地为两个 PowerShell 脚本：

- [`check_draft_ownership.ps1`][mhabit-check-draft-ownership-script] 负责比对当前草稿 ID 与已知的 CI 归属标记
- [`update_changelog.ps1`][mhabit-update-changelog-script] 负责写入 changelog 并回写归属标记

两个脚本都可以脱离 CI 在本机直接跑，跟 fastlane lane 的用法一致。

### 细粒度 PAT 第一次配的权限类别选错了

`gh variable set --env store-submission ...` 需要 PAT 有写入权限。第一次配的时候以为勾上 "Variables: read and write" 就够了，结果真实跑直接报 403。查了文档才发现：**Environment 级**的 Variable 接口（带 `--env` 参数那种）实际归在 **"Environments"** 这个权限类别下，跟仓库/组织级 Variable 用的 "Variables" 类别是两个独立的勾选项——这个分类非常不直观，很容易选错而不自知。把 "Environments" 也勾上（保留原来的 "Variables"，两个都给 Read and write）之后才跑通。

![细粒度 PAT 权限选择页面：Environments 与 Variables 是两个独立的勾选项，都需要 Read and write](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/flutter-windows-store-submission-automation-08.png){: width="800" }

## 总结

最终整体流程其实就是*账号配置 → CLI 认证 → 写 Environment → CI 落地*这四步，账号部分卡住的点基本都在第一步，代码部分的坑全在最后一步，中间两步反而是最顺利的。

## 参考资料

1. [msstore-cli—Microsoft Store CLI][msstore-cli]
2. [Quickstart: Register an application—Microsoft identity platform][quickstart-register-app]
3. [Microsoft Entra service principal—Partner Center][partner-center-entra]
4. [Microsoft Entra ID Free—Microsoft Cost Management][entra-id-free-billing]
5. [Associate an existing Microsoft Entra ID tenant with your Partner Center account][associate-existing-tenant]

<!-- refs -->

[msstore-cli]: https://github.com/microsoft/msstore-cli
[quickstart-register-app]: https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
[partner-center-entra]: https://learn.microsoft.com/en-us/partner-center/enroll/service-principal
[entra-id-free-billing]: https://learn.microsoft.com/en-us/azure/cost-management-billing/manage/microsoft-entra-id-free
[associate-existing-tenant]: https://learn.microsoft.com/en-us/windows/apps/publish/partner-center/associate-existing-azure-ad-tenant-with-partner-center-account
[entra-portal]: https://entra.microsoft.com
[entra-id-docs]: https://learn.microsoft.com/en-us/entra/
[mhabit-repo]: https://github.com/FriesI23/mhabit
[fastlane]: https://fastlane.tools
[mhabit-fastlane-android]: https://github.com/FriesI23/mhabit/blob/main/android/fastlane/Fastfile
[mhabit-submit-windows-store-workflow]: https://github.com/FriesI23/mhabit/blob/main/.github/workflows/_submit-windows-store.yml
[mhabit-build-windows-store-action]: https://github.com/FriesI23/mhabit/blob/main/.github/actions/build_windows_store/action.yml
[mhabit-build-msix-store-script]: https://github.com/FriesI23/mhabit/blob/main/scripts/build_msix_store.cmd
[mhabit-check-draft-ownership-script]: https://github.com/FriesI23/mhabit/blob/main/scripts/msstore/check_draft_ownership.ps1
[mhabit-update-changelog-script]: https://github.com/FriesI23/mhabit/blob/main/scripts/msstore/update_changelog.ps1
