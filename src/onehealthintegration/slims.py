import json
import os
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from pprint import pprint
from slims.criteria import conjunction, equals
from slims.slims import Record, Slims
from slims.util import display_field_value
from typing import Any, Dict, Optional

from .utils import make_utc_from_string


class SlimsConnector:

  def __init__(self,
               slims_url: Optional[str] = None,
               slims_username: Optional[str] = None,
               slims_password: Optional[str] = None,
               slims_1health_order_type_lab_code_map: Dict[str, Any] = None,
               slims_1health_content_type_specimen_map: Dict[str, Any] = None,
               requisition: Optional[Dict[str, int]] = None,
               verbose: bool = False):

    if not slims_url:
      # https://dxterity.cloud.us.genohm.com/slimsrest
      slims_url = os.environ.get("slims_url")

    if not slims_username:
      slims_username = os.environ.get("slims_username")

    if not slims_password:
      slims_password = os.environ.get("slims_password")

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

    self.requisition = requisition
    self.verbose = verbose

  def get_order_name_from_requisition_id(self) -> str:

    # determine order name
    order_name = str(self.requisition["id"])
    if os.environ.get("environment_type", "").lower() == "development":
      order_name += " (1health Dev)"

    return order_name

  def create_slims_order(self, auto_link_samples: bool = False) -> None:

    # get matching order type
    order_type_name = self.slims_1health_order_type_lab_code_map.get(
      self.requisition["order"]["tests"][0]["labCode"])
    order_type = self.slims.fetch("OrderType",
                                  equals("rdtp_name", order_type_name))

    if not order_type:
      raise Exception(f'No order type found matching "{order_type_name}"')

    # determine new order data
    order_date = make_utc_from_string(self.requisition["order"]["orderDate"])
    order_name = self.get_order_name_from_requisition_id()

    new_order_data = {
      "ordr_cf_orderName": order_name,
      "ordr_fk_orderType": order_type[0].pk(),
      "ordr_plannedOnDate": order_date.strftime("%m/%d/%Y"),
      "ordr_plannedOnTime": order_date.strftime("%H:%M"),
      "ordr_cf_ofSpecimens": len(self.requisition['samples']),
      "ordr_cf_distributionType":
      "1health"  # TODO: Check for better option / not included in requisition (e.g. Fedex)
    }

    # create new order
    new_order = self.slims.add("Order", new_order_data)

    if self.verbose is True:
      print("Order has been successfully created (barcode below):")
      display_field_value(new_order, ["ordr_barCode"])

    # check to auto link samples to order
    if auto_link_samples is True:
      self.link_samples_to_order(new_order)

  def link_samples_to_order(self, slims_order: Record) -> None:

    for sample in self.requisition['samples']:

      # get matching content type
      content_type_name = self.slims_1health_content_type_specimen_map.get(
        sample["snomedConceptCode"]["name"])
      content_type = self.slims.fetch("ContentType",
                                      equals("cntp_name", content_type_name))

      if not content_type:
        raise Exception(
          f'No content type found matching "{content_type_name}"')

      # determine new content data
      collection_date = make_utc_from_string(sample["collectionDate"])
      kits_df = pd.DataFrame(self.requisition["kits"])

      matching_inbound_shipment = kits_df[
        kits_df.kitKey == sample["collectionBarcode"]].inboundShipment
      if not matching_inbound_shipment.empty and not pd.isnull(
          matching_inbound_shipment).all():
        tracking_number = matching_inbound_shipment[0].get(
          "masterTrackingNumber")
        distribution_type = "1health"  # TODO: Check for better option / not included in requisition (e.g. Fedex)
      else:
        tracking_number = None
        distribution_type = None

      test_name = self.requisition["order"]["tests"][0]["name"]
      status = self.slims.fetch("Status", equals("stts_name", "Received"))

      new_sample_data = {
        "cntn_fk_contentType": content_type[0].pk(),
        "cntn_cf_test": test_name,
        "cntn_cf_tracking": tracking_number,
        "cntn_barCode": sample["collectionBarcode"],
        "cntn_cf_containerName": sample["collectionBarcode"],
        "cntn_id": sample["collectionBarcode"],
        "cntn_collectionDate": int(collection_date.timestamp() * 1000),
        "cntn_cf_distributionType": distribution_type,
        "cntn_fk_status": status[0].pk(),
        "cntn_status": None,
        "cntp_slimsGeneratesBarcode": False
      }
      new_sample = self.slims.add("Content", new_sample_data)
      self.slims.add("OrderContent", {
        'rdcn_fk_order': slims_order.pk(),
        'rdcn_fk_content': new_sample.pk()
      })

      if self.verbose is True:
        print(
          "Content has been successfully created (barcode below) and linked to order:"
        )
        display_field_value(new_sample, ["cntn_barCode"])

  def update_slims_order(self, updated_order_data: Dict[str, Any]) -> None:

    # get order name
    order_name = self.get_order_name_from_requisition_id()

    # fetch order
    order = self.slims.fetch("Order", equals("ordr_cf_orderName", order_name))

    if not order:
      raise Exception(f'No order matching name "{order_name}"')
    elif len(order) > 1:
      raise Exception(
        f'More than one order found matching name "{order_name}"')

    updated_order = order[0].update(updated_order_data)

    if self.verbose is True:
      print("Order has been successfully updated (barcode below):")
      display_field_value(updated_order, ["ordr_barCode"])
