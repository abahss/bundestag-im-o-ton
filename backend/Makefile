default:
	@echo There are no default targets

#################### DOCKER #######################
BUILDX ?= DOCKER_BUILDKIT=1
TAG := $(shell date +%Y%m%d-%H%M%S)
ifeq ($(BUILD_FORCE),1)
BUILD_FORCE = --no-cache --progress=plain
else
BUILD_FORCE =
endif

docker-build:
	$(BUILDX) docker --debug build $(BUILD_FORCE) --tag=$$GAR_IMAGE:dev .

docker-run:
	bin/docker-run.sh

docker-build-dev:
	docker build \
  --platform linux/amd64 \
  -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:dev .

docker-push-dev:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:dev

deploy-dev: docker-build-dev docker-push-dev
	gcloud run deploy rag-service-dev \
    --image=$$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:dev \
    --region=europe-west10

docker-build-prod:
	docker build \
  --platform linux/amd64 \
  -t $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG) .

docker-push-prod:
	docker push $$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG)

# When the Cloud Run service definition changed.
deploy-terraform: docker-build-prod docker-push-prod
	cd terraform && terraform apply -var="rag_image_tag=$(TAG)" -auto-approve

deploy: docker-build-prod docker-push-prod
	gcloud run deploy rag-service \
    --image=$$GCP_REGION-docker.pkg.dev/$$GCP_PROJECT/$$GCP_PROJECT/$$GAR_IMAGE:$(TAG) \
    --region=europe-west10 \
    --cpu=2 \
    --memory=8Gi \
    --env-vars-file=env_gcloud_run.yaml
################################################
