一、总体判断：不要只做鼠标坐标录制
你的需求包括：

录制鼠标点击；
录制键盘输入；
回放操作；
根据页面上的文字做 IF 判断；
比如根据“合同类型”下方的文字，走不同流程；
可能还要识别表格行、点击“预览 / 修改 / 删除”等按钮；
页面可能滚动、分辨率可能变化、浏览器缩放可能变化。
所以如果只录制：

text
移动到 x=2560, y=760
点击
输入文字

会非常不稳定。

更推荐的方案是：

录制坐标只是辅助，真正执行时优先使用 DOM 元素定位、OCR、图像识别和规则引擎。

二、推荐技术架构
可以设计成下面几个模块：

text
┌──────────────────────────────┐
│           桌面控制台           │
│ 流程管理 / 录制 / 编辑 / 执行    │
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│          流程定义引擎          │
│ Step / IF / Loop / Variable   │
└───────────────┬──────────────┘
                │
┌───────────────▼──────────────┐
│          执行引擎 Runner       │
│ 点击 / 输入 / 等待 / 判断 / 异常 │
└───────┬─────────┬────────────┘
        │         │
        │         │
┌───────▼───┐ ┌───▼────────────┐
│ 浏览器自动化 │ │ 屏幕自动化/OCR │
│ Playwright │ │ pyautogui/OCR  │
└───────────┘ └────────────────┘

三、核心技术选型建议
方案 A：如果这个系统是浏览器 Web 页面，优先使用 Playwright
从截图看，这明显是一个浏览器里的 Web 系统。

因此最推荐：

后端执行核心
Python + Playwright
或者 Node.js + Playwright
Playwright 可以直接定位网页元素，而不是依赖坐标。例如：

python
page.get_by_text("合同起草").click()
page.get_by_text("预览").nth(0).click()

Run

或者通过 CSS/XPath 定位表格：

python
rows = page.locator("table tbody tr")
contract_type = rows.nth(0).locator("td").nth(1).inner_text()

Run

然后：

python
if "低压居民供用电合同" in contract_type:
    # 执行低压居民合同流程
elif "本地费控协议" in contract_type:
    # 执行费控协议流程

Run

这个方式比鼠标坐标稳定得多。

方案 B：如果页面控件无法直接获取 DOM，再用 OCR / 图像识别
有些政企系统可能有 iframe、canvas、水印、加密控件，Playwright 不一定能直接读取。

这时可以加一层：

OCR：PaddleOCR / Tesseract / Windows OCR
图像识别：OpenCV
鼠标控制：pyautogui / pynput
窗口控制：pywinauto
例如识别“合同类型”这一列下面的文字，再判断：

text
识别区域：
表格第 2 列，第 1 行

OCR 结果：
低压居民供用电合同

执行：
IF 合同类型 == 低压居民供用电合同
    点击预览
    填写起草时间
ELSE IF 合同类型 == 本地费控协议
    选择第二行
    点击预览

四、建议采用“混合自动化”方案
也就是：

优先级 1：DOM 自动化
适合：

点击按钮；
读取表格；
输入文本；
切换 Tab；
判断元素是否存在；
读取合同类型；
点击某一行的“预览”。
优先级 2：OCR 自动化
适合：

页面文字无法通过 DOM 获取；
表格是图片或 Canvas；
某些控件无法选中；
弹窗、验证码以外的提示识别。
优先级 3：坐标点击
适合：

最后兜底；
某些按钮没有 DOM 定位；
控件被复杂组件包裹；
录制调试阶段快速跑通流程。
也就是说，不要让坐标成为主方案，而是：

text
DOM 定位失败 → OCR 查找 → 图像模板匹配 → 坐标点击兜底

五、流程应该如何设计
你这个程序的关键不是“点击”，而是要有一个流程定义语言。

可以用 JSON / YAML 来定义每一步。

例如：

yaml
name: 合同起草自动化流程
steps:
  - type: click
    target:
      text: 合同起草

  - type: wait
    target:
      text: 合同信息
    timeout: 10

  - type: read_table
    name: contract_table
    selector: "table"
    columns:
      - 序号
      - 合同类型
      - 合同名称
      - 合同编号
      - 合同文本形式
      - 状态
      - 操作

  - type: if
    condition: "contract_table.rows[0].合同类型 contains '低压居民供用电合同'"
    then:
      - type: click_table_action
        table: contract_table
        row: 0
        action_text: 预览

      - type: input
        target:
          label: 起草时间
        value: "2026-05-14"

    else_if:
      - condition: "contract_table.rows[0].合同类型 contains '本地费控协议'"
        then:
          - type: click_table_action
            table: contract_table
            row: 0
            action_text: 预览

    else:
      - type: log
        message: 未识别合同类型，人工处理

这样以后不用每次改代码，只需要改流程文件。

六、录制器应该怎么设计
你希望程序可以“录制鼠标和键盘的点击”。

可以分两层录制。

1. 基础录制：记录鼠标和键盘事件
可以记录：

json
[
  {
    "type": "click",
    "x": 2530,
    "y": 662,
    "button": "left",
    "timestamp": 1720000000
  },
  {
    "type": "keypress",
    "key": "tab"
  },
  {
    "type": "input",
    "text": "测试内容"
  }
]

技术可以用：

Python pynput
Python keyboard
Python mouse
Windows Hook API
但是这只是低级事件。

2. 智能录制：把点击转换成网页元素操作
更重要的是，当用户点击页面时，程序应该尝试识别：

text
你点击的是哪个元素？
它的文本是什么？
它的 XPath 是什么？
它的 CSS selector 是什么？
它是否在表格第几行第几列？
它附近的 label 是什么？

比如用户点击截图中的“预览”，录制结果不要只保存：

json
{
  "type": "click",
  "x": 2580,
  "y": 660
}

