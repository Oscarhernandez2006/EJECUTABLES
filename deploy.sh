#!/bin/bash
# Despliegue de EJECUTABLES en Dokploy con Docker Swarm + Traefik
# Reemplaza "ejecutables-ejecutables-XXXXX" con el ID real del servicio

docker service update \
  --label-add 'traefik.enable=true' \
  --label-add 'traefik.http.routers.ejecutables.rule=Host(`ejecutables.grupo-santacruz.com`)' \
  --label-add 'traefik.http.routers.ejecutables.entrypoints=websecure' \
  --label-add 'traefik.http.routers.ejecutables.tls=true' \
  --label-add 'traefik.http.routers.ejecutables.tls.certresolver=letsencrypt' \
  --label-add 'traefik.http.routers.ejecutables.service=ejecutables' \
  --label-add 'traefik.http.services.ejecutables.loadbalancer.server.port=5000' \
  --label-add 'traefik.http.routers.ejecutables-web.rule=Host(`ejecutables.grupo-santacruz.com`)' \
  --label-add 'traefik.http.routers.ejecutables-web.entrypoints=web' \
  --label-add 'traefik.http.routers.ejecutables-web.middlewares=ejecutables-redirect-https' \
  --label-add 'traefik.http.middlewares.ejecutables-redirect-https.redirectscheme.scheme=https' \
  --label-add 'traefik.http.middlewares.ejecutables-redirect-https.redirectscheme.permanent=true' \
  --label-add 'traefik.docker.network=dokploy-network' \
  ejecutables-ejecutables-XXXXX
