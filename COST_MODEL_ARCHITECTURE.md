# Cost Model Architecture Diagram

```
                                newRoller Cost Model System
                                ===========================

┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                Construction Policies                                │
│                          (Select optimal tile configurations)                      │
└──────────────────────────────┬──────────────────────────────────────────────────────┘
                               │ calls
                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────┐
│                                 CostModelBase                                      │
│                                (Abstract Interface)                                │
│                                                                                     │
│  • compute_estimate(schedule, tile_tensor)                                        │
│  • memory_estimate(schedule, mem_level, tile_tensor)                              │
│  • Theoretical_Perf(schedule, pure_memory, tile_tensor)                           │
└──────────────────────────┬─────────────────────────────┬────────────────────────────┘
                           │                             │
                   implements │                   implements │
                           ▼                             ▼
┌─────────────────────────────────────┐    ┌─────────────────────────────────────────┐
│         SimpleCostModel            │    │        WarpBasedCostModel               │
│                                    │    │                                         │
│  Characteristics:                  │    │  Characteristics:                       │
│  • Basic alignment penalties       │    │  • Profiled warp-level performance      │
│  • Peak performance assumptions    │    │  • Bank conflict modeling               │
│  • Fast estimation                │    │  • Database-driven accuracy            │
│  • Good for initial screening     │    │  • Complex scheduling analysis         │
│                                    │    │                                         │
│  Methods:                          │    │  Methods:                               │
│  • _align(x, unit_size)           │    │  • tile_size(dim_list)                 │
│  • _num_tiles(large, small)       │    │  • num_tiles(large_tile, base_tile)    │
│  • _fused_inner_axis(...)         │    │  • block_warps_num(reg, smem)          │
│  • compute_estimate(...)          │    │  • get_glbmem_bandwidth(...)           │
│  • memory_estimate(...)           │    │  • get_compute_peak_performance(...)    │
└─────────────────────────────────────┘    │  • get_smem_bandwidth(...)             │
                                           │  • compute_estimate(...)               │
                                           │  • memory_estimate(...)                │
                                           └─────────────────────────────────────────┘
                                                                │
                                                        uses    │
                                                                ▼
                                           ┌─────────────────────────────────────────┐
                                           │           Supporting Modules             │
                                           │                                         │
                                           │  glbmem.py:                            │
                                           │  • DRAM_latency(...)                   │
                                           │  • Transaction alignment               │
                                           │  • Warp access patterns               │
                                           │                                         │
                                           │  bcp.py:                               │
                                           │  • Bank_Conflict_Penalty(...)          │
                                           │  • Shared memory bank analysis         │
                                           │  • Address pattern modeling            │
                                           └─────────────────────────────────────────┘

                    Data Flow and Dependencies
                    ==========================

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Architecture  │    │   Operation     │    │    Schedule     │
│   Parameters    │    │   Definition    │    │  (Tile Config)  │
│                 │    │                 │    │                 │
│ • Peak FLOPS    │    │ • Tensor dims   │    │ • SMEM tiles    │
│ • Bandwidth     │    │ • Data types    │    │ • REG tiles     │
│ • Warp size     │    │ • Workload      │    │ • Reduction     │
│ • Bank config   │    │ • Dependencies  │    │   parameters    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │     Cost Estimation     │
                    │                         │
                    │  Compute Latency:       │
                    │  workload / throughput  │
                    │                         │
                    │  Memory Latency:        │
                    │  bytes / bandwidth      │
                    │                         │
                    │  Total Latency:         │
                    │  max(compute, memory)   │
                    └─────────────────────────┘

                        Memory Hierarchy
                        ================

Level 0: Global Memory (DRAM)
┌─────────────────────────────────────────────────────────────┐
│ Capacity: ~16-80 GB                                         │
│ Bandwidth: ~750 GB/s                                        │
│ Latency: ~400-600 cycles                                    │
│ Transaction: 32-128 bytes                                   │
│                                                             │
│ Cost Factors:                                               │
│ • Transaction alignment                                     │
│ • Memory coalescing                                         │
│ • Warp access patterns                                      │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
Level 1: Shared Memory (SMEM)
┌─────────────────────────────────────────────────────────────┐
│ Capacity: ~96 KB per SM                                     │
│ Bandwidth: ~12 TB/s                                         │
│ Latency: ~20-30 cycles                                      │
│ Transaction: 4-128 bytes                                    │
│                                                             │
│ Cost Factors:                                               │
│ • Bank conflicts                                            │
│ • Access patterns                                           │
│ • Thread synchronization                                    │
└─────────────────────────────────────────────────────────────┘
                                │
                                ▼
Level 2: Register File (REG)
┌─────────────────────────────────────────────────────────────┐
│ Capacity: ~256 KB per SM                                    │
│ Bandwidth: ~20+ TB/s                                        │
│ Latency: 1-2 cycles                                         │
│ Transaction: 4 bytes                                        │
│                                                             │
│ Cost Factors:                                               │
│ • Register pressure                                         │
│ • Thread occupancy                                          │
│ • Instruction scheduling                                    │
└─────────────────────────────────────────────────────────────┘
```

## Usage Example Flow

1. **Initialize**: Create cost model with operation and architecture
2. **Configure**: Set up tiling schedule with memory hierarchy levels  
3. **Estimate**: Call cost model methods to get performance predictions
4. **Optimize**: Use estimates to select best configuration
5. **Validate**: (Optional) Compare with actual execution time

```python
# Example workflow
arch = V100()
op = MatMulOp(...)
cost_model = WarpBasedCostModel(op, arch)

schedule = Schedule(...)
schedule.add_tile(0, [128, 128])  # SMEM
schedule.add_tile(1, [8, 8])      # REG

total_time = cost_model.Theoretical_Perf(schedule)
```