# GitHub Actions CI/CD Data Platform ke Home Server

Tutorial end-to-end untuk belajar GitHub Actions CI/CD dari dasar sampai deployment Apache Airflow menggunakan Docker Compose.

Target akhir:

```text
Pull Request
    │
    ▼
GitHub-hosted Runner
    │
    ├── Python / DAG test
    ├── Docker build test
    └── CI PASS
          │
          ▼
        Merge
          │
          ▼
        main
          │
          ▼
GitHub-hosted Runner
    │
    ├── Build Docker Image
    └── Push GHCR
          │
          ▼
        GHCR
          │
          ▼
GitHub Self-hosted Runner
di Home Server
    │
    ├── docker compose pull
    ├── docker compose up -d
    └── smoke test
          │
          ▼
        Airflow

Laptop
    │
    │ Tailscale
    ▼
Home Server / Airflow UI
```

---

# 0. Asumsi Tutorial

Tutorial ini menggunakan:

```text
Repository        : data-platform-cicd-lab
Default branch    : main
Repository        : Private
Home server       : Ubuntu / Debian Linux
Home server IP    : Tidak memiliki public IP
Private network   : Tailscale
Runner user       : gha-runner
Docker            : Docker Engine + Docker Compose v2
Python lab        : Python 3.12
Airflow           : Apache Airflow 3.3.0
Container registry: GitHub Container Registry (GHCR)
```

Path di home server:

```text
/opt/cicd-lab
/opt/cicd-docker
/opt/airflow-platform
```

> Jangan mengganti semua nama sekaligus saat belajar. Selesaikan satu checkpoint terlebih dahulu, baru lanjut ke checkpoint berikutnya.

---

# Roadmap

```text
CHECKPOINT 0
GitHub Self-hosted Runner
Home Server
        ↓
CHECKPOINT 1
Python CI
PR → GitHub-hosted → pytest
        ↓
CHECKPOINT 2
Python CD
main → self-hosted → /opt/cicd-lab
        ↓
CHECKPOINT 3
Docker Compose CD
main → self-hosted → docker compose up
        ↓
CHECKPOINT 4
Proper Docker CI/CD
GitHub-hosted → Build → GHCR → self-hosted → Compose
        ↓
CHECKPOINT 5
Airflow CI
DAG syntax → Docker build → DAG import test
        ↓
CHECKPOINT 6
Airflow CI/CD
PR → CI → merge → GHCR → Home Server → Airflow
        ↓
CHECKPOINT 7
Protection
Ruleset + required CI + production environment
```

---

# Struktur Repository Akhir

Nanti repository akan berbentuk:

```text
data-platform-cicd-lab/
│
├── labs/
│   ├── python/
│   │   ├── transform.py
│   │   ├── requirements-dev.txt
│   │   └── tests/
│   │       └── test_transform.py
│   │
│   └── docker/
│       ├── Dockerfile
│       ├── compose.build.yaml
│       └── compose.prod.yaml
│
├── airflow/
│   ├── dags/
│   │   └── hello_cicd.py
│   ├── Dockerfile
│   ├── requirements.txt
│   └── docker-compose.yaml
│
└── .github/
    └── workflows/
        ├── test-runner.yml
        ├── python-ci-cd.yml
        ├── docker-ghcr-cicd.yml
        └── airflow-ci-cd.yml
```

---

# CHECKPOINT 0 — Pasang GitHub Actions Runner di Home Server

## Tujuan

Membuat GitHub dapat memberikan deployment job ke home server tanpa public IP.

```text
GitHub
   │
   │ HTTPS outbound
   ▼
Self-hosted Runner
di Home Server
```

Tailscale tetap digunakan untuk:

```text
Laptop → Home Server
```

GitHub runner tidak membutuhkan koneksi inbound dari internet.

---

## 0.1 Buat Repository GitHub

Di GitHub:

```text
+
→ New repository
```

Isi:

```text
Repository name:
data-platform-cicd-lab

Visibility:
Private
```

Klik:

```text
Create repository
```

Clone ke laptop:

```bash
git clone https://github.com/USERNAME/data-platform-cicd-lab.git
cd data-platform-cicd-lab
```

Ganti `USERNAME` dengan username GitHub Anda.

---

## 0.2 Masuk Home Server via Tailscale

Cari IP Tailscale home server jika diperlukan:

```bash
tailscale ip -4
```

Dari laptop:

```bash
ssh USER@TAILSCALE_IP
```

Contoh:

```bash
ssh seakun@100.x.x.x
```

---

## 0.3 Cek Docker

Di home server:

```bash
docker --version
docker compose version
docker ps
```

Semua command sebaiknya berhasil.

---

## 0.4 Buat User Khusus Runner

Jangan menjalankan GitHub runner sebagai root.

```bash
sudo adduser gha-runner
```

Tambahkan runner ke group Docker:

```bash
sudo usermod -aG docker gha-runner
```

Masuk ke user tersebut:

```bash
sudo su - gha-runner
```

Cek:

```bash
whoami
```

Expected:

```text
gha-runner
```

Cek Docker:

```bash
docker ps
```

Jika muncul permission denied, logout lalu login kembali:

```bash
exit
sudo su - gha-runner
```

> Membership group `docker` memberi privilege sangat tinggi terhadap host. Karena itu gunakan self-hosted runner hanya untuk repository private yang Anda percaya.

---

## 0.5 Tambahkan Runner dari GitHub

Di repository GitHub:

```text
Settings
→ Actions
→ Runners
→ New self-hosted runner
```

Pilih:

```text
Runner image : Linux
Architecture : X64
```

Cek architecture home server:

```bash
uname -m
```

Jika:

```text
x86_64
```

gunakan:

```text
X64
```

Jika:

```text
aarch64
```

gunakan:

```text
ARM64
```

---

## 0.6 Download dan Configure Runner

GitHub akan menampilkan command terbaru untuk:

```text
Download
Configure
```

Copy dan jalankan command yang diberikan GitHub satu per satu.

Bentuk umumnya:

```bash
mkdir actions-runner
cd actions-runner
```

Kemudian:

```bash
curl -o actions-runner-linux-x64-....tar.gz -L ...
tar xzf ./actions-runner-linux-x64-....tar.gz
```

Lalu:

```bash
./config.sh \
  --url https://github.com/USERNAME/data-platform-cicd-lab \
  --token TOKEN_DARI_GITHUB
```

Gunakan command persis dari halaman GitHub karena versi runner dapat berubah.

Saat ditanya nama runner:

```text
Enter the name of runner:
```

isi:

```text
home-server
```

Runner group:

```text
Default
```

Work folder:

```text
_work
```

Label default biasanya:

```text
self-hosted
Linux
X64
```

---

## 0.7 Install Runner sebagai Service

Tujuan:

```text
Home Server reboot
        ↓
systemd
        ↓
GitHub Runner otomatis hidup
```