而应该保存为：

json
{
  "type": "click",
  "target": {
    "method": "text",
    "value": "预览",
    "index": 0,
    "fallback": {
      "x": 2580,
      "y": 660
    }
  }
}

如果是表格中的按钮，应该更进一步：

json
{
  "type": "click_table_action",
  "table": "合同信息",
  "row_condition": {
    "column": "合同类型",
    "contains": "低压居民供用电合同"
  },
  "action_text": "预览"
}

这种录制才有价值。

七、IF 条件判断怎么实现
你的例子是：

依据合同类型下边的文字，进行不同的后续操作。

这个应该设计成一个独立的条件判断模块。

条件来源可以有几种
1. DOM 文字
例如读取表格单元格：

python
contract_type = page.locator("table tbody tr").nth(0).locator("td").nth(1).inner_text()

Run

然后判断：

python
if "低压居民供用电合同" in contract_type:
    run_low_voltage_flow()
elif "本地费控协议" in contract_type:
    run_fee_control_flow()

Run

2. OCR 文字
如果无法读取 DOM：

python
text = ocr_region(x1, y1, x2, y2)

if "低压居民" in text:
    run_low_voltage_flow()
elif "费控协议" in text:
    run_fee_control_flow()

Run

3. 元素是否存在
例如：

yaml
condition: "exists(text='修改')"

或者：

yaml
condition: "not_exists(text='待签订')"

4. 表格行状态判断
例如截图里有状态：

text
生效
待签订

可以设计：

yaml
- type: if
  condition: "table['合同信息'].row[合同类型='低压居民供用电合同'].状态 == '待签订'"
  then:
    - type: click_table_action
      action_text: 修改

八、针对你截图里的页面，建议抽象成这些操作
截图中主要元素包括：

顶部 Tab：合同起草；
子 Tab：业务受理、合同起草、办电收资；
二级 Tab：合同账户信息、合同起草信息；
合同信息表格；
表格列：
序号；
合同类型；
合同名称；
合同编号；
合同文本形式；
状态；
操作；
操作按钮：
预览；
修改；
删除；
下方表单：
起草人；
起草时间；
有效期；
备注。
建议把这些封装成页面对象。

页面对象示例
python

View all
            cells = row.locator("td")
            rows.append({
                "index": i,
                "contract_type": cells.nth(1).inner_text().strip(),
                "contract_name": cells.nth(2).inner_text().strip(),
                "contract_no": cells.nth(3).inner_text().strip(),
                "text_format": cells.nth(4).inner_text().strip(),
                "status": cells.nth(5).inner_text().strip(),
            })

        return rows

    def click_preview_by_contract_type(self, contract_type_keyword):
        rows = self.page.locator("table tbody tr")
        count = rows.count()

        for i in range(count):
            row = rows.nth(i)
            text = row.inner_text()
            if contract_type_keyword in text:
                row.get_by_text("预览").click()
                return True

        return False

Run

九、程序界面建议
你的工具可以做成一个 Windows 桌面程序。

技术选型
简单快速版
Python
PySide6 / PyQt6 做界面
Playwright 做浏览器自动化
pynput 做录制
PaddleOCR 做 OCR
SQLite 保存流程
更工程化版本
前端：Electron / Tauri
后端：Python FastAPI 或 Node.js
自动化：Playwright
OCR：PaddleOCR
数据库：SQLite / PostgreSQL
流程格式：YAML / JSON
我个人建议你第一版用：

Python + PySide6 + Playwright + SQLite + PaddleOCR

开发成本低，功能够用，后期也好扩展。

十、流程编辑器建议
你可以做一个可视化流程编辑器，节点类型包括：

基础节点
节点	说明
点击	点击按钮、文字、坐标
输入	输入文本
等待	等待元素、等待时间
读取文本	读取页面元素或 OCR 区域
截图	保存当前页面截图
滚动	页面滚动
热键	Ctrl+C、Tab、Enter 等
逻辑节点
节点	说明
IF 判断	根据文字、状态、变量判断
ELSE IF	多分支
循环	遍历表格行
异常处理	找不到元素时走人工处理
变量赋值	保存合同类型、用户编号等
表格节点
节点	说明
读取表格	识别合同信息表格
查找行	按合同类型、状态查找
点击行内按钮	点击某行的预览、修改、删除
遍历行	对每个合同执行操作
十一、一个适合你场景的流程示例
比如你要根据合同类型做不同操作，可以定义成：

yaml
name: 合同起草处理
steps:
  - id: open_contract_tab
    type: click_text
    text: 合同起草

  - id: wait_table
    type: wait_text
    text: 合同信息
    timeout: 10

  - id: read_contract_table
    type: read_table
    output: contracts
    columns:
      - 序号
      - 合同类型
      - 合同名称
      - 合同编号
      - 合同文本形式
      - 状态
      - 操作

  - id: handle_low_voltage
    type: if
    condition: "any(contracts, 合同类型 contains '低压居民供用电合同' and 状态 == '待签订')"
    then:
      - type: click_table_action
        table: contracts
        row_where:
          合同类型_contains: 低压居民供用电合同
          状态: 待签订
        action: 修改

      - type: input_by_label
        label: 起草时间
        value: "${today}"

      - type: input_by_label
        label: 有效期
        value: "12"

      - type: input_by_label
        label: 备注
        value: "自动起草"

  - id: handle_fee_control
    type: if
    condition: "any(contracts, 合同类型 contains '本地费控协议')"
    then:
      - type: click_table_action
        table: contracts
        row_where:
          合同类型_contains: 本地费控协议
        action: 预览

  - id: fallback
    type: if
    condition: "not any(contracts, 合同类型 contains '低压居民供用电合同')"
    then:
      - type: screenshot
        path: "./logs/unhandled_${工单编号}.png"
      - type: log
        message: "未找到低压居民供用电合同，转人工处理"

