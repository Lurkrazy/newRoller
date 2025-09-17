# Cost Model Guide for newRoller

This guide provides a comprehensive overview of the cost model system in newRoller, which is used to estimate the performance of tensor operations under different tiling configurations.

## Overview

The cost model system is responsible for predicting the execution time of tensor kernels without actually running them on hardware. This enables rapid exploration of different optimization strategies during the compilation process.

## Architecture

### Base Class: CostModelBase

Located in `cost_model/CostModelBase.py`, this abstract base class defines the interface that all cost models must implement:

```python
class CostModelBase:
    def compute_estimate(self, schedule, tile_tensor="output"):
        # Estimate compute latency
        raise NotImplementedError
    
    def memory_estimate(self, schedule, mem_level, tile_tensor="output"):
        # Estimate memory latency for a given memory level
        raise NotImplementedError
    
    def Theoretical_Perf(self, schedule, pure_memory=False, tile_tensor="output"):
        # Calculate theoretical performance as max of compute and memory latencies
        pass
```

### Key Methods

1. **`compute_estimate()`**: Estimates the time spent on computation (FLOPS)
2. **`memory_estimate()`**: Estimates the time spent on data movement at different memory hierarchy levels
3. **`Theoretical_Perf()`**: Returns the bottleneck latency (max of compute and all memory levels)

## Concrete Implementations

### 1. SimpleCostModel

Located in `cost_model/SimpleCostModel.py`, this provides a basic cost estimation model:

**Features:**
- Assumes peak FLOPS can be achieved if properly aligned
- Estimates penalties due to non-aligned warps and memory transactions
- Does not consider bank conflicts in detail

**Key Calculations:**
- **Compute Latency**: `(workload * penalty) / peak_throughput`
- **Memory Latency**: `(bytes_transferred * alignment_penalty) / bandwidth`

**Example Usage:**
```python
from cost_model import SimpleCostModel
from arch.V100 import V100
from op import MatMulOp

# Initialize
arch = V100()
op = MatMulOp(...)
cost_model = SimpleCostModel(op, arch)

# Estimate performance for a schedule
compute_time = cost_model.compute_estimate(schedule)
memory_time = cost_model.memory_estimate(schedule, mem_level=0)  # DRAM
total_time = cost_model.Theoretical_Perf(schedule)
```

### 2. WarpBasedCostModel

Located in `cost_model/WarpBasedCostModel.py`, this is a more sophisticated model:

**Features:**
- Uses profiled warp-level performance data
- Considers different scheduling strategies (warp vs active block scheduling)
- Incorporates bank conflict penalties for shared memory
- Handles small parallelism cases with database lookups

**Key Components:**
- **Compute Estimation**: Uses profiled single-warp FLOPS and scales based on parallelism
- **Memory Estimation**: Considers transaction alignment, bank conflicts, and scheduling units
- **Database Integration**: Uses performance databases for accurate small-scale predictions

**Example Usage:**
```python
from cost_model import WarpBasedCostModel

cost_model = WarpBasedCostModel(op, arch)

# The model requires additional database information
schedule.compute_peak_performance = compute_db.lookup(...)
schedule.glbmem_bandwidth = cost_model.get_glbmem_bandwidth(schedule, small_glbmem_db)
schedule.smem_bandwidth = cost_model.get_smem_bandwidth(schedule)

# Estimate performance
total_time = cost_model.Theoretical_Perf(schedule)
```

## Memory Hierarchy Levels

The cost models work with different memory hierarchy levels:

- **Level 0**: Global Memory (DRAM)
- **Level 1**: Shared Memory (SMEM) 
- **Level 2**: Register File (REG)

Each level has different:
- Bandwidth characteristics
- Transaction sizes
- Capacity constraints
- Access patterns

## Supporting Modules

### Bank Conflict Penalty (bcp.py)

Calculates performance penalties due to shared memory bank conflicts:

```python
from cost_model.bcp import Bank_Conflict_Penalty

# Calculate bank conflict penalties for all tensors
penalties = Bank_Conflict_Penalty(schedule, tiling)
# Returns: {tensor_name: penalty_factor}
```

