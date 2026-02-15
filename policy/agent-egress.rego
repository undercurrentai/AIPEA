# TEMPLATE — OPA deny-by-default egress policy from Engineering Standards Appendix J.
# Replace placeholder agent_id and dst_host values with your actual agents and allowed endpoints.
# Run: conftest test --policy policy --no-color .
package agent.egress

default allow = false

# Allow only explicitly listed domains per agent
allow {
  input.agent_id == "pricing-agent"
  input.dst_host == "api.pricing.internal"
}

deny[msg] {
  not allow
  msg := sprintf("Agent %v denied egress to %v", [input.agent_id, input.dst_host])
}
