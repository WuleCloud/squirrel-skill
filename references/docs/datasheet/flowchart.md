# Squirrel Test Framework Flowchart

```mermaid
flowchart TB
    subgraph "test-data-generator/"
        TD_MF["Makefile"]
        TD_MF --> |"make tvla"| TD_G1["generate.py tvla"]
        TD_MF --> |"make dtw"| TD_G2["generate.py dtw"]

        TD_G1 --> TD_TVLAGEN["src/generate_tvla_dataset.py"]
        TD_G2 --> TD_DTWGEN["src/generate_dtw_dataset.py"]

        TD_TVLAGEN --> TD_ZARR["src/zarr_datasets.py"]
        TD_DTWGEN --> TD_ZARR
    end

    subgraph "verify/tvla-test/"
        VT_MF["Makefile"]
        VT_MF --> VT_GEN["generate_tvla_dataset.py + add_leakage_regions"]
        VT_MF --> VT_ANALYZE["run_tvla_analysis"]
        VT_MF --> VT_VERIFY["verify_tvla"]
    end

    subgraph "verify/dtw-test/"
        DT_MF["Makefile"]
        DT_MF --> DT_GEN["generate_dtw_dataset.py"]
        DT_MF --> DT_ALIGN["align_dtw"]
        DT_MF --> DT_VERIFY["verify_dtw"]
    end

    subgraph "输出目录"
        TVLA_OUT["TVLA/traces/tvla_regions.zarr"]
        DTW_OUT["DWT/traces/dtw_test.zarr"]
    end

    TD_TVLAGEN --> TVLA_OUT
    TD_DTWGEN --> DTW_OUT
    VT_GEN --> TVLA_OUT
    DT_GEN --> DTW_OUT

    VT_ANALYZE --> VT_REPORT["result/tvla_report.json<br/>result/tvla_plot.png"]
    VT_VERIFY --> VT_RESULT["验证报告"]

    DT_ALIGN --> DT_ALIGNED["result/dtw_aligned.zarr"]
    DT_VERIFY --> DT_RESULT["验证报告"]

    style TD_MF fill:#e3f2fd
    style VT_MF fill:#e3f2fd
    style DT_MF fill:#e3f2fd
    style TD_TVLAGEN fill:#c8e6c9
    style TD_DTWGEN fill:#c8e6c9
    style VT_GEN fill:#c8e6c9
    style DT_GEN fill:#c8e6c9
    style VT_ANALYZE fill:#fff9c4
    style DT_ALIGN fill:#fff9c4
    style VT_VERIFY fill:#ffcdd2
    style DT_VERIFY fill:#ffcdd2
```

---

## 使用流程

### 数据生成
```bash
cd test-data-generator
make tvla   # → TVLA/traces/tvla_regions.zarr
make dtw    # → DWT/traces/dtw_test.zarr
```

### TVLA 测试
```bash
cd verify/tvla-test
make verify  # generate → analyze → verify
```

### DTW 测试
```bash
cd verify/dtw-test
make verify  # generate → align → verify
```