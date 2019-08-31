#! /bin/bash
#
# Helper for running docker compose
#

if [[ $1 =~ setupaws$ ]]; then
  service_root="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
  statefile="${service_root}/config/awsproviderstate.json"
  
  # check if the provider state file already exists on host
  if [[ -f "${statefile}"  ]]; then
    echo "State file already exists, exiting..."
    exit 0
  elif [[ -d "${statefile}" ]]; then
    echo "State file is a directory, not a regular file; this can happen when running the server before trying to run setup; remove the directory then rerun command"
    exit 1
  fi

  # ensure the paropt-service docker image exists
  if ! sudo docker image inspect paropt-service:latest > /dev/null 2>&1; then
    echo "Service image not build - building before running setup..."
    if ! ./$0 --build; then
      echo "Failed to build image, not running setup and exiting"
      exit 1
    fi
  fi

  # create tmp dir for logs
  tmp_dir=$(mktemp -d -t paropt-awssetup-logs-XXX)
  
  # dir in container where we'll copy the state file to
  # this dir will be shared with host so that its persistant
  container_state_file_dir=/tmp-paropt-config

  # run command to create awsproviderstate.json
  sudo docker run \
    --rm \
    --env-file "${service_root}/config/.env.prod" \
    --env CONTAINER_STATE_FILE_DIR=${container_state_file_dir} \
    -p 54000-54100:54000-54100 \
    -v ${tmp_dir}:/var/log/paropt \
    -v ${service_root}/config:${container_state_file_dir} \
    paropt-service \
    bash -c "source activate paroptservice_py367 && python paropt_service/app.py --setupaws"

  setup_res=$?

  if [[ $setup_res == 0 ]]; then
    echo "Successfully ran setup and created ${service_root}/config/awsproviderstate.json"
    exit 0
  fi
  echo "Failed to run setup - see logs in $tmp_dir"
  exit $setup_res
fi

if [[ "$(uname)" == "Darwin" ]]; then
  export PAROPT_HOST_LOGS=~/Library/Logs/paropt/
else
  export PAROPT_HOST_LOGS=/var/log/paropt/
fi

if [[ $1 =~ build$ ]]; then
  sudo -E docker-compose build --no-cache
  exit $?
fi

if [[ $1 =~ prod$ ]]; then
  paropt_env="prod"
  shift
else
  paropt_env="dev"
  shift
fi

sudo -E docker-compose -f docker-compose.yml -f docker-compose.${paropt_env}.yml up $@
