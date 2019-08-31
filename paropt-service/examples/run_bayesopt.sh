#! /bin/bash

curl -d "@bayesopt.json" -H "Content-Type: application/json" -X POST http://localhost:8080/api/v1/experiments/1/trials
