"""
可视化工具：绘制摆放结果
"""
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Polygon as MPLPolygon
import numpy as np
import warnings

# 配置中文字体
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'SimSun', 'KaiTi', 'FangSong']  # Windows中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 忽略字体警告（作为备用）
warnings.filterwarnings('ignore', category=UserWarning)


def visualize_placement(input_file: str, output_file: str, save_image: str = None):
    """可视化摆放结果"""
    # 读取输入和输出
    with open(input_file, 'r', encoding='utf-8') as f:
        input_data = json.load(f)
    
    with open(output_file, 'r', encoding='utf-8') as f:
        output_data = json.load(f)
    
    # 创建图形
    fig, ax = plt.subplots(figsize=(12, 10))
    
    # 绘制边界
    boundary = input_data['boundary']
    boundary_array = np.array(boundary)
    boundary_polygon = MPLPolygon(boundary_array, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(boundary_polygon)
    
    # 绘制门
    door = input_data['door']
    door_line = np.array(door)
    ax.plot(door_line[:, 0], door_line[:, 1], 'r-', linewidth=4, label='Door')
    
    # 如果是内开门，绘制门的禁区
    if input_data.get('isOpenInward', False):
        door_p1, door_p2 = door[0], door[1]
        door_width = np.sqrt((door_p2[0] - door_p1[0])**2 + (door_p2[1] - door_p1[1])**2)
        dx = door_p2[0] - door_p1[0]
        dy = door_p2[1] - door_p1[1]
        perp_x = -dy / door_width
        perp_y = dx / door_width
        
        door_zone_points = [
            door_p1,
            door_p2,
            (door_p2[0] + perp_x * door_width, door_p2[1] + perp_y * door_width),
            (door_p1[0] + perp_x * door_width, door_p1[1] + perp_y * door_width)
        ]
        door_zone = MPLPolygon(door_zone_points, fill=True, facecolor='red', 
                               alpha=0.2, edgecolor='red', linestyle='--')
        ax.add_patch(door_zone)
    
    # 颜色映射
    colors = {
        'fridge': '#FF6B6B',
        'iceMaker': '#4ECDC4',
        'shelf': '#45B7D1',
        'overShelf': '#FFA07A'
    }
    
    # 绘制摆放的物品
    if output_data['feasible']:
        for placement in output_data['placements']:
            item_name = placement['item']
            center = placement['center']
            rotation = placement['rotation']
            
            # 获取物品尺寸
            item_dims = input_data['algoToPlace'][item_name]
            length, width = item_dims[0], item_dims[1]
            
            # 确定颜色
            item_type = None
            for type_name in colors.keys():
                if item_name.startswith(type_name):
                    item_type = type_name
                    break
            color = colors.get(item_type, '#95E1D3')
            
            # 创建矩形
            if rotation == 0:
                rect_width, rect_height = length, width
            else:
                rect_width, rect_height = width, length
            
            rect = patches.Rectangle(
                (center[0] - rect_width/2, center[1] - rect_height/2),
                rect_width, rect_height,
                linewidth=2, edgecolor='black', facecolor=color, alpha=0.7
            )
            ax.add_patch(rect)
            
            # 添加标签
            ax.text(center[0], center[1], item_name, 
                   ha='center', va='center', fontsize=8, weight='bold')
            
            # 如果是冰箱，绘制开门边
            if item_type == 'fridge':
                door_clearance = width * 1.2
                if rotation == 0:
                    # 开门边在右侧
                    door_zone_points = [
                        (center[0] + length/2, center[1] - width/2),
                        (center[0] + length/2 + door_clearance, center[1] - width/2),
                        (center[0] + length/2 + door_clearance, center[1] + width/2),
                        (center[0] + length/2, center[1] + width/2)
                    ]
                else:
                    # 开门边在上侧
                    door_zone_points = [
                        (center[0] - length/2, center[1] + width/2),
                        (center[0] + length/2, center[1] + width/2),
                        (center[0] + length/2, center[1] + width/2 + door_clearance),
                        (center[0] - length/2, center[1] + width/2 + door_clearance)
                    ]
                
                fridge_door_zone = MPLPolygon(door_zone_points, fill=True, 
                                              facecolor='yellow', alpha=0.2, 
                                              edgecolor='orange', linestyle=':')
                ax.add_patch(fridge_door_zone)
    
    # 设置坐标轴
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    
    # 标题
    feasible_text = "可行" if output_data['feasible'] else "不可行"
    ax.set_title(f'物品摆放结果 - {feasible_text}', fontsize=14, weight='bold')
    
    # 图例
    legend_elements = [
        patches.Patch(facecolor=colors['fridge'], edgecolor='black', label='冰箱 (Fridge)'),
        patches.Patch(facecolor=colors['iceMaker'], edgecolor='black', label='制冰机 (Ice Maker)'),
        patches.Patch(facecolor=colors['shelf'], edgecolor='black', label='货架 (Shelf)'),
        patches.Patch(facecolor=colors['overShelf'], edgecolor='black', label='离地架 (Over Shelf)'),
        plt.Line2D([0], [0], color='red', linewidth=4, label='门 (Door)')
    ]
    ax.legend(handles=legend_elements, loc='upper right')
    
    plt.tight_layout()
    
    # 保存或显示
    if save_image:
        plt.savefig(save_image, dpi=150, bbox_inches='tight')
        print(f"图像已保存到: {save_image}")
    else:
        plt.show()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 2:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        save_image = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        # 默认测试
        input_file = "example1.json"
        output_file = "output1.json"
        save_image = "result1.png"
    
    visualize_placement(input_file, output_file, save_image)
