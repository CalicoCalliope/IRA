[ -f services/coordinator/README.md ] || cat > services/coordinator/README.md <<'EOF'
# Coordinator Service
Orchestrates calls between extension and services. See api/coordinator.openapi.yml for the contract.