Jika sekarang berada sebagai:

```text
gha-runner
```

keluar:

```bash
exit
```

Masuk ke user `root`:

```bash
sudo -i
```

Cek:

```bash
whoami
```

Expected:

```text
root
```

Masuk folder runner:

```bash
cd /home/gha-runner/actions-runner
```

Install service, tetapi tetap jalankan runner sebagai `gha-runner`:

```bash
./svc.sh install gha-runner
```

Start:

```bash
./svc.sh start
```

Cek:

```bash
./svc.sh status
```

Expected:

```text
active (running)
```

Keluar dari root:

```bash
exit
```

> Root hanya dipakai untuk mengelola service systemd. Proses runner tetap berjalan sebagai `gha-runner`.

---

## 0.8 Cek Runner di GitHub

Buka:

```text
Repository
→ Settings
→ Actions
→ Runners
```

Expected:

```text
home-server
Idle
```

`Idle` berarti runner online dan sedang menunggu job.

---

## 0.9 Buat Workflow Test Runner

Di laptop:

```bash
mkdir -p .github/workflows
```

Buat:

```text
.github/workflows/test-runner.yml
```

Isi:

```yaml
name: Test Home Server Runner

on:
  workflow_dispatch:

jobs:
  test-home-server:
    runs-on:
      - self-hosted
      - Linux
      - X64

    steps:
      - name: Show hostname
        run: hostname

      - name: Show current user
        run: whoami

      - name: Check Docker
        run: docker ps

      - name: Check Docker Compose
        run: docker compose version
```

Jika runner ARM64, sesuaikan label `X64`.

Commit:

```bash
git add .
git commit -m "Add self-hosted runner test"
git push
```

---

## 0.10 Jalankan Manual

Di GitHub:

```text
Actions
→ Test Home Server Runner
→ Run workflow
→ Run workflow
```

Expected:

```text
Show hostname         ✅
Show current user     ✅
Check Docker          ✅
Check Docker Compose  ✅
```

Pada `Show current user`:

```text
gha-runner
```

Checkpoint 0 selesai.

---

# CHECKPOINT 1 — Python CI

## Tujuan

Belajar:

```text
Pull Request
      │
      ▼
GitHub-hosted Runner
      │
      └── pytest
            │
       PASS / FAIL
```

Belum ada deployment.

---

## 1.1 Buat File Python

Di laptop:

```bash
mkdir -p labs/python/tests
```

Buat:

```text
labs/python/transform.py
```

Isi:

```python
def calculate_net_revenue(gross_revenue, discount):
    return gross_revenue - discount


if __name__ == "__main__":
    result = calculate_net_revenue(100_000, 20_000)
    print(f"Net revenue: {result}")
```

---

## 1.2 Buat Unit Test

Buat:

```text
labs/python/tests/test_transform.py
```

Isi:

```python
from transform import calculate_net_revenue


def test_calculate_net_revenue():
    assert calculate_net_revenue(100_000, 20_000) == 80_000
```

---

## 1.3 Buat Dependency

Buat:

```text
labs/python/requirements-dev.txt
```

Isi:

```text
pytest>=8,<10
```

---

## 1.4 Buat Workflow CI

Buat:

```text
.github/workflows/python-ci-cd.yml
```

Isi awal:

```yaml
name: Python CI/CD

on:
  pull_request:
    branches:
      - main
    paths:
      - "labs/python/**"
      - ".github/workflows/python-ci-cd.yml"

  push:
    branches:
      - main
    paths:
      - "labs/python/**"
      - ".github/workflows/python-ci-cd.yml"

permissions:
  contents: read

jobs:
  python-ci:
    name: Python CI

    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: labs/python

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: labs/python/requirements-dev.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Check Python syntax
        run: |
          python -m compileall .

      - name: Run tests
        run: |
          pytest -v
```

Mental model:

```text
workflow
└── job: Python CI
    ├── checkout
    ├── setup Python
    ├── install pytest
    ├── syntax check
    └── pytest
```

---

## 1.5 Buat Feature Branch

```bash
git checkout -b feature/python-ci
```

Commit:

```bash
git add .
git commit -m "Add Python CI lab"
git push -u origin feature/python-ci
```

---

## 1.6 Buat Pull Request

Di GitHub:

```text
Pull requests
→ New pull request
```

Pilih:

```text
base    : main
compare : feature/python-ci
```

Klik:

```text
Create pull request
```

Buka tab:

```text
Checks
```

atau:

```text
Actions
```

Expected:

```text
Python CI ✅
```

---

## 1.7 Sengaja Buat CI Gagal

Ubah test:

```python
assert calculate_net_revenue(100_000, 20_000) == 90_000
```

Commit:

```bash
git add .
git commit -m "Break test intentionally"
git push
```

Expected:

```text
Python CI ❌
```

Kembalikan menjadi:

```python
assert calculate_net_revenue(100_000, 20_000) == 80_000
```

Commit:

```bash
git add .
git commit -m "Fix Python test"
git push
```

Expected:

```text
Python CI ✅
```

Checkpoint 1 selesai.

---

# CHECKPOINT 2 — Python CD ke Home Server

## Tujuan

Setelah merge ke `main`:

```text
Python CI
   │
   │ PASS
   ▼
Self-hosted Runner
   │
   ▼
/opt/cicd-lab
```

Tidak menggunakan SSH dari GitHub.

Deployment job memang sudah berjalan langsung di home server.

---

## 2.1 Siapkan Folder Deployment

Masuk home server lewat Tailscale:

```bash
ssh USER@TAILSCALE_IP
```

Masuk root:

```bash
sudo -i
```

Buat folder:

```bash
mkdir -p /opt/cicd-lab
```

Berikan ownership:

```bash
chown -R gha-runner:gha-runner /opt/cicd-lab
```

Keluar:

```bash
exit
```

---

## 2.2 Buat GitHub Environment

Di GitHub:

```text
Repository
→ Settings
→ Environments
→ New environment
```

Nama:

```text
production
```

Klik:

```text
Configure environment
```

Untuk sekarang belum perlu secret.

Environment berguna untuk menandai bahwa job tersebut adalah deployment.

---

## 2.3 Tambahkan Deployment Job

Edit:

```text
.github/workflows/python-ci-cd.yml
```

Menjadi:

