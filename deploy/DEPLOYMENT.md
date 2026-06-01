# Deploying GLI PFT Calculator on AWS

This guide covers a **single EC2 instance** (Ubuntu 22.04/24.04) with **Nginx** + **systemd** — a straightforward production setup for a research tool. Alternatives (Docker, ECS) are noted at the end.

## Architecture

```
Internet → HTTPS (443) → Nginx
                            ├── /          → frontend/dist (React static)
                            └── /api/*     → uvicorn on 127.0.0.1:8000 (FastAPI)
```

The API is **not** exposed publicly; only Nginx is open on ports 80/443.

---

## 1. AWS resources

### EC2 instance

| Setting | Recommendation |
|---------|----------------|
| AMI | Ubuntu Server 22.04 or 24.04 LTS |
| Instance type | `t3.small` (2 GB RAM) minimum; `t3.medium` if large batch files |
| Storage | 20–30 GB gp3 |
| Key pair | SSH access for setup |

### Security group (inbound)

| Port | Source | Purpose |
|------|--------|---------|
| 22 | Your IP only | SSH |
| 80 | `0.0.0.0/0` | HTTP → redirect to HTTPS |
| 443 | `0.0.0.0/0` | HTTPS |

Do **not** open port 8000 to the internet.

### Domain (optional but recommended)

- Route 53 A record → EC2 public IP, or
- Elastic IP (static IP) attached to the instance

Use **HTTPS** if anyone uploads real patient PFT data (PHI).

---

## 2. Server setup (SSH into EC2)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip nginx git certbot python3-certbot-nginx

# Node.js 20 LTS (for building frontend)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Deploy application code

```bash
sudo mkdir -p /opt/gli-pft
sudo chown $USER:$USER /opt/gli-pft
cd /opt/gli-pft

git clone <YOUR_REPO_URL> .
# Or: rsync/scp from your laptop — exclude .venv and node_modules
```

### GLI reference files (required)

Copy onto the server (not always in git):

```bash
mkdir -p /opt/gli-pft/data/reference
# Upload from your machine:
# scp data/reference/*.xlsx ubuntu@<EC2_IP>:/opt/gli-pft/data/reference/
```

Must exist:

- `data/reference/spirometry_GLI.xlsx`
- `data/reference/TLC_GLI.xlsx`

### Python backend

```bash
cd /opt/gli-pft
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

export PYTHONPATH=/opt/gli-pft
.venv/bin/python -c "from backend.app.main import app; print('OK')"
```

### Frontend build

```bash
chmod +x scripts/production-build.sh
./scripts/production-build.sh
```

### Environment

```bash
sudo mkdir -p /etc/gli-pft
sudo cp deploy/env.example /etc/gli-pft/env
sudo nano /etc/gli-pft/env
```

Set at least:

```bash
PYTHONPATH=/opt/gli-pft
ALLOWED_ORIGINS=https://your-domain.com
```

If frontend and API are served from the **same domain** via Nginx (recommended), CORS is less critical because the browser calls `/api` on the same origin. Still set `ALLOWED_ORIGINS` to your public URL.

---

## 3. systemd service (API)

```bash
sudo cp /opt/gli-pft/deploy/gli-pft-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable gli-pft-api
sudo systemctl start gli-pft-api
sudo systemctl status gli-pft-api
```

Logs:

```bash
journalctl -u gli-pft-api -f
```

Health check on the server:

```bash
curl -s http://127.0.0.1:8000/api/health
```

---

## 4. Nginx

```bash
sudo cp /opt/gli-pft/deploy/nginx-gli-pft.conf /etc/nginx/sites-available/gli-pft
sudo nano /etc/nginx/sites-available/gli-pft
# Replace YOUR_DOMAIN everywhere

sudo ln -sf /etc/nginx/sites-available/gli-pft /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # if unused
sudo nginx -t
```

### TLS with Let's Encrypt

```bash
# First: use a temporary HTTP-only server block, or certbot --nginx after editing domain
sudo certbot --nginx -d your-domain.com
sudo systemctl reload nginx
```

Verify in a browser:

- `https://your-domain.com` → app UI  
- `https://your-domain.com/api/health` → `{"status":"ok",...}`  

---

## 5. Updates (redeploy)

```bash
cd /opt/gli-pft
git pull

.venv/bin/pip install -r requirements.txt
./scripts/production-build.sh

sudo systemctl restart gli-pft-api
sudo systemctl reload nginx
```

---

## 6. Checklist

- [ ] `data/reference/*.xlsx` present on server  
- [ ] `frontend/dist/` built  
- [ ] `gli-pft-api` active (`systemctl status`)  
- [ ] Nginx serves UI and proxies `/api`  
- [ ] HTTPS enabled  
- [ ] Security group: no public port 8000  
- [ ] `ALLOWED_ORIGINS` set in `/etc/gli-pft/env`  
- [ ] Upload limit OK (`client_max_body_size 50M` in nginx)  

---

## 7. Troubleshooting

| Problem | Fix |
|---------|-----|
| 502 Bad Gateway on `/api` | API not running: `journalctl -u gli-pft-api -n 50` |
| Excel / reference error | Missing files in `data/reference/` |
| `python-multipart` error | Use `/opt/gli-pft/.venv/bin/uvicorn`, not system Python |
| Blank page after deploy | Re-run `npm run build`; check `root` path in nginx |
| CORS errors | Set `ALLOWED_ORIGINS` or serve UI+API on same domain |

---

## 8. Other AWS options

| Option | When to use |
|--------|-------------|
| **AWS Lightsail** | Simpler than EC2; same Ubuntu + Nginx steps |
| **Docker on EC2/ECS** | Add `Dockerfile` later for repeatable deploys |
| **Application Load Balancer + ECS** | Team ops, auto-scaling — more setup |
| **AWS Amplify + Lambda** | Poor fit (Excel processing, long requests, local GLI files) |

For a thesis/research deployment, **EC2 + Nginx + systemd** is usually sufficient.

---

## 9. Security notes (clinical data)

- Use **HTTPS** only in production.  
- Restrict SSH (key-only, your IP).  
- Consider VPN or IP allowlist if the tool is internal to UHN.  
- Uploaded PFT files are processed in memory; nothing is stored server-side by default — still treat uploads as sensitive.  
- Do not commit `data/reference/` or patient Excel files to public git if license or PHI applies.

---

## File reference

| File | Purpose |
|------|---------|
| `deploy/gli-pft-api.service` | systemd unit for uvicorn |
| `deploy/nginx-gli-pft.conf` | Nginx site template |
| `deploy/env.example` | Environment variables template |
| `scripts/production-build.sh` | Build React `dist/` |