十二、执行引擎的数据结构
可以把每一步标准化成这样的结构：

json
{
  "id": "step_001",
  "type": "click",
  "target": {
    "strategy": "text",
    "value": "合同起草",
    "fallback": {
      "strategy": "coordinate",
      "x": 650,
      "y": 170
    }
  },
  "before_wait": 0.5,
  "after_wait": 1,
  "on_error": {
    "action": "screenshot_and_stop"
  }
}

条件节点：

json
{
  "id": "if_001",
  "type": "if",
  "condition": {
    "left": "${contract_type}",
    "operator": "contains",
    "right": "低压居民"
  },
  "then": [
    {
      "type": "click",
      "target": {
        "strategy": "text",
        "value": "修改"
      }
    }
  ],
  "else": [
    {
      "type": "log",
      "message": "合同类型不匹配"
    }
  ]
}

十三、录制与回放的关键难点
1. 页面加载时间不稳定
不能固定：

text
等待 3 秒

应该优先：

text
等待某个元素出现
等待表格加载完成
等待按钮可点击

例如：

python
page.get_by_text("合同信息").wait_for(timeout=10000)

Run

2. 表格行数不固定
不能假设合同永远在第一行。

应该按条件找行：

text
找合同类型包含“低压居民供用电合同”的那一行
然后点击该行的“预览”

3. 同名按钮很多
截图里每一行都有“预览”。

所以不能简单：

python
page.get_by_text("预览").click()

Run

而应该：

python
目标行.get_by_text("预览").click()

Run

4. iframe 问题
很多企业系统会把业务页面放在 iframe 里。

Playwright 里要处理：

python
frame = page.frame_locator("iframe").locator("text=合同信息")

Run

或者遍历所有 iframe 找文本。

5. 浏览器缩放与分辨率问题
如果使用坐标，要统一：

浏览器缩放 100%；
Windows 缩放 100% 或 125% 固定；
浏览器窗口最大化；
分辨率固定；
录制和执行环境一致。
但更好的方式还是 DOM 定位。

十四、OCR 识别如何用于你的 IF 判断
假设要读取截图中“合同类型”下面的文字，可以这样设计：

方式 1：固定区域 OCR
记录表格区域：

json
{
  "type": "ocr_read",
  "name": "contract_type_row1",
  "region": {
    "x1": 720,
    "y1": 625,
    "x2": 1040,
    "y2": 700
  }
}

识别后判断：

json
{
  "type": "if",
  "condition": "${contract_type_row1} contains '低压居民'"
}

缺点是分辨率变化后容易偏。

方式 2：锚点定位 OCR
先找到表头“合同类型”，再往下读取第一行。

逻辑是：

text
找到“合同类型”文字区域
向下偏移 50 像素
读取下面那一块

这个比固定坐标稳定。

方式 3：表格结构识别
通过 OCR 识别整张表格，并根据表头列位置切分：

text
表头：
序号 | 合同类型 | 合同名称 | 合同编号 | 合同文本形式 | 状态 | 操作

然后读取每列下面的文本。

这个适合 DOM 无法读取时使用。

十五、异常处理一定要做
RPA 最怕页面状态不一致。

建议每个步骤都要有：

超时时间；
失败截图；
错误日志；
是否重试；
是否跳过；
是否转人工。
例如：

yaml
- type: click_text
  text: 修改
  timeout: 5
  retry: 2
  on_error:
    - screenshot: "./logs/error_${工单编号}.png"
    - log: "找不到修改按钮"
    - stop: true

十六、日志和审计
这个很重要，尤其是涉及合同、营销系统、电力业务。

建议记录：

text
执行时间
操作账号
工单编号
用户编号
用户名称
合同类型
执行步骤
是否成功
失败原因
截图路径
耗时

例如数据库表：

sql
CREATE TABLE run_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_name TEXT,
    work_order_no TEXT,
    user_no TEXT,
    user_name TEXT,
    contract_type TEXT,
    status TEXT,
    error_message TEXT,
    screenshot_path TEXT,
    started_at DATETIME,
    ended_at DATETIME
);

十七、安全与权限
因为这是在业务系统里自动操作，建议加几个限制：

操作前确认当前登录账号；
限制只能在指定系统域名运行；
对关键操作加二次确认；
删除、提交、签订类动作默认需要人工确认；
敏感数据加密保存；
不保存明文密码；
每次执行生成日志和截图。
十八、推荐的第一版 MVP
第一版不要做太复杂，建议先实现：

MVP 功能
打开指定浏览器页面；
手动登录；
程序接管当前页面；
可以录制点击和输入；
可以把点击保存成流程；
支持编辑流程；
支持读取页面文字；
支持 IF 条件；
支持表格行查找；
支持错误截图；
支持执行日志。
第一版先不要做
暂时不要急着做：

大型可视化流程设计器；
多人权限系统；
云端调度；
复杂 AI 识别；
自动处理验证码；
完全无人值守。
先把一个固定业务流程跑稳，再扩展。

十九、我建议的落地路线
第 1 阶段：技术验证
目标：证明 Playwright 能不能读取这个页面里的合同表格。

做一个脚本：

python

View all
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://127.0.0.1:9222")
    page = browser.contexts[0].pages[0]

    print(page.title())
    print(page.get_by_text("合同信息").count())

    rows = page.locator("table tbody tr")
    print("rows:", rows.count())

    for i in range(rows.count()):
        print(rows.nth(i).inner_text())

Run

如果能打印出表格内容，后面就很好做。

第 2 阶段：固定流程脚本
先不做录制器，直接写一个固定流程：

text
读取合同表格
判断合同类型
点击对应行的修改/预览
填写起草时间
填写有效期
保存日志

