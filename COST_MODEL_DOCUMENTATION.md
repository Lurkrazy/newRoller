# ROLLER Cost Model Documentation

This document provides a comprehensive overview of the cost model implementation in the newRoller system.

## Overview

The newRoller system implements a sophisticated cost model for estimating the performance of tensor computation kernels. The cost model is crucial for the construction algorithm to evaluate different tiling strategies and select optimal configurations without actually executing kernels on the target hardware.

## Architecture

### Base Class: CostModelBase

Located in: `cost_model/CostModelBase.py`

The `CostModelBase` class defines the interface that all cost models must implement:

```python
class CostModelBase:
    def compute_estimate(self, schedule, tile_tensor="output"):
        # Estimate the latency of compute operations
        
    def memory_estimate(self, schedule, mem_level, tile_tensor="output"):
        # Estimate memory latency for a given memory level
        
    def Theoretical_Perf(self, schedule, pure_memory=False, tile_tensor="output"):
        # Calculate theoretical performance considering both compute and memory
```

### Cost Model Implementations

#### 1. SimpleCostModel

Located in: `cost_model/SimpleCostModel.py`

**Purpose**: A basic cost model implementation for initial estimation.

**Key Features**:
- Assumes peak FLOPS can be achieved
- Estimates penalties due to non-aligned warps
- Considers memory transaction alignment penalties
- Does not model bank conflicts

**Compute Estimation**:
- Calculates grid size and block size from tile dimensions
- Applies warp alignment penalties (32-thread warps)
- Estimates raw compute workload and applies throughput calculations

**Memory Estimation**:
- Models memory latency for different memory hierarchy levels
- Considers transaction alignment penalties
- Supports multiple memory levels (global, shared, register)

#### 2. WarpBasedCostModel (Primary Implementation)

Located in: `cost_model/WarpBasedCostModel.py`

**Purpose**: Advanced cost model based on profiled warp-level performance data.

**Key Features**:
- Uses profiled single-warp FLOPS data
- Scales performance estimates across tiling levels
- Integrates with performance databases
- Considers GPU architecture-specific scheduling

**Architecture-Aware Scheduling**:
- Supports warp-level and block-level scheduling strategies
- Considers SM (Streaming Multiprocessor) partitioning
- Models active block constraints per SM

**Database Integration**:
- `compute_peak_performance`: Looked up from compute database
- `glbmem_bandwidth`: Uses small global memory database for low parallelism
- `smem_bandwidth`: Estimates shared memory bandwidth considering bank conflicts
- `active_blocks_per_sm`: Database lookup for block occupancy

### Supporting Modules

#### Global Memory Latency (glbmem.py)

Located in: `cost_model/glbmem.py`

**Purpose**: Specialized functions for modeling global memory (DRAM) latency.

**Key Functions**:
- `DRAM_latency()`: Main function for calculating DRAM access latency
- `_align()`: Alignment calculations for memory transactions
- `_fuse_inner_axis()`: Calculates contiguous memory access patterns
- `_num_tiles()`: Tile count calculations

**Features**:
- Models memory coalescing effects
- Considers transaction size alignment
- Accounts for warp-level memory access patterns

#### Bank Conflict Penalty (bcp.py)

Located in: `cost_model/bcp.py`

**Purpose**: Models shared memory bank conflict penalties.

**Key Functions**:
- `Bank_Conflict_Penalty()`: Calculates bank conflict penalties
- `Area()`: Computes tile area for conflict analysis
- `Access_To_Delay()`: Empirical delay modeling for bank conflicts

## Integration with Construction Algorithm

The cost model is integrated into the ROLLER construction algorithm through:

1. **Policy Classes**: All construction policies instantiate `WarpBasedCostModel`
2. **Performance Evaluation**: Used to estimate kernel performance during tile selection
3. **Database Queries**: Integrates with profiled performance databases
4. **Scheduling Decisions**: Helps select optimal tiling configurations

### Usage in Construction Policies

Example from `Constrution.py`:
```python
self.cost_model = WarpBasedCostModel(op, arch)

# Performance estimation during construction
config.compute_peak_performance = self.cost_model.get_compute_peak_performance(config, self.compute_db)
config.glbmem_bandwidth = self.cost_model.get_glbmem_bandwidth(config, self.small_glbmem_db)
config.smem_bandwidth = self.cost_model.get_smem_bandwidth(config)
```

## Performance Estimation Process

1. **Tile Configuration**: Given a specific tiling strategy (schedule)
2. **Compute Estimation**: Calculate compute latency based on workload and peak performance
3. **Memory Estimation**: Estimate memory latency for each memory level
4. **Combined Performance**: Use `Theoretical_Perf()` to get the bottleneck (max of compute and memory)

## Architecture Support

The cost model supports various GPU architectures through the `arch` parameter:

- **Warp Size**: Configurable warp size (typically 32 for NVIDIA GPUs)
- **SM Partitioning**: Models streaming multiprocessor characteristics
- **Memory Hierarchy**: Supports multi-level memory (global, shared, register)
- **Block Scheduling**: Configurable block scheduling strategies

## Database Dependencies

The `WarpBasedCostModel` relies on several performance databases:

1. **Compute Database**: Profiled compute performance for different tile sizes
2. **Global Memory Database**: Bandwidth measurements for varying parallelism levels
3. **Active Block Database**: Block occupancy data for different configurations

## Key Strengths

1. **Accuracy**: Uses profiled data rather than theoretical estimates
2. **Architecture Awareness**: Considers GPU-specific characteristics
3. **Multi-Level Modeling**: Handles complex memory hierarchies
4. **Scalability**: Efficiently estimates performance without kernel execution

## Usage Guidelines

1. **Primary Model**: Use `WarpBasedCostModel` for production workloads
2. **Simple Model**: Use `SimpleCostModel` for basic estimation or debugging
3. **Database Setup**: Ensure performance databases are populated for target architecture
4. **Tile Validation**: Always validate tile eligibility before cost estimation

This cost model implementation is a key component that enables ROLLER's fast kernel construction approach, providing accurate performance estimates in seconds rather than hours required by search-based methods.