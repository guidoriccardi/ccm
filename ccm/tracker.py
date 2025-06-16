import os
import time
import psutil
import threading
import csv
from functools import wraps

CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

def get_process_cpu_time(process):
    times = process.cpu_times()
    return times.user + times.system

def get_total_cpu_time():
    with open("/proc/stat", "r") as f:
        line = f.readline()
    fields = [float(column) for column in line.strip().split()[1:]]
    return sum(fields) / CLK_TCK

def tracker_cpu(
    log_file="cpu_log_continuous.csv",
    cpu_max_power_watt=62,
    emission_factor_italy=0.28,
    sample_interval=0.5
):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            cpu_samples = []
            stop_flag = threading.Event()

            def sampler():
                while not stop_flag.is_set():
                    proc_time = get_process_cpu_time(process)
                    total_time = get_total_cpu_time()
                    timestamp = time.time()
                    cpu_samples.append((timestamp, proc_time, total_time))
                    time.sleep(sample_interval)

            thread = threading.Thread(target=sampler)
            thread.start()

            wall_start = time.time()
            result = func(*args, **kwargs)
            wall_end = time.time()

            stop_flag.set()
            thread.join()

            cpu_percents = []
            for i in range(1, len(cpu_samples)):
                t0, p0, sys0 = cpu_samples[i - 1]
                t1, p1, sys1 = cpu_samples[i]
                delta_proc = p1 - p0
                delta_sys = sys1 - sys0
                if delta_sys > 0:
                    cpu_percents.append((delta_proc / delta_sys) * 100)

            avg_cpu_percent = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0
            wall_time = wall_end - wall_start
            energy_joule = (cpu_max_power_watt * (avg_cpu_percent / 100)) * wall_time
            energy_wh = energy_joule / 3600
            co2_kg = energy_wh * emission_factor_italy
            co2_g = co2_kg * 1000

            os.makedirs(os.path.dirname(log_file), exist_ok=True)

            with open(log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_cpu_percent", "energy_joule", "energy_wh", "co2_eq_kg", "co2_eq_g", "n_samples"
                ])
                writer.writerow([
                    round(wall_time, 2), round(avg_cpu_percent, 2), round(energy_joule, 2),
                    round(energy_wh, 6), round(co2_kg, 6), round(co2_g, 2), len(cpu_samples)
                ])

            return result
        return wrapper
    return decorator
