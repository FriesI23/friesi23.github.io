---
#  friesi23.github.io (c) by FriesI23
#
#  friesi23.github.io is licensed under a
#  Creative Commons Attribution-ShareAlike 4.0 International License.
#
#  You should have received a copy of the license along with this
#  work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
title: Flutter macOS 应用构建：GitHub Actions + 自动管理签名 (Automatically Manage Signing)
excerpt: |
  在 GitHub Actions 中构建并自动签名 macOS Flutter 应用，
  使用 App Store Connect API 和 Developer ID Certificate 实现自动化发布流程。
author: FriesI23
date: 2025-04-11 08:00:00 +0800
category: deploy
tags:
  - flutter
  - github-action
  - macos
  - ci/cd
  - code-signing
---

Github 官方文档 ["Installing an Apple certificate on macOS runners for Xcode development"][github-action-xcode]
阐述了如何在 macOS 环境中装载 Apple 证书以便为代码签名。不过该文档基于手动管理`配置文件（Provision Proile）`，
而对于启用`自动管理签名（Automatically manage signing）`的项目，由于使用`云签名（Cloud signing）`，
因此无需创建该配置文件。

而在 Xcode 13 及更高版本中，`xcodebuild` 可以使用 App Store Connect API 在 Apple Developer 上进行身份验证。
因此我们可以使用该验证方式在 CI 中对代码进行自动签名。

## 需要准备

1. 一个 Apple 开发者账号。
2. 一个 App Store Connect API 对应的团队密钥（导出为 `P8` 文件）。
   - Issuer ID
   - API Key
   - API Certificate (`Auth_xxx.p8`)
3. 一个 Developer Id Application Certificate（导出为 `P12` 文件）。
   - Certificate (`***.p12`)
   - Certificate Password

### App Store Connect API 团队密钥

访问 [App Store Connect / 用户和访问 / App Store Connect API][apple-integrations-api]，
选择 `团队密钥`，然后添加一个新的密钥，完成后下载 `p8` 证书。

此时我们拥有以下三个需要的信息：

1. Issuer ID: 可以从**“团队密钥”**下找到。
2. API Key: 可以从**“团队密钥 / 有效”**下找到（中文名：密钥 ID）。
3. API Certificate：上面下载的文件，由于只能下载一次，请妥善保存。

### Developer Id Application Certificate

一个快捷的生成方式：直接在 Xcode 中进行生成。

1. 导航到 `Xcode --> Settings... --> Accounts --> Manage Certificates...`。
2. 点击左下角 `+`，点击 `Develop ID Application`，等待创建完成。
3. 找到刚刚创建的 Certificate，右键单击，选取 `Export Certificate`。
4. 导出时需要密码，随机生成一个即可，记得记录这个密码，最后会生成一个 `p12` 文件。

![pic-1](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/github-action-macos-app-with-auto-sign-pic-1.png){: width="800" }
![pic-2](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/github-action-macos-app-with-auto-sign-pic-2.png){: width="800" }

此时我们拥有以下两个需要的信息：

1. Certificate: 刚刚导出的 `p12` 文件。
2. Certificate Password: 导出时输入的密码。

### Github Action Secret Keys

将上面的信息存储到 `Repository secrets` 中，其中两个文件使用 `base64` 进行编码。

```shell
base64 -i ${your-api-auth}.p8 | pbcopy
base64 -i ${your-certificate}.p12 | pbcopy
```

同时我们需要一个 `APPLE_KEYCHAIN_PASSWORD`，后续导入证书时需要使用，随机生成一个字符串填入即可。

