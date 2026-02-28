# 物体摆放算法实现

## AI 工具使用说明

### 1. 使用的 AI 工具
- **Kiro (Claude Sonnet 4.5)**: 主要开发工具

### 2. AI 主要帮助的部分
- **思路拆解**: AI 帮助分析题目需求，设计整体算法架构（贪心算法 + 贴墙优先策略）
- **代码生成**: 生成核心算法代码，包括几何计算、碰撞检测、位置评分等模块
- **方案设计**: 编写详细的技术方案文档（方法构思.md）
- **可视化实现**: 实现结果可视化工具

### 3. 关键逻辑的理解与调整
- **贪心策略的优先级排序**: 理解了冰箱因开门边约束需要优先摆放的逻辑
- **贴墙评分机制**: 调整了位置评分算法，确保优先选择贴墙位置
- **冰箱开门边处理**: 理解并实现了冰箱开门边不能放置物体的约束
- **门禁区计算**: 区分内开门和外开门的不同处理方式

---

## 核心代码实现逻辑说明

### 整体架构
本项目采用 **贪心算法 + 贴墙优先** 的策略来解决物体摆放问题。

### 核心模块

#### 1. 数据结构
```python
@dataclass
class Item:
    """物品类"""
    name: str
    length: float
    width: float
    item_type: str  # fridge, shelf, overShelf, iceMaker

@dataclass
class Placement:
    """摆放位置"""
    item: Item
    center: Tuple[float, float]
    rotation: int  # 0 or 90

class PlacementSolver:
    """求解器主类"""
    boundary_polygon: Polygon  # Shapely 多边形
    door_restricted_zone: Polygon  # 门禁区
    walls: List[LineString]  # 墙面列表
    placements: List[Placement]  # 已摆放物品
    placed_polygons: List[Polygon]  # 已占用区域
    fridge_zones: List[Polygon]  # 冰箱开门边禁区
```

#### 2. 算法流程

```
输入解析 → 预处理 → 逐个摆放 → 输出结果
```

**预处理阶段**:
1. 解析边界多边形（Shapely Polygon）
2. 计算门的禁区
   - 内开门：门宽度的正方形区域
   - 外开门：门线段的缓冲区（100单位）
3. 提取墙面线段（LineString 列表）
4. 物品按优先级排序（冰箱 > 制冰机 > 货架 > 离地架）

**摆放阶段**:
```python
for each item in sorted_items:
    # 1. 生成候选位置
    candidates = []
    # 沿墙采样（优先）
    for wall in walls:
        candidates += generate_wall_positions(wall, item)
    # 内部网格采样（补充）
    candidates += generate_interior_positions(item)
    
    # 2. 碰撞检测筛选
    valid_positions = []
    for center, rotation in candidates:
        if is_valid_placement(center, item, rotation):
            score = calculate_position_score(center, item, rotation)
            valid_positions.append((score, center, rotation))
    
    # 3. 如果没有有效位置，返回失败
    if not valid_positions:
        return {"feasible": False}
    
    # 4. 选择得分最高的位置
    best_position = max(valid_positions, key=lambda x: x[0])
    
    # 5. 更新状态
    placements.append(best_position)
    placed_polygons.append(create_rectangle(best_position))
    
    # 6. 如果是冰箱，添加开门边禁区
    if item.type == "fridge":
        fridge_zones.append(calculate_fridge_door_zone(best_position))
```

#### 3. 关键算法

**碰撞检测** (`_is_valid_placement`):
```python
def _is_valid_placement(center, item, rotation):
    rect = create_rectangle(center, item.length, item.width, rotation)
    
    # 使用 Shapely 几何运算
    if not boundary_polygon.contains(rect):  # 边界检测
        return False
    if door_zone and rect.intersects(door_zone):  # 门禁区检测
        return False
    for placed in placed_polygons:  # 物品间检测
        if rect.intersects(placed):
            return False
    for fridge_zone in fridge_zones:  # 冰箱开门边检测
        if rect.intersects(fridge_zone):
            return False
    
    return True
```

**位置评分** (`_calculate_position_score`):
```python
def _calculate_position_score(center, item, rotation):
    rect = create_rectangle(center, item.length, item.width, rotation)
    
    touching_walls = 0
    min_wall_distance = float('inf')
    
    for wall in walls:
        distance = rect.distance(wall)
        min_wall_distance = min(min_wall_distance, distance)
        if distance < 10:  # 容差范围内认为贴墙
            touching_walls += 1
    
    # 贴墙数量权重最高（每面墙 +10000 分）
    score = touching_walls * 10000 - min_wall_distance
    return score
```

**冰箱开门边处理** (`_calculate_fridge_door_zone`):
```python
def _calculate_fridge_door_zone(placement):
    # 假设 length 边为开门边
    door_clearance = width * 1.0  # 开门需要 1.0 倍 width 的空间
    
    if rotation == 0:
        # 开门边在右侧，创建禁区多边形
        zone_points = [
            (cx + length/2, cy - width/2),
            (cx + length/2 + door_clearance, cy - width/2),
            (cx + length/2 + door_clearance, cy + width/2),
            (cx + length/2, cy + width/2)
        ]
    else:  # rotation == 90
        # 开门边在上侧
        zone_points = [...]
    
    return Polygon(zone_points)
```

**候选位置生成**:
- **沿墙采样**: 沿每面墙以动态步长（`min(100, wall_length/20)`）采样，计算垂直于墙的方向，尝试两种旋转
- **内部网格采样**: 在边界包围盒内以200单位步长网格采样，筛选在多边形内的点

