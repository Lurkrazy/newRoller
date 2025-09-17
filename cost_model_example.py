#!/usr/bin/env python3
"""
Cost Model Example Script

This script demonstrates how to use the cost models in newRoller to estimate
the performance of different tiling configurations for tensor operations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from cost_model import SimpleCostModel, WarpBasedCostModel
    from arch.V100 import V100
    from config.sche import Schedule
    print("✓ Successfully imported cost model components")
    HAS_FULL_ENV = True
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Running in demonstration mode without full dependencies")
    HAS_FULL_ENV = False

def demonstrate_simple_cost_model():
    """Demonstrate basic usage of SimpleCostModel"""
    print("\n" + "="*60)
    print("SimpleCostModel Demonstration")
    print("="*60)
    
    if not HAS_FULL_ENV:
        print("Demo: Architecture parameters (V100 example)")
        print(f"Peak FLOPS: 12480 GFLOPS")
        print(f"Memory Bandwidth: DRAM=750 GB/s, SMEM=12080 GB/s")
        print("\nDemo: Simulated tiling configurations evaluation")
        print("-" * 80)
        print(f"{'Configuration':<15} {'SMEM Tile':<12} {'REG Tile':<12} {'Compute (ns)':<15} {'Memory (ns)':<15}")
        print("-" * 80)
        
        # Simulate some results
        configs = [
            {"name": "Small tiles", "smem": [128, 128], "reg": [8, 8], "compute": 245.2, "memory": 180.5},
            {"name": "Medium tiles", "smem": [256, 256], "reg": [16, 16], "compute": 156.8, "memory": 95.3},
            {"name": "Large tiles", "smem": [512, 512], "reg": [32, 32], "compute": 98.1, "memory": 52.7},
        ]
        
        for config in configs:
            print(f"{config['name']:<15} {str(config['smem']):<12} {str(config['reg']):<12} "
                  f"{config['compute']:<15.1f} {config['memory']:<15.1f}")
        return
    
    # Initialize architecture
    arch = V100()
    print(f"Architecture: V100")
    print(f"Peak FLOPS: {arch.peak_flops} GFLOPS")
    print(f"Memory Bandwidth: DRAM={arch.bandwidth[0]} GB/s, SMEM={arch.bandwidth[1]} GB/s")
    
    if not HAS_FULL_ENV:
        return
        
    # Create a simple mock operation for demonstration
    class MockOp:
        def __init__(self):
            self.dims = {"output": [1024, 1024]}
            
        def compute_workload(self, tile_dim, tile_tensor="output"):
            # Simple workload calculation for demo
            workload = 1
            for d in tile_dim:
                workload *= d
            return workload * 2  # 2 FLOPS per element (simplified)
            
        def memory_workload(self, tile_dim, tile_tensor, mem_level):
            # Simple memory workload for demo
            bytes_per_element = 4  # float32
            elements = 1
            for d in tile_dim:
                elements *= d
            return {"input_a": elements * bytes_per_element,
                   "input_b": elements * bytes_per_element,
                   "output": elements * bytes_per_element}
    
    op = MockOp()
    cost_model = SimpleCostModel(op, arch)
    
    # Create different tiling configurations
    configs = [
        {"smem": [128, 128], "reg": [8, 8], "name": "Small tiles"},
        {"smem": [256, 256], "reg": [16, 16], "name": "Medium tiles"},
        {"smem": [512, 512], "reg": [32, 32], "name": "Large tiles"},
    ]
    
    print(f"\nEvaluating {len(configs)} tiling configurations:")
    print("-" * 80)
    print(f"{'Configuration':<15} {'SMEM Tile':<12} {'REG Tile':<12} {'Compute (ns)':<15} {'Memory (ns)':<15}")
    print("-" * 80)
    
    if HAS_FULL_ENV:
        for config in configs:
            # Create schedule
            schedule = Schedule(dim_size=2)
            schedule.add_tile(0, config["smem"])  # SMEM level
            schedule.add_tile(1, config["reg"])   # REG level
            
            try:
                # Estimate performance
                compute_time = cost_model.compute_estimate(schedule)
                memory_time = cost_model.memory_estimate(schedule, 0)  # DRAM level
                
                print(f"{config['name']:<15} {str(config['smem']):<12} {str(config['reg']):<12} "
                      f"{compute_time:<15.2f} {memory_time:<15.2f}")
            except Exception as e:
                print(f"{config['name']:<15} {str(config['smem']):<12} {str(config['reg']):<12} "
                      f"{'ERROR':<15} {'ERROR':<15}")

def demonstrate_cost_model_comparison():
    """Compare different cost model approaches"""
    print("\n" + "="*60)
    print("Cost Model Comparison")
    print("="*60)
    
    print("Key differences between cost models:")
    print()
    
    print("SimpleCostModel:")
    print("  • Basic alignment penalty calculations")
    print("  • Assumes peak performance with penalties") 
    print("  • Fast estimation")
    print("  • Good for initial screening")
    print()
    
    print("WarpBasedCostModel:")
    print("  • Uses profiled warp-level performance")
    print("  • Considers bank conflicts and scheduling")
    print("  • Requires performance databases")
    print("  • More accurate but complex")
    print()

def show_cost_factors():
    """Show the factors that influence cost estimation"""
    print("\n" + "="*60)
    print("Performance Factors in Cost Models")
    print("="*60)
    
    factors = [
        ("Compute Factors", [
            "Peak FLOPS of the architecture",
            "Warp alignment (32-thread boundaries)",
            "Thread block scheduling efficiency",
            "Reduction operation complexity"
        ]),
        ("Memory Factors", [
            "Memory bandwidth at each hierarchy level",
            "Transaction alignment penalties",
            "Bank conflicts in shared memory",
            "Global memory coalescing efficiency",
            "Memory capacity constraints"
        ]),
        ("Architecture Factors", [
            "Number of streaming multiprocessors",
            "Warp schedulers per SM",
            "Memory transaction sizes",
            "Register file capacity"
        ])
    ]
    
    for category, items in factors:
        print(f"\n{category}:")
        for item in items:
            print(f"  • {item}")

def show_memory_hierarchy():
    """Explain the memory hierarchy levels"""
    print("\n" + "="*60)
    print("Memory Hierarchy in Cost Models")
    print("="*60)
    
    hierarchy = [
        ("Level 0: Global Memory (DRAM)", {
            "Capacity": "~16-80 GB",
            "Bandwidth": "~750 GB/s (V100)",
            "Latency": "~400-600 cycles",
            "Transaction": "32-128 bytes"
        }),
        ("Level 1: Shared Memory (SMEM)", {
            "Capacity": "~96 KB per SM",
            "Bandwidth": "~12 TB/s (V100)",  
            "Latency": "~20-30 cycles",
            "Transaction": "4-128 bytes"
        }),
        ("Level 2: Register File (REG)", {
            "Capacity": "~256 KB per SM",
            "Bandwidth": "~20+ TB/s",
            "Latency": "1-2 cycles", 
            "Transaction": "4 bytes"
        })
    ]
    
    for level, specs in hierarchy:
        print(f"\n{level}:")
        for spec, value in specs.items():
            print(f"  {spec:<12}: {value}")

def main():
    """Main demonstration function"""
    print("newRoller Cost Model Demonstration")
    print("=" * 60)
    print("This script shows how cost models estimate tensor operation performance")
    
    # Run demonstrations
    demonstrate_simple_cost_model()
    demonstrate_cost_model_comparison()
    show_cost_factors()
    show_memory_hierarchy()
    
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print("Cost models in newRoller provide fast performance estimates that enable:")
    print("  • Rapid exploration of optimization space")
    print("  • Selection of promising configurations")
    print("  • Avoiding expensive device execution during search")
    print("  • Architecture-aware optimization decisions")
    print()
    print("For more details, see COST_MODEL_GUIDE.md")

if __name__ == "__main__":
    main()