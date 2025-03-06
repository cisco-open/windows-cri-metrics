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


# docker build -t windows-cri-metrics -f Dockerfile .
#
# docker run -d -p 8000:8000 --name windows-cri-metrics -v $(pwd)/servers.txt:/home/metrics/servers.txt -e LOG_LEVEL=DEBUG -e USER="administrator" -e PASSWORD="XXXXX" -e SERVERS_FILE="/home/metrics/servers.txt" windows-cri-metrics
#

FROM python:3.11-alpine

LABEL org.opencontainers.image.authors="chdurbin@cisco.com"
LABEL org.opencontainers.image.title="Windows CRI metrics exporter v1.6"

RUN apk update && apk add python3 py3-pip bash

RUN python3 -m pip install --upgrade pip
ADD ./requirements.txt ./
RUN python3 -m pip install -r ./requirements.txt

COPY windows_metrics.py /usr/bin
COPY config.py /usr/bin
COPY metrics_logger.py /usr/bin

# metrics exposed
EXPOSE 8000

# Scan the container for vulns
RUN echo "scan for vulnerabilities"
RUN apk add curl \
    && curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/master/contrib/install.sh | sh -s -- -b /usr/local/bin \
    && trivy filesystem --exit-code 0 --no-progress /

# user and env
RUN adduser -h /home/metrics -s /bin/bash -D metrics
USER metrics
WORKDIR /home/metrics

ENTRYPOINT ["python3", "/usr/bin/windows_metrics.py", "-f"]