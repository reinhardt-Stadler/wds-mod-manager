# Changelog

## [1.1.0] - 2026-07-22

### Fixed
- REPL 交互模式内 `-help`/`-un`/`-u` 自管理命令无法使用（报 "No such option"），现已在循环内正确拦截
- REPL 内输入带 `wds` 前缀的命令（如 `wds install ...`）现在自动剥离前缀

### Changed
- 启动横幅重新设计：标题改为方框字符艺术字（WDS MOD MANAGER），字符间留空隙避免粘连，全部采用 GBK 安全字符，兼容中文 Windows 终端

### Docs
- 使用说明「游戏根目录」章节扩写：三层优先级说明、`setx` 命令示例、游戏目录迁移操作指引

## [1.0.0] - 2026-07-20

首个正式版本。

- 核心功能：scan / install / status / uninstall / switch / rename / ls-mods / undo
- D-014 类别优先匹配引擎（normalize + build_game_categories + _match_category）
- 交互 REPL（wds> 提示符）+ 单命令模式
- 自管理命令：-un（卸载工具）/ -u（远程更新）/ -help（打开说明文档）
- 操作日志 + undo 回退
- 完整备份体系（原版快照 / 增量快照 / mod 文件副本 / 注册表）
- 344 pytest 用例
