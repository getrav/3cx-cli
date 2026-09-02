#!/usr/bin/env python3
"""cx_config command HTTP contracts: departments, users, roles, live chat,
parking, department members, and who-can-dial reports."""

import types
import unittest
from io import StringIO
from unittest import mock

from cx_test_support import (
    AUTH_HEADERS,
    CONFIG_CREDS,
    cx_config,
    invoke_config_cmd,
    list_args,
    make_response,
)


class TestConfigCmdDepartments(unittest.TestCase):
    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.get")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_name_filter(self, mock_load, mock_hdr, mock_get, mock_hr):
        args = types.SimpleNamespace(top=100, skip=0, odata_filter=None, name="Sales")
        cx_config.cmd_departments(args)
        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["$filter"], "Name eq 'Sales'")


class TestConfigCmdUsers(unittest.TestCase):
    @mock.patch.object(cx_config, "handle_response")
    @mock.patch("requests.get")
    @mock.patch.object(cx_config, "get_headers", return_value={"Authorization": "Bearer t"})
    @mock.patch.object(cx_config, "load_config", return_value={"fqdn": "pbx.example.com"})
    def test_email_filter_lowered(self, mock_load, mock_hdr, mock_get, mock_hr):
        args = types.SimpleNamespace(top=100, skip=0, odata_filter=None,
                                     email="Admin@Example.COM")
        cx_config.cmd_users(args)
        params = mock_get.call_args.kwargs["params"]
        self.assertIn("admin@example.com", params["$filter"])
        self.assertEqual(params["$top"], 1)


class TestConfigCmdDepartmentsHttp(unittest.TestCase):
    def test_list_gets_groups_with_default_odata_params(self):
        # Given default list args
        args = list_args(name=None)
        # When departments are listed
        mock_get = invoke_config_cmd(cx_config.cmd_departments, args)
        # Then Groups is queried with default OData params and auth headers
        call = mock_get.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Groups")
        self.assertEqual(call.kwargs["headers"], AUTH_HEADERS)
        self.assertEqual(call.kwargs["params"],
                         {"$top": 100, "$skip": 0, "$orderby": "Id"})


class TestConfigCmdCreateDepartment(unittest.TestCase):
    def test_posts_full_group_payload(self):
        # Given department creation args with defaults
        args = types.SimpleNamespace(name="Support", language="EN", prompt_set="uuid-1",
                                     timezone="51", sys_from="300", sys_to="319",
                                     trunk_from="340", trunk_to="345",
                                     user_from="320", user_to="339")
        # When the department is created
        mock_post = invoke_config_cmd(cx_config.cmd_create_department, args, "post")
        # Then the full Groups payload is posted
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Groups")
        payload = call.kwargs["json"]
        self.assertEqual(payload["Name"], "Support")
        self.assertEqual(payload["Id"], 0)
        self.assertEqual(payload["Language"], "EN")
        self.assertEqual(payload["PromptSet"], "uuid-1")
        self.assertEqual(payload["TimeZoneId"], "51")
        self.assertTrue(payload["AllowCallService"])
        self.assertTrue(payload["DisableCustomPrompt"])
        self.assertEqual(payload["Props"], {
            "LiveChatMaxCount": 20,
            "PersonalContactsMaxCount": 500,
            "PromptsMaxCount": 10,
            "SystemNumberFrom": "300",
            "SystemNumberTo": "319",
            "TrunkNumberFrom": "340",
            "TrunkNumberTo": "345",
            "UserNumberFrom": "320",
            "UserNumberTo": "339",
        })


