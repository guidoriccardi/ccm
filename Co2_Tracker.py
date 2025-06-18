import os
import time
import psutil
import threading
import csv
from functools import wraps
import subprocess

CLK_TCK = os.sysconf(os.sysconf_names['SC_CLK_TCK'])

class Co2_Tracker:
    def __init__(self, log_file="cpu_gpu_log_continuous.csv", gpu_id=0, cpu_max_power_watt=62, emission_factor=0.00028, sample_interval=0.5):
        self.log_file = log_file
        self.gpu_id = gpu_id
        self.cpu_max_power_watt = cpu_max_power_watt
        self.emission_factor = emission_factor
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
    # Ottiene informazioni sulla GPU utilizzando nvidia-smi.
    def get_gpu_info(self, gpu_id=0):
        """
        Ottiene informazioni sulla GPU utilizzando nvidia-smi.
        """
        try:
            # Esegui il comando nvidia-smi per raccogliere l'uso della GPU
            cmd = f"nvidia-smi --id={gpu_id} --query-gpu=power.draw --format=csv,noheader,nounits"
            result = subprocess.check_output(cmd, shell=True).decode('utf-8').strip()
            power = float(result)  # La potenza in watt
            return power
        except subprocess.CalledProcessError:
            print(f"Errore nel comando nvidia-smi per la GPU {gpu_id}")
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
            co2_g = energy_wh * self.emission_factor
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



    def track_gpu(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            gpu_samples = []
            stop_flag = threading.Event()

            def gpu_sampler():
                while not stop_flag.is_set():
                    power = self.get_gpu_info(self.gpu_id)
                    if power is not None:
                        timestamp = time.time()
                        gpu_samples.append((timestamp, power))
                    time.sleep(self.sample_interval)

            thread = threading.Thread(target=gpu_sampler)
            thread.start()

            wall_start = time.time()
            result = func(*args, **kwargs)
            wall_end = time.time()

            stop_flag.set()
            thread.join()

            # Calcolo della potenza media
            avg_gpu_power = 0.0
            if gpu_samples:
                total_power = sum([sample[1] for sample in gpu_samples])
                avg_gpu_power = total_power / len(gpu_samples)

            # Calcolo dell'energia consumata in Wh
            wall_time = wall_end - wall_start
            energy_joule = avg_gpu_power * wall_time  # Energia in joule (potenza media * tempo)
            energy_wh = energy_joule / 3600  # Conversione in wattora (Wh)

            # Calcolo delle emissioni di CO2
            co2_g = energy_wh * self.emission_factor * 1000  # Emissioni in grammi di CO2

            # Creazione della cartella di log se non esiste
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            # Scrittura dei dati nel file CSV
            with open(self.log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_gpu_power", "energy_joule", "energy_wh", "co2_eq_g", "n_samples"
                ])
                writer.writerow([
                    round(wall_time, 2), round(avg_gpu_power, 2), round(energy_joule, 2),
                    round(energy_wh, 6), round(co2_g, 6), len(gpu_samples)
                ])

            return result
        return wrapper
    
    # Metodo per tracciare sia CPU che GPU
    def track_cpu_and_gpu(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cpu_samples = []
            gpu_samples = []
            stop_flag = threading.Event()

            # Funzione per campionare i dati della CPU
            def cpu_sampler():
                while not stop_flag.is_set():
                    process = psutil.Process(os.getpid())
                    proc_time = self.get_process_cpu_time(process)
                    total_time = self.get_total_cpu_time()
                    timestamp = time.time()
                    cpu_samples.append((timestamp, proc_time, total_time))
                    time.sleep(self.sample_interval)

            # Funzione per campionare i dati della GPU
            def gpu_sampler():
                while not stop_flag.is_set():
                    power = self.get_gpu_info(self.gpu_id)
                    if power is not None:
                        timestamp = time.time()
                        gpu_samples.append((timestamp, power))
                    time.sleep(self.sample_interval)

            # Avvia i thread per CPU e GPU
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

            # Calcolo della potenza media della CPU
            cpu_percents = []
            for i in range(1, len(cpu_samples)):
                t0, p0, sys0 = cpu_samples[i - 1]
                t1, p1, sys1 = cpu_samples[i]
                delta_proc = p1 - p0
                delta_sys = sys1 - sys0
                if delta_sys > 0:
                    cpu_percents.append((delta_proc / delta_sys) * 100)

            avg_cpu_percent = sum(cpu_percents) / len(cpu_percents) if cpu_percents else 0.0

            # Calcolo della potenza media della GPU
            avg_gpu_power = 0.0
            if gpu_samples:
                total_power = sum([sample[1] for sample in gpu_samples])
                avg_gpu_power = total_power / len(gpu_samples)

            # Calcolo dell'energia consumata in Wh per la CPU e la GPU
            cpu_wall_time = wall_end - wall_start
            energy_joule_cpu = (self.cpu_max_power_watt * (avg_cpu_percent / 100)) * cpu_wall_time
            energy_wh_cpu = energy_joule_cpu / 3600  # Conversione in wattora (Wh)

            energy_joule_gpu = avg_gpu_power * cpu_wall_time  # Energia in joule per la GPU
            energy_wh_gpu = energy_joule_gpu / 3600  # Conversione in wattora (Wh)

            # Calcolo dele emissioni di CO2 per la CPU e la GPU
            co2_g_cpu = energy_wh_cpu * self.emission_factor * 1000
            co2_g_gpu = energy_wh_gpu * self.emission_factor * 1000

            # Calcolo delle emissioni totali di CO2 e dell'energia totale
            total_co2_g = co2_g_cpu + co2_g_gpu
            total_energy_wh = energy_wh_cpu + energy_wh_gpu
            total_energy_joule = energy_joule_cpu + energy_joule_gpu
            # Creazione della cartella di log se non esiste
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

            # Scrittura dei dati nel file CSV
            with open(self.log_file, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    "wall_time_sec", "avg_cpu_percent", "avg_gpu_power", "energy_joule_cpu", "energy_wh_cpu", "co2_eq_g_cpu",
                    "energy_joule_gpu", "energy_wh_gpu", "co2_eq_g_gpu", "total_wh","total_g_co2", "n_samples_cpu", "n_samples_gpu"
                ])
                writer.writerow([
                    round(wall_end - wall_start, 2), round(avg_cpu_percent, 2), round(avg_gpu_power, 2),
                    round(energy_joule_cpu, 2), round(energy_wh_cpu, 6), round(co2_g_cpu, 6),
                    round(energy_joule_gpu, 2), round(energy_wh_gpu, 6), round(co2_g_gpu, 6), round(total_energy_wh, 6),
                    round(total_co2_g, 6),
                    len(cpu_samples), len(gpu_samples)
                ])

            return result
        return wrapper