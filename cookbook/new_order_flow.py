from onehealthintegration.slims import SlimsConnector


# Step - Create SlimsConnector instance
slims_connector = SlimsConnector(requisition=None, verbose=True)

# Step - Load requisition data
slims_connector.load_requisition_from_file("testdata/requisition_3128114.txt")

# Step - Create SLIMS order
slims_connector.create_slims_order(auto_link_samples=True, ignore_if_order_already_exists=False)

# Step - Update SLIMS order
updated_order_data = {}
slims_connector.update_slims_order(updated_order_data)

# Step - Fetch results only (matching filter(s)) (e.g by container name)
results = slims_connector.fetch_slims_results(container_name="MAF21E31")

# Step - Fetch results only (matching filter(s)) (e.g by test label)
results = slims_connector.fetch_slims_results(test_label="IFN-1 Test")

# Step - Fetch and submit results (matching filter(s))
slims_connector.submit_slims_results_to_1health(container_name="MAF21E31", dry_run=False)
