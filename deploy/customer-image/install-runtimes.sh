#!/bin/bash
# Pinned versions already qualified by this repository's LOCAL_AI.md.
# Image-build only. Models and all customer data remain absent.
set -euo pipefail
test -f /.cdb-image-build || exit 1
mkdir -p /opt/meeting-recorder
git clone https://github.com/ggml-org/whisper.cpp /opt/meeting-recorder/whisper.cpp
git -C /opt/meeting-recorder/whisper.cpp checkout --detach 4979e04f5dcaccb36057e059bbaed8a2f5288315
cmake -S /opt/meeting-recorder/whisper.cpp -B /opt/meeting-recorder/whisper.cpp/build -DCMAKE_BUILD_TYPE=Release
cmake --build /opt/meeting-recorder/whisper.cpp/build --target whisper-cli -j3
ln -s /opt/meeting-recorder/whisper.cpp/build/bin/whisper-cli /usr/local/bin/whisper-cli
curl --fail --location --proto '=https' --tlsv1.2 https://github.com/ollama/ollama/releases/download/v0.40.3/ollama-linux-arm64.tar.zst -o /tmp/cdb-ollama.tar.zst
printf '%s\n' '5754700747a93ea14db88888f08072386d2da6fbf7dd75be19a684348b9f28b8  /tmp/cdb-ollama.tar.zst' | sha256sum -c -
mkdir /tmp/cdb-ollama
# Only CPU libraries; CUDA directories are not part of this appliance.
tar --zstd -xf /tmp/cdb-ollama.tar.zst -C /tmp/cdb-ollama --wildcards --no-wildcards-match-slash --no-recursion 'bin/ollama' 'lib/ollama/*'
install -m 755 /tmp/cdb-ollama/bin/ollama /usr/bin/ollama
mkdir -p /usr/lib/ollama
find /tmp/cdb-ollama/lib/ollama -maxdepth 1 \( -type f -o -type l \) -exec cp -a {} /usr/lib/ollama/ \;
useradd --system --home /var/lib/ollama --create-home --shell /usr/sbin/nologin ollama
install -d -m 700 -o ollama -g ollama /var/lib/ollama/models
install -m 644 /opt/cdb/factory/ollama.service /etc/systemd/system/ollama.service
systemctl enable ollama.service
rm -rf /tmp/cdb-ollama /tmp/cdb-ollama.tar.zst