```yaml
name: Python CI/CD

on:
  pull_request:
    branches:
      - main
    paths:
      - "labs/python/**"
      - ".github/workflows/python-ci-cd.yml"

  push:
    branches:
      - main
    paths:
      - "labs/python/**"
      - ".github/workflows/python-ci-cd.yml"

permissions:
  contents: read

jobs:
  python-ci:
    name: Python CI

    runs-on: ubuntu-latest

    defaults:
      run:
        working-directory: labs/python

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: "pip"
          cache-dependency-path: labs/python/requirements-dev.txt

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest -v


  deploy-python:
    name: Deploy Python to Home Server

    needs:
      - python-ci

    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main'

    environment:
      name: production

    runs-on:
      - self-hosted
      - Linux
      - X64

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Deploy Python file
        run: |
          cp labs/python/transform.py /opt/cicd-lab/transform.py
          printf '%s\n' "$GITHUB_SHA" > /opt/cicd-lab/VERSION

      - name: Run deployed application
        run: |
          python3 /opt/cicd-lab/transform.py \
            | tee /opt/cicd-lab/last-run.txt

      - name: Verify deployment
        run: |
          echo "Version:"
          cat /opt/cicd-lab/VERSION

          echo "Output:"
          cat /opt/cicd-lab/last-run.txt
```

---

## 2.4 Merge Pull Request

Setelah CI hijau:

```text
Pull Request
→ Merge pull request
→ Confirm merge
```

Merge menghasilkan:

```text
push → main
```

Workflow berjalan lagi.

Expected:

```text
Python CI                      ✅
Deploy Python to Home Server  ✅
```

---

## 2.5 Verifikasi di Home Server

```bash
cat /opt/cicd-lab/VERSION
```

Harus berisi Git commit SHA.

Cek output:

```bash
cat /opt/cicd-lab/last-run.txt
```

Expected:

```text
Net revenue: 80000
```

Mental model:

```text
PR
│
└── CI di GitHub-hosted

merge
│
▼
main
│
├── CI di GitHub-hosted
│
└── CD di self-hosted home server
```

Checkpoint 2 selesai.

---

# CHECKPOINT 3 — Docker Compose CD

## Tujuan

Sekarang aplikasi dijalankan sebagai container.

```text
main
 │
 ▼
Self-hosted Runner
 │
 ▼
docker compose build
 │
 ▼
docker compose up -d
```

Image masih dibuild langsung pada home server.

Ini sengaja dilakukan sebagai tahap belajar.

---

## 3.1 Siapkan Folder

Di home server:

```bash
sudo -i
mkdir -p /opt/cicd-docker
chown -R gha-runner:gha-runner /opt/cicd-docker
exit
```

---

## 3.2 Buat Dockerfile

Di laptop:

```bash
mkdir -p labs/docker
```

Buat:

```text
labs/docker/Dockerfile
```

Isi:

```dockerfile
FROM python:3.12-slim

ARG GIT_SHA=local

WORKDIR /app

RUN printf '<h1>GitHub Actions Docker Lab</h1><p>Version: %s</p>\n' \
    "${GIT_SHA}" \
    > /app/index.html

EXPOSE 8000

CMD [
  "python",
  "-m",
  "http.server",
  "8000",
  "--bind",
  "0.0.0.0"
]
```

---

## 3.3 Buat Compose Build Version

Buat:

```text
labs/docker/compose.build.yaml
```

Isi:

```yaml
services:
  demo:
    build:
      context: .
      args:
        GIT_SHA: ${GIT_SHA:-local}

    restart: unless-stopped

    ports:
      - "127.0.0.1:8000:8000"
```

Port hanya dibind ke localhost karena aplikasi ini hanya untuk smoke test.

---

## 3.4 Buat Workflow Docker Compose

Buat:

```text
.github/workflows/docker-compose-cd.yml
```

Isi:

```yaml
name: Docker Compose CD

on:
  pull_request:
    branches:
      - main
    paths:
      - "labs/docker/**"
      - ".github/workflows/docker-compose-cd.yml"

  push:
    branches:
      - main
    paths:
      - "labs/docker/**"
      - ".github/workflows/docker-compose-cd.yml"

permissions:
  contents: read

jobs:
  docker-ci:
    name: Docker Build Test

    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Validate Compose
        run: |
          docker compose \
            -f labs/docker/compose.build.yaml \
            config

      - name: Test Docker build
        run: |
          docker build \
            --build-arg GIT_SHA="$GITHUB_SHA" \
            -t demo-ci:"$GITHUB_SHA" \
            labs/docker


  deploy:
    name: Deploy Docker Compose

    needs:
      - docker-ci

    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main'

    environment:
      name: production

    runs-on:
      - self-hosted
      - Linux
      - X64

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Copy deployment files
        run: |
          rm -rf /opt/cicd-docker/*
          cp -a labs/docker/. /opt/cicd-docker/

      - name: Build and deploy
        working-directory: /opt/cicd-docker
        run: |
          GIT_SHA="$GITHUB_SHA" \
          docker compose \
            -f compose.build.yaml \
            up \
            -d \
            --build \
            --remove-orphans

      - name: Smoke test
        run: |
          curl \
            --fail \
            --retry 10 \
            --retry-delay 2 \
            --retry-connrefused \
            http://127.0.0.1:8000
```

---

## 3.5 Commit via Feature Branch

```bash
git checkout main
git pull
git checkout -b feature/docker-compose-cd
```

Commit:

```bash
git add .
git commit -m "Add Docker Compose CD lab"
git push -u origin feature/docker-compose-cd
```

Buat Pull Request.

Expected saat PR:

```text
Docker Build Test ✅
Deploy             skipped
```

Setelah merge:

```text
Docker Build Test      ✅
Deploy Docker Compose  ✅
```

---

## 3.6 Verifikasi Home Server

```bash
cd /opt/cicd-docker
```

Cek:

```bash
docker compose -f compose.build.yaml ps
```

Cek aplikasi:

```bash
curl http://127.0.0.1:8000
```

Expected:

```html
<h1>GitHub Actions Docker Lab</h1>
<p>Version: COMMIT_SHA</p>
```

---

## 3.7 Apa Kekurangan Pola Ini?

Image diuji di GitHub:

```text
GitHub → docker build
```

tetapi kemudian dibuild ulang:

```text
Home Server → docker build
```

Artinya:

```text
image yang dites
≠
secara identitas image yang dijalankan
```

Checkpoint berikutnya memperbaiki ini.

---

# CHECKPOINT 4 — Proper Docker CI/CD dengan GHCR

## Tujuan

Build hanya sekali:

```text
GitHub-hosted Runner
        │
        ▼
Docker Image
        │
        ▼
GHCR
        │
        ▼
Home Server
        │
        ▼
docker compose pull
        │
        ▼
docker compose up -d
```

Artifact deployment sekarang adalah Docker image.

---

## 4.1 Buat Compose Production

Buat:

```text
labs/docker/compose.prod.yaml
```

Isi:

```yaml
services:
  demo:
    image: ${APP_IMAGE:?APP_IMAGE must be set}

    restart: unless-stopped

    ports:
      - "127.0.0.1:8000:8000"
```

Perbedaannya:

```yaml
build:
```

hilang.

Sekarang home server hanya:

```text
pull image
→ run image
```

---

## 4.2 Hapus Workflow Checkpoint 3

Supaya tidak ada dua workflow yang men-deploy aplikasi sama:

