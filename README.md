# CCM - Carbon & CPU Monitor

**CCM** is a Python decorator that tracks **CPU usage**, estimates **energy consumption**, and **CO₂ emissions** during the execution of a Python function. It is designed for **Linux environments** and **does not depend on RAPL**.

## 🔧 Requirements

- Python 3.6+
- Linux operating system
- `psutil` installed:
  ```bash
  pip install psutil
  ```

## 🚀 How to Use

1. Clone the repo

2. Usage example:

   ```python
   tracker = Tracker(log_file="cpu_gpu_log.csv", gpu_id=0)

   @tracker.track_cpu_gpu
   def my_function():
      # Codice da eseguire
      pass

   my_function()

   ```

3. After execution, a CSV file is generated containing:
   - wall time,
   - average CPU usage,
   - energy used (Joules and Wh),
   - CO₂ emissions (kg and grams).

## 📄 CSV Output Format

| wall_time_sec | avg_cpu_percent | energy_joule | energy_wh | co2_eq_g | n_samples |
|---------------|------------------|--------------|------------|-----------|-----------|
| 5.02          | 32.5             | 10.1         | 0.0028     | 0.00078   | 11        |

## 📎 Customizable Parameters

- `log_file`: path to output CSV file
- `cpu_max_power_watt`: estimated max CPU power (default: 62 W)
- `emission_factor_italy`: CO₂ emission factor in Italy (kg/Wh) (default: 0.28)
- `sample_interval`: CPU usage sampling interval in seconds (default: 0.5)