目标是跑通真实业务。

第 3 阶段：流程配置化
把固定代码改成 YAML / JSON 流程。

第 4 阶段：录制器
加入录制功能。

但是录制结果要尽量转成高级动作：

text
点击文本
点击表格行按钮
输入指定 label
等待元素出现
读取表格
IF 判断

而不是单纯坐标。

第 5 阶段：桌面程序
用 PySide6 做一个管理界面：

流程列表；
流程编辑；
开始执行；
暂停；
终止；
日志查看；
截图查看；
变量配置。
二十、具体推荐技术栈
Python 版
text
语言：Python 3.11+
浏览器自动化：Playwright
桌面 GUI：PySide6
鼠标键盘录制：pynput
OCR：PaddleOCR
图像识别：OpenCV
数据库：SQLite
流程配置：YAML
日志：loguru
打包：PyInstaller

Node.js 版
text
语言：TypeScript
桌面 GUI：Electron
浏览器自动化：Playwright
鼠标键盘录制：iohook / uiohook-napi
OCR：PaddleOCR 服务 / tesseract.js
数据库：SQLite
流程配置：JSON/YAML

如果团队 Python 能力可以，我更推荐 Python。

二十一、一个比较稳的最终方案
我建议你们最终设计成：

text
Windows 桌面 RPA 工具
    ├── 流程录制器
    │     ├── 鼠标键盘事件记录
    │     ├── DOM 元素识别
    │     ├── OCR 辅助识别
    │     └── 动作智能转换
    │
    ├── 流程编辑器
    │     ├── 点击
    │     ├── 输入
    │     ├── 等待
    │     ├── 读取表格
    │     ├── IF 判断
    │     ├── 循环
    │     └── 异常处理
    │
    ├── 执行引擎
    │     ├── Playwright DOM 操作
    │     ├── OCR 图像识别
    │     ├── 坐标点击兜底
    │     └── 日志截图
    │
    ├── 业务适配层
    │     ├── 合同起草页面
    │     ├── 工单页面
    │     ├── 用户信息页面
    │     └── 表格识别规则
    │
    └── 数据层
          ├── 流程配置
          ├── 执行日志
          ├── 截图文件
          └── 变量参数

二十二、针对你这个截图的建议
从截图看，我建议你重点做这几个能力：

1. 读取合同信息表格
读取：

text
合同类型
合同名称
合同编号
合同文本形式
状态
操作

2. 按合同类型定位行
比如：

text
合同类型 contains 低压居民供用电合同
合同类型 contains 本地费控协议

3. 按状态判断
比如：

text
状态 == 生效
状态 == 待签订

4. 点击同行的操作按钮
比如：

text
点击该行的 预览
点击该行的 修改
点击该行的 删除

5. 填写下方表单
比如：

text
起草人
起草时间
有效期
备注

二十三、结论
我的建议是：

不要做一个简单的“鼠标键盘宏录制器”，而是做一个轻量级 RPA 引擎。

最佳方案是：

text
Python + Playwright + PySide6 + SQLite + OCR

执行策略是：

text
DOM 操作优先
OCR 识别辅助
坐标点击兜底
流程配置驱动
IF/ELSE 条件分支
表格行级别操作
完整日志和截图

这样才能适应你截图里的这种复杂业务页面，也方便后面扩展更多工单和合同流程。

10:15 AM

但是这个项目还需要进行跨应用操作。 并且项目需要可以读取一个excel中的某一列的数据，需要有一个预览和记忆界面。 现在你帮我理清我的项目需求，我准备进行开发。

10:18 AM

GPT-5.5


下面我帮你把这个项目需求重新整理成一份可开发的需求说明草案。你可以把它当成后续立项、开发排期、技术选型和原型设计的基础。

一、项目定位
这个项目本质上不是一个简单的“鼠标连点器”，而是一个面向 Windows 桌面环境的：

跨应用 RPA 自动化执行工具

它需要能够：

录制用户在 Windows 上的鼠标、键盘操作；
回放这些操作；
在多个应用之间切换并执行动作；
读取 Excel 中指定列的数据；
根据页面、表格、文字、合同类型等信息进行条件判断；
提供操作流程预览界面；
记忆用户配置、历史流程、历史执行记录；
支持半自动或自动执行业务流程。
二、核心使用场景
根据你目前描述，你的典型业务场景大概是：

用户准备一个 Excel 文件；
Excel 中包含多个待处理对象，例如：
工单编号；
用户编号；
用户名称；
合同类型；
地址；
日期；
金额；
其他业务字段；
程序读取 Excel 中指定列或多列；
用户在软件界面中预览读取结果；
用户选择要执行的数据行；
程序启动自动化流程；
程序跨应用操作，例如：
浏览器中的营销管理系统；
Excel；
Word；
PDF 阅读器；
文件资源管理器；
企业微信 / OA / 其他内部系统；
程序根据页面内容做条件判断；
程序完成点击、输入、复制、粘贴、保存、上传、下载等动作；
执行过程中记录日志和截图；
失败时允许人工介入或跳过当前任务；
执行完毕后生成执行结果。
三、项目目标
1. 第一目标
开发一个 Windows 桌面自动化工具，用于替代重复性的人工点击、输入、复制、粘贴、跨应用切换等操作。

2. 第二目标
支持从 Excel 读取批量数据，实现一条数据对应一次自动化流程。

3. 第三目标
支持流程预览、参数记忆、历史记录和执行日志，便于用户复用流程。

4. 第四目标
支持条件判断，例如：

text
如果合同类型 = 低压居民供用电合同
    执行流程 A
否则如果合同类型 = 本地费控协议
    执行流程 B
否则
    转人工处理

四、用户角色
项目初期可以先考虑一个角色：

操作员
负责：