```bash
git rm .github/workflows/docker-compose-cd.yml
```

---

## 4.3 Buat Workflow GHCR

Buat:

```text
.github/workflows/docker-ghcr-cicd.yml
```

Isi:

```yaml
name: Docker GHCR CI/CD

on:
  pull_request:
    branches:
      - main
    paths:
      - "labs/docker/**"
      - ".github/workflows/docker-ghcr-cicd.yml"

  push:
    branches:
      - main
    paths:
      - "labs/docker/**"
      - ".github/workflows/docker-ghcr-cicd.yml"


jobs:
  docker-ci:
    name: Docker CI

    runs-on: ubuntu-latest

    permissions:
      contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Validate production Compose
        env:
          APP_IMAGE: ghcr.io/example/example:test
        run: |
          docker compose \
            -f labs/docker/compose.prod.yaml \
            config

      - name: Test Docker build
        run: |
          docker build \
            --build-arg GIT_SHA="$GITHUB_SHA" \
            -t demo-ci:"$GITHUB_SHA" \
            labs/docker


  publish:
    name: Publish Docker Image

    needs:
      - docker-ci

    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main'

    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    outputs:
      image: ${{ steps.image.outputs.image }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Define immutable image name
        id: image
        shell: bash
        run: |
          IMAGE="ghcr.io/${GITHUB_REPOSITORY,,}:${GITHUB_SHA}"
          echo "image=${IMAGE}" >> "$GITHUB_OUTPUT"
          echo "Building ${IMAGE}"

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push image
        uses: docker/build-push-action@v6
        with:
          context: labs/docker
          push: true
          build-args: |
            GIT_SHA=${{ github.sha }}
          tags: ${{ steps.image.outputs.image }}


  deploy:
    name: Deploy Immutable Docker Image

    needs:
      - publish

    environment:
      name: production

    runs-on:
      - self-hosted
      - Linux
      - X64

    permissions:
      contents: read
      packages: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Login Home Server Docker to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Copy Compose file
        run: |
          cp \
            labs/docker/compose.prod.yaml \
            /opt/cicd-docker/compose.prod.yaml

      - name: Pull and deploy exact image
        working-directory: /opt/cicd-docker
        env:
          APP_IMAGE: ${{ needs.publish.outputs.image }}
        run: |
          docker compose \
            -f compose.prod.yaml \
            pull

          docker compose \
            -f compose.prod.yaml \
            up \
            -d \
            --remove-orphans

      - name: Smoke test
        run: |
          curl \
            --fail \
            --retry 10 \
            --retry-delay 2 \
            --retry-connrefused \
            http://127.0.0.1:8000
```

---

## 4.4 Kenapa Pakai `GITHUB_TOKEN`?

Workflow mendapatkan token sementara dari GitHub.

Publish job:

```yaml
permissions:
  packages: write
```

Deploy job:

```yaml
permissions:
  packages: read
```

Jadi untuk package GHCR yang terhubung ke repository ini, kita tidak perlu langsung membuat Personal Access Token.

---

## 4.5 Commit dan Pull Request

```bash
git checkout main
git pull
git checkout -b feature/docker-ghcr
```

Commit:

```bash
git add .
git commit -m "Deploy Docker image through GHCR"
git push -u origin feature/docker-ghcr
```

Buat PR.

Saat PR:

```text
Docker CI ✅
Publish   skipped
Deploy    skipped
```

Setelah merge:

```text
Docker CI                       ✅
Publish Docker Image            ✅
Deploy Immutable Docker Image  ✅
```

---

## 4.6 Cek GHCR

Di GitHub buka:

```text
Repository
→ Packages
```

atau profile GitHub:

```text
Packages
```

Akan terlihat container package.

Tag image menggunakan:

```text
Git commit SHA
```

Contoh:

```text
ghcr.io/user/data-platform-cicd-lab:3b8f1e...
```

---

## 4.7 Verifikasi Image yang Berjalan

Di home server:

```bash
docker ps
```

Lihat image:

```bash
docker inspect \
  --format='{{.Config.Image}}' \
  "$(docker ps -q --filter name=demo)"
```

Tujuan checkpoint ini:

```text
commit
   │
   ▼
immutable image tag
   │
   ▼
deployment
```

Checkpoint 4 selesai.

---

# CHECKPOINT 5 — Airflow CI

Sekarang baru masuk Apache Airflow.

## Tujuan

```text
Pull Request
    │
    ▼
GitHub-hosted Runner
    │
    ├── Python syntax
    ├── Build Airflow image
    └── DAG import check
```

Belum men-deploy Airflow.

---

# 5.1 Siapkan Folder Airflow

Di laptop:

```bash
mkdir -p airflow/dags
```

Download Docker Compose resmi Airflow 3.3.0:

```bash
curl -Lf \
  'https://airflow.apache.org/docs/apache-airflow/3.3.0/docker-compose.yaml' \
  -o airflow/docker-compose.yaml
```

---

## 5.2 Hapus DAG Bind Mount

Untuk tutorial CI/CD ini DAG akan dimasukkan ke Docker image.

Official Compose secara default melakukan:

```text
host ./dags
→
/opt/airflow/dags
```

Kalau bind mount tersebut tetap ada, DAG yang sudah dimasukkan ke image akan tertutup oleh mount host.

Hapus line DAG mount:

```bash
sed -i \
  '/\/dags:\/opt\/airflow\/dags/d' \
  airflow/docker-compose.yaml
```

Cek:

```bash
grep "/opt/airflow/dags" airflow/docker-compose.yaml
```

Expected:

```text
tidak ada output
```

Mount berikut tetap boleh ada:

```text
logs
config
plugins
```

---

## 5.3 Buat DAG Pertama

Buat:

```text
airflow/dags/hello_cicd.py
```

Isi:

```python
import pendulum

from airflow.sdk import dag, task


@dag(
    dag_id="hello_cicd",
    schedule=None,
    start_date=pendulum.datetime(
        2026,
        1,
        1,
        tz="UTC",
    ),
    catchup=False,
    tags=["cicd"],
)
def hello_cicd():

    @task
    def hello():
        print("Airflow deployed through GitHub Actions")

    hello()


hello_cicd()
```

Untuk Airflow 3 gunakan public API:

```python
from airflow.sdk import dag, task
```

---

## 5.4 Buat requirements.txt

Buat:

```text
airflow/requirements.txt
```

Untuk DAG sederhana ini boleh kosong.

Contoh nanti ketika butuh provider:

```text
apache-airflow-providers-postgres
apache-airflow-providers-google
```

Jangan install provider yang belum digunakan.

---

## 5.5 Buat Custom Dockerfile Airflow

Buat:

```text
airflow/Dockerfile
```

Isi:

```dockerfile
ARG AIRFLOW_VERSION=3.3.0

FROM apache/airflow:${AIRFLOW_VERSION}

ARG AIRFLOW_VERSION

COPY requirements.txt /requirements.txt

RUN if [ -s /requirements.txt ]; then \
      pip install \
        --no-cache-dir \
        "apache-airflow==${AIRFLOW_VERSION}" \
        -r /requirements.txt ; \
    fi

COPY \
  --chown=airflow:root \
  dags/ \
  /opt/airflow/dags/
```

Tujuan:

```text
Git commit
   │
   ▼
Airflow Docker image
   │
   ├── Airflow runtime
   ├── dependency
   └── DAG
```

---

## 5.6 Buat Airflow CI Workflow

Buat:

```text
.github/workflows/airflow-ci.yml
```

Isi:

```yaml
name: Airflow CI

on:
  pull_request:
    branches:
      - main
    paths:
      - "airflow/**"
      - ".github/workflows/airflow-ci.yml"

  push:
    branches:
      - main
    paths:
      - "airflow/**"
      - ".github/workflows/airflow-ci.yml"

permissions:
  contents: read

jobs:
  airflow-ci:
    name: Airflow CI

    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Check Python syntax
        run: |
          python -m compileall airflow/dags

      - name: Build Airflow CI image
        run: |
          docker build \
            --build-arg AIRFLOW_VERSION=3.3.0 \
            -t airflow-ci:"$GITHUB_SHA" \
            airflow

      - name: Check DAG import errors
        run: |
          docker run \
            --rm \
            airflow-ci:"$GITHUB_SHA" \
            airflow dags list-import-errors \
              --output=json \
            > import-errors.json

          cat import-errors.json

      - name: Fail if DAG import errors exist
        run: |
          python - <<'PY'
          import json
          import sys

          with open("import-errors.json", encoding="utf-8") as file:
              errors = json.load(file)

          if errors:
              print("DAG import errors detected:")
              print(json.dumps(errors, indent=2))
              sys.exit(1)

          print("No DAG import errors.")
          PY
```

Airflow menyediakan:

```bash
airflow dags list-import-errors --output=json
```

untuk automation/CI.

Expected jika sehat:

```json
[]
```

---

## 5.7 Test CI

```bash
git checkout main
git pull
git checkout -b feature/airflow-ci
```

Commit:

```bash
git add .
git commit -m "Add Airflow CI"
git push -u origin feature/airflow-ci
```

Buat PR.

Expected:

```text
Airflow CI ✅
```

---

## 5.8 Sengaja Buat DAG Error

Contoh sementara ubah:

```python
from airflow.sdk import dag, task
```

menjadi:

```python
from airflow.sdk import dag, task, TidakAda
```

Push.

Expected:

```text
Airflow CI ❌
```

Kembalikan kode yang benar.

Push lagi.

Expected:

```text
Airflow CI ✅
```

Checkpoint 5 selesai.

---

# CHECKPOINT 6 — Full Airflow CI/CD

Sekarang kita gabungkan:

```text
PR
│
▼
Airflow CI
│
▼
Merge main
│
▼
Airflow CI
│
▼
Build Docker image
│
▼
GHCR
│
▼
Self-hosted Runner
│
▼
Docker Compose
│
▼
Airflow
```

---

# 6.1 Siapkan Folder Airflow di Home Server

Masuk melalui Tailscale:

```bash
ssh USER@TAILSCALE_IP
```

Masuk root:

```bash
sudo -i
```

Buat folder:

```bash
mkdir -p \
  /opt/airflow-platform/logs \
  /opt/airflow-platform/config \
  /opt/airflow-platform/plugins
```

Ownership:

```bash
chown -R \
  gha-runner:gha-runner \
  /opt/airflow-platform
```

---

## 6.2 Buat `.env` Airflow di Home Server

Masih sebagai root:

```bash
cd /opt/airflow-platform
```

Generate password aman untuk lab:

```bash
ADMIN_PASSWORD="$(openssl rand -hex 16)"
```

Buat `.env`:

```bash
cat > .env <<EOF
AIRFLOW_UID=$(id -u gha-runner)
AIRFLOW_API_PORT=8080
_AIRFLOW_WWW_USER_USERNAME=admin
_AIRFLOW_WWW_USER_PASSWORD=${ADMIN_PASSWORD}
EOF
```

Set permission:

```bash
chmod 600 .env
chown gha-runner:gha-runner .env
```

Tampilkan password sekali:

```bash
echo "Airflow username: admin"
echo "Airflow password: ${ADMIN_PASSWORD}"
```

Simpan password tersebut di password manager Anda.

Hapus variable shell:

```bash
unset ADMIN_PASSWORD
```

Keluar root:

```bash
exit
```

> `.env` ini hanya ada di home server dan tidak di-commit ke GitHub.

---

# 6.3 Hapus Workflow Airflow CI Lama

Di laptop:

```bash
git rm .github/workflows/airflow-ci.yml
```

Kita akan menggantinya dengan workflow final.

---

# 6.4 Buat Workflow Airflow CI/CD

Buat:

```text
.github/workflows/airflow-ci-cd.yml
```

Isi:

```yaml
name: Airflow CI/CD

on:
  pull_request:
    branches:
      - main
    paths:
      - "airflow/**"
      - ".github/workflows/airflow-ci-cd.yml"

  push:
    branches:
      - main
    paths:
      - "airflow/**"
      - ".github/workflows/airflow-ci-cd.yml"


jobs:
  airflow-ci:
    name: Airflow CI

    runs-on: ubuntu-latest

    permissions:
      contents: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Check DAG Python syntax
        run: |
          python -m compileall airflow/dags

      - name: Build CI image
        run: |
          docker build \
            --build-arg AIRFLOW_VERSION=3.3.0 \
            -t airflow-ci:"$GITHUB_SHA" \
            airflow

      - name: Check DAG import errors
        run: |
          docker run \
            --rm \
            airflow-ci:"$GITHUB_SHA" \
            airflow dags list-import-errors \
              --output=json \
            > import-errors.json

          cat import-errors.json

      - name: Validate import result
        run: |
          python - <<'PY'
          import json
          import sys

          with open("import-errors.json", encoding="utf-8") as file:
              errors = json.load(file)

          if errors:
              print("DAG import errors detected:")
              print(json.dumps(errors, indent=2))
              sys.exit(1)

          print("No DAG import errors.")
          PY


  publish:
    name: Publish Airflow Image

    needs:
      - airflow-ci

    if: |
      github.event_name == 'push' &&
      github.ref == 'refs/heads/main'

    runs-on: ubuntu-latest

    permissions:
      contents: read
      packages: write

    outputs:
      image: ${{ steps.image.outputs.image }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Define immutable image
        id: image
        shell: bash
        run: |
          IMAGE="ghcr.io/${GITHUB_REPOSITORY,,}-airflow:${GITHUB_SHA}"
          echo "image=${IMAGE}" >> "$GITHUB_OUTPUT"
          echo "Image: ${IMAGE}"

      - name: Login to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push Airflow image
        uses: docker/build-push-action@v6
        with:
          context: airflow
          file: airflow/Dockerfile
          push: true
          build-args: |
            AIRFLOW_VERSION=3.3.0
          tags: ${{ steps.image.outputs.image }}


  deploy:
    name: Deploy Airflow to Home Server

    needs:
      - publish

    environment:
      name: production

    runs-on:
      - self-hosted
      - Linux
      - X64

    permissions:
      contents: read
      packages: read

    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Login Home Server Docker to GHCR
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Copy Airflow Compose
        run: |
          cp \
            airflow/docker-compose.yaml \
            /opt/airflow-platform/docker-compose.yaml

      - name: Set deployment image
        env:
          AIRFLOW_IMAGE: ${{ needs.publish.outputs.image }}
        run: |
          cd /opt/airflow-platform

          if grep -q '^AIRFLOW_IMAGE_NAME=' .env; then
            sed -i \
              "s|^AIRFLOW_IMAGE_NAME=.*|AIRFLOW_IMAGE_NAME=${AIRFLOW_IMAGE}|" \
              .env
          else
            printf '\nAIRFLOW_IMAGE_NAME=%s\n' \
              "${AIRFLOW_IMAGE}" \
              >> .env
          fi

      - name: Pull deployment images
        working-directory: /opt/airflow-platform
        run: |
          docker compose pull

      - name: Initialize Airflow once
        working-directory: /opt/airflow-platform
        run: |
          if [ ! -f .airflow-initialized ]; then
            docker compose up airflow-init
            touch .airflow-initialized
          else
            echo "Airflow already initialized."
          fi

      - name: Deploy Airflow
        working-directory: /opt/airflow-platform
        run: |
          docker compose \
            up \
            -d \
            --remove-orphans

      - name: Show container status
        working-directory: /opt/airflow-platform
        run: |
          docker compose ps

      - name: Airflow API smoke test
        run: |
          curl \
            --fail \
            --retry 30 \
            --retry-delay 5 \
            --retry-connrefused \
            http://127.0.0.1:8080/api/v2/monitor/health
```

---

# 6.5 Penjelasan Job Final

## `airflow-ci`

Berjalan di:

```yaml
runs-on: ubuntu-latest
```

Artinya:

```text
GitHub-hosted Runner
```

Pekerjaan:

```text
syntax
→ Docker build
→ DAG import validation
```

---

## `publish`

Hanya berjalan setelah:

```text
merge / push ke main
```

Pekerjaan:

```text
build image
→ tag dengan commit SHA
→ push GHCR
```

Contoh:

```text
ghcr.io/user/data-platform-cicd-lab-airflow:abc123...
```

---

## `deploy`

Berjalan di:

```yaml
runs-on:
  - self-hosted
  - Linux
  - X64
```

Artinya command dieksekusi langsung di home server.

Pekerjaan:

```text
login GHCR
→ copy Compose
→ set AIRFLOW_IMAGE_NAME
→ docker compose pull
→ airflow-init hanya pertama kali
→ docker compose up -d
→ smoke test
```

---

# 6.6 Commit Final Workflow

```bash
git checkout main
git pull
git checkout -b feature/airflow-cicd
```

Commit:

```bash
git add .
git commit -m "Add Airflow CI/CD to home server"
git push -u origin feature/airflow-cicd
```

Buat PR.

Expected pada PR:

```text
Airflow CI ✅
```

`publish` dan `deploy` belum berjalan.

---

# 6.7 Merge

Setelah CI berhasil:

```text
Merge pull request
→ Confirm merge
```

Expected pada workflow push `main`:

```text
Airflow CI                     ✅
Publish Airflow Image          ✅
Deploy Airflow to Home Server  ✅
```

---

# 6.8 Verifikasi Home Server

Masuk server:

```bash
ssh USER@TAILSCALE_IP
```

Cek:

```bash
cd /opt/airflow-platform
docker compose ps
```

Minimal akan terlihat service Airflow dan dependency seperti:

```text
airflow-api-server
airflow-scheduler
airflow-dag-processor
airflow-worker
airflow-triggerer
postgres
redis
```

---

# 6.9 Cek Airflow Health

```bash
curl \
  http://127.0.0.1:8080/api/v2/monitor/health
```

Output akan berisi status seperti:

```json
{
  "metadatabase": {
    "status": "healthy"
  },
  "scheduler": {
    "status": "healthy"
  },
  "triggerer": {
    "status": "healthy"
  },
  "dag_processor": {
    "status": "healthy"
  }
}
```

Catatan:

```text
HTTP 200
```

hanya berarti endpoint health dapat diakses.

Tetap lihat status component di JSON.

---

# 6.10 Akses Airflow dari Laptop via Tailscale

Cari Tailscale IP home server:

```bash
tailscale ip -4
```

Dari browser laptop:

```text
http://TAILSCALE_IP:8080
```

Contoh:

```text
http://100.x.x.x:8080
```

Login menggunakan username/password yang dibuat di `.env`.

Tidak perlu:

```text
router port forwarding
public IP
expose 8080 ke internet
```

---

# 6.11 Cek DAG

Di Airflow UI cari:

```text
hello_cicd
```

Trigger manual.

Expected log:

```text
Airflow deployed through GitHub Actions
```

Checkpoint 6 selesai.

---

# CHECKPOINT 7 — Protect `main`

Sekarang deployment sudah otomatis.

Jangan biarkan workflow normal melakukan:

```text
langsung push ke main
```

Gunakan:

```text
feature branch
→ Pull Request
→ CI
→ merge
→ deployment
```

---

## 7.1 Buat Ruleset

GitHub:

```text
Repository
→ Settings
→ Rules
→ Rulesets
→ New ruleset
→ New branch ruleset
```

Nama:

```text
protect-main
```

Enforcement:

```text
Active
```

Target branch:

```text
main
```

---

## 7.2 Aktifkan Pull Request Requirement

Aktifkan:

```text
Require a pull request before merging
```

Untuk personal project, minimal:

```text
Required approvals: 0 atau 1
```

Yang penting perubahan masuk melalui PR.

---

## 7.3 Require CI

Aktifkan:

```text
Require status checks to pass
```

Tambahkan status check:

```text
Airflow CI
```

Jika belum muncul, jalankan workflow minimal satu kali terlebih dahulu.

Untuk lab Python/Docker, Anda juga dapat menambahkan:

```text
Python CI
Docker CI
```

sesuai branch/workflow yang masih aktif.

---

## 7.4 Block Force Push

Aktifkan:

```text
Block force pushes
```

Jika tersedia dan sesuai kebutuhan, aktifkan juga:

```text
Restrict deletions
```

Save ruleset.

---

# 7.5 Production Environment Approval

Buka:

```text
Settings
→ Environments
→ production
```

Jika fitur required reviewers tersedia pada plan/repository Anda, tambahkan reviewer.

