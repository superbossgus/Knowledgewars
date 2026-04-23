#!/bin/bash

cd ~/Downloads/Knowledgewars_Anthropic_FINAL/backend

cat > .env << 'ENVFILE'
JWT_SECRET="knowledgewars_secret_2026_super_seguro"
MONGO_URL="mongodb+srv://gustavojimenezcerda_db_user:gustavojimenezcerda_db_user@cluster0.ntzwzao.mongodb.net/knowledgewars?appName=Cluster0"
ANTHROPIC_API_KEY="sk-ant-YOUR_KEY_HERE"
ENVFILE

pip3 install -r requirements.txt

python3 -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
