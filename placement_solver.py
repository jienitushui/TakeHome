"""
物体摆放算法核心实现
"""
import json
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from shapely.geometry import Polygon, Point, LineString, box
from shapely.ops import unary_union
import numpy as np


@dataclass
class Item:
    """物品类"""
    name: str
    length: float
    width: float
    item_type: str  # fridge, shelf, overShelf, iceMaker
    
    def get_area(self) -> float:
        return self.length * self.width


@dataclass
class Placement:
    """摆放位置"""
    item: Item
    center: Tuple[float, float]
    rotation: int  # 0 or 90
    
    def to_dict(self) -> dict:
        return {
            "item": self.item.name,
            "center": list(self.center),
            "rotation": self.rotation
        }


class PlacementSolver:
    """物体摆放求解器"""
    
    def __init__(self, boundary: List[Tuple[float, float]], 
                 door: List[Tuple[float, float]],
                 is_open_inward: bool,
                 items: Dict[str, List[float]]):
        self.boundary_points = boundary
        self.boundary_polygon = Polygon(boundary)
        self.door = door
        self.is_open_inward = is_open_inward
        self.items = self._parse_items(items)
        
        # 计算门的禁区
        self.door_restricted_zone = self._calculate_door_zone()
        
        # 提取墙面
        self.walls = self._extract_walls()
        
        # 已摆放的物品
        self.placements: List[Placement] = []
        self.placed_polygons: List[Polygon] = []
        
        # 冰箱开门边禁区
        self.fridge_zones: List[Polygon] = []
        
    def _parse_items(self, items_dict: Dict[str, List[float]]) -> List[Item]:
        """解析物品列表并排序"""
        items = []
        for name, dims in items_dict.items():
            # 识别物品类型
            if name.startswith("fridge"):
                item_type = "fridge"
            elif name.startswith("iceMaker"):
                item_type = "iceMaker"
            elif name.startswith("overShelf"):
                item_type = "overShelf"
            elif name.startswith("shelf"):
                item_type = "shelf"
            else:
                item_type = "unknown"
            
            items.append(Item(name, dims[0], dims[1], item_type))
        
        # 按优先级和面积排序
        priority = {"fridge": 0, "iceMaker": 1, "shelf": 2, "overShelf": 3, "unknown": 4}
        items.sort(key=lambda x: (priority.get(x.item_type, 4), -x.get_area()))
        
        return items
    
    def _calculate_door_zone(self) -> Optional[Polygon]:
        """计算门的禁区"""
        if not self.door or len(self.door) < 2:
            return None
        
        door_p1, door_p2 = self.door[0], self.door[1]
        door_width = math.sqrt((door_p2[0] - door_p1[0])**2 + (door_p2[1] - door_p1[1])**2)
        
        if self.is_open_inward:
            # 内开门：占据门宽度的正方形区域
            # 计算门的方向向量
            dx = door_p2[0] - door_p1[0]
            dy = door_p2[1] - door_p1[1]
            
            # 垂直向量（指向室内）
            perp_x = -dy / door_width
            perp_y = dx / door_width
            
            # 创建正方形禁区
            zone_points = [
                door_p1,
                door_p2,
                (door_p2[0] + perp_x * door_width, door_p2[1] + perp_y * door_width),
                (door_p1[0] + perp_x * door_width, door_p1[1] + perp_y * door_width)
            ]
            return Polygon(zone_points)
        else:
            # 外开门：门所在线段需要保持畅通，扩展一小段距离
            buffer_distance = 100  # 门前留出的空间
            door_line = LineString([door_p1, door_p2])
            return door_line.buffer(buffer_distance)
    
    def _extract_walls(self) -> List[LineString]:
        """提取墙面线段"""
        walls = []
        n = len(self.boundary_points)
        for i in range(n):
            p1 = self.boundary_points[i]
            p2 = self.boundary_points[(i + 1) % n]
            walls.append(LineString([p1, p2]))
        return walls
    
    def _create_rectangle(self, center: Tuple[float, float], 
                         length: float, width: float, 
                         rotation: int) -> Polygon:
        """创建旋转矩形"""
        cx, cy = center
        
        if rotation == 0:
            # 不旋转：length为x方向，width为y方向
            half_l, half_w = length / 2, width / 2
            points = [
                (cx - half_l, cy - half_w),
                (cx + half_l, cy - half_w),
                (cx + half_l, cy + half_w),
                (cx - half_l, cy + half_w)
            ]
        else:  # rotation == 90
            # 旋转90度：width为x方向，length为y方向
            half_l, half_w = length / 2, width / 2
            points = [
                (cx - half_w, cy - half_l),
                (cx + half_w, cy - half_l),
                (cx + half_w, cy + half_l),
                (cx - half_w, cy + half_l)
            ]
        
        return Polygon(points)
    
    def _is_valid_placement(self, center: Tuple[float, float], 
                           item: Item, rotation: int) -> bool:
        """检查摆放位置是否有效"""
        rect = self._create_rectangle(center, item.length, item.width, rotation)
        
        # 检查1：是否完全在边界内
        if not self.boundary_polygon.contains(rect):
            return False
        
        # 检查2：是否与门禁区重叠
        if self.door_restricted_zone and rect.intersects(self.door_restricted_zone):
            return False
        
        # 检查3：是否与已摆放物品重叠
        for placed_poly in self.placed_polygons:
            if rect.intersects(placed_poly):
                return False
        
        # 检查4：是否与冰箱开门边禁区重叠
        for fridge_zone in self.fridge_zones:
            if rect.intersects(fridge_zone):
                return False
        
        return True
    
    def _generate_wall_positions(self, wall: LineString, item: Item) -> List[Tuple[Tuple[float, float], int]]:
        """沿墙生成候选位置"""
        candidates = []
        
        # 获取墙的起点和终点
        coords = list(wall.coords)
        p1, p2 = coords[0], coords[1]
        
        # 计算墙的长度和方向
        wall_length = wall.length
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        
        # 判断墙的方向（水平或垂直）
        is_horizontal = abs(dy) < abs(dx)
        
        # 采样步长 - 更密集的采样
        step = min(100, wall_length / 20)
        step = max(step, 1)  # 确保步长至少为1，避免除零错误
        
        # 沿墙采样位置
        for dist in np.arange(0, wall_length, step):
            t = dist / wall_length
            wall_x = p1[0] + t * dx
            wall_y = p1[1] + t * dy
            
            # 计算垂直于墙的方向（指向室内）
            perp_x = -dy / wall_length
            perp_y = dx / wall_length
            
            # 尝试两种旋转方向
            for rotation in [0, 90]:
                if rotation == 0:
                    offset = item.width / 2
                    length_along_wall = item.length
                else:
                    offset = item.length / 2
                    length_along_wall = item.width
                
                # 确保物品不超出墙的范围
                if dist + length_along_wall / 2 > wall_length or dist - length_along_wall / 2 < 0:
                    continue
                
                # 物品中心位置（贴墙）
                center_x = wall_x + perp_x * offset
                center_y = wall_y + perp_y * offset
                
                candidates.append(((center_x, center_y), rotation))
        
        return candidates
    
    def _generate_interior_positions(self, item: Item) -> List[Tuple[Tuple[float, float], int]]:
        """生成内部候选位置（网格采样）"""
        candidates = []
        
        # 获取边界的包围盒
        minx, miny, maxx, maxy = self.boundary_polygon.bounds
        
        # 网格步长 - 更密集的采样以提高成功率
        step = 200
        
        for x in np.arange(minx, maxx, step):
            for y in np.arange(miny, maxy, step):
                # 检查点是否在多边形内
                if self.boundary_polygon.contains(Point(x, y)):
                    for rotation in [0, 90]:
                        candidates.append(((x, y), rotation))
        
        return candidates
    
    def _calculate_position_score(self, center: Tuple[float, float], 
                                  item: Item, rotation: int) -> float:
        """计算位置得分（贴墙优先）"""
        rect = self._create_rectangle(center, item.length, item.width, rotation)
        score = 0.0
        
        # 计算贴墙数量
        touching_walls = 0
        min_wall_distance = float('inf')
        
        for wall in self.walls:
            distance = rect.distance(wall)
            min_wall_distance = min(min_wall_distance, distance)
            
            if distance < 10:  # 容差范围内认为贴墙
                touching_walls += 1
        
        # 贴墙数量权重最高
        score += touching_walls * 10000
        
        # 距离墙越近越好
        score -= min_wall_distance
        
        return score
    
    def _calculate_fridge_door_zone(self, placement: Placement) -> Optional[Polygon]:
        """计算冰箱开门边禁区"""
        if placement.item.item_type != "fridge":
            return None
        
        cx, cy = placement.center
        length = placement.item.length
        width = placement.item.width
        rotation = placement.rotation
        
        # 假设length边为开门边，开门需要1.0倍width的空间（减少禁区以提高成功率）
        door_clearance = width * 1.0
        
        if rotation == 0:
            # 开门边在右侧
            zone_points = [
                (cx + length/2, cy - width/2),
                (cx + length/2 + door_clearance, cy - width/2),
                (cx + length/2 + door_clearance, cy + width/2),
                (cx + length/2, cy + width/2)
            ]
        else:  # rotation == 90
            # 开门边在上侧
            zone_points = [
                (cx - length/2, cy + width/2),
                (cx + length/2, cy + width/2),
                (cx + length/2, cy + width/2 + door_clearance),
                (cx - length/2, cy + width/2 + door_clearance)
            ]
        
        return Polygon(zone_points)
    
    def solve(self) -> Dict:
        """求解摆放方案"""
        for item in self.items:
            print(f"正在摆放: {item.name} ({item.length} x {item.width})")
            
            # 生成候选位置
            candidates = []
            
            # 优先尝试沿墙摆放
            for wall in self.walls:
                wall_candidates = self._generate_wall_positions(wall, item)
                candidates.extend(wall_candidates)
            
            # 总是尝试内部位置以增加候选方案
            interior_candidates = self._generate_interior_positions(item)
            candidates.extend(interior_candidates)
            
            # 筛选有效位置
            valid_positions = []
            for center, rotation in candidates:
                if self._is_valid_placement(center, item, rotation):
                    score = self._calculate_position_score(center, item, rotation)
                    valid_positions.append((score, center, rotation))
            
            # 如果没有有效位置，返回失败
            if not valid_positions:
                print(f"无法摆放 {item.name}")
                return {
                    "feasible": False,
                    "placements": [p.to_dict() for p in self.placements],
                    "message": f"无法摆放物品: {item.name}"
                }
            
            # 选择得分最高的位置
            valid_positions.sort(key=lambda x: x[0], reverse=True)
            best_score, best_center, best_rotation = valid_positions[0]
            
            # 创建摆放记录
            placement = Placement(item, best_center, best_rotation)
            self.placements.append(placement)
            
            # 添加到已摆放物品
            placed_rect = self._create_rectangle(best_center, item.length, item.width, best_rotation)
            self.placed_polygons.append(placed_rect)
            
            # 如果是冰箱，添加开门边禁区
            if item.item_type == "fridge":
                fridge_zone = self._calculate_fridge_door_zone(placement)
                if fridge_zone:
                    self.fridge_zones.append(fridge_zone)
            
            print(f"  ✓ 摆放在 {best_center}, 旋转 {best_rotation}°, 得分 {best_score:.2f}")
        
        return {
            "feasible": True,
            "placements": [p.to_dict() for p in self.placements]
        }


def solve_placement(input_file: str, output_file: str):
    """求解摆放问题"""
    # 读取输入
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 创建求解器
    solver = PlacementSolver(
        boundary=data['boundary'],
        door=data['door'],
        is_open_inward=data['isOpenInward'],
        items=data['algoToPlace']
    )
    
    # 求解
    result = solver.solve()
    
    # 保存结果
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\n结果已保存到: {output_file}")
    print(f"是否可行: {result['feasible']}")
    if result['feasible']:
        print(f"成功摆放 {len(result['placements'])} 个物品")
    
    return result


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "output.json"
    else:
        # 默认测试
        input_file = "example1.json"
        output_file = "output1.json"
    
    solve_placement(input_file, output_file)
