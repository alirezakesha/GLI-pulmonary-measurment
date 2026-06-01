# Deploying GLI PFT Calculator on AWS

This guide deploys the app on a **single Ubuntu EC2** instance using **Nginx** (web server + HTTPS) and **systemd** (keeps the Python API running).

---

## Paths used in this guide

| Path | Role |
|------|------|
| **`/opt/gli-pft/GLI-pulmonary-measurment`** | **Application root** — your git repo, Python venv, React build, GLI Excel files |
| **`/etc/gli-pft/env`** | **Server config file** — environment variables for the API (not your code) |
| **`/etc/nginx/sites-available/gli-pft`** | **Nginx site config** — how HTTPS and `/api` routing work |
| **`/etc/systemd/system/gli-pft-api.service`** | **systemd unit** — starts/restarts the API on boot |

Everything below assumes the project lives at:

```text
/opt/gli-pft/GLI-pulmonary-measurment
```

---

## 0. Dev mode first (before systemd / Nginx)

Use this to confirm Python, GLI Excel files, and the API work **without** systemd. Stop the broken service while testing:

```bash
sudo systemctl stop gli-pft-api
```

### 0.1 One-time setup (if not done yet)

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment

python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

# Required — adjust scp from your laptop if needed
ls data/reference/spirometry_GLI.xlsx data/reference/TLC_GLI.xlsx
```

### 0.2 Start API (dev — auto-reload on code changes)

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment
chmod +x scripts/run-dev-server.sh
./scripts/run-dev-server.sh
```

Leave this terminal open. In **another** SSH session:

```bash
curl -s http://127.0.0.1:8000/api/health
```

You want: `{"status":"ok",...}`

- Interactive API docs: http://127.0.0.1:8000/docs (on the server, or via SSH tunnel below)

If this fails, read the traceback in the first terminal (missing Excel, wrong path, etc.). Fix before production.

### 0.3 UI options in dev

**Option A — SSH tunnel from your Mac (easiest, no open ports on EC2)**

On your **laptop** (new terminal):

```bash
ssh -L 8000:127.0.0.1:8000 -L 5173:127.0.0.1:5173 ubuntu@YOUR_EC2_IP
```

On the **server** (second terminal), with API already running:

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment
./scripts/run-dev-frontend.sh   # needs npm on server
```

On your **Mac browser**: http://127.0.0.1:5173

**Option B — API only (test with /docs)**

Tunnel only port 8000, open http://127.0.0.1:8000/docs on your Mac, try `POST /api/calculate/manual`.

**Option C — Built UI without Vite**

On Mac: `cd frontend && npm run build`, then `rsync` `dist/` to the server. Temporarily point Nginx `root` at that folder, or serve with a quick static server — skip until API health works.

### 0.4 When dev works → go back to production

1. `Ctrl+C` to stop dev uvicorn  
2. Fix `deploy/gli-pft-api.service` paths (see §3)  
3. `sudo systemctl daemon-reload && sudo systemctl start gli-pft-api`  
4. Configure Nginx (§4)

---

## How traffic flows (architecture)

```text
Browser
   │
   ▼  HTTPS :443  (only port open to the world)
 Nginx
   ├──  GET /              →  files in .../frontend/dist/     (React UI)
   └──  GET/POST /api/...  →  http://127.0.0.1:8000           (FastAPI, local only)
```

- **Nginx** is the public face: TLS, static files, reverse proxy.
- **uvicorn** listens on `127.0.0.1:8000` — not reachable from the internet (security group should **not** open 8000).

---

## 1. AWS setup

### EC2 instance

Create an instance with:

| Setting | Suggestion | Why |
|---------|------------|-----|
| AMI | Ubuntu 22.04 or 24.04 LTS | Matches commands below |
| Type | `t3.small` (2 GB RAM) or larger | GLI + pandas + Excel batch need some memory |
| Disk | 20–30 GB | Repo, venv, logs, Excel files |

### Security group (inbound rules)

| Port | Who can connect | Why |
|------|-----------------|-----|
| **22** | Your IP only | SSH administration |
| **80** | Anyone | HTTP → redirects to HTTPS |
| **443** | Anyone | HTTPS for the app |
| **8000** | **Nobody** | API stays on localhost behind Nginx |

### Domain (recommended)

Point a DNS name (e.g. `pft.yourlab.ca`) to the instance’s **Elastic IP** so HTTPS certificates work reliably.

---

## 2. First-time server preparation

SSH into the instance, then run:

```bash
# Refresh package lists and install security updates
sudo apt update && sudo apt upgrade -y
```

```bash
# Install: Python venv, web server, git, Let's Encrypt helper for Nginx
sudo apt install -y python3 python3-venv python3-pip nginx git certbot python3-certbot-nginx
```

**Optional — Node.js only if you will build the frontend on the server:**

```bash
# Adds NodeSource repo for Node 20, then installs node + npm
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node -v && npm -v   # sanity check
```

Skip Node on the server if you build `frontend/dist` on your Mac and `rsync` it (see §2.5 Option B).

---

## 2.1 Application directory

Your repo should already be at `/opt/gli-pft/GLI-pulmonary-measurment`. If you are cloning fresh:

```bash
# Parent folder for the project
sudo mkdir -p /opt/gli-pft
sudo chown $USER:$USER /opt/gli-pft