### Global Memory Latency (glbmem.py)

Specialized DRAM latency calculation considering:
- Transaction alignment
- Warp-level access patterns
- Memory coalescing efficiency

```python
from cost_model.glbmem import DRAM_latency

latency = DRAM_latency(
    op=op,
    bandwidth=750,  # GB/s
    transaction_size=32,  # bytes
    warp_size=32,
    reg_tile_dim=[8, 8],
    smem_tile_dim=[128, 128], 
    reduction_size={"k": 16}
)
```

## Integration with Policies

Cost models are primarily used by construction policies to evaluate and select optimal tile configurations:

```python
# In ConstructionPolicy.py
def emit_config_without_trails(self, topk):
    raw_configs = self.emit_raw_configs()
    perf_config = []
    
    for config in raw_configs:
        # Use cost model to evaluate theoretical performance
        theo_perf = self.cost_model.Theoretical_Perf(config)
        perf_config.append((theo_perf, config))
    
    # Sort by performance and return top-k
    perf_config.sort(key=lambda x: x[0])
    return [config for (_, config) in perf_config[:topk]]
```

## Performance Factors Considered

### Compute Performance
1. **Peak FLOPS**: Maximum theoretical compute throughput
2. **Warp Alignment**: Penalty for non-32-aligned thread blocks
3. **Scheduling Efficiency**: How well work is distributed across SMs
4. **Reduction Efficiency**: Impact of reduction operations

### Memory Performance  
1. **Transaction Alignment**: Penalty for non-aligned memory accesses
2. **Bank Conflicts**: Shared memory bank conflict penalties
3. **Coalescing**: Global memory access coalescing efficiency
4. **Bandwidth Utilization**: How effectively available bandwidth is used

## Architecture Dependencies

Cost models depend on architecture-specific parameters defined in classes like `V100`:

```python
# Example V100 parameters used by cost models
class V100(Arch):
    def __init__(self):
        self.bandwidth = [750, 12080]  # DRAM, SMEM bandwidth (GB/s)
        self.peak_flops = 12480        # Peak FLOPS (GFLOPS)
        self.warp_size = 32           # Warp size
        self.transaction_size = [32, 128]  # Transaction sizes (bytes)
        self.smem_bank_size = 4       # Bank size (bytes)
        self.bank_number = 32         # Number of banks
```

## Best Practices

1. **Choose the Right Model**: Use `SimpleCostModel` for quick estimates, `WarpBasedCostModel` for accuracy
2. **Database Integration**: For `WarpBasedCostModel`, ensure proper database initialization
3. **Architecture Matching**: Use cost models with matching architecture parameters
4. **Validation**: Compare estimates with actual execution times when possible
5. **Profiling**: Update databases with new profiling data for better accuracy

## Example: Complete Workflow

```python
from arch.V100 import V100
from cost_model import WarpBasedCostModel
from op import MatMulOp

# 1. Initialize components
arch = V100()
op = MatMulOp(shape=[1024, 1024, 1024], dtype="float")
cost_model = WarpBasedCostModel(op, arch)

# 2. Create schedule with tiling
schedule = Schedule(dim_size=2)
schedule.add_tile(0, [128, 128], {"k": 16})  # SMEM tile
schedule.add_tile(1, [8, 8], {"k": 16})      # REG tile

# 3. Add performance parameters (normally from databases)
schedule.compute_peak_performance = 14000  # GFLOPS
schedule.glbmem_bandwidth = 750           # GB/s  
schedule.smem_bandwidth = 12080           # GB/s

# 4. Estimate performance
compute_latency = cost_model.compute_estimate(schedule)
dram_latency = cost_model.memory_estimate(schedule, 0)
smem_latency = cost_model.memory_estimate(schedule, 1)
total_latency = cost_model.Theoretical_Perf(schedule)

print(f"Compute: {compute_latency:.2f} ns")
print(f"DRAM: {dram_latency:.2f} ns")  
print(f"SMEM: {smem_latency:.2f} ns")
print(f"Total (bottleneck): {total_latency:.2f} ns")
```

This cost model system enables newRoller to quickly evaluate thousands of potential optimizations and select the most promising ones for actual execution.