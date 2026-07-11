.PHONY: plan apply destroy fmt clean init

init:
	terraform init -upgrade

plan:
	terraform plan -parallelism=16 -out=tf.plan

apply:
	terraform apply -parallelism=16 tf.plan

destroy:
	terraform destroy

fmt:
	terraform fmt

clean:
	rm -f *.plan