cd /opt/gli-pft
git clone <YOUR_REPO_URL> GLI-pulmonary-measurment
cd /opt/gli-pft/GLI-pulmonary-measurment
```

- `mkdir -p` — create folders without error if they exist  
- `chown` — let your SSH user own the tree (easier than always using `sudo` for git/pip)

Set a shell variable for later commands:

```bash
export APP_ROOT=/opt/gli-pft/GLI-pulmonary-measurment
cd "$APP_ROOT"
```

---

## 2.2 GLI reference Excel files (required)

The calculators read official lookup tables from disk:

```bash
mkdir -p "$APP_ROOT/data/reference"
```

From your laptop:

```bash
scp data/reference/spirometry_GLI.xlsx \
    data/reference/TLC_GLI.xlsx \
    ubuntu@YOUR_EC2_IP:"$APP_ROOT/data/reference/"
```

(Adjust `ubuntu@YOUR_EC2_IP` and use the full remote path if `$APP_ROOT` is not set in that SSH session.)

Without these files, the API will fail on startup when loading splines.

---

## 2.3 Python virtual environment and dependencies

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment

# Isolated Python environment inside the project (not system-wide)
python3 -m venv .venv

# Install packages into .venv only
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
```

```bash
# PYTHONPATH lets Python find the "backend" package from the project root
export PYTHONPATH=/opt/gli-pft/GLI-pulmonary-measurment
.venv/bin/python -c "from backend.app.main import app; print('OK')"
```

You should see `OK`. If not, fix errors before continuing.

---

## 2.4 Environment file (`/etc/gli-pft/env`)

This is **not** your project folder. It is a small file systemd reads when starting the API.

```bash
# Create the config directory under /etc (standard place for app-specific settings)
sudo mkdir -p /etc/gli-pft
```

```bash
# Copy the template from your repo into that directory
sudo cp /opt/gli-pft/GLI-pulmonary-measurment/deploy/env.example /etc/gli-pft/env
```

```bash
# Edit values (domain, etc.)
sudo nano /etc/gli-pft/env
```

File contents should be:

```bash
# Tells Python where the project root is (must match your clone path)
PYTHONPATH=/opt/gli-pft/GLI-pulmonary-measurment

# Public URL of the site (for CORS). Use your real https:// domain.
ALLOWED_ORIGINS=https://your-domain.com
```

| Variable | What it does |
|----------|----------------|
| `PYTHONPATH` | So `import backend.app.main` works when uvicorn starts |
| `ALLOWED_ORIGINS` | Which browser origins may call the API cross-origin (same domain via Nginx is fine) |

---

## 2.5 Frontend production build

The UI must exist as static files in `frontend/dist/`.

### Option A — Build on the server (needs `npm`)

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment
chmod +x scripts/production-build.sh
./scripts/production-build.sh
```

The script runs `npm ci` and `npm run build` inside `frontend/`.

### Option B — Build on your Mac, upload (no `npm` on server)

On your Mac:

```bash
cd /path/to/LLN-GLI-Pulmonary/frontend
npm ci
npm run build
```

Upload to the server:

```bash
rsync -avz --delete frontend/dist/ \
  ubuntu@YOUR_EC2_IP:/opt/gli-pft/GLI-pulmonary-measurment/frontend/dist/
```

- `rsync -avz` — archive mode, compress, show progress  
- `--delete` — remove old files on server that were removed from the build  

---

## 3. systemd — run the API as a service

**systemd** starts the API on boot and restarts it if it crashes.

### 3.1 Install the unit file

The template in the repo is already set for your path. Copy it:

```bash
sudo cp /opt/gli-pft/GLI-pulmonary-measurment/deploy/gli-pft-api.service \
        /etc/systemd/system/gli-pft-api.service
```

What the unit file does (see `deploy/gli-pft-api.service`):

| Line | Meaning |
|------|---------|
| `WorkingDirectory=...` | Run uvicorn from your project root |
| `EnvironmentFile=/etc/gli-pft/env` | Load `PYTHONPATH`, `ALLOWED_ORIGINS` |
| `ExecStart=.../.venv/bin/uvicorn ...` | Use **project venv**, bind **localhost:8000** only |
| `Restart=on-failure` | Auto-restart if the process dies |
| `User=www-data` | Run as the web server user (optional; match Nginx) |

### 3.2 Enable and start

```bash
# Reload systemd so it sees the new unit file
sudo systemctl daemon-reload

# Start API automatically on boot
sudo systemctl enable gli-pft-api