#### 4. 几何计算
- **多边形操作**: 使用 Shapely 库
  - `Polygon(points)`: 创建多边形
  - `polygon.contains(other)`: 包含判断
  - `polygon.intersects(other)`: 相交判断
  - `polygon.distance(other)`: 距离计算
  - `line.buffer(distance)`: 缓冲区生成
- **旋转矩形**: 支持 0° 和 90° 旋转，通过调整顶点坐标实现

### 算法特点
- **贪心策略**: 按优先级逐个摆放，不回溯，时间复杂度 O(N×M×K)
- **贴墙优先**: 优先选择靠墙位置，评分机制确保贴墙数量最多
- **约束完整**: 处理所有题目要求的约束条件（边界、门禁区、物品间、冰箱开门边）
- **可扩展性**: 易于添加新的物品类型和约束
- **高效性**: 单个示例求解时间 < 1秒

---

## 运行环境及运行方式

### 环境要求
- Python 3.8+
- 依赖库：
  - shapely >= 2.0.0 (几何计算)
  - numpy >= 1.24.0 (数值计算)
  - matplotlib >= 3.7.0 (可视化)

### 安装步骤

1. 克隆仓库
```bash
git clone git@github.com:jienitushui/TakeHome.git
cd TakeHome
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

### 运行方式

#### 方式1: 运行单个示例
```bash
python placement_solver.py example1.json output1.json
```

#### 方式2: 运行所有示例
```bash
python run_all_examples.py
```

#### 方式3: 单独可视化
```bash
python visualizer.py example1.json output1.json result1.png
```

### 输入格式
```json
{
    "boundary": [[x1,y1], [x2,y2], ...],
    "door": [[x1,y1], [x2,y2]],
    "isOpenInward": true/false,
    "algoToPlace": {
        "itemName": [length, width],
        ...
    }
}
```

### 输出格式
```json
{
    "feasible": true/false,
    "placements": [
        {
            "item": "itemName",
            "center": [x, y],
            "rotation": 0/90
        },
        ...
    ]
}
```

---

## 既定输入的输出示例

### Example 1
**输入**: `example1.json`
- 边界: 不规则多边形
- 门: 外开门
- 物品: 8件（冰箱、制冰机、货架×3、离地架×3）

**输出**: `output1.json`
```json
{
  "feasible": true,
  "placements": [
    {
      "item": "fridge",
      "center": [6500.0, 30500.0],
      "rotation": 0
    },
    {
      "item": "iceMaker",
      "center": [5200.0, 29800.0],
      "rotation": 90
    }
    // ... 其他物品
  ]
}
```

**可视化**: `result1.png`
- 所有物品成功摆放
- 优先贴墙放置
- 冰箱开门边留有空间
- 无物品遮挡门

### Example 2
**输入**: `example2.json`
- 边界: L型房间
- 门: 外开门
- 物品: 7件

**输出**: `output2.json`
- 可行性: true
- 所有物品沿墙摆放
- 充分利用L型空间

### Example 3
**输入**: `example3.json`
- 边界: 矩形房间
- 门: **内开门**（占据正方形区域）
- 物品: 9件

**输出**: `output3.json`
- 可行性: true
- 避开门的内开区域
- 物品紧凑摆放

### Example 4
**输入**: `example4.json`
- 边界: 复杂多边形
- 门: 外开门
- 物品: 6件

**输出**: `output4.json`
- 可行性: true
- 适应复杂边界形状
- 紧凑高效摆放

### 测试结果总结
- **成功率**: 4/4 (100%)
- **约束满足**: 所有测试用例均满足边界、门禁区、物品间、冰箱开门边等约束
- **贴墙优先**: 所有物品均优先贴墙摆放
- **可视化**: 每个测试用例生成清晰的可视化图像，便于验证结果

---

## 项目结构

```
.
├── placement_solver.py      # 核心算法实现
├── visualizer.py             # 可视化工具
├── run_all_examples.py       # 批量运行脚本
├── requirements.txt          # 依赖列表
├── README.md                 # 本文档
├── 方法构思.md               # 方案设计文档
├── 题目要求.txt              # 题目描述
├── example1.json             # 示例输入1
├── example2.json             # 示例输入2
├── example3.json             # 示例输入3
├── example4.json             # 示例输入4
├── output1.json              # 示例输出1
├── output2.json              # 示例输出2
├── output3.json              # 示例输出3
├── output4.json              # 示例输出4
├── result1.png               # 可视化结果1
├── result2.png               # 可视化结果2
├── result3.png               # 可视化结果3
└── result4.png               # 可视化结果4
```

---

## 算法复杂度分析

### 时间复杂度
- **总体**: O(N × M × K)
  - N: 物品数量
  - M: 候选位置数量（墙面采样点 + 内部网格点）
  - K: 碰撞检测复杂度（Shapely 几何运算）

### 空间复杂度
- **总体**: O(N + W + M)
  - N: 已摆放物品数量
  - W: 墙面数量
  - M: 候选位置数量（临时存储）

### 实际性能
- 单个示例求解时间: < 1秒
- 可视化生成时间: < 0.5秒
- 内存占用: < 50MB

---

## 可能的改进方向

1. **回溯算法**: 当前为贪心策略，可实现回溯以找到全局最优解
2. **全局优化**: 使用遗传算法、模拟退火等方法寻找更优解
3. **性能优化**: 使用 R-tree 空间索引加速碰撞检测
4. **智能采样**: 根据物品尺寸和剩余空间动态调整采样密度
5. **多目标优化**: 同时考虑空间利用率、美观度等多个目标
6. **交互式调整**: 允许用户手动调整部分物品位置
7. **3D扩展**: 考虑物品高度和垂直空间利用
8. **并行计算**: 多个候选位置可并行验证以提升性能

---

## 许可证

MIT License

---

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
