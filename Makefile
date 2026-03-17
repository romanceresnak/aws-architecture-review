.PHONY: init plan apply destroy validate output logs

# ── Config ────────────────────────────────────────────────────────────────────
TF_DIR   := terraform
REGION   ?= us-east-1
ENV      ?= dev

# ── Terraform ────────────────────────────────────────────────────────────────
init:
	cd $(TF_DIR) && terraform init

validate: init
	cd $(TF_DIR) && terraform validate

plan: validate
	cd $(TF_DIR) && terraform plan -var="aws_region=$(REGION)" -var="environment=$(ENV)"

apply: validate
	mkdir -p $(TF_DIR)/lambda_packages
	cd $(TF_DIR) && terraform apply -var="aws_region=$(REGION)" -var="environment=$(ENV)" -auto-approve

destroy:
	cd $(TF_DIR) && terraform destroy -var="aws_region=$(REGION)" -var="environment=$(ENV)" -auto-approve

output:
	cd $(TF_DIR) && terraform output

# ── Frontend ─────────────────────────────────────────────────────────────────
configure-frontend:
	@API_URL=$$(cd $(TF_DIR) && terraform output -raw api_url); \
	sed -i '' "s|REPLACE_WITH_YOUR_API_GATEWAY_URL|$$API_URL|g" frontend/app.js; \
	echo "✅ frontend/app.js configured with API URL: $$API_URL"

# ── Logs ─────────────────────────────────────────────────────────────────────
logs:
	@FN=$$(cd $(TF_DIR) && terraform output -raw reviewer_function_name); \
	aws logs tail /aws/lambda/$$FN --follow --region $(REGION)

# ── Full deploy ───────────────────────────────────────────────────────────────
deploy: apply configure-frontend
	@echo ""
	@echo "🚀 Deployment complete!"
	@echo "📂 Open frontend/index.html in your browser"
	@cd $(TF_DIR) && terraform output