选择 Excel；
配置读取哪一列；
预览数据；
选择流程；
启动执行；
暂停 / 继续 / 终止；
查看执行结果；
处理异常。
后期可以扩展：

管理员
负责：

创建流程模板；
管理用户权限；
管理执行日志；
配置系统参数。
五、功能需求总览
可以分为以下几个模块：

text
1. Excel 数据读取模块
2. 数据预览模块
3. 流程录制模块
4. 流程编辑模块
5. 自动执行模块
6. 跨应用控制模块
7. 条件判断模块
8. 记忆与配置模块
9. 日志与结果模块
10. 异常处理模块

六、功能模块详细说明
1. Excel 数据读取模块
目标
允许用户选择一个 Excel 文件，并读取其中指定工作表、指定列或指定范围的数据。

功能点
1.1 选择 Excel 文件
用户可以选择：

text
.xlsx
.xls
.csv

建议第一版优先支持：

text
.xlsx
.csv

1.2 选择 Sheet
如果 Excel 有多个工作表，软件需要展示：

text
Sheet1
Sheet2
合同数据
工单列表

用户可以选择其中一个。

1.3 识别表头
程序读取第一行作为表头，例如：

text
工单编号 | 用户编号 | 用户名称 | 合同类型 | 地址 | 起草时间 | 有效期

1.4 选择需要读取的列
用户可以选择：

读取单列；
读取多列；
指定某一列作为主键；
指定某一列作为循环处理字段。
例如：

text
读取列：用户编号
辅助列：用户名称、合同类型、起草时间

1.5 数据清洗
需要支持：

去除空行；
去除前后空格；
忽略重复数据；
空值提醒；
格式转换；
日期格式标准化。
1.6 数据变量化
Excel 每一行数据进入流程执行时，应转换为变量：

json
{
  "工单编号": "1526050610028032",
  "用户名称": "陈埃平",
  "用户编号": "026218800922",
  "合同类型": "低压居民供用电合同",
  "起草时间": "2026-05-14",
  "有效期": "12"
}

流程中可以使用：

text
${工单编号}
${用户名称}
${用户编号}
${合同类型}
${起草时间}
${有效期}

2. 数据预览模块
目标
用户读取 Excel 后，需要先看到数据，确认是否正确。

功能点
2.1 表格预览
界面展示 Excel 内容，例如：

勾选	序号	工单编号	用户编号	用户名称	合同类型	状态
✅	1	1526050610028032	026218800922	陈埃平	低压居民供用电合同	待执行
✅	2	1526050610028033	026218800923	张三	本地费控协议	待执行
2.2 选择执行范围
支持：

全部执行；
只执行勾选行；
从第 N 行开始执行；
执行前 N 条；
跳过已成功的记录；
只执行失败记录。
2.3 数据校验提示
例如：

text
第 3 行：用户编号为空
第 5 行：起草时间格式不正确
第 8 行：合同类型未识别

2.4 数据状态展示
每一行需要显示执行状态：

text
待执行
执行中
成功
失败
跳过
人工处理

3. 记忆界面 / 配置记忆模块
你提到需要“预览和记忆界面”，这里建议拆成两个概念：

text
预览界面：展示即将执行的数据和流程
记忆界面：保存用户常用配置，下次自动恢复

3.1 需要记忆的内容
Excel 相关记忆
text
上次打开的 Excel 路径
上次选择的 Sheet
上次选择的字段列
上次设置的主键列
上次数据清洗规则

流程相关记忆
text
上次选择的流程模板
流程参数配置
IF 条件配置
目标应用配置
浏览器路径
窗口标题关键字

执行相关记忆
text
执行速度
等待时间
失败重试次数
是否截图
是否跳过成功项
是否执行前确认

页面定位记忆
text
某个按钮的定位方式
某个输入框的定位方式
某个 OCR 区域
某个窗口标题
某个表格列位置

3.2 记忆界面建议
界面可以设计为：

text
配置名称：合同起草默认配置

Excel 文件：
D:\业务数据\合同起草列表.xlsx

Sheet：
合同数据

主键列：
用户编号

读取字段：
工单编号、用户编号、用户名称、合同类型、起草时间、有效期

执行流程：
合同起草自动化流程

目标应用：
Chrome - 新一代营销管理信息平台

执行策略：
失败重试 2 次
每步间隔 500ms
失败截图：开启
跳过已成功：开启

用户可以点击：

text
保存为配置
加载配置
另存为模板
删除配置
恢复默认

七、流程录制模块
目标
允许用户手动操作一次，程序记录操作步骤。

7.1 需要录制的内容
鼠标事件
text
移动
单击
双击
右键
拖拽
滚轮

键盘事件
text
按键
组合键
文本输入
复制
粘贴
回车
Tab

窗口事件
text
切换应用
激活窗口
最大化窗口
等待窗口出现

浏览器事件
text
点击网页元素
输入网页表单
读取网页文字
等待网页加载

7.2 录制结果不应该只是坐标
录制时建议保存三层定位信息：

json
{
  "type": "click",
  "target": {
    "app": "Chrome",
    "window_title": "新一代营销管理信息平台",
    "dom": {
      "text": "合同起草",
      "xpath": "//*[@id='xxx']/div[2]/span",
      "css": ".tab-title"
    },
    "image": {
      "template": "contract_tab.png"
    },
    "coordinate": {
      "x": 612,
      "y": 171
    }
  }
}

执行时优先级：

text
DOM 定位 > UIA 控件定位 > 图像识别 > OCR > 坐标点击

八、跨应用操作模块
这是你新补充的关键需求。

8.1 跨应用是什么意思
软件需要能够在多个 Windows 应用之间切换，例如：

text
浏览器
Excel
Word
PDF
文件资源管理器
企业微信
OA 系统
内网客户端
签章软件
打印预览窗口

