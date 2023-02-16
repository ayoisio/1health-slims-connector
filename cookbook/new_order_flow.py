import json
from onehealthintegration.slims import SlimsConnector

# Step - Create SlimsConnector instance
slims_connector = SlimsConnector(requisition=None, verbose=True)

# Step - Load requisition data
slims_connector.requisition = {}
slims_connector.load_requisition_from_file("../testdata/requisition_3066253.txt")

# Step - Create SLIMS order
slims_connector.create_slims_order(auto_link_samples=True)

# Step - Update SLIMS order
updated_order_data = {}
slims_connector.update_slims_order(updated_order_data)
