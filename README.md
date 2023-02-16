# 1health-SLIMS-connector
Package and supporting functions for:
* Creating, linking samples, and updating orders in SLIMS using requisition data from 1health
* Pushing results from SLIMS to 1health


## Requirements
Python >=3.9

## Installation

To use the onehealthintegration package, follow these steps:

1. Clone the GitHub repository:

```
https://github.com/ayoisio/1health-slims-connector.git
```

2. Navigate to the cloned directory:

```
cd 1health-slims-connector
```

3. Run the setup script to install the package:

```
python setup.py install
```

* This will install the onehealthintegration package and its dependencies.

4. Set environmental variables (optional): 
* slims_username
* slims_password
* slims_url (i.e, https://dxterity.cloud.us.genohm.com/slimsrest)
* environment_type (i.e., Development, Production) (case insensitive)

If slims_username, slims_password, and slims_url are not provided as environmental variables, they can be passed in as parameters to the [SlimsConnector](src/onehealthintegration/slims.py#L15) class. If environment_type is not provided as an environmental variable, development mode will be assumed by default.

4. You can now import the onehealthintegration package:
```
import onehealthintegration
```

That's it! You're now ready to use the onehealthintegration package to sync updates between 1health and SLIMS

5. Got to the [cookbook](/cookbook) directory for example integration workflows

* [New Order Flow](/cookbook/new_order_flow.py)