![pic-3](https://cdn.jsdelivr.net/gh/FriesI23/blog-image@master/img/github-action-macos-app-with-auto-sign-pic-3.png){: width="800" }

## Github Action 流程

### 导入证书

使用以下步骤进行证书导入，这里和 Github 官方文档的区别在于：我们不需要导入`配置文件（Provision Profile）`。

```yaml
jobs/<build-app>/steps:
  - name: Import Certificate
    env:
      KEYCHAIN_PASSWORD: ${{ secrets.APPLE_KEYCHAIN_PASSWORD }}
    run: |
      # create variables
      CERTIFICATE_PATH=$RUNNER_TEMP/certificate.p12
      KEYCHAIN_PATH=$RUNNER_TEMP/app-signing.keychain-db
      # import certificate from secrets
      echo "${{ secrets.APPLE_DEV_CERT_P12_BASE64 }}" | base64 --decode > $CERTIFICATE_PATH
      # create temporary keychain
      security create-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
      security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
      security unlock-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
      # import certificate to keychain
      security import $CERTIFICATE_PATH \
        -k $KEYCHAIN_PATH \
        -P "${{ secrets.APPLE_DEV_CERT_PASSWORD }}" \
        -A -t cert -f pkcs12
      security set-key-partition-list -S apple-tool:,apple: -k "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
      security list-keychain -d user -s $KEYCHAIN_PATH
```

### 导入 API Key

由于使用配置文件，我们需要使用 "App Store Connect API"，因此需要导入 `p8` 文件：

```yaml
jobs/<build-app>/steps:
  - name: Extract App Store Connect API Key
    env:
      APPLE_API_KEY_ID: ${{ secrets.APPLE_MACOS_API_KEY_ID }}
      APPLE_API_AUTHKEY_P8_BASE64: ${{ secrets.APPLE_MACOS_API_AUTHKEY_P8_BASE64 }}
    run: |
      mkdir ./private_keys
      echo -n "$APPLE_API_AUTHKEY_P8_BASE64" | base64 --decode --output ./private_keys/AuthKey_$APPLE_API_KEY_ID.p8
```

### 手动构建

由于我们需要手动签名，因此不能直接使用 `flutter build macos --release` 进行构建（会报“找不到配置文件”的错误）。
此时我们需要手动运行构建命名，如下：

> 由于后续签名需要，这里直接导出归档文件。

```yaml
jobs/<build-app>/steps:
  - name: Build APP
    env:
      APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
    run: |
      flutter build macos --release --config-only
      xcodebuild CODE_SIGNING_ALLOWED=NO \
        -workspace macos/Runner.xcworkspace \
        -scheme Runner \
        -configuration Release \
        -archivePath build/macos/Runner.xcarchive \
        archive
      # ls -al build/macos/Runner.xcarchive/Products/Applications
```

### 签名应用

签名导出时需要使用 `xcodebuild -exportArchive` 命名，此时需要手动创建一个 `ExportOptions.plist` 文件。
该文件的具体格式可 GUI 创建方法参考[**官方文档**][apple-distributing-your-app]，这里只给出一个示例：

> 注意 plist 本身并不支持诸如 `<string>${APPLE_TEAM_ID}</string>` 之类的格式，这里是作为一个 template，
> 由 `envsubst` 进行变量替换生成真正的 plist 文件。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>manageAppVersionAndBuildNumber</key>
    <false/>
    <key>method</key>
    <string>developer-id</string>
    <key>teamID</key>
    <string>${APPLE_TEAM_ID}</string>
  </dict>
</plist>
```

这里注意需要使用 `developer-id`，该方法依赖 `Developer Id Application Certificate`，而我们在上面已经进行导入，
参考[“导入证书”](#导入证书)。

我们假定将该文件存放在 `./installers/macos_exporter/GithubExportOptions.plist`，构建以下步骤：

```yaml
jobs/<build-app>/steps:
  - name: Signed APP
    env:
      APPLE_API_ISSUER_ID: ${{ secrets.APPLE_API_ISSUER_ID }}
      APPLE_API_KEY_ID: ${{ secrets.APPLE_MACOS_API_KEY_ID }}
      APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
    run: |
      envsubst \
        < ./installers/macos_exporter/GithubExportOptions.plist \
        > ./installers/macos_exporter/GithubExportOptions.resolved.plist
      cat ./installers/macos_exporter/GithubExportOptions.resolved.plist
      plutil -lint ./installers/macos_exporter/GithubExportOptions.resolved.plist
      xcodebuild -exportArchive -archivePath ./build/macos/Runner.xcarchive \
        -exportPath ./build/macos/Build/Products/Release \
        -exportOptionsPlist ./installers/macos_exporter/GithubExportOptions.resolved.plist \
        -allowProvisioningUpdates \
        -authenticationKeyIssuerID $APPLE_API_ISSUER_ID \
        -authenticationKeyID $APPLE_API_KEY_ID \
        -authenticationKeyPath `pwd`/private_keys/AuthKey_$APPLE_API_KEY_ID.p8
```

最终我们将签名的应用导出到 `./build/macos/Build/Products/Release`。

## 整体流程

这里直接粘贴自己项目中的流程，仅供参考：

> [**Workflow Source**](https://github.com/FriesI23/mhabit/blob/a57159998792d5c7890c690e6340b11100bac590/.github/workflows/app-release.yml)

```yaml
jobs:
  # other actions
  build-macos-dmg:
    name: "Build macos DMG"
    runs-on: macos-latest
    steps:
      - uses: maxim-lobanov/setup-xcode@v1
        with:
          xcode-version: ^16
      - uses: actions/checkout@v4
      - uses: ./.github/actions/setup_flutter
      - name: Import Certificate
        env:
          KEYCHAIN_PASSWORD: ${{ secrets.APPLE_KEYCHAIN_PASSWORD }}
        run: |
          # refs: https://docs.github.com/en/actions/use-cases-and-examples/deploying/installing-an-apple-certificate-on-macos-runners-for-xcode-development
          # create variables
          CERTIFICATE_PATH=$RUNNER_TEMP/certificate.p12
          KEYCHAIN_PATH=$RUNNER_TEMP/app-signing.keychain-db
          # import certificate from secrets
          echo "${{ secrets.APPLE_DEV_CERT_P12_BASE64 }}" | base64 --decode > $CERTIFICATE_PATH
          # create temporary keychain
          security create-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
          security set-keychain-settings -lut 21600 $KEYCHAIN_PATH
          security unlock-keychain -p "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
          # import certificate to keychain
          security import $CERTIFICATE_PATH \
            -k $KEYCHAIN_PATH \
            -P "${{ secrets.APPLE_DEV_CERT_PASSWORD }}" \
            -A -t cert -f pkcs12
          security set-key-partition-list -S apple-tool:,apple: -k "$KEYCHAIN_PASSWORD" $KEYCHAIN_PATH
          security list-keychain -d user -s $KEYCHAIN_PATH
      - name: Extract App Store Connect API Key
        env:
          APPLE_API_KEY_ID: ${{ secrets.APPLE_MACOS_API_KEY_ID }}
          APPLE_API_AUTHKEY_P8_BASE64: ${{ secrets.APPLE_MACOS_API_AUTHKEY_P8_BASE64 }}
        run: |
          mkdir ./private_keys
          echo -n "$APPLE_API_AUTHKEY_P8_BASE64" | base64 --decode --output ./private_keys/AuthKey_$APPLE_API_KEY_ID.p8
      - name: Build APP
        env:
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: |
          flutter build macos --release --config-only
          xcodebuild CODE_SIGNING_ALLOWED=NO \
            -workspace macos/Runner.xcworkspace \
            -scheme Runner \
            -configuration Release \
            -archivePath build/macos/Runner.xcarchive \
            archive
          ls -al build/macos/Runner.xcarchive/Products/Applications
      - name: Signed APP
        env:
          APPLE_API_ISSUER_ID: ${{ secrets.APPLE_API_ISSUER_ID }}
          APPLE_API_KEY_ID: ${{ secrets.APPLE_MACOS_API_KEY_ID }}
          APPLE_TEAM_ID: ${{ secrets.APPLE_TEAM_ID }}
        run: |
          envsubst \
            < ./installers/macos_exporter/GithubExportOptions.plist \
            > ./installers/macos_exporter/GithubExportOptions.resolved.plist
          cat ./installers/macos_exporter/GithubExportOptions.resolved.plist
          plutil -lint ./installers/macos_exporter/GithubExportOptions.resolved.plist
          xcodebuild -exportArchive -archivePath ./build/macos/Runner.xcarchive \
            -exportPath ./build/macos/Build/Products/Release \
            -exportOptionsPlist ./installers/macos_exporter/GithubExportOptions.resolved.plist \
            -allowProvisioningUpdates \
            -authenticationKeyIssuerID $APPLE_API_ISSUER_ID \
            -authenticationKeyID $APPLE_API_KEY_ID \
            -authenticationKeyPath `pwd`/private_keys/AuthKey_$APPLE_API_KEY_ID.p8
      - uses: actions/setup-node@v4
        with:
          node-version: 20
          token: ${{ secrets.APP_RELEASE_TOKEN }}
      - run: npm install -g appdmg
      - name: Build DMP
        run: appdmg ./installers/dmg_creator/config.json ./build/macos/Build/Products/Release/mhabit.dmg
      - name: Released - MacOS
        uses: ncipollo/release-action@v1
        with:
          allowUpdates: true
          omitBodyDuringUpdate: true
          omitDraftDuringUpdate: true
          omitPrereleaseDuringUpdate: true
          artifacts: >
            build/macos/Build/Products/Release/mhabit.dmg
          token: ${{ secrets.APP_RELEASE_TOKEN }}
```

## 问题：应用签名时出现 Segmentation fault: 11

参考该 ISSUE：[FB13797668: xcodebuild crashes systematically when exporting an archive (segfault)](https://github.com/feedback-assistant/reports/issues/562)

该问题已在 `Xcode 16 Beta 4` 进行修复。如果出现该问题，请指定执行时的 Xcode 版本（而不是使用容器自带的版本）：

```yaml
jobs/...:
  # https://github.com/maxim-lobanov/setup-xcode
  - uses: maxim-lobanov/setup-xcode@v1
    with:
      xcode-version: ^16  #
```

## 参考资料

1. [GitHub Actions で Automatically manage signing を使って Flutter の ipa ビルドする][build-automatically-manage-singin-on-ci]
2. [Distributing your app for beta testing and releases][apple-distributing-your-app]

<!-- refs -->

[build-automatically-manage-singin-on-ci]: https://zenn.dev/yorifuji/articles/build-automatically-manage-singin-on-ci
[apple-integrations-api]: https://appstoreconnect.apple.com/access/integrations/api
[apple-distributing-your-app]: https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases
[github-action-xcode]: https://docs.github.com/en/actions/use-cases-and-examples/deploying/installing-an-apple-certificate-on-macos-runners-for-xcode-development
