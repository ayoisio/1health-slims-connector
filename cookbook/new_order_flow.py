import json
from src.onehealthintegration.slims import SlimsConnector

# Step - Get example requisition
with open("testdata/requisition_3066253.txt") as requisition_file:
  example_requisition = json.load(requisition_file)

slims_connector = SlimsConnector(requisition=example_requisition, verbose=True)

# Step - Create SLIMS order
# slims_connector.create_slims_order(auto_link_samples=True)

# Step - Update SLIMS order
updated_order_data = {}
slims_connector.update_slims_order(updated_order_data)
