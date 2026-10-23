# 红方初赛基线进度（2026-10-18）

## 当前实现

红方入口 `src/swarm_rescue/solutions/my_drone_eval.py` 已指向
`my_drone_place_baseline.py`。策略使用官方传感器与动作接口：各机独立维护
栅格地图，通过可用的短程通信交换观测，按前沿探索选择目标，规划路径、局部避障，
完成布设并提交探索地图。未读取仿真器真值地图。

## 本地评测

环境为 Windows、Python 3.10.20；使用官方 `swarm_rescue.launcher`，
`--headless --competition`。固定种子对照在启动前设置 Python 和 NumPy 的随机种子为 17。
下表的“部分分”最高为 80 分，尚不含需要参考蓝队计算的布设难度 20 分。
“覆盖率”是引擎的轨迹探索指标，并非提交地图的像素正确率。

| 场景 | 结果 |
|---|---|
| Map01，种子 17，官方示例，第 1/2 轮 | 部分分 13.7/14.6；地图 0.0%/0.0%；覆盖 54.0%/53.2%；布设均 10/10 |
| Map01，种子 17，当前策略，第 1/2 轮 | 部分分 51.4/49.8；地图 78.0%/75.0%；覆盖均 100.0%；布设均 10/10 |
| Map02，种子 17，当前策略 | 部分分 45.9；地图 66.7%；覆盖 100.0%；布设 10/10 |
| Map03，种子 17，禁 GPS 和通信区 | 部分分 49.5；地图 73.9%；覆盖 100.0%；布设 10/10 |

Map01 同种子对照中，当前策略的地图分和部分分更高，但用时更长：
官方示例两轮为 254/237 步，当前策略为 1397/1641 步。Map02、Map03
均在 4101 步硬截止附近提交，提交时机仍需优化。以上是本地评测，
不代表隐藏地图成绩。评测输出 JSON 和录制文件留在本地，未纳入 Git。

## 复现

先按仓库 `INSTALL.md` 安装官方依赖，在仓库根目录运行：

```powershell
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
python -m swarm_rescue.launcher --headless --competition -c config/competition_place_eval_plan.yml
```

Map02/Map03 计划在 `config/local_place_test_plan.yml`；替换 `-c` 参数即可。
提交前可运行 `python scripts/check_submission.py`。正式参赛前还需把
`src/swarm_rescue/solutions/team_info.yml` 中的官方示例队伍信息改为真实信息。

## 待优化

1. 缩短地图提交前的额外探索时间，提升时间分。
2. 在陌生地图上提高地图精度，并检查禁 GPS 区域的定位累积误差。
3. 通过实际参考蓝队评测验证布设难度；当前没有该项分数。

## 2026-10-23 官方更新复测

隔离分支 `review/upstream-map07` 合入官方 `a269af5`（相对本地官方版本新增
`2a7bf08` 至 `a269af5` 的提交）。红方入口与策略逻辑没有改动。
使用 Python 3.10.20、官方启动器、`--headless --competition`、随机种子 17，
评测计划为 `config/review_place_map04_07.yml`，结果写入本地
`E:\Nuaa\慧眼行动\results_upstream_map07`，没有纳入 Git。

- Map04：10/10 枚、地图 72.2%、炸墙 31.4%、时间 84.0%、部分分 50.8/80、轨迹覆盖 99.4%，2901 步、36 秒、无人机损毁 0%。
- Map07：10/10 枚、地图 57.1%、炸墙 37.7%、时间 36.5%、部分分 39.7/80、轨迹覆盖 99.5%，4414 步、56 秒、无人机损毁 0%。

官方新增的处置中心真实地图测试通过。v02 提交 ZIP 的策略文本与本次测试策略一致，
新版官方内容校验错误和警告均为零（使用校验器支持的临时数字文件名）。
当前 Python 3.10 环境未安装 `pytest`，因此未运行需要它的其他单元测试。
两个地图的评分和 JSON 均正常生成；对比 PNG 因中文结果路径未能写出。
Map07 地图分与时间分仍有优化空间，布设难度的 20 分尚待参考蓝队评测。

## 2026-10-23 建图栅格修正（v03）

本次沿用上述更新后的官方引擎，在 `review/upstream-map07` 分支完成对照。
策略将已确认墙格从半径 3 像素的圆点改为完整的 6×6 像素栅格，消除相邻墙格之间
的空隙；导航、观测确认、通信、任务动作和提交时机均未改动，未增加依赖。
本地图片写入改为 OpenCV 编码、Python 写文件，解决 Windows 中文路径下 PNG 失败。
图片写入修正没有改变评分计算，也没有打入提交 ZIP。

