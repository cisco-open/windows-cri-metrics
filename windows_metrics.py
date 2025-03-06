# Copyright (c) 2022 Cisco Systems, Inc. and its affiliates
# All rights reserved.

# The license notice is:
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import winrm
import json
import time
from prometheus_client import start_http_server, Gauge
import metrics_logger
import config

# Gauges with labels for dynamic pod tracking
cpu_gauge = Gauge('pod_cpu_usage_mcores', 'CPU usage in mCores', ['node', 'pod'])
memory_gauge = Gauge('pod_memory_usage_mb', 'Memory usage in MB', ['node', 'pod'])
disk_gauge = Gauge('pod_disk_usage_mb', 'Disk usage in MB', ['node', 'pod'])
rx_gauge = Gauge('pod_rx_mb', 'Rx in Mb', ['node', 'pod'])
tx_gauge = Gauge('pod_tx_mb', 'Tx in Mb', ['node', 'pod'])

# Needed to infer stale/dead pods per server
active_pods_per_server = {}  


def get_servers():
    try:
        servers = []
        with open(f'{config.servers_file}', 'r') as serversfile:
            for server in serversfile:
                server = server.strip()
                # Ignore comment lines
                if not server or server.startswith("#"):
                    continue
                servers.append(server)

        get_pod_metrics(servers)

    except Exception as error:
        metrics_logger.logger.error(f"Error getting servers - {error}")


def get_pod_metrics(servers):
    for server in servers:
        try:
            # Configure the session
            session = winrm.Session(server, auth=(config.user, config.passwd), transport='ntlm')
            # PowerShell command to get JSON of pods
            stats = """crictl --runtime-endpoint=npipe:////./pipe/containerd-containerd statsp -o json"""
            # Inject the command
            r = session.run_ps(stats)
            # If command successful
            if r.status_code == 0:
                # Decode the blob and pass for processing
                decoded = r.std_out.decode('utf-8')
                json_data = json.loads(decoded)

                # If response empty
                if len(json_data["stats"]) == 0:
                    metrics_logger.logger.info(f"No pods on {server}")
                    process_metrics([], server)  # Ensure stale metrics are cleaned up
                else:
                    process_metrics(json_data["stats"], server)
            else:
                metrics_logger.logger.error(f"Improper PowerShell response from {server}")

        except Exception as error:
            metrics_logger.logger.error(f"Error getting pod metrics on {server} - {error}")
            continue


def process_metrics(pod_stats, server):
    global active_pods_per_server

    # track currently active pods for this server
    new_active_pods = set()

    try:
        for pod in pod_stats:
            metadata = pod["attributes"]["metadata"]
            pod_name = metadata["name"]

            # Use .get() to safely access the "windows" data
            windows_data = pod.get("windows", None)

            if windows_data is not None:
                # CPU (convert nanoCores to millicores)
                cpu = int(windows_data.get("cpu", {}).get("usageNanoCores", {}).get("value", 0)) // 1000

                # Memory MB
                memory = int(windows_data.get("memory", {}).get("workingSetBytes", {}).get("value", 0)) // (1024 * 1024)

                # Disk MB (sum container writable layer usage)
                disk = sum(
                    int(container.get("writableLayer", {}).get("usedBytes", {}).get("value", 0)) // (1024 * 1024)
                    for container in windows_data.get("containers", [])
                )

                # Get network Mb
                network = windows_data.get("network", {}).get("defaultInterface", {})
                rx = (int(network.get("rxBytes", {}).get("value", 0)) * 8) // (1024 * 1024)
                tx = (int(network.get("txBytes", {}).get("value", 0)) * 8) // (1024 * 1024)

                # Update Prometheus metrics
                cpu_gauge.labels(node=server, pod=pod_name).set(cpu)
                memory_gauge.labels(node=server, pod=pod_name).set(memory)
                disk_gauge.labels(node=server, pod=pod_name).set(disk)
                rx_gauge.labels(node=server, pod=pod_name).set(rx)
                tx_gauge.labels(node=server, pod=pod_name).set(tx)

                metrics_logger.logger.info(f"Updated metrics for {pod_name} on {server}, CPU = {cpu} mCores, memory = {memory} MB, disk = {disk} MB, tx = {tx} Mb, rx = {rx} Mb")

                # Track active pod
                new_active_pods.add(pod_name)

            else:
                metrics_logger.logger.warning(f"Windows data missing for pod: {pod_name}")

        # remove dead pods for this specific server
        stale_pods = active_pods_per_server.get(server, set()) - new_active_pods
        for pod in stale_pods:
            cpu_gauge.remove(server, pod)
            memory_gauge.remove(server, pod)
            disk_gauge.remove(server, pod)
            rx_gauge.remove(server, pod)
            tx_gauge.remove(server, pod)
            metrics_logger.logger.info(f"Removed stale metrics for {pod} on {server}")

        # update active_pods_per_server with the new set
        active_pods_per_server[server] = new_active_pods

    except Exception as error:
        metrics_logger.logger.error(f"Error processing metrics for {server} - {error}")


if __name__ == "__main__":
    start_http_server(8000)

    while True:
        get_servers()
        time.sleep(10)
