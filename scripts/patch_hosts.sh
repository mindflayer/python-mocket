HOSTS=/etc/hosts
MOCKET_HOSTS=/etc/hosts.mocket
HTTPBIN_HOST=httpbin.local

sudo grep -v ${HTTPBIN_HOST} ${HOSTS} | sudo tee ${MOCKET_HOSTS}
CONTAINER_ID=$(docker compose ps -q proxy)
CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' ${CONTAINER_ID})
echo "${CONTAINER_IP} ${HTTPBIN_HOST}" | sudo tee -a ${MOCKET_HOSTS}
sudo mv ${MOCKET_HOSTS} ${HOSTS}