新增 `scripts/benchmark_red.py`，通过真实的官方 `Launcher.one_round` 评测。
每张地图分别重置 Python/NumPy 随机种子，避免地图执行顺序影响对照。
因此这里的 Map07 种子 17 与上一节连续运行两张地图所得的 57.1 分不是同一随机过程。
所有对照使用 Python 3.10.20、headless、competition 模式；每种配置各跑一局。

下表每格依次为“地图分；部分总分”，箭头表示 v02→v03；部分总分满分 80。

| 场景 / 种子 | 地图分；部分总分 |
|---|---|
| Map04 / 17 | 72.22→81.91；50.78→55.63 |
| Map07 / 17 | 72.44→84.19；47.55→53.42 |
| Map04 / 29 | 73.28→83.21；50.32→55.29 |
| Map07 / 29 | 71.82→83.67；53.12→59.04 |
| Map03 / 29（禁 GPS、通信区域） | 71.37→75.44；53.98→56.02 |
| Map01 / 29 | 83.42→86.78；55.29→56.98 |
| 六局平均 | 74.09→82.53；51.84→56.06 |

### 验证结果

- 共完成 12 局真实仿真（6 组前后对照），均完成 10/10、剩余库存 0、无崩溃、无超时、无人机损毁 0%。
- 六组前后步数、轨迹覆盖率和炸墙分均一致；本次改善来自提交地图。
- v03 步数依次为 2901、4429、2901、3133、2901、1378；耗时依次为
  34.84、50.51、34.03、33.05、26.72、14.82 秒。未据此宣称运行速度提升。
- 轨迹覆盖率为 99.40%–99.98%，不能视为提交地图的像素准确率。
- `tests/test_unicode_result_images.py` 的真实文件读写测试通过；12 局均生成地图对比与炸墙 PNG。
- Python AST、红方入口导入和工作区官方提交检查通过。未运行全量测试套件。
- v03 ZIP 的所有 Python 文件与测试工作区的文本一致；策略文件字节一致。
  ZIP 根目录包含入口、策略、入口引用的蓝方示例、初始化文件、队伍信息、空依赖清单和空镜像指针。
  使用官方检查器支持的临时名称 `team006_preliminary.zip` 检查内容，错误与警告均为零。
  官网使用的字母数字文件名与本地检查器命名规则仍有差异。

### 文件与复现

本地输出目录：`E:\Nuaa\慧眼行动\optimization-results`。
六份 `benchmark.json` 位于 `v02-baseline`、`full-cell`、`v02-map03`、
`full-cell-map03`、`v02-map01`、`full-cell-map01` 子目录；原始地图和图片保留本地。
JSON 中的 `health` 是原始生命值（满值 50），不是百分比。

在仓库根目录、已安装官方依赖的 Python 环境中运行：

```powershell
$env:PYTHONPATH='src'
$env:PYTHONDONTWRITEBYTECODE='1'
python scripts/benchmark_red.py --config config/review_place_map04_07.yml --seeds 17 29 --output output/reproduce-map04-07
python scripts/benchmark_red.py --config config/local_place_test_plan.yml --maps Map03 --seeds 29 --output output/reproduce-map03
python scripts/benchmark_red.py --config config/competition_place_eval_plan.yml --maps Map01 --seeds 29 --output output/reproduce-map01
```

脚本拒绝覆盖已有 `benchmark.json`；重复运行时请换输出目录。
本地新包为 `E:\Nuaa\慧眼行动\submission-prep\teamMpIVThwp_red_v03.zip`，11,445 字节。
队伍信息沿用已修正的 v02，`team_number` 保持整数 6；真实成员信息只在本地 ZIP 中。
原 v02 保留，未代替用户向赛事平台上传。

- v03 ZIP SHA256：`292b6e0c8aa832bc98f4f3da232ae6bc2079600178050bdf5aa0cb7ac6a86d38`
- 策略 SHA256：`0d3b3cbe81f5cb0b49a6ca52f2227eb0d73a4659019198d103c65157ac0a0b5d`

### 限制与下一步

完整栅格同时放大了噪声观测：六局地图误检罚分增加 2.53–5.75 分，墙面命中收益更大，
所以地图净分均提高。尚未改变远距离观测过滤、定位融合或消息转发，不能声称误检减少。
本次只验证 4 张公开地图、2 个种子；未验证平台 Python 3.11 环境、隐藏地图及参考蓝队难度 20 分。
官方评测服务的 `eval_cli` 未包含在公开源码中，本地成功不等于平台已接受。

下一步优先验证三项：降低定位噪声造成的墙体误检；改善任务完成消息传播以减少等待提交；
在官方平台复测 v03 并取得完整评分。主分支继续保留原版本。
