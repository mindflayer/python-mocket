sudo grep -v httpbin.local /etc/hosts | sudo tee /etc/hosts.mocket
export CONTAINER_ID=$(docker compose ps -q proxy)
export CONTAINER_IP=$(docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $CONTAINER_ID)
echo "$CONTAINER_IP httpbin.local" | sudo tee -a /etc/hosts.mocket
sudo mv /etc/hosts.mocket /etc/hosts