Flow menjadi:

```text
CI
 ↓
publish image
 ↓
production approval
 ↓
deploy
```

Untuk tahap belajar, approval boleh belum digunakan.

---

# FINAL FLOW

Sekarang seluruh sistem bekerja seperti ini:

```text
Developer
   │
   │ feature branch
   ▼
GitHub
   │
   │ Pull Request
   ▼
Airflow CI
GitHub-hosted Runner
   │
   ├── Python syntax
   ├── Docker build
   └── DAG import test
   │
   ▼
CI PASS
   │
   ▼
Merge
   │
   ▼
main
   │
   ▼
Airflow CI
   │
   ▼
Build Production Image
   │
   ▼
GHCR
   │
   │ image:<commit-sha>
   ▼
Self-hosted Runner
Home Server
   │
   ├── docker compose pull
   ├── docker compose up -d
   └── health check
   │
   ▼
Airflow
   │
   ▼
Data Pipeline
```

---

# CI vs CD vs Airflow

Ingat pemisahan ini.

## CI

```text
Apakah kode aman untuk digabung?
```

Contoh:

```text
pytest
DAG import
Docker build
dbt compile
dbt test
```

---

## CD

```text
Bagaimana versi yang sudah lolos CI dikirim ke environment?
```

Contoh:

```text
Docker build
GHCR
docker compose pull
docker compose up
```

---

## Airflow

```text
Kapan data pipeline dijalankan?
```

Contoh:

```text
Postgres
   ↓
ingestion
   ↓
BigQuery raw
   ↓
dbt
   ↓
mart
```

GitHub Actions tidak menggantikan Airflow.

Airflow tidak menggantikan GitHub Actions.

---

# Runner Mental Model

## GitHub-hosted

```yaml
runs-on: ubuntu-latest
```

Berarti:

```text
temporary machine milik GitHub
```

Gunakan untuk:

```text
CI
test
lint
build
```

---

## Self-hosted

```yaml
runs-on:
  - self-hosted
  - Linux
  - X64
```

Berarti:

```text
home server Anda
```

Gunakan untuk:

```text
deployment
docker compose
health check
```

---

# `uses:` vs `run:`

Contoh:

```yaml
- uses: actions/checkout@v6
```

Berarti memakai reusable GitHub Action.

Sedangkan:

```yaml
- run: docker compose up -d
```

berarti menjalankan shell command.

---

# `needs:`

Contoh:

```yaml
deploy:
  needs:
    - publish
```

Berarti:

```text
publish harus sukses
baru deploy boleh jalan
```

Jika:

```text
publish ❌
```

maka:

```text
deploy tidak berjalan
```

---

# `permissions:`

Contoh publish:

```yaml
permissions:
  contents: read
  packages: write
```

Artinya job boleh:

```text
membaca repository
menulis package GHCR
```

Deploy:

```yaml
permissions:
  contents: read
  packages: read
```

Artinya:

```text
boleh checkout
boleh pull image
tidak perlu push image
```

Gunakan permission minimal.

---

# Mengapa Image Ditag dengan Commit SHA?

Jangan hanya deploy:

```text
latest
```

Gunakan:

```text
ghcr.io/user/repo-airflow:<commit-sha>
```

Contoh:

```text
ghcr.io/user/repo-airflow:2a40db4...
```

Keuntungannya:

```text
commit Git
   │
   ▼
image
   │
   ▼
deployment
```

bisa ditelusuri.

---

# Rollback Airflow

Misalnya image terbaru bermasalah.

Current:

```text
ghcr.io/user/repo-airflow:NEW_SHA
```

Versi sebelumnya:

```text
ghcr.io/user/repo-airflow:OLD_SHA
```

Masuk home server:

```bash
cd /opt/airflow-platform
```

Edit:

```bash
nano .env
```

Ganti:

```text
AIRFLOW_IMAGE_NAME=ghcr.io/user/repo-airflow:OLD_SHA
```

Pull:

```bash
docker compose pull
```

Deploy:

```bash
docker compose up -d --remove-orphans
```

Cek:

```bash
docker compose ps
```

Health:

```bash
curl \
  http://127.0.0.1:8080/api/v2/monitor/health
```

---

# Jangan Jalankan Ini Saat Deployment Normal

Jangan gunakan:

```bash
docker compose down --volumes
```

atau:

```bash
docker compose down -v
```

karena volume metadata database bisa ikut terhapus.

Deployment normal:

```bash
docker compose pull
docker compose up -d --remove-orphans
```

---

# Troubleshooting Berdasarkan Stage

## CI Python Gagal

Contoh:

```text
Python CI ❌
```

Cek:

```text
syntax
dependency
pytest
```

Jangan troubleshooting Docker Compose home server dahulu.

---

## Docker Build Gagal

Contoh:

```text
Docker CI ❌
```

Cek:

```text
Dockerfile
build context
dependency
COPY path
```

---

## DAG Import Gagal

Contoh:

```text
Airflow CI ❌
```

Cek:

```text
Python import
Airflow provider
ModuleNotFoundError
DAG syntax
dependency version
```

Command lokal untuk reproduksi:

```bash
docker build \
  --build-arg AIRFLOW_VERSION=3.3.0 \
  -t airflow-local:test \
  airflow
```

Kemudian:

```bash
docker run \
  --rm \
  airflow-local:test \
  airflow dags list-import-errors \
    --output=json
```

---

## Publish GHCR Gagal

Cek job:

```text
Publish Airflow Image
```

Periksa:

```text
packages: write
GITHUB_TOKEN
image name
Docker build
```

---

## Deploy Job `Queued`

Cek:

```text
Settings
→ Actions
→ Runners
```

Runner harus:

```text
Idle
```

Jika offline di home server:

```bash
sudo -i
cd /home/gha-runner/actions-runner
./svc.sh status
```

Start:

```bash
./svc.sh start
```

---

## `docker: permission denied`

Cek runner user:

```bash
id gha-runner
```

Harus mempunyai group:

```text
docker
```

Jika belum:

```bash
sudo usermod -aG docker gha-runner
```

Restart runner service:

```bash
sudo -i
cd /home/gha-runner/actions-runner
./svc.sh stop
./svc.sh start
```

---

## GHCR Pull Gagal

Cek deploy job mempunyai:

```yaml
permissions:
  packages: read
```

dan login:

```yaml
uses: docker/login-action@v3
```

dengan:

```yaml
registry: ghcr.io
username: ${{ github.actor }}
password: ${{ secrets.GITHUB_TOKEN }}
```

---

## Airflow Container Tidak Healthy

```bash
cd /opt/airflow-platform
docker compose ps
```

Logs API:

```bash
docker compose logs \
  --tail=200 \
  airflow-api-server
```

Scheduler:

```bash
docker compose logs \
  --tail=200 \
  airflow-scheduler
```

DAG processor:

