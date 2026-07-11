## Infrastructure

Resources are stored/deployed to GCP and managed with terraform.

**Please avoid creating resrouces manually**. Prefer defining them here.

See [documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs).

### GCP Auth

Make sure you're using your user authentication, not the service account one:

```
unset GOOGLE_API_KEY
unset GOOGLE_APPLICATION_CREDENTIALS
gcloud auth list
```

Possibly login:

```
gcloud auth login
gcloud auth application-default login
```

Also check your config:

```
$ gcloud config list
[billing]
quota_project = lw-speech-preach
[core]
account = foudil.bretel@gmail.com
disable_usage_reporting = False
project = lw-speech-preach

Your active configuration is: [default]
```

### Rollback

```
gcloud run revisions list --service=rag-service --region=europe-west10
# "=100" for 100% traffic
gcloud run services update-traffic rag-service \
  --to-revisions=rag-service-00001-abc=100 \
  --region=europe-west10
```