8.2 跨应用能力列表
窗口管理
需要支持：

text
查找窗口
激活窗口
最大化窗口
最小化窗口
关闭窗口
等待窗口出现
判断窗口是否存在

例如：

yaml
- type: activate_window
  title_contains: "新一代营销管理信息平台"

应用启动
需要支持：

text
启动 Chrome
启动 Excel
启动某个 exe
打开某个文件
打开某个 URL

例如：

yaml
- type: open_app
  path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"

- type: open_url
  url: "http://xxx.xxx.xxx"

应用切换
例如：

yaml
- type: switch_window
  title_contains: "Excel"

- type: switch_window
  title_contains: "合同模板.docx"

剪贴板交互
很多跨应用操作推荐用剪贴板中转：

text
从 Excel 复制用户编号
切换到浏览器
粘贴到搜索框
点击查询

需要支持：

yaml
- type: set_clipboard
  value: "${用户编号}"

- type: hotkey
  keys: ["ctrl", "v"]

文件操作
需要支持：

text
选择文件
上传文件
下载文件
重命名文件
移动文件
复制文件
判断文件是否存在
等待下载完成

UIA 控件操作
对于 Windows 原生软件，建议使用 Windows UI Automation。

适合：

text
点击按钮
读取文本框
设置输入框
选择下拉框
读取窗口控件

技术可以用：

text
pywinauto
uiautomation
WinAppDriver

九、条件判断模块
9.1 条件来源
条件判断可以来自多个地方：

text
Excel 字段
网页文字
OCR 识别结果
窗口标题
文件是否存在
按钮是否存在
表格内容
执行结果

9.2 示例条件
根据 Excel 中的合同类型判断
yaml
- type: if
  condition: "${合同类型} contains '低压居民'"
  then:
    - type: run_subflow
      name: 低压居民合同流程
  else:
    - type: run_subflow
      name: 通用合同流程

根据网页表格中的合同类型判断
yaml
- type: read_web_table
  output: contracts

- type: if
  condition: "contracts[0].合同类型 contains '本地费控协议'"
  then:
    - type: click_table_action
      row: 0
      action: 预览

根据文件是否存在判断
yaml
- type: if
  condition: "file_exists('D:\\合同\\${用户编号}.pdf')"
  then:
    - type: upload_file
      path: "D:\\合同\\${用户编号}.pdf"
  else:
    - type: log
      message: "合同文件不存在"

根据窗口是否出现判断
yaml
- type: if
  condition: "window_exists('签章软件')"
  then:
    - type: activate_window
      title_contains: "签章软件"
  else:
    - type: open_app
      path: "D:\\SignTool\\SignTool.exe"

十、流程执行模块
10.1 执行方式
应该支持：

text
单条执行
批量执行
从选中行开始执行
失败重试
断点续跑
跳过成功项

10.2 执行逻辑
对于 Excel 中的每一行：

text
读取当前行数据
生成变量
启动流程
执行自动化步骤
记录结果
更新预览表格状态
失败则截图
继续下一行或停止

10.3 执行状态
每条数据有状态：

text
待执行
执行中
成功
失败
跳过
暂停
人工处理

每个步骤有状态：

text
未开始
执行中
成功
失败
重试中
已跳过

十一、异常处理模块
必须设计好异常处理，否则项目后期会很难用。

11.1 常见异常
text
找不到窗口
找不到按钮
页面加载超时
Excel 数据为空
合同类型无法识别
网页掉线
系统卡顿
弹窗遮挡
登录过期
文件不存在
上传失败
下载失败

11.2 异常处理策略
每个步骤都应该支持：

text
失败重试
等待后重试
截图
记录日志
跳过当前数据
暂停等待人工处理
终止全部任务
执行备用流程

例如：

yaml
on_error:
  retry: 2
  screenshot: true
  action: pause_for_manual

十二、日志与结果模块
12.1 执行日志
每次执行需要记录：

text
执行批次号
开始时间
结束时间
Excel 文件
Sheet
当前行号
工单编号
用户编号
用户名称
合同类型
执行结果
失败原因
截图路径
耗时

12.2 步骤日志
每一步记录：

text
步骤编号
步骤名称
动作类型
目标应用
目标窗口
输入值
执行状态
错误信息
截图
耗时

12.3 结果导出
支持导出：

text
执行结果 Excel
执行日志 CSV
失败清单
截图压缩包

结果 Excel 可以追加几列：

text
执行状态
执行时间
失败原因
截图路径
备注

十三、界面需求
建议第一版界面分成几个页面。

1. 首页 / 执行面板
显示：

text
选择配置
选择 Excel
选择流程
开始执行
暂停
继续
停止
当前状态
执行进度

2. Excel 数据预览页
显示：

text
Excel 路径
Sheet 选择
字段列选择
数据表格
数据校验结果
执行状态

按钮：

text
重新读取
保存配置
开始执行选中行
导出结果

3. 流程管理页
显示：

text
流程列表
新增流程
编辑流程
复制流程
删除流程
导入流程
导出流程

4. 流程编辑页
第一版可以不做复杂拖拽，先用表格形式：

序号	动作类型	目标	参数	等待	失败处理
1	激活窗口	Chrome	标题包含“营销平台”	1s	重试
2	输入文本	搜索框	${用户编号}	0.5s	停止
3	点击	查询	-	2s	重试
4	IF 判断	合同类型	包含“低压居民”	-	-
5. 录制页
功能：

text
开始录制
暂停录制
停止录制
显示已录制步骤
编辑步骤
删除步骤
保存为流程

录制时显示当前捕获到的动作：

text
[Chrome] 点击文本：合同起草
[Chrome] 点击表格第 3 行：修改
[键盘] 输入：${用户编号}
[窗口] 切换到 Excel

6. 记忆 / 配置页
显示：

