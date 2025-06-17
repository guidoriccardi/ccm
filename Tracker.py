import os
import time
import psutil
import threading
import csv
from functools import wraps
import subprocess

CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

class Tracker:
    def __init__(self, log_file="cpu_gpu_log_continuous.csv", gpu_id=0, cpu_max_power_watt=62, emission_factor_italy=0.00028, sample_interval=0.5):
        self.log_file = log_file
        self.gpu_id = gpu_id
        self.cpu_max_power_watt = cpu_max_power_watt
        self.emission_factor_italy = emission_factor_italy
        self.sample_interval = sample_interval

    # Funzione per monitorare la CPU
    def get_process_cpu_time(self, process):
        times = process.cpu_times()
        return times.user + times.system

    def get_total_cpu_time(self):
        with open("/proc/stat", "r") as f:
            line = f.readline()
        fields = [float(column) for column in line.strip().split()[1:]]
        return sum(fields) / CLK_TCK

    # Funzione per monitorare la GPU
    def get_gpu_info(self, gpu_id=0):
        try:
            cmd = f"nvidia-smi --id={gpu_id} --query-gpu=utilization.gpu,memory.used,memory.total,power.draw,temperature.gpu --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            utilization, memory_used, memory_total, power, temperature = map(float, result.split(', '))
            return utilization, memory_used, memory_total, power, temperature
        except subprocess.CalledProcessError:
            return None

    # Metodo per tracciare la CPU
    def track_cpu(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            cpu_samples = []
            stop_flag = threading.Event()

            def cpu_sampler():
                while not stop_flag.is_set():
                    proc_time = self.get_process_cpu_time(process)
                    total_time = self.get_total_cpu_time()
                    timestamp = time.time()
                    cpu_samples.append((timestamp, proc_time, total_time))
                    time.sleep(self.sample_interval)

            thread = threading.Thread(target=cpu_sampler)
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
            energy_joule = (self.cpu_max_power_watt * (avg_cpu_percent / 100)) * wall_time
            energy_wh = energy_joule / 3600
            co2_g = energy_wh * self.emission_factor_italy
            co2_g = co2_g * 1000

            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            with open(self.log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_cpu_percent", "energy_joule", "energy_wh", "co2_eq_g", "n_samples"
                ])
                writer.writerow([
                    round(wall_time, 2), round(avg_cpu_percent, 2), round(energy_joule, 2),
                    round(energy_wh, 6), round(co2_g, 6), len(cpu_samples)
                ])

            return result
        return wrapper

    # Metodo per tracciare la GPU
    def track_gpu(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            gpu_samples = []
            stop_flag = threading.Event()

            def gpu_sampler():
                while not stop_flag.is_set():
                    gpu_info = self.get_gpu_info(self.gpu_id)
                    if gpu_info:
                        timestamp = time.time()
                        gpu_samples.append((timestamp, *gpu_info))
                    time.sleep(self.sample_interval)

            thread = threading.Thread(target=gpu_sampler)
            thread.start()

            wall_start = time.time()
            result = func(*args, **kwargs)
            wall_end = time.time()

            stop_flag.set()
            thread.join()

            gpu_utilization_percents = []
            for i in range(1, len(gpu_samples)):
                t0, util0, mem_used0, mem_total0, power0, temp0 = gpu_samples[i - 1]
                t1, util1, mem_used1, mem_total1, power1, temp1 = gpu_samples[i]
                delta_util = util1 - util0
                if mem_total0 > 0:
                    gpu_utilization_percents.append(delta_util)

            avg_gpu_percent = sum(gpu_utilization_percents) / len(gpu_utilization_percents) if gpu_utilization_percents else 0.0

            wall_time = wall_end - wall_start
            energy_joule = (self.cpu_max_power_watt * (avg_gpu_percent / 100)) * wall_time  # Se vuoi calcolare energia simile alla CPU
            energy_wh = energy_joule / 3600
            co2_g = energy_wh * self.emission_factor_italy
            co2_g = co2_g * 1000

            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            with open(self.log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_gpu_percent", "energy_joule", "energy_wh", "co2_eq_g", "n_samples"
                ])
                writer.writerow([
                    round(wall_time, 2), round(avg_gpu_percent, 2), round(energy_joule, 2),
                    round(energy_wh, 6), round(co2_g, 6), len(gpu_samples)
                ])

            return result
        return wrapper

    # Metodo combinato per CPU e GPU
    def track_cpu_gpu(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            cpu_samples = []
            gpu_samples = []
            stop_flag = threading.Event()

            def cpu_sampler():
                while not stop_flag.is_set():
                    proc_time = self.get_process_cpu_time(process)
                    total_time = self.get_total_cpu_time()
                    timestamp = time.time()
                    cpu_samples.append((timestamp, proc_time, total_time))
                    time.sleep(self.sample_interval)

            def gpu_sampler():
                while not stop_flag.is_set():
                    gpu_info = self.get_gpu_info(self.gpu_id)
                    if gpu_info:
                        timestamp = time.time()
                        gpu_samples.append((timestamp, *gpu_info))
                    time.sleep(self.sample_interval)

            cpu_thread = threading.Thread(target=cpu_sampler)
            gpu_thread = threading.Thread(target=gpu_sampler)
            cpu_thread.start()
            gpu_thread.start()

            wall_start = time.time()
            result = func(*args, **kwargs)
            wall_end = time.time()

            stop_flag.set()
            cpu_thread.join()
            gpu_thread.join()

            cpu_percents = []
            for i in range(1, len(cpu_samples)):
                t0, p0, sys0 = cpu_samples[i - 1]
                t1, p1, sys1 = cpu_samples[i]
                delta_proc = p1 - p0
                delta_sys = sys1 - sys0
                if delta_sys > 0:
                    cpu_percents.append((delta_proc / delta_sys) * 100)

            avg_cpu_percent = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0

            gpu_utilization_percents = []
            for i in range(1, len(gpu_samples)):
                t0, util0, mem_used0, mem_total0, power0, temp0 = gpu_samples[i - 1]
                t1, util1, mem_used1, mem_total1, power1, temp1 = gpu_samples[i]
                delta_util = util1 - util0
                if mem_total0 > 0:
                    gpu_utilization_percents.append(delta_util)

            avg_gpu_percent = sum(gpu_utilization_percents) / len(gpu_utilization_percents) if gpu_utilization_percents else 0.0

            energy_joule_cpu = (self.cpu_max_power_watt * (avg_cpu_percent / 100)) * (wall_end - wall_start)
            energy_joule_gpu = sum([power * (wall_end - wall_start) for t, util, mem_used, mem_total, power, temp in gpu_samples]) / len(gpu_samples)
            energy_wh_cpu = energy_joule_cpu / 3600
            energy_wh_gpu = energy_joule_gpu / 3600
            co2_g_cpu = energy_wh_cpu * self.emission_factor_italy * 1000
            co2_g_gpu = energy_wh_gpu * self.emission_factor_italy * 1000

            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            with open(self.log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_cpu_percent", "avg_gpu_percent", 
                    "energy_joule_cpu", "energy_joule_gpu", 
                    "energy_wh_cpu", "energy_wh_gpu", 
                    "co2_eq_cpu_g", "co2_eq_gpu_g", "n_samples_cpu", "n_samples_gpu"
                ])
                writer.writerow([
                    round(wall_end - wall_start, 2), round(avg_cpu_percent, 2), round(avg_gpu_percent, 2),
                    round(energy_joule_cpu, 2), round(energy_joule_gpu, 2),
                    round(energy_wh_cpu, 6), round(energy_wh_gpu, 6),
                    round(co2_g_cpu, 6), round(co2_g_gpu, 6), len(cpu_samples), len(gpu_samples)
                ])

            return result
        return wrapper
