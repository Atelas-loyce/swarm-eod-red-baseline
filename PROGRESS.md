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
