<div align="center">
  <img src="Resources/teleport-icon.webp" alt="Teleport 应用图标" width="160" />

  <h1>Teleport</h1>

  <p>在 Mac 上模拟 iOS 设备定位，支持模拟器及通过 USB 或 Wi-Fi 连接的实体设备。</p>

  <p>
    <img src="https://img.shields.io/badge/platform-macOS-34C759" alt="macOS 应用" />
    <img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT 许可证" />
    <a href="https://github.com/BlackCCCat/Teleport/releases/latest"><img src="https://img.shields.io/badge/%E4%B8%8B%E8%BD%BD-%E6%9C%80%E6%96%B0%E7%89%88%E6%9C%AC-007AFF?logo=apple&logoColor=white" alt="下载最新版 Teleport" /></a>
  </p>

  <p><a href="README.md">English</a> · <a href="#安装">安装</a></p>
</div>

---

> [!NOTE]
> **Fork 说明与改动：**
> - **解耦 Xcode 环境选项**：在应用左侧栏底部增加了“Xcode 环境”开关。关闭后，真机设备（USB 与 Wi-Fi）将完全通过 Python `pymobiledevice3` 纯协议栈发现与连接，**彻底摆脱对 Xcode 及 `xcrun devicectl` 的强依赖**。
> - **免密码/免提权模拟选项**：在左侧栏底部新增“免密码提权模拟”开关，默认开启。采用 iOS 17+ 原生/用户态免提权通道直连，**彻底告别每次模拟定位时频繁弹出管理员密码或 Touch ID 指纹验证的烦扰**。
> - **独立 CLI 命令行工具 (`teleport`)**：无需打开图形界面，即可通过终端完整控制设备发现、连通性检测、定位模拟与还原，更适合自动化脚本与终端极客。
> - **无感自动连接与连通性检测**：执行 `teleport set` 时自动识别设备并建立隧道；同时提供 `teleport connect` 显式检测设备握手状态与延迟。
> - **GUI 收藏夹无缝同步与按地点名称定位**：CLI 自动读取 Teleport App 中保存的收藏地点（`teleport locations`），并支持直接使用地点名称进行模拟定位（`teleport set "工作打卡"`），支持精确匹配与模糊搜索。
> - **AI Agent 原生集成**：内置 AI 技能包 (`teleport-location`)，让 AI 助手可通过自然语言对话帮用户查询收藏、一键修改手机定位。
> - **状态持久化**：开关状态会自动记住（存储于 `UserDefaults`），重启应用或电脑后依旧保持上次设置。
> - **自动打包发布**：新增 GitHub Actions 工作流，发布 GitHub Release 时自动编译打包 macOS `.dmg` 与 `.zip` 安装包。

Teleport 基于 SwiftUI 和 MapKit 构建。在地图上点一个位置，按下 Simulate，设备就以为自己在那里。

![Teleport – 定位模拟](Resources/screenshot-main.jpg)

![Teleport – 路线构建](Resources/screenshot-route.jpg)

## 安装

### 直接下载

