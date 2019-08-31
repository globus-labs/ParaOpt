#! /bin/bash
curl -d "@experiment.json" -H "Content-Type: application/json" -X POST http://localhost:8080/api/v1/experiments