# Start it now
sudo systemctl start gli-pft-api

# Check status (should say "active (running)")
sudo systemctl status gli-pft-api
```

### 3.3 Logs and health check

```bash
# Follow live logs
journalctl -u gli-pft-api -f
```

```bash
# API should respond (only works ON the server, not from your laptop unless tunneled)
curl -s http://127.0.0.1:8000/api/health
```

Expected: `{"status":"ok",...}`

---

## 4. Nginx — HTTPS and routing

### 4.1 Install site config

```bash
sudo cp /opt/gli-pft/GLI-pulmonary-measurment/deploy/nginx-gli-pft.conf \
        /etc/nginx/sites-available/gli-pft

sudo nano /etc/nginx/sites-available/gli-pft
```

Edit:

1. Replace every **`YOUR_DOMAIN`** with your real hostname (e.g. `pft.example.com`).  
2. Confirm **`root`** points to:

   ```nginx
   root /opt/gli-pft/GLI-pulmonary-measurment/frontend/dist;
   ```

What the Nginx config does:

| Block | What it does |
|-------|----------------|
| `listen 80` + `return 301 https://...` | Force HTTPS |
| `listen 443 ssl` | Serve TLS |
| `root .../frontend/dist` | Serve React `index.html`, JS, CSS |
| `location /api/` + `proxy_pass http://127.0.0.1:8000` | Forward API calls to uvicorn |
| `try_files ... /index.html` | SPA routing for React |
| `client_max_body_size 50M` | Allow large PFT Excel uploads |

### 4.2 Enable site and test

```bash
# Activate this site (symlink into sites-enabled)
sudo ln -sf /etc/nginx/sites-available/gli-pft /etc/nginx/sites-enabled/

# Disable default Nginx welcome page if it conflicts
sudo rm -f /etc/nginx/sites-enabled/default

# Test syntax before reload
sudo nginx -t

# Apply config
sudo systemctl reload nginx
```

### 4.3 TLS certificate (Let's Encrypt)

```bash
# Obtains cert and can patch Nginx config for you
sudo certbot --nginx -d your-domain.com

sudo systemctl reload nginx
```

### 4.4 Verify in a browser

- `https://your-domain.com` → GLI PFT Calculator UI  
- `https://your-domain.com/api/health` → JSON `{"status":"ok",...}`  

---

## 5. Redeploy after code changes

```bash
cd /opt/gli-pft/GLI-pulmonary-measurment
git pull

.venv/bin/pip install -r requirements.txt

# Frontend: one of:
./scripts/production-build.sh
# OR rsync frontend/dist/ from your Mac

sudo systemctl restart gli-pft-api
sudo systemctl reload nginx
```

---

## 6. Checklist

- [ ] Project at `/opt/gli-pft/GLI-pulmonary-measurment`  
- [ ] `data/reference/spirometry_GLI.xlsx` and `TLC_GLI.xlsx` on server  
- [ ] `.venv` created and `pip install -r requirements.txt` done  
- [ ] `frontend/dist/` exists (build or rsync)  
- [ ] `/etc/gli-pft/env` has correct `PYTHONPATH` and `ALLOWED_ORIGINS`  
- [ ] `systemctl status gli-pft-api` → active  
- [ ] `curl http://127.0.0.1:8000/api/health` → OK  
- [ ] Nginx `root` and `YOUR_DOMAIN` correct  
- [ ] HTTPS works; port **8000** not open in security group  

---

## 7. Troubleshooting

| Symptom | Likely cause | What to do |
|---------|----------------|------------|
| `502 Bad Gateway` on `/api` | API not running | `journalctl -u gli-pft-api -n 50` |
| `ModuleNotFoundError: backend` | Wrong `PYTHONPATH` | Fix `/etc/gli-pft/env` |
| Excel / spline error | Missing reference files | Check `data/reference/*.xlsx` |
| `python-multipart` error | Wrong Python (conda/system) | Use `.venv/bin/uvicorn` in service file |
| `npm: command not found` | Node not installed | Option B: build on Mac + rsync `dist/` |
| Blank white page | No build or wrong `root` in Nginx | Rebuild; fix `root` path |
| CORS errors | Wrong `ALLOWED_ORIGINS` | Set to your `https://` URL |

---

## 8. Config files in this repo

| File | Purpose |
|------|---------|
| `deploy/gli-pft-api.service` | systemd template (paths set for `GLI-pulmonary-measurment`) |
| `deploy/nginx-gli-pft.conf` | Nginx template |
| `deploy/env.example` | Copy to `/etc/gli-pft/env` |
| `scripts/production-build.sh` | Build `frontend/dist/` |

---

## 9. Security (clinical / PHI data)

- Use **HTTPS** in production.  
- Restrict SSH to your IP; use key-based login.  
- PFT uploads are processed in memory and not stored by default — still handle as sensitive.  
- Do not publish GLI Excel or patient spreadsheets in a public git repo if license or policy requires otherwise.