从 [Releases](https://github.com/BlackCCCat/Teleport/releases) 下载最新 `.dmg`，将 `Teleport.app` 拖入应用程序文件夹，然后启动。

## 功能

**全面的设备支持** — 同一个应用，支持 iOS 模拟器和通过 USB 或 Wi-Fi 连接的实体 iPhone。

**虚拟摇杆** — 实时移动模拟位置，无需每次重新选点。非常适合在测试时随时调整位置。

**自定义路线** — 在任意停靠点之间绘制直线路径，或通过 Apple 地图导航将路线贴合真实道路。两种模式均支持按固定间隔或目标速度回放，路线的保存、加载和编辑全部支持。

**GPX 导入与导出** — 导入现有路线，或将你的路线导出备用。

其他功能：

- 点击地图任意位置选点，或按名称搜索，或直接输入坐标
- 在应用内保存路线，随时重新加载、重命名、编辑或复制
- 会话控制提供清晰的状态显示，随时可以停止或重置

## 免责声明

Teleport 仅用于开发测试和调试。其他用途风险自负，应用及其开发者对任何后果不承担责任。

## 环境要求

- macOS
- 已安装 Xcode，并至少启动过一次（使 `xcrun`、`simctl` 和 `devicectl` 可用）
- 真机：iPhone 已开启开发者模式，并安装 `python3` 和 `pymobiledevice3 >= 5.0`
- Wi-Fi 真机：先通过 USB 配对一次，然后保持设备解锁并连接同一网络

如果 macOS 提示缺少开发者工具：

```sh
xcode-select --install
```

如果 `xcrun` 指向了错误的 Xcode：

```sh
sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
```

然后启动一次 Xcode，完成初始化。

安装或升级 Python 依赖：

```sh
python3 -m pip install --upgrade pymobiledevice3
```

Teleport 的真机定位模拟要求 `pymobiledevice3` 版本不低于 5.0。

## 从源码运行

### Xcode

1. 打开 `Teleport.xcodeproj`。
2. 选择 `Teleport` scheme。
3. 构建并运行。

### 命令行

```sh
xcodebuild -project Teleport.xcodeproj -scheme Teleport -destination 'platform=macOS' build
```

## 基本用法

1. 启动 Teleport，选择设备。
2. 连接设备。
3. 选择位置——点击地图、搜索，或直接输入坐标。
4. 点击 `Simulate`，完成。
5. 如需模拟移动，可以创建路线。
6. 路线可保存备用，也可导入/导出 GPX 文件。
7. 完成后点击 `Stop`。

真机可能会在首次运行时请求管理员授权、提示安装 Python 依赖，或需要先通过 USB 连接一次才能启用 Wi-Fi 发现。

## 命令行工具 (CLI)

Teleport 配备了功能完善的无头命令行工具（`teleport`），支持在不启动 GUI 图形应用的情况下完成所有定位模拟操作。其全程运行于普通用户态，无需输入 root 密码，支持设备自动识别与连接，并原生适配 AI Agent。

### 安装配置

将 CLI 软链接到你的系统的 `PATH` 路径中：

```sh
ln -sf $(pwd)/bin/teleport ~/.local/bin/teleport
```

### 核心工作流与使用示例

#### 1. 设备发现与健康检测
```sh
# 列出所有已连接的实体 iPhone 及运行中的 iOS 模拟器
teleport devices
teleport devices --json

# 测试设备握手连通性与隧道延迟
teleport connect
```
*提示：当仅有一台设备连接时，`teleport` 将全自动选定该设备，无需手动输入 UDID。*

#### 2. 读取收藏夹与按地点名称模拟定位
CLI 会直接同步你在 Teleport macOS 界面中收藏的地点：

```sh
# 查看所有已收藏的地点与经纬度
teleport locations
teleport locations --json

# 直接使用收藏地点名称进行定位（支持完全匹配与模糊搜索）
teleport set "工作打卡"
teleport set "公司"
teleport set "故宫"
```

#### 3. 按指定经纬度模拟定位
```sh
# 模拟到北京故宫
teleport set 39.9163 116.3972 --name "故宫"

# 模拟到上海外滩
teleport set 31.2400 121.4900 --name "外滩"

# 多设备连接时指定特定设备
teleport set 37.3349 -122.0090 --device 00008140-001E0C291E33001C --name "Apple Park"
```
*内部机制：首次执行 `set` 会在后台静默启动常驻守护进程。后续切换位置时通过本地 Socket 热更新，耗时 `< 0.1s`，无需重新握手。*

#### 4. 模拟状态查看与重置
```sh
# 查看当前活跃的模拟定位会话与坐标
teleport status

# 停止模拟，恢复设备真实的 GPS 定位
teleport clear
```

### CLI 命令速查表

| 指令 | 作用说明 |
| :--- | :--- |
| `teleport devices` | 列出已连接的真机与模拟器 |
| `teleport connect` | 测试设备连通性与隧道延迟（支持 `--json`） |
| `teleport locations` | 读取 Teleport App 中的所有收藏地点（支持 `--json`） |
| `teleport set <地点名>` | **直接按收藏夹名称进行模拟定位（支持模糊搜索）** |
| `teleport set <纬度> <经度>` | 按具体经纬度数值进行模拟定位 |
| `teleport status` | 显示后台正在运行的模拟定位会话 |
| `teleport clear` | 停止模拟并恢复手机真实 GPS 定位 |

### AI Agent 联动

Teleport 附带了开箱即用的 AI 技能配置 (`teleport-location`)。配置后，AI 助手可以通过自然语言理解直接帮用户查收藏、换位置（例如：“帮我把手机定位改到工作打卡”），全程无需人工操作。

## 开发

- `make format` 执行 `swift format -r -p -i .`
- `make lint` 执行 `swift format lint -r -p .`

## 说明

Teleport 最初叫做 iOSAnywhere。

如果你在中国大陆使用，Apple 地图搜索通常只返回中国境内的地点，搜索海外地点一般需要 VPN。当然你也可以直接在地图上拖到任意位置手动选点。
