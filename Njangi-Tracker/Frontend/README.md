# Njangi Tracker - Frontend

Static website (HTML + CSS + JavaScript, no build step) for Njangi Tracker. It talks to the **Backend** API over HTTP.

## Run locally

```bash
python3 serve.py            # http://127.0.0.1:5500   (start.sh / start.bat do the same)
```
The backend must be running on port 8000 of the same machine (`python3 server.py` in the Backend folder).

## How it finds the API

`js/config.js` decides the API address:
- on the development server (port 5500): `http://<host>:8000/api`
- anywhere else (production): the relative path `/api` - nginx forwards `/api/` to the backend.

If your backend is on another address, set the full URL there (it must end with `/api`) and list the site's address in the backend's `NJANGI_CORS_ORIGINS`.

## Deploy with nginx

Serve this folder as the web root and forward the API:

```nginx
server {
    listen 80;
    server_name your-domain;
    root /var/www/Njangi-Frontend;
    index index.html;

    location ~ ^/(serve\.py|update\.sh|start\.sh|start\.bat)$ { return 404; }
    location ~* \.(py|db|env|md)$ { return 404; }
    location ~ /\.(?!well-known) { deny all; }

    location /api/ {
        proxy_pass http://127.0.0.1:2030;     # the port the backend listens on
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    location / { try_files $uri $uri/ =404; }
}
```
Then `certbot --nginx -d your-domain` for HTTPS.

## Update on the server

```bash
./update.sh      # git pull, checks every page/script reference and JS syntax, no restart needed
```

## Pages

| Page | Who | What it does |
|---|---|---|
| `index.html`, `terms.html`, `privacy-policy.html` | everyone | landing page and legal pages |
| `register.html`, `login.html` | administrator | create a group / sign in |
| `dashboard.html`, `members.html`, `cycles.html`, `contributions.html`, `history.html`, `loans.html`, `login-activity.html` | administrator | manage the group |
| `settings.html` | administrator and member | profile, group settings, change password |
| `member-login.html`, `member-dashboard.html` | member | see own payments, request loans |
| `forgot-password.html`, `verify-pin.html`, `reset-password.html` | everyone | password recovery by e-mailed PIN |
