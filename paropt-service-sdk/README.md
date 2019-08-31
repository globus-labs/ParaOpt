## TLDR
Simple cli/sdk for making http requests to a paropt-service.

## Setup
```bash
git clone git@github.com:macintoshpie/paropt-service-sdk.git &&
  cd paropt-service-sdk &&
  pip install -r requirements.txt

export GLOBUS_SDK_SSL_VERIFY=False

./paropt_cli.py -h
```

## Usage
Use flag `-h` for help.
```bash
./paropt_cli.py -h
```
### Env var configs
- `GLOBUS_SDK_SSL_VERIFY`: when `False`, globus requests don't verify ssl (required currently due to self signed certs)
- `PAROPT_SERVICE_DOMAIN`: defaults to the aws instance, but can be set to `localhost` if developing locally

## Examples
See `/experiments` and `/optimizers` for example files use. These are intended to be *examples* for you to modify to fit your needs. Do not expect them to work by default.
