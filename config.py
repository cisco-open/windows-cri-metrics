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

import os

log_level = os.getenv("LOG_LEVEL")
user = os.getenv("USER")
passwd = os.getenv("PASSWORD")
servers_file = os.getenv("SERVERS_FILE")

#export LOG_LEVEL=DEBUG
#export USER="administrator"
#export PASSWORD="WombatXXX"
#export SERVERS_FILE="servers.txt"