```bash
docker compose logs \
  --tail=200 \
  airflow-dag-processor
```

Worker:

```bash
docker compose logs \
  --tail=200 \
  airflow-worker
```

---

# Cek Versi Image Airflow yang Sedang Dipakai

```bash
cd /opt/airflow-platform
grep AIRFLOW_IMAGE_NAME .env
```

Contoh:

```text
AIRFLOW_IMAGE_NAME=ghcr.io/user/repo-airflow:abc123
```

Lihat container:

```bash
docker compose images
```

---

# Cek DAG dari CLI

Di home server:

```bash
cd /opt/airflow-platform
```

Gunakan service Airflow:

```bash
docker compose run \
  --rm \
  airflow-worker \
  airflow dags list
```

Cek import errors:

```bash
docker compose run \
  --rm \
  airflow-worker \
  airflow dags list-import-errors \
    --output=json
```

---

# Security Checklist

Gunakan:

```text
[ ] Repository private
[ ] Self-hosted runner tidak dipakai untuk untrusted PR
[ ] CI berjalan di GitHub-hosted runner
[ ] CD saja yang berjalan di self-hosted runner
[ ] Runner bukan root
[ ] Deployment memakai production environment
[ ] main menggunakan Pull Request
[ ] CI wajib lulus sebelum merge
[ ] Docker image memakai immutable commit SHA
[ ] Credential tidak di-commit
[ ] .env hanya ada di home server
[ ] Tidak membuka router port 8080 ke internet
[ ] Akses Airflow melalui Tailscale
```

Tambahkan ke `.gitignore` bila nanti ada file lokal:

```gitignore
.env
*.env
credentials/
*.json
__pycache__/
.pytest_cache/
```

> Jangan gunakan rule `*.json` jika project memang memiliki JSON source/config yang harus di-version-control. Untuk credential Google Cloud, lebih baik ignore path credential secara spesifik.

Contoh:

```gitignore
credentials/
service-account.json
```

---

# Extension — Menambahkan dbt Nanti

Setelah Airflow CI/CD ini stabil, CI dapat ditambah:

```text
Airflow CI
│
├── DAG import
│
├── Docker build
│
└── dbt validation
    ├── dbt deps
    ├── dbt parse
    └── dbt compile
```

Dan Airflow runtime:

```text
Airflow DAG
    │
    ├── ingestion
    │
    ▼
BigQuery raw
    │
    ▼
dbt build
    │
    ▼
mart
```

Jangan mencampur:

```text
GitHub Actions menjalankan scheduled ELT
```

dengan:

```text
Airflow menjalankan scheduled ELT
```

GitHub Actions mengelola lifecycle kode.

Airflow mengelola lifecycle data workflow.

---

# Extension — Dev dan Prod

Setelah satu environment berhasil, baru pecah:

```text
development
production
```

Contoh path:

```text
/opt/airflow-dev
/opt/airflow-prod
```

Port:

```text
Airflow DEV  : 8081
Airflow PROD : 8080
```

GitHub Environments:

```text
Settings
→ Environments
├── development
└── production
```

Contoh flow:

```text
develop
   │
   ▼
CI
   │
   ▼
deploy development

main
   │
   ▼
CI
   │
   ▼
production approval
   │
   ▼
deploy production
```

Belajar satu environment sampai stabil terlebih dahulu sebelum menambah dev/prod.

---

# Checklist Seluruh Roadmap

## Checkpoint 0

```text
[ ] home-server muncul di GitHub Runner
[ ] status Idle
[ ] runner sebagai service
[ ] workflow manual berhasil
[ ] whoami = gha-runner
[ ] docker ps berhasil
```

## Checkpoint 1

```text
[ ] Python CI berjalan saat PR
[ ] pytest berhasil
[ ] pernah mencoba CI gagal
[ ] memahami PASS vs FAIL
```

## Checkpoint 2

```text
[ ] deploy hanya setelah push main
[ ] deployment job memakai self-hosted
[ ] /opt/cicd-lab/VERSION berubah
[ ] VERSION = Git commit SHA
```

## Checkpoint 3

```text
[ ] Dockerfile berhasil build
[ ] Compose berhasil
[ ] container hidup
[ ] curl localhost:8000 berhasil
```

## Checkpoint 4

```text
[ ] image dibuild di GitHub
[ ] image dipush ke GHCR
[ ] image menggunakan SHA
[ ] home server hanya pull image
[ ] smoke test berhasil
```

## Checkpoint 5

```text
[ ] Airflow Docker image berhasil build
[ ] DAG valid
[ ] list-import-errors = []
[ ] pernah mencoba DAG import error
```

## Checkpoint 6

```text
[ ] Airflow image tersedia di GHCR
[ ] Airflow Compose berjalan
[ ] airflow-init sukses
[ ] API health bisa diakses
[ ] UI bisa dibuka via Tailscale
[ ] hello_cicd muncul
```

## Checkpoint 7

```text
[ ] main dilindungi
[ ] Pull Request required
[ ] Airflow CI required
[ ] force push diblok
[ ] production environment tersedia
```

Jika semua selesai, Anda sudah memiliki fondasi CI/CD data platform yang dapat dikembangkan ke:

```text
Airflow
dbt
BigQuery
Trino
PostgreSQL
data quality
GitHub Actions
Docker
GHCR
```

---

# Referensi Resmi

GitHub — Self-hosted runners:

https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners

GitHub — Adding self-hosted runners:

https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners

GitHub — Runner as a service:

https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/configure-the-application

GitHub — Building and testing Python:

https://docs.github.com/en/actions/tutorials/build-and-test-code/python

GitHub — Publishing Docker images:

https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images

GitHub — Rulesets:

https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets

Docker — Compose in production:

https://docs.docker.com/compose/how-tos/production/

Apache Airflow 3.3.0 — Running Airflow in Docker:

https://airflow.apache.org/docs/apache-airflow/stable/howto/docker-compose/index.html

Apache Airflow — CLI / DAG import validation:

https://airflow.apache.org/docs/apache-airflow/stable/howto/usage-cli.html

Apache Airflow — Public interface:

https://airflow.apache.org/docs/apache-airflow/stable/public-airflow-interface.html

Apache Airflow — Health checks:

https://airflow.apache.org/docs/apache-airflow/stable/administration-and-deployment/logging-monitoring/check-health.html

---

# Catatan Airflow Docker Compose

Docker Compose resmi Airflow sangat cocok untuk:

```text
learning
portfolio
home lab
exploration
```

Tetapi dokumentasi Airflow secara eksplisit menyatakan quick-start Compose tersebut tidak memberikan security guarantees yang diperlukan untuk production system.

Untuk tutorial ini istilah:

```text
production environment
```

berarti environment deployment utama di home lab Anda, bukan klaim bahwa Docker Compose quick-start Airflow sudah merupakan arsitektur production-grade enterprise.