class TestConfigCmdUpdateDepartment(unittest.TestCase):
    def test_patch_transcription_mode(self):
        # Given a transcription update for department 29
        args = types.SimpleNamespace(id=29, transcription="Both")
        # When the update runs
        mock_patch = invoke_config_cmd(cx_config.cmd_update_department, args, "patch")
        # Then the entity is patched with the mapped field name
        call = mock_patch.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Groups(29)")
        self.assertEqual(call.kwargs["json"], {"TranscriptionMode": "Both"})

    def test_no_flags_exits_with_error(self):
        # Given no update flags
        args = types.SimpleNamespace(id=29, transcription=None)
        # When the update runs, it exits 1 without any HTTP call
        err = StringIO()
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.patch") as mock_patch, \
             mock.patch("sys.stderr", err):
            with self.assertRaises(SystemExit) as cm:
                cx_config.cmd_update_department(args)
        self.assertEqual(cm.exception.code, 1)
        mock_patch.assert_not_called()
        self.assertIn("--transcription", err.getvalue())


class TestConfigCmdCreateUser(unittest.TestCase):
    def test_posts_user_payload(self):
        # Given user creation args
        args = types.SimpleNamespace(first_name="John", last_name="Doe",
                                     email="j@d.c", password="Pw", extension="201",
                                     language="EN", prompt_set="uuid")
        # When the user is created
        mock_post = invoke_config_cmd(cx_config.cmd_create_user, args, "post")
        # Then the Users payload carries the documented fields
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Users")
        self.assertEqual(call.kwargs["json"], {
            "AccessPassword": "Pw",
            "EmailAddress": "j@d.c",
            "FirstName": "John",
            "LastName": "Doe",
            "Id": 0,
            "Language": "EN",
            "Number": "201",
            "PromptSet": "uuid",
            "SendEmailMissedCalls": True,
            "VMEmailOptions": "Notification",
            "Require2FA": False,
        })


class TestConfigCmdAssignRole(unittest.TestCase):
    def test_patches_user_with_group_role(self):
        # Given a role assignment for user 120 into group 95
        args = types.SimpleNamespace(user_id=120, group_id=95, role="managers")
        # When the role is assigned
        mock_patch = invoke_config_cmd(cx_config.cmd_assign_role, args, "patch")
        # Then the user entity is patched with the nested role payload
        call = mock_patch.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Users(120)")
        self.assertEqual(call.kwargs["json"], {
            "Groups": [{"GroupId": 95, "Rights": {"RoleName": "managers"}}],
            "Id": 120,
        })


class TestConfigCmdLiveChat(unittest.TestCase):
    def test_check_builds_filter_url_without_params(self):
        # Given a link availability check
        args = list_args(check="mychat123")
        # When live-chat --check runs
        mock_get = invoke_config_cmd(cx_config.cmd_live_chat, args)
        # Then the $filter is embedded in the URL with no params dict
        call = mock_get.call_args
        self.assertEqual(call[0][0],
            "https://pbx.example.com/xapi/v1/WebsiteLinks?$filter=Link eq 'mychat123'")
        self.assertNotIn("params", call.kwargs)

    def test_list_gets_websitelinks(self):
        # Given default list args
        args = list_args(check=None)
        # When live-chat lists links
        mock_get = invoke_config_cmd(cx_config.cmd_live_chat, args)
        # Then WebsiteLinks is queried with default OData params
        call = mock_get.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/WebsiteLinks")
        self.assertEqual(call.kwargs["params"]["$top"], 100)


class TestConfigCmdParking(unittest.TestCase):
    def test_create_posts_groups_payload(self):
        # Given a shared parking creation across two groups
        args = list_args(create=True, delete=None, group_ids=[95, 122])
        # When parking is created
        mock_post = invoke_config_cmd(cx_config.cmd_parking, args, "post")
        # Then the Parkings payload lists each group
        call = mock_post.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Parkings")
        self.assertEqual(call.kwargs["json"], {
            "Groups": [{"GroupId": 95}, {"GroupId": 122}], "Id": 0})

    def test_delete_uses_delete_method_on_parking_entity(self):
        # Given a parking deletion
        args = list_args(create=False, delete=126, group_ids=None)
        # When parking is deleted
        mock_del = invoke_config_cmd(cx_config.cmd_parking, args, "delete")
        # Then HTTP DELETE targets the parking entity
        call = mock_del.call_args
        self.assertEqual(call[0][0], "https://pbx.example.com/xapi/v1/Parkings(126)")
        self.assertNotIn("json", call.kwargs)

    def test_list_gets_parkings(self):
        # Given default list args
        args = list_args(create=False, delete=None, group_ids=None)
        # When parking entries are listed
        mock_get = invoke_config_cmd(cx_config.cmd_parking, args)
        # Then Parkings is queried
        self.assertEqual(mock_get.call_args[0][0],
                         "https://pbx.example.com/xapi/v1/Parkings")


