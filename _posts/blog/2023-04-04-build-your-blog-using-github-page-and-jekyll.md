---
layout: post
title: "使用 Github Page 与 Jekyll 创建自己的博客"
date: 2023-04-04 08:07:06 +0800
category: blog
tags:
  - build
  - github-page
  - jekyll
  - blog
---

<!--
 friesi23.github.io (c) by weooh

 friesi23.github.io is licensed under a
 Creative Commons Attribution-ShareAlike 4.0 International License.

 You should have received a copy of the license along with this
 work. If not, see <http://creativecommons.org/licenses/by-sa/4.0/>.
-->

## 为什么要写这一篇 Blog

1. 作为该 Blog 的第一篇文章, 记录搭搭建博客的过程还是很有必要的.
2. 现有的教程或多或少存在不完整或者过时的情况, 因此需要整合一下各方的资源.

## 技术选型

由于不是专业的前段开发, 也不想自己费时费力造轮子; 但是又不想自己花钱租赁服务器, 因此排除了
`wordpress`, `nextjs` 等方案, 最终选择最为简单(同时也是 github 官方推荐)的方案, 即:

```yaml
- github page
- github action
- jekyll
```

## 1. 创建 blog 仓库

可以跟随 Github 中的官方文档创建自己的 Blog Repo
[Creating a repository for your site](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll#creating-a-repository-for-your-site)

下面将简述一下简要的过程:

1. 点击 `New repository` 进入创建 repo 的界面
2. `Repository name` 填写 `<yourname>.github.io`, 注意将 `<yourname>` 替换为用户名, 并注意以下几点
   1. 一定是用户名(而不是昵称)
   2. 用户名如果有大写的部分要转化为小写(e.g. username => `Foo`, reponame => `foo.github.io`)
3. `repo` 的 `visibility` 选择 `public`
4. 点击 `Create Repository` 完成创建

经过以上步骤, 我们已经创建了一个空的 Blog 仓库.

## 2. 初始化 Blog

接下来需要在本地创建一个 `Jekyll` 项目.

### 2.1. Init Git

首先在一个空文件夹下使用 `Git` 记性版本管理(什么, 不会用/没有安装 Git, 戳[这里](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git))

```shell
cd /path/to/your/blog/folder
git init .
# 切换Branch不是必须的, 但是想要将您的Jekyll网站托管在GitHubPages上,
# 还是需要使用 `gh-pages`
git checkout --orphan gh-pages
```

### 2.2. Install Jekyll

然后需要在本地安装 `Jekyll`, 可以参考官方文档 [Installation](https://jekyllrb.com/docs/installation/)

以下已 `osx` 和 `brew` 环境举例说明步骤:

```shell
brew install chruby ruby-install xz
ruby-install ruby # 这里会安装最后一个last stable的ruby
# 将chruby相关配置添加到shell的配置文件中
echo "source $(brew --prefix)/opt/chruby/share/chruby/chruby.sh" >> ~/.zshrc
echo "source $(brew --prefix)/opt/chruby/share/chruby/auto.sh" >> ~/.zshrc
```

输入 `source ~/.zshrc` 或者重启新的会话得配置生效后, 输入 `chruby` 获取刚刚安装的版本号:

```shell
» chruby
 * ruby-3.2.2
```

然后输入 `chruby <ruby-3.2.2>` 切换当前 ruby 环境为 `3.2.2` 的环境, 输入 `ruby -v` 确认
切换是否成功:

```shell
ruby -v
ruby 3.2.2 (2023-03-30 revision e51014f9c0) [arm64-darwin22]
```

最后输入 `gem install jekyll`, 至此本地安装 `jekyll` 完成.

### 2.3. Init Jekyll Project

该部分主要参考官方文档 [Creating your site](https://docs.github.com/en/pages/setting-up-a-github-pages-site-with-jekyll/creating-a-github-pages-site-with-jekyll#creating-your-site),
并针对一些流程中的报错进行提醒.

首先切换到 blog 目录下, 并执行一下步骤

```shell
# 删除所有文件, 因为创建Jekyll项目的前提条件是一个空的目录
git rm -rf .
# Main Progress
Jekyll new --skip-bundle .
```

完后后打开 `Gemfile` (这个文件是刚刚 Jekyll 自动生成的), Template config 如下;

其中 `GITHUB-PAGES-VERSION` 需要替换的版本号可以在 [Dependency versions](https://pages.github.com/versions/)
找到.

![github-page](https://user-images.githubusercontent.com/20661034/229664408-57ae7bdb-8734-4f2d-ae52-0732e394f4ff.png)

```yaml
source "https://rubygems.org"
# 1. 将 `gem "jekyll", "~> x.y.z"` 这一行注释掉
# gem "jekyll", "~> 4.3.2"
gem "minima", "~> 2.5"

# 2. 增加这一行, 将 `GITHUB-PAGES-VERSION` 替换微正确的版本号
gem "github-pages", "~> GITHUB-PAGES-VERSION", group: :jekyll_plugins

group :jekyll_plugins do
  gem "jekyll-feed", "~> 0.12"
end

platforms :mingw, :x64_mingw, :mswin, :jruby do
  gem "tzinfo", ">= 1", "< 3"
  gem "tzinfo-data"
end

gem "wdm", "~> 0.1.1", :platforms => [:mingw, :x64_mingw, :mswin]

gem "http_parser.rb", "~> 0.6.0", :platforms => [:jruby]
```

保存后执行 `bundle install`, 等待完成后即可.

### 2.4. 保存以上更改

```shell
git add .
git commit -m "Init new blog"
```

以上, 我们已经完成了一个 `Jekyll Blog` 的本地初始化的全部工作.

## 3. 本地测试

在发布到 `Github page` 前, 最好做一下本地测试, 输入 `bundle exec jekyll serve`:

```shell
Configuration file: /path/to/blog/folder/_config.yml
To use retry middleware with Faraday v2.0+, install `faraday-retry` gem
            Source: /path/to/blog/folder
       Destination: /path/to/blog/folder/_site
 Incremental build: disabled. Enable with --incremental
      Generating...
       Jekyll Feed: Generating feed for posts
                    done in 0.09 seconds.
 Auto-regeneration: enabled for '/path/to/blog/folder'
    Server address: http://127.0.0.1:4000/
  Server running... press ctrl-c to stop.
```

## 3.1. 运行 `bundle exec jekyll serve` 产生如下报错

```log
bundler: failed to load command: jekyll (/Users/foo/.gem/ruby/3.2.2/bin/jekyll)
<internal:/Users/foo/.rubies/ruby-3.2.2/lib/ruby/3.2.0/rubygems/core_ext/kernel_require.rb>:37:in `require': cannot load such file -- webrick (LoadError)
        from <internal:/Users/foo/.rubies/ruby-3.2.2/lib/ruby/3.2.0/rubygems/core_ext/kernel_require.rb>:37:in `require'
        from /Users/foo/.gem/ruby/3.2.2/gems/jekyll-3.9.3/lib/jekyll/commands/serve/servlet.rb:3:in `<top (required)>'
        from /Users/foo/.gem/ruby/3.2.2/gems/jekyll-3.9.3/lib/jekyll/commands/serve.rb:184:in `require_relative'
...
```

该问题出现在 `Ruby>3.0` 的版本, 相关讨论详见 [Jekyll serve fails on Ruby 3.0 (webrick missing)](https://github.com/github/pages-gem/issues/752),
解决方法为 输入 `bundle add webrick`

## 4. 上传至 `Github`

执行以下命令:

```shell
git remote add origin git@github.com:FooBar/foobar.github.io.git
git fetch
git push --set-upstream origin gh-pages
```

在 Github 上, 定位到 "`Settings` -> `Code and automation` -> `Build and deployment`",
将 `Source` 切换到 `Github Actions`, 选择 `Github Pages Jekyll`

![change to github action](https://user-images.githubusercontent.com/20661034/229669106-82b52648-2435-48ff-87a6-92eecd609936.png)

![select Github Pages Jekyll]("https://user-images.githubusercontent.com/20661034/229670216-df72dfb5-8f3c-411e-8475-acf0319c463d.png")

![commit builder](https://user-images.githubusercontent.com/20661034/229670454-bc2f3015-10eb-4bd3-a807-06d1398db4d9.png)

等待 `Action` 完成后, 浏览器内输入 `https://foobar.github.io.git` 即可防访问博客主页

### 4.1. `Github Workflow` 报错

```log
...
Ruby and Rails Github Action exit code 16
```

问题的讨论在[这里](https://stackoverflow.com/questions/72331753/ruby-and-rails-github-action-exit-code-16)

```text
The config declares ubuntu-latest platform image for running the job on Github Actions.
Github Actions uses x86_64-linux platform for ubuntu. However,
the Gemfile.lock is missing that platform leading to exit code 16.
```

解决方法为在本地输入 `bundle lock --add-platform x86_64-linux`,
提交 `Gemfile.lock` 更改后 push 到 Github 即可