text
配置名称
Excel 路径
Sheet
字段映射
流程模板
目标窗口
执行参数
OCR 区域
截图目录
日志目录

支持：

text
保存
加载
另存为
删除
设置默认

7. 日志页
显示：

text
执行批次
执行时间
成功数量
失败数量
失败原因
截图查看
导出日志

十四、数据结构建议
1. 配置文件
json
{
  "config_name": "合同起草默认配置",
  "excel": {
    "last_file": "D:\\数据\\合同数据.xlsx",
    "sheet": "合同数据",
    "header_row": 1,
    "primary_key": "用户编号",
    "selected_columns": [
      "工单编号",
      "用户编号",
      "用户名称",
      "合同类型",
      "起草时间",
      "有效期"
    ]
  },
  "flow": {
    "flow_id": "contract_draft_flow",
    "speed": "normal",
    "retry": 2,
    "screenshot_on_error": true
  },
  "window": {
    "browser_title": "新一代营销管理信息平台",
    "excel_title": "Excel"
  }
}

2. 流程文件
json
{
  "id": "contract_draft_flow",
  "name": "合同起草自动化流程",
  "steps": [
    {
      "id": "step_001",
      "type": "activate_window",
      "title_contains": "新一代营销管理信息平台"
    },
    {
      "id": "step_002",
      "type": "click_text",
      "text": "合同起草"
    },
    {
      "id": "step_003",
      "type": "input_text",
      "target": {
        "label": "用户编号"
      },
      "value": "${用户编号}"
    },
    {
      "id": "step_004",
      "type": "if",
      "condition": "${合同类型} contains '低压居民'",
      "then": [
        {
          "type": "run_subflow",
          "name": "低压居民流程"
        }
      ],
      "else": [
        {
          "type": "run_subflow",
          "name": "其他合同流程"
        }
      ]
    }
  ]
}

3. 执行记录
json
{
  "batch_id": "20260514_001",
  "excel_file": "D:\\数据\\合同数据.xlsx",
  "row_index": 3,
  "variables": {
    "工单编号": "1526050610028032",
    "用户编号": "026218800922",
    "用户名称": "陈埃平",
    "合同类型": "低压居民供用电合同"
  },
  "status": "failed",
  "error": "找不到修改按钮",
  "screenshot": "D:\\RPA\\logs\\20260514_001\\row_3_error.png",
  "started_at": "2026-05-14 09:30:00",
  "ended_at": "2026-05-14 09:31:20"
}

十五、技术方案建议
推荐技术栈
text
开发语言：Python
桌面界面：PySide6
浏览器自动化：Playwright
Windows 应用自动化：pywinauto / uiautomation
鼠标键盘控制：pynput / pyautogui
Excel 读取：openpyxl / pandas
OCR：PaddleOCR
图像识别：OpenCV
数据库：SQLite
配置格式：JSON / YAML
打包：PyInstaller
日志：loguru

为什么推荐 Python
因为你这个项目涉及：

text
Windows 自动化
Excel 读取
OCR
浏览器自动化
桌面软件控制
图像识别
脚本编排

Python 生态最合适，开发速度也快。

十六、自动化执行优先级
执行某个动作时，建议采用多策略：

text
1. 浏览器 DOM 定位
2. Windows UIA 控件定位
3. OCR 文字定位
4. 图像模板匹配
5. 坐标点击

这样跨应用时更稳定。

十七、第一版 MVP 范围建议
为了尽快开发出来，第一版建议只做这些。

MVP 必做
Excel
选择 Excel；
选择 Sheet；
选择指定列；
数据预览；
每行转变量；
执行状态展示。
流程
手动创建流程；
支持点击、输入、等待、热键、激活窗口；
支持 IF 判断；
支持变量替换；
支持从 Excel 行循环执行。
跨应用
激活窗口；
切换窗口；
键盘输入；
鼠标点击；
剪贴板粘贴；
打开文件；
打开浏览器 URL。
记忆
保存上次 Excel 路径；
保存字段映射；
保存流程选择；
保存目标窗口标题；
保存执行参数。
日志
成功 / 失败状态；
失败原因；
失败截图；
导出执行结果。
MVP 可暂缓
暂时不建议第一版就做：

复杂拖拽式流程设计器；
多用户权限；
云端调度；
AI 自动识别所有控件；
完全智能修复流程；
复杂图像模板管理；
大规模并发执行。
十八、建议的开发阶段
阶段 1：基础框架
目标：把软件壳子搭起来。

功能：

text
PySide6 主界面
SQLite 数据库
配置保存/读取
日志系统
项目目录结构

阶段 2：Excel 读取与预览
功能：

text
选择 Excel
读取 Sheet
选择列
表格预览
数据校验
保存字段映射

阶段 3：基础执行引擎
功能：

text
流程步骤模型
变量替换
点击
输入
等待
热键
激活窗口
执行日志

阶段 4：跨应用能力
功能：

text
窗口查找
窗口激活
应用启动
文件打开
剪贴板操作
UIA 控件识别

阶段 5：条件判断
功能：

text
IF / ELSE
变量条件
文本包含
窗口存在
文件存在
页面文字存在

阶段 6：浏览器增强
功能：

text
Playwright 接管浏览器
网页元素定位
网页表格读取
点击网页按钮
读取合同类型

阶段 7：录制功能
功能：

text
鼠标键盘录制
窗口切换录制
录制步骤展示
录制结果编辑
保存为流程

阶段 8：OCR / 图像识别
功能：

text
区域截图
OCR 识别
按文字点击
图像模板点击
OCR 区域记忆

