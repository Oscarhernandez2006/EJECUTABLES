docker service update \
  --label-add 'traefik.enable=true' \
  --label-add 'traefik.docker.network=dokploy-network' \
  --label-add 'traefik.http.routers.cnx-secure.rule=Host(`cnx.grupo-santacruz.com`)' \
  --label-add 'traefik.http.routers.cnx-secure.entrypoints=websecure' \
  --label-add 'traefik.http.routers.cnx-secure.tls=true' \
  --label-add 'traefik.http.routers.cnx-secure.tls.certresolver=letsencrypt' \
  --label-add 'traefik.http.routers.cnx-web.rule=Host(`cnx.grupo-santacruz.com`)' \
  --label-add 'traefik.http.routers.cnx-web.entrypoints=web' \
  --label-add 'traefik.http.routers.cnx-web.middlewares=cnx-redirect' \
  --label-add 'traefik.http.middlewares.cnx-redirect.redirectscheme.scheme=https' \
  --label-add 'traefik.http.services.cnx.loadbalancer.server.port=5000' \
  cnx-cnx-wqn7jq