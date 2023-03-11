import json
import datetime as dt
import os
import requests
import pandas as pd
from dateutil.relativedelta import relativedelta
from pprint import pprint
from slims.criteria import *
from slims.slims import Record, Slims
from slims.util import display_field_value
from typing import Any, Dict, List, Optional, Union

from .utils import make_utc_from_string


class SlimsConnector:

    def __init__(self,
                 slims_url: Optional[str] = None,
                 slims_username: Optional[str] = None,
                 slims_password: Optional[str] = None,
                 slims_1health_order_type_lab_code_map: Dict[str, Any] = None,
                 slims_1health_content_type_specimen_map: Dict[str, Any] = None,
                 onehealth_url: Optional[str] = None,
                 onehealth_api_key: Optional[str] = None,
                 requisition: Optional[Dict[str, int]] = None,
                 development_flag: str = " (1health Dev)",
                 verbose: bool = False):
        """
        Initializes a new instance of SlimsConnector class

        Args:
            slims_url: SLIMS REST API base URL (e.g. https://dxterity.cloud.us.genohm.com/slimsrest)
            slims_username: SLIMS username
            slims_password: SLIMS password
            slims_1health_order_type_lab_code_map: Dictionary that maps 1health lab code to SLIMS order type
            slims_1health_content_type_specimen_map: Dictionary that maps 1health specimen code to SLIMS content type
            onehealth_url: 1health REST API base URL (e.g. https://demo.1health.io)
            onehealth_api_key: 1health API Key
            requisition: 1health order requisition data
            development_flag: Development or production mode
            verbose: Verbosity

        Returns:
            None
        """

        if not slims_url:
            slims_url = os.environ.get("slims_url")
        else:
            self.slims_url = self.slims_url

        if not slims_username:
            slims_username = os.environ.get("slims_username")
        else:
            self.slims_username = slims_username

        if not slims_password:
            slims_password = os.environ.get("slims_password")

        if not onehealth_url:
            self.onehealth_url = os.environ.get("onehealth_url")
        else:
            self.onehealth_url = onehealth_url

        if self.onehealth_url.endswith('/'):
            self.onehealth_url = self.onehealth_url[:-1]

        if not onehealth_api_key:
            self.onehealth_api_key = os.environ.get("1health_api_key")
        else:
            self.onehealth_api_key = onehealth_api_key

        # define SLIMS instance
        self.slims = Slims("slims", slims_url, slims_username, slims_password)

        # define SLIMS-1health order type to lab code map
        if slims_1health_order_type_lab_code_map is None:
            self.slims_1health_order_type_lab_code_map = {
                "1001": "IFN-1 Test",
                "1002": "IFN-1 Test",
                "2001": "SARS-CoV-2 Test",
                "2002": "SARS-CoV-2 Test",
                "2003": "SARS-CoV-2 Test"
            }
        else:
            self.slims_1health_order_type_lab_code_map = {}

        # define SLIMS-1health order type to lab code map
        if slims_1health_content_type_specimen_map is None:
            self.slims_1health_content_type_specimen_map = {
                "119297000 - Blood specimen (specimen)": "Blood Sample",
                "119342007 - Saliva specimen (specimen)": "Saliva Sample"
            }
        else:
            self.slims_1health_content_type_specimen_map = {}

        self.development_flag = development_flag
        self.requisition = requisition
        self.verbose = verbose

    def get_clean_1health_order_id(self, order_id: str) -> str:
        """
        Get clean 1health order ID

        Args:
            order_id: SLIMS order name / 1health order ID

        Returns:
            order_id
        """

        if os.environ.get("environment_type", "").lower() == "development":
            order_id = order_id.replace(self.development_flag, "")

        return order_id

    def load_requisition_from_file(self, file_path: str) -> None:
        """
        Load requisition from file

        Args:
            file_path: file path (e.g. /home/requisition.txt)

        Returns:
            None
        """

        # Read requisition file (json format)
        with open(file_path) as requisition_file:
            requisition = json.load(requisition_file)

        self.requisition = requisition

    def get_slims_formatted_order_name(self, order_name: str) -> str:
        """
        Get SLIMS formatted order name

        Args:
            order_name: original name to formatted (e.g 3128680)

        Returns:
            order_name
        """

        if os.environ.get("environment_type", "").lower() == "development":
            order_name += self.development_flag

        return order_name

    def create_slims_order(self, auto_link_samples: bool = False, ignore_if_order_already_exists: bool = False) -> None:
        """
        Create SLIMS order

        Args:
            auto_link_samples: Check to link samples after creating order in SLIMS
            ignore_if_order_already_exists: Check to ignore order creation if order (based on order name) already exists
        Returns:
            None
        """

        # determine order name
        order_name = str(self.requisition["id"])
        slims_formatted_order_name = self.get_slims_formatted_order_name(order_name)

        # get matching order type
        lab_code = self.requisition["order"]["tests"][0]["labCode"]
        order_type_name = self.slims_1health_order_type_lab_code_map.get(lab_code)
        order_type = self.slims.fetch("OrderType", equals("rdtp_name", order_type_name))[0]

        # check for matching order
        matching_orders = self.slims.fetch("Order", is_one_of("ordr_cf_orderName", [order_name, slims_formatted_order_name]))

        if matching_orders and not ignore_if_order_already_exists:
          raise Exception(f'Order "{slims_formatted_order_name}" already exists')
      
        if not order_type:
            raise Exception(f'No order type found matching "{order_type_name}"')

        # determine new order data
        order_date = make_utc_from_string(self.requisition["order"]["orderDate"])

        new_order_data = {
            "ordr_cf_orderName": slims_formatted_order_name,
            "ordr_fk_orderType": order_type.pk(),
            "ordr_plannedOnDate": order_date.strftime("%m/%d/%Y"),
            "ordr_plannedOnTime": order_date.strftime("%H:%M"),
            "ordr_cf_ofSpecimens": len(self.requisition['samples']),
            "ordr_cf_distributionType": "1health"
            # TODO: Check for better option / not included in requisition (e.g. Fedex)
        }

        # create new order
        new_order = self.slims.add("Order", new_order_data)

        if self.verbose:
            print("Order has been successfully created (barcode below):")
            display_field_value(new_order, ["ordr_barCode"])

        # check to auto link samples to order
        if auto_link_samples:
            self.link_samples_to_order(new_order)

    def link_samples_to_order(self,
                              slims_order: Record,
                              default_status: str = "Received",
                              default_group: str = "Clinical Lab User") -> None:
        """
        Link samples to order

        Args:
            slims_order: SLIMS order record
            default_status: Default status label set to each linked sample(s) status in SLIMS
            default_group: Default group label set to each linked sample(s) status in SLIMS

        Returns:
            None
        """

        # get matching status
        status = self.slims.fetch("Status", equals("stts_name", default_status))[0]

        # get matching group
        group = self.slims.fetch("Groups", equals("grps_groupName", default_group))[0]

        for sample in self.requisition['samples']:

            # get matching content type
            content_type_name = self.slims_1health_content_type_specimen_map.get(sample["snomedConceptCode"]["name"])
            content_type = self.slims.fetch("ContentType", equals("cntp_name", content_type_name))[0]

            if not content_type:
                raise Exception(f'No content type found matching "{content_type_name}"')

            # determine new content data
            collection_date = make_utc_from_string(sample["collectionDate"])
            kits_df = pd.DataFrame(self.requisition["kits"])

            tracking_number = None
            distribution_type = None
            if "kitKey" in kits_df:
              matching_inbound_shipment = kits_df[kits_df.kitKey == sample["collectionBarcode"]].inboundShipment
              if not matching_inbound_shipment.empty and not pd.isnull(matching_inbound_shipment).all():
                  tracking_number = matching_inbound_shipment[0].get("masterTrackingNumber")
                  distribution_type = "1health"  # TODO: Check for better option / not included in requisition (e.g. Fedex)

            test_name = self.requisition["order"]["tests"][0]["name"]

            new_sample_data = {
                "cntn_fk_contentType": content_type.pk(),
                "cntn_cf_test": test_name,
                "cntn_cf_tracking": tracking_number,
                "cntn_cf_containerName": sample["collectionBarcode"],
                "cntn_id": sample["collectionBarcode"],
                "cntn_barCode": sample["collectionBarcode"],
                "cntn_collectionDate": int(collection_date.timestamp() * 1000),
                "cntn_cf_distributionType": distribution_type,
                "cntn_fk_status": status.pk(),
                "cntn_status": None,
                "cntn_fk_group": group.pk(),
                "cntp_useBarcodeAsId": False,
                "cntp_slimsGeneratesBarcode": False,
            }
            new_sample = self.slims.add("Content", new_sample_data)
            self.slims.add("OrderContent", {
                'rdcn_fk_order': slims_order.pk(),
                'rdcn_fk_content': new_sample.pk()
            })

            if self.verbose:
                print(
                    "Content has been successfully created (barcode below) and linked to order:"
                )
                display_field_value(new_sample, ["cntn_cf_containerName", "cntn_barCode"])

    def update_slims_order(self,
                           updated_order_data: Optional[dict],
                           order_name: Optional[str] = None,
                           use_requisition_order_id: bool = False) -> None:
        """
        Update SLIMS order

        Args:
            updated_order_data: Dictionary with updated order data
            order_name: SLIMS order name to be updated
            use_requisition_order_id: Check to use requisition order ID

        Returns:
            None
        """

        if not order_name and not use_requisition_order_id:
            raise Exception("Order name must be specified or use requisition order ID must be set to True")
        elif order_name and use_requisition_order_id:
            raise Exception("Cannot specify both Order ID and use of requisition order ID")
        elif use_requisition_order_id:
            # get order name from requisition ID
            order_name = self.get_slims_formatted_order_name(str(self.requisition["id"]))

        # fetch matching orders
        matching_orders = self.slims.fetch("Order", equals("ordr_cf_orderName", order_name))

        if not matching_orders:
            raise Exception(f'No order matching name "{order_name}"')
        elif len(matching_orders) > 1:
            raise Exception(
                f'More than one order found matching name "{order_name}"')

        updated_order = matching_orders[0].update(updated_order_data)

        if self.verbose:
            print("Order has been successfully updated (barcode below):")
            display_field_value(updated_order, ["ordr_cf_orderName", "ordr_barCode"])

    def fetch_slims_results(self,
                            result_status: Optional[str] = "Validated",
                            order_name: Optional[str] = None,
                            container_id: Optional[str] = None,
                            container_name: Optional[str] = None,
                            test_label: Optional[str] = None,
                            at_before_timestamp: Union[str, dt.datetime] = None,
                            at_after_timestamp: Union[str, dt.datetime] = None,
                            tz: str = None) -> List[Record]:
        """
        Fetch SLIMS results with optional result filters

        Args:
            result_status: Result status (e.g. Pending, Verified, Validated)
            order_name: SLIMS order name
            container_id: SLIMS generated sample barcode (e.g. PRO00000079, PK of SLIMS Content table)
            container_name: 1health sample collection barcode  (e.g. 9cd51121, requisition.samples[].collectionBarcode)
            test_label: Test name (e.g. IFN-1 Test)
            at_before_timestamp: At or before this timestamp (e.g. 2023-03-01 19:26:04 or March 1st, 2023)
            at_after_timestamp: At or after this timestamp (e.g. 2023-03-01 19:26:04 or March 1st, 2023)
            tz: Time zone (e.g. America/Los_Angeles, localize at_[before,after]_timestamp(s) to a non-UTC time zone)

        Returns:
            results
        """

        # define result status filter
        result_status_filter = conjunction()

        # result status label filter
        if result_status:
            result_status_filter = result_status_filter.add(equals("stts_name", result_status))

        # at or before timestamp filter
        if at_before_timestamp:
            at_before_timestamp = make_utc_from_string(str(at_before_timestamp), tz=tz)
            at_before_timestamp_int = int(at_before_timestamp.timestamp() * 1000)
            result_status_filter = result_status_filter.add(
                less_than_or_equal("rslt_modifiedOn", at_before_timestamp_int))

        # at or after timestamp filter
        if at_after_timestamp:
            at_after_timestamp = make_utc_from_string(str(at_after_timestamp), tz=tz)
            at_after_timestamp_int = int(at_after_timestamp.timestamp() * 1000)
            result_status_filter = result_status_filter.add(
                greater_than_or_equal("rslt_modifiedOn", at_after_timestamp_int))

        # order name filter
        if order_name:
            # get slims formatted order name
            slims_formatted_order_name = self.get_slims_formatted_order_name(order_name)

            # get order that matches raw or slims formatted order name
            orders = self.slims.fetch("Order", is_one_of("ordr_cf_orderName", [order_name, slims_formatted_order_name]))
            order_pk_list = list(map(lambda order: order.pk(), orders))
            order_contents = self.slims.fetch("OrderContent", is_one_of("rdcn_fk_order", order_pk_list))
            content_pk_list = list(map(lambda content: content.rdcn_fk_content.value, order_contents))
        else:
            content_pk_list = []

        # content container id / container name filter
        filter_contents = False
        content_filter = conjunction()
        if container_id:
            content_filter = content_filter.add(equals("cntn_id", container_id))
            filter_contents = True

        if container_name:
            content_filter = content_filter.add(equals("cntn_cf_containerName", container_name))
            filter_contents = True

        if filter_contents:
            contents = self.slims.fetch("Content", content_filter)
            fc_content_pk_list = list(map(lambda content: content.pk(), contents))
            content_pk_list.extend(fc_content_pk_list)
            content_pk_list = list(set(content_pk_list))

        if content_pk_list:
            result_status_filter = result_status_filter.add(is_one_of("rslt_fk_content", content_pk_list))

        # test label filter
        if test_label:
            result_status_filter = result_status_filter.add(equals("test_label", test_label))

        # get results matching filter
        results = self.slims.fetch("Result", result_status_filter)

        if self.verbose:
            print(f"{len(results)} result(s) found matching filters")

        return results

    def submit_slims_results_to_1health(self,
                                        order_name: Optional[str] = None,
                                        container_id: Optional[str] = None,
                                        container_name: Optional[str] = None,
                                        test_label: Optional[str] = None,
                                        accessioning_test_label: str = "Hamilton Accessioning",
                                        at_before_timestamp: Union[str, dt.datetime] = None,
                                        at_after_timestamp: Union[str, dt.datetime] = None,
                                        tz: str = None,
                                        dry_run: bool = False) -> None:
        """
        Submit SLIMS results to 1health with optional result filters

        Args:
            order_name: SLIMS order name
            container_id: SLIMS generated sample barcode (e.g. PRO00000079, PK of SLIMS Content table)
            container_name: 1health sample collection barcode  (e.g. 9cd51121, requisition.samples[].collectionBarcode)
            test_label: Test name (e.g. IFN-1 Test)
            accessioning_test_label: The plate/method used to accession the samples (e.g. Hamilton Accessioning)
            at_before_timestamp: At or before this timestamp (e.g. 2023-03-01 19:26:04 or March 1st, 2023)
            at_after_timestamp: At or after this timestamp (e.g. 2023-03-01 19:26:04 or March 1st, 2023)
            tz: Time zone (e.g. America/Los_Angeles, localize at_[before,after]_timestamp(s) to a non-UTC time zone)
            dry_run: If false, generate result payload and submit to 1health. If true, only generate result payload
                     (and print payload if verbose is True). Useful for running tests and printing payloads to
                     console before submitting results.

        Returns:
            None
        """

        # fetch SLIMS results
        results = self.fetch_slims_results(
            result_status="Validated",
            order_name=order_name,
            container_id=container_id,
            container_name=container_name,
            test_label=test_label,
            at_before_timestamp=at_before_timestamp,
            at_after_timestamp=at_after_timestamp,
            tz=tz)

        for result in results:
            # get matching order and order content
            content = self.slims.fetch("Content", equals("cntn_pk", result.rslt_fk_content.value))[0]
            order_content = self.slims.fetch("OrderContent", equals("rdcn_fk_content", result.rslt_fk_content.value))

            # get matching order
            if order_content:
                order_content = order_content[0]
                order = self.slims.fetch("Order", equals("ordr_pk", order_content.rdcn_fk_order.value))[0]
            else:
                order = None

            # get matching test and result status
            test = self.slims.fetch("Test", equals("test_pk", result.rslt_fk_test.value))[0]
            result_status = self.slims.fetch("Status", equals("stts_pk", result.rslt_fk_status.value))[0]

            # get accession date
            accession_result_filter = conjunction().add(equals("rslt_fk_content", content.pk()))
            accession_result_filter = accession_result_filter.add(equals("test_label", accessioning_test_label))
            accession_result = self.slims.fetch("Result", accession_result_filter)

            if accession_result:
                accession_date = accession_result[0].rslt_createdOn.value
                accession_date = dt.datetime.utcfromtimestamp(accession_date / 1000).strftime("%Y-%m-%dT%H:%M:%S.%f")
            else:
                accession_date = None

            # determine processed date
            pr_date = dt.datetime.utcfromtimestamp(result.rslt_modifiedOn.value / 1000).strftime("%Y-%m-%dT%H:%M:%S.%f")

            # create 1health test result payload
            onehealth_test_result = {
                "accessionDate": accession_date,
                "processedDate": pr_date,
                "results": [
                    {
                        "name": result.test_label.value,
                        "resultType": result.test_label.value,
                        "notes": result_status.stts_name.value,
                        "value": str(result.rslt_value.value)
                    }
                ]
            }

            if self.verbose:
                print(f'1health test result for {content.cntn_cf_containerName.value} in order "{order.ordr_cf_orderName.value}":')
                pprint(onehealth_test_result)

            # submit result to 1health
            if not dry_run:
                order_id = order.ordr_cf_orderName.value
                self.submit_result_to_1health(order_id, onehealth_test_result)

    def submit_result_to_1health(self, order_id: str, test_result: dict) -> None:
        """
        Submit result to 1health

        Args:
            order_id: SLIMS order name or 1health order ID (e.g. 3128114)
            test_result: Dictionary with 1health result keys and values

        Returns:
            None
        """

        # get clean 1health order ID
        order_id = self.get_clean_1health_order_id(order_id)

        # define upsert result 1health endpoint
        upsert_result_url = self.onehealth_url
        upsert_result_url += f"/api/v2/health/order/{order_id}/test-result"

        # submit result
        headers = {"Authorization": f"Bearer {self.onehealth_api_key}"}
        response = requests.post(upsert_result_url, json=test_result, headers=headers)

        if not response.ok:
            raise Exception(f"Error occurred while submitting result:\n {response.text}")

        if self.verbose:
            print(f'Result was successfully submitted for "{order_id}" ({response.status_code})')