class TestConfigCmdDepartmentMembers(unittest.TestCase):
    """department-members user/dept lookup behavior."""

    def _responses(self):
        users = make_response(200, body={"value": [
            {"Number": "100", "FirstName": "A", "LastName": "B", "PrimaryGroupId": 1}]})
        depts = make_response(200, body={"value": [{"Id": 1, "Name": "DEFAULT"}]})
        return [users, depts]

    def test_unknown_user_exits(self):
        # Given a user number that does not exist
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", side_effect=self._responses()), \
             mock.patch("builtins.print"), \
             mock.patch("sys.stderr", StringIO()):
            # When department-members --user runs, it exits 1
            with self.assertRaises(SystemExit) as cm:
                cx_config.cmd_department_members(
                    types.SimpleNamespace(user=999, department=None))
        self.assertEqual(cm.exception.code, 1)

    def test_lists_users_with_department_names(self):
        # Given one user mapped to department 1
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", side_effect=self._responses()), \
             mock.patch("builtins.print") as mock_print:
            # When department-members runs without filters
            cx_config.cmd_department_members(
                types.SimpleNamespace(user=None, department=None))
        # Then the user line resolves the department name
        printed = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("100: A B → DEFAULT", printed)


class TestConfigCmdWhoCanDial(unittest.TestCase):
    """who-can-dial routing report behavior."""

    def _responses(self):
        users = make_response(200, body={"value": [
            {"Number": "100", "FirstName": "A", "LastName": "B", "PrimaryGroupId": 30}]})
        depts = make_response(200, body={"value": [{"Id": 30, "Name": "Sales"}]})
        rules = make_response(200, body={"value": [
            {"Name": "EU", "GroupIds": [30],
             "Routes": [{"TrunkId": 7, "CallerID": "+31"}]}]})
        trunks = make_response(200, body={"value": [{"Id": 7, "Name": "VoipTrunk"}]})
        return [users, depts, rules, trunks]

    def test_unknown_extension_exits(self):
        # Given an extension that does not exist
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", side_effect=self._responses()), \
             mock.patch("builtins.print"), \
             mock.patch("sys.stderr", StringIO()):
            # When who-can-dial --extension runs, it exits 1
            with self.assertRaises(SystemExit) as cm:
                cx_config.cmd_who_can_dial(types.SimpleNamespace(extension=999))
        self.assertEqual(cm.exception.code, 1)

    def test_extension_routing_output(self):
        # Given an extension whose department has an outbound rule
        with mock.patch.object(cx_config, "load_config",
                               return_value=dict(CONFIG_CREDS)), \
             mock.patch.object(cx_config, "get_headers",
                               return_value=dict(AUTH_HEADERS)), \
             mock.patch("requests.get", side_effect=self._responses()), \
             mock.patch("builtins.print") as mock_print:
            # When who-can-dial --extension runs
            cx_config.cmd_who_can_dial(types.SimpleNamespace(extension=100))
        # Then the report names the rule and trunk
        printed = "\n".join(c[0][0] for c in mock_print.call_args_list)
        self.assertIn("CAN DIAL OUT via: EU", printed)
        self.assertIn("VoipTrunk", printed)


if __name__ == "__main__":
    unittest.main()
