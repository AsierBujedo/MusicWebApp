# Nginx for Resonar

This is a host-Nginx deployment. Docker must publish the application ports on
loopback only (`127.0.0.1:3000:3000` and `127.0.0.1:8000:8000`).

1. Point the public DNS A/AAAA records for `resonar.superbitsor.es` at this
   server and allow inbound TCP ports 80 and 443.
2. Install Nginx and Certbot on the host.
3. Create `/var/www/certbot` and use a temporary port-80-only server for the
   initial HTTP-01 certificate request.
4. Obtain the first certificate with Certbot, then copy
   `resonar.superbitsor.es.conf` to `/etc/nginx/sites-available/`, create the
   `sites-enabled` symlink, and test/reload Nginx.
5. Start Docker and test the public URL and `/api/health`.

The `/api/events` location disables proxy buffering because it transports the
backend's Server-Sent Events stream.
