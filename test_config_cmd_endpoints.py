#!/usr/bin/env python3
"""cx_config endpoint-mapping contracts: inbound/outbound/IVR/queue/
ring-group rules, trunks/phones/contacts infrastructure, and blacklist /
IP blocklist security payloads."""

import unittest
from unittest import mock

from cx_test_support import (
    AUTH_HEADERS,
    CONFIG_CREDS,
    cx_config,
    invoke_config_cmd,
    list_args,
    make_response,
)


class TestConfigCmdRuleEndpoints(unittest.TestCase):
    """Inbound/outbound/IVR/queue/ring-group endpoint mapping."""

    def test_inbound_delete_posts_bulk_endpoint(self):
        # Given inbound rule deletions
        args = list_args(delete=[10, 11], id=None)
        # When inbound-rules --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_inbound_rules, args, "post")
        # Then the bulk inbound delete endpoint receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/InboundRules/Pbx.BulkInboundRulesDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [10, 11]})

    def test_inbound_get_by_id(self):
        # Given a rule id
        args = list_args(delete=None, id=5)
        # When inbound-rules --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_inbound_rules, args)
        # Then the single entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/InboundRules(5)")

    def test_outbound_delete_posts_bulk_numbers_delete(self):
        # Given outbound rule deletions
        args = list_args(delete=[10], id=None)
        # When outbound-rules --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_outbound_rules, args, "post")
        # Then BulkNumbersDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/OutboundRules/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [10]})

    def test_outbound_get_by_id(self):
        # Given a rule id
        args = list_args(delete=None, id=5)
        # When outbound-rules --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_outbound_rules, args)
        # Then the single entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/OutboundRules(5)")

    def test_ivrs_use_receptionists_endpoint(self):
        # Given default list args (local behavior: IVRs live under Receptionists)
        args = list_args(id=None)
        # When ivrs runs
        mock_get = invoke_config_cmd(cx_config.cmd_ivrs, args)
        # Then Receptionists is queried, not CallFlowApps
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Receptionists")

    def test_ivrs_get_by_id_uses_receptionists_entity(self):
        # Given an IVR id
        args = list_args(id=3)
        # When ivrs --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_ivrs, args)
        # Then the Receptionists entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Receptionists(3)")

    def test_queues_get_by_id(self):
        # Given a queue id
        args = list_args(id=3)
        # When queues --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_queues, args)
        # Then the Queues entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Queues(3)")

    def test_ring_groups_get_by_id(self):
        # Given a ring group id
        args = list_args(id=3)
        # When ring-groups --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_ring_groups, args)
        # Then the RingGroups entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/RingGroups(3)")


class TestConfigCmdInfrastructureEndpoints(unittest.TestCase):
    """Trunks/phones/contacts endpoint mapping."""

    def test_trunks_delete_posts_bulk_numbers_delete(self):
        # Given trunk deletions
        args = list_args(delete=[5, 6], id=None)
        # When trunks --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_trunks, args, "post")
        # Then BulkNumbersDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/Trunks/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [5, 6]})

    def test_phones_list_uses_sipdevices_endpoint(self):
        # Given default list args
        args = list_args(delete=None, id=None)
        # When phones runs
        mock_get = invoke_config_cmd(cx_config.cmd_phones, args)
        # Then SipDevices is queried (CLI name differs from API name)
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/SipDevices")

    def test_phones_get_by_id_uses_sipdevices_entity(self):
        # Given a phone id
        args = list_args(delete=None, id=2)
        # When phones --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_phones, args)
        # Then the SipDevices entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/SipDevices(2)")

    def test_phones_delete_posts_bulk_numbers_delete(self):
        # Given phone deletions
        args = list_args(delete=[7, 8], id=None)
        # When phones --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_phones, args, "post")
        # Then SipDevices BulkNumbersDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/SipDevices/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [7, 8]})

    def test_contacts_delete_posts_bulk(self):
        # Given contact deletions
        args = list_args(export=False, delete=[10, 11], id=None)
        # When contacts --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_contacts, args, "post")
        # Then Contacts BulkNumbersDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/Contacts/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [10, 11]})

    def test_contacts_get_by_id(self):
        # Given a contact id
        args = list_args(export=False, delete=None, id=42)
        # When contacts --id runs
        mock_get = invoke_config_cmd(cx_config.cmd_contacts, args)
        # Then the Contacts entity is fetched
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Contacts(42)")

    def test_contacts_export_writes_csv(self):
        # Given an exportable contacts response
        resp = make_response(200)
        resp.content = b"CSVBYTES"
        args = list_args(export=True, delete=None, id=None)
        m_open = mock.mock_open()
        # When contacts --export runs
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", return_value=resp) as mock_get, \
             mock.patch("builtins.open", m_open), \
             mock.patch("builtins.print"):
            cx_config.cmd_contacts(args)
        # Then the export endpoint is hit and bytes land in contacts_export.csv
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Contacts/Pbx.Export")
        m_open.assert_called_once_with("contacts_export.csv", "wb")
        m_open().write.assert_called_once_with(b"CSVBYTES")


class TestConfigCmdSecurityEndpoints(unittest.TestCase):
    """Blacklist / IP blocklist payload contracts."""

    def test_blacklist_add_posts_number_payload(self):
        # Given a number to blacklist
        args = list_args(add="555-0000", delete=None)
        # When blacklist --add runs
        mock_post = invoke_config_cmd(cx_config.cmd_blacklist, args, "post")
        # Then BlackListNumbers receives the number with Id 0
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/BlackListNumbers")
        self.assertEqual(call.kwargs["json"], {"Number": "555-0000", "Id": 0})

    def test_blacklist_delete_posts_bulk(self):
        # Given blacklist deletions
        args = list_args(add=None, delete=[1, 2])
        # When blacklist --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_blacklist, args, "post")
        # Then the bulk endpoint receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/BlackListNumbers/Pbx.BulkNumbersDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [1, 2]})

    def test_ip_blocklist_add_defaults_description_to_empty(self):
        # Given an IP to block with no description
        args = list_args(add="192.168.1.100", description=None, delete=None)
        # When ip-blocklist --add runs
        mock_post = invoke_config_cmd(cx_config.cmd_ip_blocklist, args, "post")
        # Then Blocklist receives the IP with an empty description
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Blocklist")
        self.assertEqual(call.kwargs["json"], {
            "IpAddress": "192.168.1.100", "Id": 0, "Description": ""})

    def test_ip_blocklist_delete_posts_bulk_ips_delete(self):
        # Given blocklist deletions
        args = list_args(add=None, description=None, delete=[5])
        # When ip-blocklist --delete runs
        mock_post = invoke_config_cmd(cx_config.cmd_ip_blocklist, args, "post")
        # Then BulkIpsDelete receives Ids
        call = mock_post.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/Blocklist/Pbx.BulkIpsDelete")
        self.assertEqual(call.kwargs["json"], {"Ids": [5]})


if __name__ == "__main__":
    unittest.main()
