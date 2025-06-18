
# CCM - Carbon & CPU/GPU Monitor

**CCM** is a Python decorator that tracks **CPU usage**, **GPU power consumption**, estimates **energy consumption**, and **CO₂ emissions** during the execution of a Python function. It is designed for **Linux environments** and **does not depend on RAPL**.

## 🔧 Requirements

- Python 3.6+
- Linux operating system
- `psutil` and `subprocess` installed:
  ```bash
  pip install psutil
  ```

- `nvidia-smi` should be installed and accessible in the system's PATH for GPU monitoring.

## 🚀 How to Use

1. **Clone the repository** or copy the code into your project.

2. **Usage Example**:

   ```python
   from co2_tracker import Co2_Tracker

   # Initialize the tracker with the desired GPU ID (0 by default)
   tracker = Co2_Tracker(log_file="cpu_gpu_log.csv", gpu_id=0)

   @tracker.track_cpu_and_gpu
   def my_function():
      # Code to be executed while monitoring CPU and GPU usage
      time.sleep(10)  # Example workload

   my_function()
   ```

3. **After execution**, a CSV file will be generated containing:
   - **wall time** (total execution time),
   - **average CPU usage** (percentage),
   - **energy used** (Joules and Wh),
   - **CO₂ emissions** (grams and kilograms),
   - **average GPU power consumption** (Watts),
   - **samples collected** for both CPU and GPU.

## 📄 CSV Output Format

The CSV file generated will contain the following columns:

| wall_time_sec | avg_cpu_percent | avg_gpu_power | energy_joule_cpu | energy_wh_cpu | co2_eq_g_cpu | energy_joule_gpu | energy_wh_gpu | co2_eq_g_gpu | n_samples_cpu | n_samples_gpu |
|---------------|------------------|---------------|------------------|---------------|--------------|------------------|---------------|--------------|---------------|---------------|
| 5.02          | 32.5             | 85.0          | 10.1             | 0.0028        | 0.00078      | 2.1              | 0.00058       | 0.00016      | 11            | 15            |

## 📎 Customizable Parameters

- **`log_file`**: Path to the output CSV file (default: `"cpu_gpu_log_continuous.csv"`).
- **`gpu_id`**: The ID of the GPU to track (default: `0`).
- **`cpu_max_power_watt`**: Estimated maximum CPU power consumption in watts (default: `62 W`).
- **`emission_factor`**: CO₂ emission factor for Italy in kg per Wh (default: `0.00028`).
- **`sample_interval`**: The interval in seconds for sampling CPU and GPU power data (default: `0.5`).

## 🚀 How the Tracker Works

1. **CPU Monitoring**: Tracks the CPU usage using the `psutil` library. It calculates the average CPU usage percentage by comparing the process CPU time with the total system CPU time during the function execution.

2. **GPU Monitoring**: Uses `nvidia-smi` to query the GPU's power draw (in watts). The GPU power consumption is sampled at regular intervals and averaged over the course of the function execution.

3. **Energy and CO₂ Calculation**: The energy consumption for both the CPU and GPU is calculated based on the average power usage and execution time. CO₂ emissions are estimated using the given emission factor (kg/Wh).

## 📋 Example Output CSV

An example of the output CSV generated after the function execution could look like this:

```
wall_time_sec, avg_cpu_percent, avg_gpu_power, energy_joule_cpu, energy_wh_cpu, co2_eq_g_cpu, energy_joule_gpu, energy_wh_gpu, co2_eq_g_gpu, n_samples_cpu, n_samples_gpu
5.02, 32.5, 85.0, 10.1, 0.0028, 0.00078, 2.1, 0.00058, 0.00016, 11, 15
```

- **wall_time_sec**: Total time the function took to run (in seconds).
- **avg_cpu_percent**: The average CPU usage during the function execution (as a percentage).
- **avg_gpu_power**: The average GPU power consumption (in watts).
- **energy_joule_cpu**: The energy consumed by the CPU (in joules).
- **energy_wh_cpu**: The energy consumed by the CPU (in watt-hours).
- **co2_eq_g_cpu**: CO₂ equivalent emissions due to CPU power consumption (in grams).
- **energy_joule_gpu**: The energy consumed by the GPU (in joules).
- **energy_wh_gpu**: The energy consumed by the GPU (in watt-hours).
- **co2_eq_g_gpu**: CO₂ equivalent emissions due to GPU power consumption (in grams).
- **n_samples_cpu**: Number of CPU samples collected.
- **n_samples_gpu**: Number of GPU samples collected.

## 📌 Notes

- **GPU Monitoring**: The `nvidia-smi` command is required for GPU power consumption tracking. Ensure that your system has `nvidia-smi` available and your GPU is supported.
- **Power Consumption Estimation**: The power consumption of the CPU is estimated based on the `cpu_max_power_watt` parameter. This value is adjustable based on the CPU model and specifications.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