十九、项目目录结构建议
text
rpa_assistant/
│
├── main.py
├── requirements.txt
│
├── app/
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── excel_preview_page.py
│   │   ├── flow_editor_page.py
│   │   ├── recorder_page.py
│   │   ├── config_page.py
│   │   └── log_page.py
│   │
│   ├── core/
│   │   ├── runner.py
│   │   ├── flow_engine.py
│   │   ├── condition_engine.py
│   │   ├── variable_engine.py
│   │   └── error_handler.py
│   │
│   ├── automation/
│   │   ├── browser.py
│   │   ├── windows.py
│   │   ├── mouse_keyboard.py
│   │   ├── clipboard.py
│   │   ├── ocr.py
│   │   └── image_match.py
│   │
│   ├── excel/
│   │   ├── reader.py
│   │   ├── validator.py
│   │   └── mapper.py
│   │
│   ├── storage/
│   │   ├── database.py
│   │   ├── config_repo.py
│   │   ├── flow_repo.py
│   │   └── log_repo.py
│   │
│   └── models/
│       ├── flow.py
│       ├── step.py
│       ├── config.py
│       └── execution.py
│
├── flows/
├── configs/
├── logs/
├── screenshots/
└── data/

二十、核心需求清单
你可以把下面这部分直接作为开发需求清单。

A. Excel 数据模块
 支持选择 Excel 文件；
 支持读取 .xlsx；
 支持选择 Sheet；
 支持识别表头；
 支持选择指定列；
 支持多列映射为变量；
 支持数据预览；
 支持空值校验；
 支持重复值校验；
 支持执行状态回写；
 支持导出执行结果。
B. 预览界面
 表格展示 Excel 数据；
 支持勾选执行行；
 支持搜索；
 支持筛选状态；
 支持显示校验错误；
 支持显示执行进度；
 支持单行重跑；
 支持失败行重跑。
C. 配置记忆模块
 记忆上次 Excel 路径；
 记忆上次 Sheet；
 记忆字段映射；
 记忆流程模板；
 记忆目标窗口；
 记忆执行速度；
 记忆失败重试次数；
 支持配置另存为；
 支持加载历史配置；
 支持删除配置。
D. 流程执行模块
 支持流程步骤模型；
 支持变量替换；
 支持点击；
 支持输入；
 支持等待；
 支持热键；
 支持剪贴板；
 支持应用启动；
 支持窗口激活；
 支持 IF 判断；
 支持子流程；
 支持失败重试；
 支持暂停 / 继续 / 停止。
E. 跨应用模块
 支持查找窗口；
 支持激活窗口；
 支持最大化窗口；
 支持切换应用；
 支持打开文件；
 支持打开程序；
 支持读写剪贴板；
 支持 Windows UIA 控件操作；
 支持鼠标键盘兜底操作。
F. 浏览器自动化模块
 支持接管浏览器；
 支持打开 URL；
 支持点击网页文本；
 支持输入网页表单；
 支持读取网页文本；
 支持读取网页表格；
 支持点击表格行内按钮；
 支持等待页面元素；
 支持 iframe 处理。
G. 条件判断模块
 支持变量判断；
 支持文本包含；
 支持等于 / 不等于；
 支持为空 / 非空；
 支持文件存在判断；
 支持窗口存在判断；
 支持页面文字存在判断；
 支持 OCR 结果判断；
 支持 IF / ELSE；
 支持多条件 AND / OR。
H. 录制模块
 支持鼠标点击录制；
 支持键盘输入录制；
 支持热键录制；
 支持窗口切换录制；
 支持录制步骤预览；
 支持编辑录制结果；
 支持保存为流程；
 支持坐标兜底；
 支持智能识别 DOM / UIA 目标。
I. OCR / 图像识别模块
 支持区域截图；
 支持 OCR 识别文字；
 支持按文字定位点击；
 支持图像模板匹配；
 支持 OCR 区域保存；
 支持识别结果用于 IF 判断。
J. 日志模块
 支持执行批次记录；
 支持每行数据执行结果；
 支持每个步骤执行日志；
 支持失败截图；
 支持导出日志；
 支持失败原因统计；
 支持断点续跑。
二十一、你这个项目的简化一句话需求
可以这样定义：

开发一个 Windows 桌面 RPA 工具，支持读取 Excel 数据并生成变量，提供数据预览和配置记忆功能，能够录制和执行跨应用鼠标键盘操作，并结合浏览器 DOM、Windows UIA、OCR 和坐标点击完成自动化流程，同时支持 IF 条件判断、批量执行、日志记录和失败处理。

二十二、我建议你第一版的最小闭环
第一版只要跑通这个闭环：

text
选择 Excel
↓
选择某一列作为变量
↓
预览数据
↓
选择流程
↓
程序逐行执行
↓
激活浏览器窗口
↓
输入当前行用户编号
↓
读取页面合同类型
↓
IF 判断
↓
执行对应点击/输入
↓
记录成功或失败
↓
继续下一行

只要这个闭环打通，你的项目就有了基础价值。

后面再慢慢加：

text
录制器
OCR
图像识别
复杂流程编辑器
多应用高级控制

---

## 本仓库应用（Anything Auto）本地运行

- 安装：在项目根目录执行 `pip install -r requirements.txt`；运行测试还需 `pip install -e ".[dev]"`（或单独安装 `pytest`）。
- 启动界面： `python main.py`。
- 可选浏览器步骤（流程类型 `pw_goto` / `pw_click_text`，经 Chrome DevTools CDP）：`pip install -e ".[browser]"`（或 `pip install playwright>=1.40`），再执行 `playwright install chromium`；默认 CDP 地址在配置中的 `browser_cdp_url`，也可在具体步骤的 `params.cdp_url` 中覆盖。
- Windows 与 macOS：通用桌面步骤用 `pyautogui`；`activate_window` 仅在 Windows 上生效。Excel 批量执行过程中可按「停止」——在当前数据行执行结束后、下一行开始前停止循环。
