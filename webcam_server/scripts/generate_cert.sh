#!/bin/bash

mkdir -p certs
openssl req -x509 -newkey rsa:4096 -nodes -out certs/cert.pem -keyout certs/key.pem -days 365 -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
chmod 644 certs/cert.pem
chmod 644 certs/key.pem