"""
批量运行所有示例
"""
import os
from placement_solver import solve_placement
from visualizer import visualize_placement


def run_all_examples():
    """运行所有示例文件"""
    examples = [
        ("example1.json", "output1.json", "result1.png"),
        ("example2.json", "output2.json", "result2.png"),
        ("example3.json", "output3.json", "result3.png"),
        ("example4.json", "output4.json", "result4.png"),
    ]
    
    print("=" * 60)
    print("开始批量处理示例")
    print("=" * 60)
    
    for input_file, output_file, image_file in examples:
        if not os.path.exists(input_file):
            print(f"\n跳过 {input_file} (文件不存在)")
            continue
        
        print(f"\n{'=' * 60}")
        print(f"处理: {input_file}")
        print(f"{'=' * 60}")
        
        try:
            # 求解
            result = solve_placement(input_file, output_file)
            
            # 可视化
            if result['feasible']:
                visualize_placement(input_file, output_file, image_file)
                print(f"✓ 成功生成可视化: {image_file}")
            else:
                print(f"✗ 摆放不可行，跳过可视化")
        
        except Exception as e:
            print(f"✗ 处理失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print(f"\n{'=' * 60}")
    print("批量处理完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_all_examples()
