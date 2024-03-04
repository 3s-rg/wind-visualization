include gcloud.env
# test if the environment variables are set
ifeq ($(GCP_PROJECT_ID),)
$(error GCP_PROJECT_ID is not set. Do you have a gcloud.env file?)
endif
ifeq ($(GCP_REGION),)
$(error GCP_REGION is not set. Do you have a gcloud.env file?)
endif


DATA_UNPROCESSED=./data/unprocessed
DATA_PROCESSED=./data/processed

.PHONY: all build ingest profile login setup deploy destroy

all: deploy

build: ./dist

./dist: index.html package.json tsconfig.json src/*.ts
	npm run build

ingest:
# test if venv is active
	@(which python | grep -q .venv/bin/python) || (echo "Please activate the virtual environment first: source .venv/bin/activate" && exit 1)
	python -m server.ingest_data ${DATA_UNPROCESSED} ${DATA_PROCESSED}

profile: ingest_profile.pdf
ingest_profile.pdf: ingest_profile.prof
	python -m gprof2dot -f pstats $< | dot -Tpdf -o $@

ingest_profile.prof:
	@(which python | grep -q .venv/bin/python) || (echo "Please activate the virtual environment first: source .venv/bin/activate" && exit 1)
	python -m cProfile -o $@ server/ingest_data.py ${DATA_UNPROCESSED} ${DATA_PROCESSED}

login:
	gcloud auth login
	gcloud auth application-default login --project ${GCP_PROJECT_ID}

setup:
	gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev
	gcloud components update
	tofu init

deploy:
	tofu apply -auto-approve --var gcloud_project=${GCP_PROJECT_ID} --var gcloud_region=${GCP_REGION} --var data_processed=${DATA_PROCESSED}

destroy:
	tofu destroy -auto-approve --var gcloud_project=${GCP_PROJECT_ID} --var gcloud_region=${GCP_REGION} --var data_processed=${DATA_PROCESSED}